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
from pathlib import Path
from datetime import datetime
import yaml
import re

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "engine"))
from frontmatter_apply import standardize_single_file, read_file
from converters import convert_to_markdown, CONVERTERS

INTAKE_DIR = Path(__file__).parent
STAGING_DIR = INTAKE_DIR / "staging"
PROCESSED_DIR = INTAKE_DIR / "processed"
PROJECT_ROOT = INTAKE_DIR.parent
KNOWLEDGE_DIR = PROJECT_ROOT / "knowledge"
COMMAND_DIR = PROJECT_ROOT / "command"
SELF_DIR = PROJECT_ROOT / "self"
LOG_FILE = INTAKE_DIR / "intake.log"

# Create directories if they don't exist
STAGING_DIR.mkdir(exist_ok=True)
PROCESSED_DIR.mkdir(exist_ok=True)


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
    if "Daily Notes" in str(relative_source):
        return True
    
    # Check for date patterns in filename
    date_patterns = [
        r'^\d{4}-\d{2}-\d{2}',  # 2025-01-05
        r'^\d{4}-\d{1,2}-\d{1,2}',  # 2025-1-5
        r'^[A-Za-z]{3}\s\d{1,2}',  # Jan 5
        r'^\d{1,2}h\d{2}',  # 17h 50
    ]
    
    for pattern in date_patterns:
        if re.match(pattern, file_path.stem):
            return True
    
    return False


def determine_destination(file_path: Path, relative_source: Path, frontmatter: dict = None) -> Path:
    """Determine destination based on Obsidian structure + metadata."""
    frontmatter = frontmatter or {}
    filename = file_path.name.lower()
    source_str = str(relative_source).lower()
    
    # Route by standardized type field (set by frontmatter_apply)
    file_type = (frontmatter.get("type") or "").lower()
    type_routes = {
        "cv": COMMAND_DIR / "finances",
        "cover-letter": COMMAND_DIR / "finances",
        "profile": COMMAND_DIR / "finances",
        "job-posting": COMMAND_DIR / "finances",
        "linkedin": COMMAND_DIR / "finances",
        "writing-sample": COMMAND_DIR / "finances",
        "financial": COMMAND_DIR / "finances",
        "daily-note": COMMAND_DIR / "inbox",
        "quick-capture": COMMAND_DIR / "inbox",
        "person": SELF_DIR / "relationships",
        "study-plan": SELF_DIR / "goals",
        "career-plan": SELF_DIR / "goals",
        "life-plan": SELF_DIR / "goals",
        "research-article": KNOWLEDGE_DIR / "articles",
        "analysis": KNOWLEDGE_DIR / "articles",
        "transcript": KNOWLEDGE_DIR / "articles",
        "guide": KNOWLEDGE_DIR / "articles",
        "tool-note": KNOWLEDGE_DIR / "notes",
        "personal-note": KNOWLEDGE_DIR / "notes",
        "note": KNOWLEDGE_DIR / "notes",
    }
    if file_type in type_routes:
        return type_routes[file_type]
    
    # Check explicit frontmatter tags
    tags = frontmatter.get("tags", [])
    if isinstance(tags, str):
        tags = [tags]
    
    # Route by explicit tag
    if "article" in tags or "research" in tags:
        return KNOWLEDGE_DIR / "articles"
    if "project" in tags:
        return KNOWLEDGE_DIR / "projects"
    if "reference" in tags:
        return KNOWLEDGE_DIR / "references"
    if "task" in tags or "todo" in tags:
        return COMMAND_DIR / "tasks"
    
    # Route by Obsidian folder structure
    if "Daily Notes" in str(relative_source):
        return COMMAND_DIR / "inbox"
    
    if "Life Plans" in str(relative_source):
        return SELF_DIR / "goals"
    
    if "People" in str(relative_source):
        return SELF_DIR / "relationships"
    
    if "PF" in str(relative_source) or "financial" in source_str or "finance" in source_str:
        return COMMAND_DIR / "finances"
    
    if "About me" in str(relative_source):
        return SELF_DIR / "profile"
    
    # Route by filename conventions
    if filename.startswith("project_"):
        return KNOWLEDGE_DIR / "projects"
    if filename.startswith("note_") or filename.startswith("idea_"):
        return KNOWLEDGE_DIR / "notes"
    if filename.startswith("article_") or filename.startswith("research_"):
        return KNOWLEDGE_DIR / "articles"
    
    # Default based on Daily Notes pattern
    if is_daily_note(file_path, relative_source):
        return COMMAND_DIR / "inbox"
    
    # Default fallback
    return KNOWLEDGE_DIR / "notes"


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
                except:
                    pass
        
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
        except:
            pass


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
