"""
sync_knowledge.py — Sync knowledge/ article and note files into knowledge.db.

Bridges the gap between human-collected research files in personal-ai-space/knowledge/
and the SQLite database that agents query. Run after adding/changing files.

Usage:
    python3 sync_knowledge.py                          # Full sync, report to stdout
    python3 sync_knowledge.py --dry-run                # Preview only, no writes
    python3 sync_knowledge.py --quick                  # Notes only (skip articles)
"""
import argparse
import hashlib
import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Allow running as `python3 sync/sync_knowledge.py` from engine/
_ENGINE_ROOT = Path(__file__).resolve().parent.parent
if str(_ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(_ENGINE_ROOT))

import yaml

import db_manager as db

logger = logging.getLogger("engine.sync_knowledge")

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_KNOWLEDGE_DIR = _PROJECT_ROOT / "knowledge"


# ── helpers ──────────────────────────────────────────────────────────────────

def _parse_frontmatter(file_path: Path) -> dict:
    """Extract YAML frontmatter from a markdown file. Returns {} on failure."""
    try:
        text = file_path.read_text(encoding="utf-8")
    except Exception:
        return {}
    if not text.startswith("---"):
        return {}
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return {}
    try:
        fm = yaml.safe_load(m.group(1))
        return fm if isinstance(fm, dict) else {}
    except Exception:
        return {}


def _strip_frontmatter(text: str) -> str:
    """Return text content without the YAML frontmatter block."""
    if not text.startswith("---"):
        return text
    m = re.match(r"^---\s*\n.*?\n---\s*\n?", text, re.DOTALL)
    if m:
        return text[m.end():]
    return text


def _fmt_tags(raw_tags) -> str:
    """Normalise tags to a comma-separated string."""
    if isinstance(raw_tags, list):
        return ", ".join(str(t).strip() for t in raw_tags if t)
    if isinstance(raw_tags, str):
        return raw_tags
    return ""


def _file_id(file_path: Path) -> str:
    """Deterministic ID from relative path under project root."""
    rel = file_path.resolve().relative_to(_PROJECT_ROOT.resolve())
    h = hashlib.md5(str(rel).encode()).hexdigest()[:16]
    return h


def _title_from_path(file_path: Path) -> str:
    """Derive a human-readable title from the filename."""
    stem = file_path.stem
    # Strip leading date/time prefixes like 20260511_141104_
    stem = re.sub(r"^\d{8}_\d{6}_", "", stem)
    stem = re.sub(r"^\d{4}-\d{2}-\d{2}_", "", stem)
    # Replace underscores and hyphens with spaces
    stem = stem.replace("_", " ").replace("-", " ").strip()
    return stem


def _try_docx_text(file_path: Path) -> str:
    """Extract text from a .docx file. Returns empty string on failure."""
    try:
        from docx import Document
        doc = Document(str(file_path))
        paras = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n".join(paras)
    except Exception as e:
        logger.debug("docx extraction failed for %s: %s", file_path.name, e)
        return ""


# ── sync: articles ───────────────────────────────────────────────────────────

def sync_articles(dry_run: bool = False) -> int:
    """Sync knowledge/articles/ → articles table. Returns rows affected."""
    articles_dir = _KNOWLEDGE_DIR / "articles"
    if not articles_dir.exists():
        logger.warning("knowledge/articles/ directory not found")
        return 0

    total = 0
    for fpath in sorted(articles_dir.iterdir()):
        if fpath.is_dir() or fpath.name.startswith("."):
            continue

        total += 1
        if dry_run:
            logger.info("  [article] %s", fpath.name)
            continue

        _upsert_article(fpath)

    logger.info("sync_articles: %d file(s) processed", total)
    return total


def _upsert_article(fpath: Path):
    """Read a single file and upsert it into the articles table."""
    ext = fpath.suffix.lower()
    fm = _parse_frontmatter(fpath) if ext == ".md" else {}
    title = fm.get("title") or _title_from_path(fpath)
    aid = _file_id(fpath)
    now = datetime.now(timezone.utc).isoformat()

    content = ""
    if ext == ".md":
        raw = fpath.read_text(encoding="utf-8", errors="replace")
        content = _strip_frontmatter(raw).strip()
    elif ext == ".docx":
        content = _try_docx_text(fpath)
    elif ext == ".pdf":
        content = "[PDF file — full text extraction requires OCR/PDF tooling]"
    elif ext == ".canvas":
        try:
            data = json.loads(fpath.read_text(encoding="utf-8"))
            nodes = data.get("nodes", [])
            parts = []
            for n in nodes:
                label = n.get("label", "")
                text = n.get("text", "")
                parts.append(f"{label}: {text}" if label else text)
            content = "\n".join(parts) if parts else json.dumps(data, indent=2)
        except Exception:
            content = json.dumps(fpath.read_text(encoding="utf-8"))

    tags = _fmt_tags(fm.get("tags", []))
    if not tags:
        tags = ext.lstrip(".")

    db.execute(
        "knowledge",
        """INSERT OR REPLACE INTO articles
           (id, title, url, source, author, published_date,
            tags, summary, full_content, status, imported_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            aid,
            title,
            f"file://{fpath.resolve()}",
            "",  # source — not typically available in local files
            fm.get("author", "") or "",
            str(fm.get("published_date", "") or "") or None,
            tags,
            title,
            content,
            fm.get("status", "imported") or "imported",
            now,
        ),
    )


# ── sync: notes ──────────────────────────────────────────────────────────────

def sync_notes(dry_run: bool = False) -> int:
    """Sync knowledge/notes/ → notes table. Returns rows affected."""
    notes_dir = _KNOWLEDGE_DIR / "notes"
    if not notes_dir.exists():
        logger.warning("knowledge/notes/ directory not found")
        return 0

    total = 0
    for fpath in sorted(notes_dir.iterdir()):
        if fpath.is_dir() or fpath.name.startswith("."):
            continue

        total += 1
        if dry_run:
            logger.info("  [note] %s", fpath.name)
            continue

        _upsert_note(fpath)

    logger.info("sync_notes: %d file(s) processed", total)
    return total


def _upsert_note(fpath: Path):
    """Read a single note file and upsert it into the notes table."""
    ext = fpath.suffix.lower()
    fm = _parse_frontmatter(fpath) if ext == ".md" else {}
    title = fm.get("title") or _title_from_path(fpath)
    nid = f"sync_{_file_id(fpath)}"
    now = datetime.now(timezone.utc).isoformat()

    content = ""
    if ext == ".md":
        raw = fpath.read_text(encoding="utf-8", errors="replace")
        content = _strip_frontmatter(raw).strip()
    elif ext == ".canvas":
        try:
            data = json.loads(fpath.read_text(encoding="utf-8"))
            nodes = data.get("nodes", [])
            parts = []
            for n in nodes:
                label = n.get("label", "")
                text = n.get("text", "")
                parts.append(f"{label}: {text}" if label else text)
            content = "\n".join(parts) if parts else json.dumps(data, indent=2)
        except Exception:
            content = json.dumps(fpath.read_text(encoding="utf-8"))
    else:
        try:
            content = fpath.read_text(encoding="utf-8", errors="replace")
        except Exception:
            content = ""

    tags = _fmt_tags(fm.get("tags", []))

    db.execute(
        "knowledge",
        """INSERT OR REPLACE INTO notes
           (id, title, content, created_at, updated_at, tags, category,
            importance_level, original_format, conversion_metadata)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            nid,
            title,
            content,
            str(fm.get("created", now)) or now,
            str(fm.get("updated", now)) or now,
            tags,
            fm.get("type", "general") or "general",
            3,
            ext.lstrip("."),
            json.dumps({"synced_from": str(fpath.resolve())}),
        ),
    )


# ── orchestrator ─────────────────────────────────────────────────────────────

def sync_all(dry_run: bool = False) -> dict[str, Any]:
    """Run all knowledge sync operations. Returns a summary dict."""
    results = {}
    if dry_run:
        logger.info("DRY RUN — No changes written")
        results["articles"] = sync_articles(dry_run=True)
        results["notes"] = sync_notes(dry_run=True)
    else:
        results["articles"] = sync_articles()
        results["notes"] = sync_notes()
    return results


def sync_quick() -> dict[str, Any]:
    """Quick sync — notes only (articles change less frequently)."""
    return {"notes": sync_notes()}


def _format_summary(results: dict[str, Any]):
    print("\nSync Summary:")
    for key, val in results.items():
        print(f"  {key:<20} → {val}")


def main():
    parser = argparse.ArgumentParser(
        description="Sync knowledge/ files to knowledge.db"
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    parser.add_argument("--quick", action="store_true",
                        help="Notes only (skip articles)")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(message)s",
    )

    if args.dry_run:
        sync_all(dry_run=True)
        return

    if args.quick:
        results = sync_quick()
    else:
        results = sync_all()

    _format_summary(results)


if __name__ == "__main__":
    main()
