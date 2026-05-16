#!/usr/bin/env python3
"""
Intake Processor — Routes files from staging to correct destinations.

Pipeline:
  1. Convert non-markdown files (.txt, .pdf, .docx) → .md FIRST
  2. Standardize YAML frontmatter on every file
  3. Route file to destination directory based on metadata + filename patterns
  4. Archive original in processed/

Usage:
  python3 process_intake.py              # Process all files
  python3 process_intake.py --dry-run    # Show what would happen
  python3 process_intake.py --history    # Show import history
"""
import os
import sys
import json
import shutil
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger("intake.process")
import yaml
import re
import json5

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "engine"))
from sync.frontmatter_apply import standardize_single_file, read_file
from extractors.converters import convert_to_markdown, CONVERTERS

INTAKE_DIR = Path(__file__).parent
STAGING_DIR = INTAKE_DIR / "staging"
PROCESSED_DIR = INTAKE_DIR / "processed"
PROJECT_ROOT = INTAKE_DIR.parent
LOG_FILE = INTAKE_DIR / "intake.log"

# Create directories if they don't exist
STAGING_DIR.mkdir(exist_ok=True)
PROCESSED_DIR.mkdir(exist_ok=True)

# Load routing config
ROUTING_CONFIG_PATH = PROJECT_ROOT / "engine" / "config" / "intake_routing.json5"
if ROUTING_CONFIG_PATH.exists():
    with open(ROUTING_CONFIG_PATH) as f:
        _ROUTING = json5.load(f)
else:
    _ROUTING = {}
    print(f"Warning: Routing config not found at {ROUTING_CONFIG_PATH}")

_DEST_DIRS = {
    "command_inbox": PROJECT_ROOT / "command" / "inbox",
    "command_finances": PROJECT_ROOT / "command" / "finances",
    "command_tasks": PROJECT_ROOT / "command" / "tasks",
    "knowledge_articles": PROJECT_ROOT / "knowledge" / "articles",
    "knowledge_notes": PROJECT_ROOT / "knowledge" / "notes",
    "knowledge_references": PROJECT_ROOT / "knowledge" / "references",
    "knowledge_projects": PROJECT_ROOT / "knowledge" / "projects",
    "self_goals": PROJECT_ROOT / "self" / "goals",
    "self_relationships": PROJECT_ROOT / "self" / "relationships",
    "self_profile": PROJECT_ROOT / "self" / "profile",
}


def log_import(filename: str, destination: str, status: str, metadata: dict = None):
    """Log import to audit trail."""
    # Sanitize metadata for JSON serialization
    clean_metadata = {}
    if metadata:
        for k, v in metadata.items():
            if isinstance(v, (str, int, float, bool, type(None))):
                clean_metadata[k] = v
            elif isinstance(v, (list, tuple)):
                clean_metadata[k] = [str(x) for x in v]
            else:
                clean_metadata[k] = str(v)
    
    entry = {
        "timestamp": datetime.now().isoformat(),
        "filename": filename,
        "destination": str(destination),
        "status": status,
        "metadata": clean_metadata
    }
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


def extract_frontmatter(file_path: Path) -> dict:
    """Extract YAML frontmatter from markdown file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 2:
                frontmatter = yaml.safe_load(parts[1])
                return frontmatter or {}
    except Exception as e:
        print(f"Warning: Could not parse frontmatter in {file_path}: {e}")
    
    return {}


def is_daily_note(file_path: Path, relative_source: Path) -> bool:
    """Check if this is a daily note based on path and name."""
    folder_routes = _ROUTING.get("folder_routes", [])
    for fr in folder_routes:
        if fr.get("pattern") in str(relative_source):
            dest_key = fr.get("destination", "")
            if dest_key and _DEST_DIRS.get(dest_key) == _DEST_DIRS.get("command_inbox"):
                return True

    date_patterns = _ROUTING.get("date_patterns", [
        r'^\d{4}-\d{2}-\d{2}',
        r'^\d{4}-\d{1,2}-\d{1,2}',
        r'^[A-Za-z]{3}\s\d{1,2}',
        r'^\d{1,2}h\d{2}',
    ])

    for pattern in date_patterns:
        if re.match(pattern, file_path.stem):
            return True

    return False


def _match_tags(tags: list, tag_routes: list) -> Path | None:
    for route in tag_routes:
        route_tags = route.get("tags", [])
        if any(t in tags for t in route_tags):
            dest_key = route.get("destination")
            if dest_key and dest_key in _DEST_DIRS:
                return _DEST_DIRS[dest_key]
    return None


def _match_folder(source_str: str, folder_routes: list) -> Path | None:
    for route in folder_routes:
        if route.get("pattern") in source_str:
            dest_key = route.get("destination")
            if dest_key and dest_key in _DEST_DIRS:
                return _DEST_DIRS[dest_key]
    return None


def _match_filename(filename: str, filename_routes: list) -> Path | None:
    for route in filename_routes:
        prefix = route.get("prefix", "")
        if filename.startswith(prefix):
            dest_key = route.get("destination")
            if dest_key and dest_key in _DEST_DIRS:
                return _DEST_DIRS[dest_key]
    return None


def _resolve_dest(dest_key: str) -> Path | None:
    return _DEST_DIRS.get(dest_key)


def determine_destination(file_path: Path, relative_source: Path, frontmatter: dict = None) -> Path:
    """Determine destination using routing config from engine/config/intake_routing.json."""
    routing = _ROUTING
    frontmatter = frontmatter or {}
    filename = file_path.name.lower()
    source_str = str(relative_source)

    # 1. Route by standardized type field (set by frontmatter_apply)
    file_type = (frontmatter.get("type") or "").lower()
    type_routes = routing.get("type_routes", {})
    if file_type in type_routes:
        dest = _resolve_dest(type_routes[file_type])
        if dest:
            return dest

    # 2. Route by frontmatter tags
    tags = frontmatter.get("tags", [])
    if isinstance(tags, str):
        tags = [tags]
    result = _match_tags(tags, routing.get("tag_routes", []))
    if result:
        return result

    # 3. Route by source folder structure
    result = _match_folder(source_str, routing.get("folder_routes", []))
    if result:
        return result

    # 4. Route by filename conventions
    result = _match_filename(filename, routing.get("filename_routes", []))
    if result:
        return result

    # 5. Check financial keywords in source path
    source_lower = source_str.lower()
    for kw in routing.get("financial_keywords", []):
        if kw.lower() in source_lower:
            dest = _resolve_dest("command_finances")
            if dest:
                return dest

    # 6. Default based on Daily Notes pattern
    if is_daily_note(file_path, relative_source):
        dest = _resolve_dest("command_inbox")
        if dest:
            return dest

    # 7. Default fallback
    default_key = routing.get("default_destination", "knowledge_notes")
    return _resolve_dest(default_key) or PROJECT_ROOT / "knowledge" / "notes"


def process_file(file_path: Path, staging_relative: Path, dry_run: bool = False) -> bool:
    """Process a single file from staging."""
    if not file_path.exists():
        print(f"  ✗ {staging_relative}: Not found")
        log_import(str(staging_relative), "N/A", "ERROR", {"reason": "not_found"})
        return False

    ext = file_path.suffix.lower()
    original_path = file_path
    conversion_metadata: dict = {}

    # Step 0: Convert non-markdown formats to .md BEFORE any other processing
    if ext in CONVERTERS:
        try:
            md_path, conversion_metadata = convert_to_markdown(file_path)
            file_path = md_path  # All downstream logic now operates on the .md
            staging_relative = staging_relative.with_suffix(".md")
        except Exception as e:
            print(f"  ✗ {staging_relative}: Conversion failed — {e}")
            log_import(str(staging_relative), "N/A", "CONVERSION_ERROR", {"error": str(e)})
            return False

    # Step 1: Standardize YAML frontmatter
    metadata = dict(conversion_metadata)
    if file_path.suffix == ".md":
        try:
            frontmatter_meta = standardize_single_file(file_path)
            metadata.update(frontmatter_meta)
        except Exception as e:
            print(f"  ⚠ Frontmatter error: {e}")

    # Step 2: Route to destination — use .md name if we converted
    dest_name = file_path.name
    dest_dir = determine_destination(file_path, staging_relative, metadata)
    dest_path = dest_dir / dest_name

    print(f"  → {staging_relative}", end="")
    if ext in CONVERTERS:
        print(f" [.{ext.lstrip('.')}→md]", end="")
    print()
    print(f"     → {dest_path.relative_to(PROJECT_ROOT)}", end="")

    file_exists_at_dest = dest_path.exists()
    if file_exists_at_dest:
        print(f" [exists, skipping copy]", end="")

    if dry_run:
        print(f" [DRY RUN]")
        log_import(str(staging_relative), str(dest_path), "DRY_RUN", metadata)
        return True

    print()

    dest_dir.mkdir(parents=True, exist_ok=True)

    if not file_exists_at_dest:
        try:
            shutil.copy2(file_path, dest_path)
        except Exception as e:
            print(f"     ✗ Error: {e}")
            log_import(str(staging_relative), str(dest_path), "ERROR", {"error": str(e)})
            return False

    # Archive ORIGINAL file (the raw input, not the converted .md)
    try:
        archive_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{original_path.name}"
        shutil.copy2(original_path, PROCESSED_DIR / archive_name)
    except Exception as e:
        print(f"     ⚠ Warning: Could not archive {original_path.name}: {e}")

    status = "ALREADY_EXISTS" if file_exists_at_dest else "SUCCESS"
    log_import(str(staging_relative), str(dest_path), status, metadata)

    return True


def process_all(dry_run: bool = False):
    """Process all files in staging recursively."""
    # Collect all files recursively
    all_files = []
    for root, dirs, files in os.walk(STAGING_DIR):
        for file in files:
            if file.startswith('.'):
                continue
            file_path = Path(root) / file
            staging_relative = file_path.relative_to(STAGING_DIR)
            all_files.append((file_path, staging_relative))
    
    if not all_files:
        print("No files in staging directory.")
        return
    
    print(f"\nProcessing {len(all_files)} file(s)...")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}\n")
    
    success = 0
    processed_files = []
    converted_md_files = set()
    for file_path, staging_relative in all_files:
        if not file_path.is_file():
            continue
        ext = file_path.suffix.lower()
        if ext not in {".md"} | set(CONVERTERS.keys()):
            continue
        if ext in CONVERTERS:
            converted_md_files.add(file_path.with_suffix(".md"))
        if process_file(file_path, staging_relative, dry_run):
            success += 1
            processed_files.append(file_path)
    
    print(f"\n✓ Processed {success}/{len(all_files)} files")
    
    if not dry_run:
        print(f"  Log: {LOG_FILE}")
        
        # Remove processed files from staging
        for file_path in processed_files:
            try:
                file_path.unlink()
            except Exception as e:
                print(f"  ⚠ Warning: Could not delete {file_path.name}: {e}")
        for md_file in converted_md_files:
            try:
                if md_file.exists():
                    md_file.unlink()
            except Exception as e:
                print(f"  ⚠ Warning: Could not delete {md_file.name}: {e}")
        
        # Remove empty staging directories
        for root, dirs, files in os.walk(STAGING_DIR, topdown=False):
            for d in dirs:
                try:
                    (Path(root) / d).rmdir()  # Only works if empty
                except OSError:
                    logger.debug("Directory not empty, skipping: %s", Path(root) / d)
        
        # Final count of remaining files
        remaining = 0
        for root, dirs, files in os.walk(STAGING_DIR):
            for f in files:
                if not f.startswith('.'):
                    remaining += 1
        
        if remaining == 0:
            print(f"  ✓ Staging cleaned up (0 files remaining)")
        else:
            print(f"  ⚠ {remaining} files still in staging")


def show_history(limit: int = 20):
    """Show import history."""
    if not LOG_FILE.exists():
        print("No import history yet.")
        return
    
    print(f"\nRecent imports (last {limit}):\n")
    
    with open(LOG_FILE, 'r') as f:
        lines = f.readlines()
    
    for line in lines[-limit:]:
        try:
            entry = json.loads(line)
            ts = entry.get("timestamp", "?")[-8:]  # Last 8 chars (time only)
            status = entry.get("status", "?")
            filename = entry.get("filename", "?")
            dest = entry.get("destination", "?").split("/")[-1]  # Last part of path
            
            status_symbol = "✓" if status == "SUCCESS" else "✗" if status.startswith("ERROR") else "→"
            print(f"  {status_symbol} {ts}  {filename:40} → {dest:20} ({status})")
        except Exception as e:
            logger.debug("Failed to parse import history entry: %s", e)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Process files from staging into project")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen")
    parser.add_argument("--history", action="store_true", help="Show import history")
    parser.add_argument("--limit", type=int, default=20, help="History limit")
    
    args = parser.parse_args()
    
    if args.history:
        show_history(args.limit)
    else:
        process_all(dry_run=args.dry_run)
