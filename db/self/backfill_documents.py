"""Backfill empty content in self.db documents table.

Now that Pillow, pytesseract, PyMuPDF, and python-docx are installed,
re-extract text from the 51 documents that have empty content.

Usage:
    python3 db/self/backfill_documents.py
"""
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add engine/ to path for imports
_ENGINE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ENGINE_DIR))

import db_manager as db

_PROJECT_ROOT = _ENGINE_DIR.parent
_SELF_DIR = _PROJECT_ROOT / "self"

# Replicate the same logic as sync_self.py
try:
    from sync.text_extractor import extract_text as _extract_binary_text
    _HAS_TEXT_EXTRACTOR = True
except ImportError:
    _HAS_TEXT_EXTRACTOR = False

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("backfill_documents")


def _strip_frontmatter(text: str) -> str:
    """Remove YAML frontmatter (--- ... ---) from the start of text."""
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            return text[end + 3 :]
    return text


def backfill() -> int:
    """Re-extract content for all documents with empty content."""
    rows = db.query("self", """
        SELECT id, title, file_path, file_format, subcategory
        FROM documents
        WHERE content IS NULL OR content = ''
    """)

    logger.info("Found %d document(s) with empty content", len(rows))
    fixed = 0
    skipped = 0
    now_iso = datetime.now(timezone.utc).isoformat()

    for row in rows:
        doc_id = row["id"]
        title = row["title"]
        file_path = row["file_path"]
        file_format = row["file_format"]
        subcategory = row["subcategory"]
        content = None  # will stay None if nothing works

        # Try to find and extract from the source file
        if file_path:
            # file_path might be relative to self/ or absolute
            candidate = _SELF_DIR / file_path
            if not candidate.exists():
                # Try documents/{subcategory}/{file_name}
                candidate = _SELF_DIR / "documents" / subcategory / Path(file_path).name

            if candidate.exists():
                try:
                    if file_format == "md" or not _HAS_TEXT_EXTRACTOR:
                        raw = candidate.read_text(encoding="utf-8")
                        body = _strip_frontmatter(raw).strip()
                        if body:
                            content = body
                    elif _HAS_TEXT_EXTRACTOR:
                        extracted = _extract_binary_text(candidate)
                        if extracted:
                            content = extracted
                except Exception as e:
                    logger.warning("  Extraction failed for %s: %s", candidate.name, e)

        if content:
            with db.transaction("self") as conn:
                conn.execute(
                    "UPDATE documents SET content = ?, updated_at = ? WHERE id = ?",
                    (content, now_iso, doc_id),
                )
            preview = content[:100].replace("\n", " ")
            logger.info("  ✓ %s (%d chars): %s...", title[:50], len(content), preview)
            fixed += 1
        else:
            logger.info("  ✗ %s — no content extracted from %s", title[:50], file_path)
            skipped += 1

    logger.info("Done: %d fixed, %d skipped (still empty)", fixed, skipped)
    return fixed


if __name__ == "__main__":
    backfill()
