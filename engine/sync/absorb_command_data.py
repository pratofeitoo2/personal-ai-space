"""
absorb_command_data.py — Absorb obsolete command/ data into SQLite databases.

Migrates the remaining data in personal-ai-space/command/ into the
appropriate SQLite databases:
  - inbox/*.md  → knowledge.db/notes (daily notes)
  - finances/*  → knowledge.db/notes (professional docs + financial overview)
  - tasks/active_tasks.json  → tasks.db projects (backfill missing project records)

The activities, calendar, and tasks data were already absorbed by earlier
sync scripts; this handles the leftovers.

Usage:
    python3 absorb_command_data.py              # Full migration
    python3 absorb_command_data.py --dry-run     # Preview only
    python3 absorb_command_data.py --only inbox  # Migrate only one section
"""
import argparse
import json
import logging
import re
from db.id_helpers import for_project
from datetime import datetime, timezone
from pathlib import Path

_ENGINE_DIR = Path(__file__).resolve().parent.parent
import sys as _sys
if str(_ENGINE_DIR) not in _sys.path:
    _sys.path.insert(0, str(_ENGINE_DIR))

import db_manager as db

logger = logging.getLogger("engine.absorb_command_data")

_COMMAND_DIR = _ENGINE_DIR.parent / "command"

_FM_RE = re.compile(r'^---\s*\n(.*?)\n---', re.DOTALL)


def _parse_frontmatter(text: str) -> dict:
    m = _FM_RE.match(text)
    if not m:
        return {}
    try:
        import yaml
        fm = yaml.safe_load(m.group(1))
        return fm if isinstance(fm, dict) else {}
    except Exception:
        return {}


def _strip_frontmatter(text: str) -> str:
    return _FM_RE.sub("", text, count=1).strip()


def _safe_title(filename: str) -> str:
    return Path(filename).stem.strip()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Inbox ────────────────────────────────────────────────────────────────────

def absorb_inbox(dry_run: bool = False) -> int:
    """Migrate inbox/*.md → knowledge.db notes table.

    Each file with frontmatter type: daily-note becomes a note with
    category='daily-note', original_format='md'.
    Skips dashboards, base files, and non-markdown files.
    """
    inbox_dir = _COMMAND_DIR / "inbox"
    if not inbox_dir.exists():
        logger.warning("inbox/ directory not found")
        return 0

    total = 0
    for fpath in sorted(inbox_dir.iterdir()):
        if fpath.suffix not in (".md", ".markdown"):
            continue

        text = _safe_read(fpath)
        if not text or not text.startswith("---"):
            continue

        fm = _parse_frontmatter(text)
        note_type = fm.get("type", "")

        # Skip non-note files (dashboards, etc.)
        if note_type not in ("daily-note", "quick-capture", ""):
            continue

        content = _strip_frontmatter(text)
        title = fm.get("title", "") or _safe_title(fpath.name)
        created = str(fm.get("created", "")) or str(fm.get("date", ""))[:10] or _now()
        tags = fm.get("tags", [])
        tags_str = ", ".join(tags) if isinstance(tags, list) else str(tags)

        if dry_run:
            print(f"  WOULD_INSERT note: {title} ({note_type}) — {len(content)} chars")
            total += 1
            continue

        note_id = uuid.uuid4().hex
        with db.transaction("knowledge") as conn:
            conn.execute(
                """INSERT OR IGNORE INTO notes
                   (id, title, content, category, tags, created_at, original_format)
                   VALUES (?, ?, ?, ?, ?, ?, 'md')""",
                (note_id, title, content, "daily-note", tags_str, created),
            )
        total += 1

    logger.info("absorb_inbox: %d note(s) inserted", total)
    return total


# ── Finances ─────────────────────────────────────────────────────────────────

def absorb_finances(dry_run: bool = False) -> int:
    """Migrate finances/ files → knowledge.db notes table.

    - .md files: full content as notes (category: professional or profile)
    - .pdf files: path-only reference notes
    - overview.json: parsed financial data
    """
    fin_dir = _COMMAND_DIR / "finances"
    if not fin_dir.exists():
        logger.warning("finances/ directory not found")
        return 0

    total = 0
    job_board_note = None

    for fpath in sorted(fin_dir.iterdir()):
        if fpath.name.startswith("."):
            continue

        stem = fpath.stem.strip()
        suffix = fpath.suffix.lower()

        if suffix == ".json":
            # Financial overview
            try:
                data = json.loads(fpath.read_text(encoding="utf-8"))
                content = json.dumps(data, indent=2)
            except Exception as e:
                logger.warning("Cannot read %s: %s", fpath.name, e)
                continue
            category = "financial"
            note_id = uuid.uuid4().hex
            if dry_run:
                print(f"  WOULD_INSERT note: {stem} (financial) — {len(content)} chars")
                total += 1
                continue
            tags = "finances, budget"
            created = _now()
            with db.transaction("knowledge") as conn:
                conn.execute(
                    """INSERT OR IGNORE INTO notes
                       (id, title, content, category, tags, created_at, original_format)
                       VALUES (?, ?, ?, ?, ?, ?, 'json')""",
                    (note_id, stem, content, category, tags, created),
                )
            total += 1
            continue

        if suffix == ".base":
            continue

        if suffix == ".md":
            text = _safe_read(fpath)
            if not text:
                continue
            fm = _parse_frontmatter(text) if text.startswith("---") else {}
            content = _strip_frontmatter(text) if text.startswith("---") else text
            category = "professional"
            tags = fm.get("tags", [])
            tags_str = ", ".join(tags) if isinstance(tags, list) else str(tags)
            tags_str = "professional, " + tags_str if tags_str else "professional"
            created = str(fm.get("created", "")) or _now()

            # Check for Job Board data
            if stem.lower() == "job board":
                job_board_note = (stem, content, category, tags_str, created)

            if dry_run:
                print(f"  WOULD_INSERT note: {stem} (professional) — {len(content)} chars")
                total += 1
                continue

            note_id = uuid.uuid4().hex
            with db.transaction("knowledge") as conn:
                conn.execute(
                    """INSERT OR IGNORE INTO notes
                       (id, title, content, category, tags, created_at, original_format)
                       VALUES (?, ?, ?, ?, ?, ?, 'md')""",
                    (note_id, stem, content, category, tags_str, created),
                )
            total += 1
            continue

        if suffix == ".pdf":
            ref_path = str(fpath.resolve())
            content = f"PDF document: {fpath.name}\nPath: {ref_path}"
            if dry_run:
                print(f"  WOULD_INSERT note: {stem} (pdf reference) — {fpath.name}")
                total += 1
                continue
            note_id = uuid.uuid4().hex
            with db.transaction("knowledge") as conn:
                conn.execute(
                    """INSERT OR IGNORE INTO notes
                       (id, title, content, category, tags, created_at, original_format)
                       VALUES (?, ?, ?, ?, ?, ?, 'pdf')""",
                    (note_id, stem, content, "professional", "professional, pdf", _now()),
                )
            total += 1
            continue

    # Insert Job Board data last to keep related data together
    if job_board_note and not dry_run:
        with db.transaction("knowledge") as conn:
            conn.execute(
                """INSERT OR IGNORE INTO notes
                   (id, title, content, category, tags, created_at, original_format)
                   VALUES (?, ?, ?, ?, ?, ?, 'base')""",
                (uuid.uuid4().hex,) + job_board_note,
            )
        logger.info("  + Job Board: inserted as single note with %d entries",
                     job_board_note[1].count("\n"))

    logger.info("absorb_finances: %d item(s) inserted", total)
    return total


# ── Tasks (project backfill) ────────────────────────────────────────────────

def absorb_task_projects(dry_run: bool = False) -> int:
    """Backfill missing project records from active_tasks.json.

    Creates project entries for any project names referenced by tasks
    that don't already exist in the projects table.
    """
    tasks_file = _COMMAND_DIR / "tasks" / "active_tasks.json"
    if not tasks_file.exists():
        logger.warning("active_tasks.json not found")
        return 0

    with open(tasks_file) as f:
        tasks = json.load(f)

    project_names = set()
    for t in tasks:
        proj = t.get("project", "").strip()
        if proj:
            project_names.add(proj)

    if not project_names:
        logger.info("No project references found in tasks")
        return 0

    existing = set()
    for name in project_names:
        rows = db.query("tasks",
            "SELECT id FROM projects WHERE name = ?", (name,))
        if rows:
            existing.add(name)

    missing = project_names - existing
    if dry_run:
        for name in sorted(missing):
            print(f"  WOULD_CREATE project: {name}")
        logger.info("absorb_task_projects: %d project(s) would be created", len(missing))
        return len(missing)

    created = 0
    now = _now()
    for name in sorted(missing):
        pid = for_project(name)
        with db.transaction("tasks") as conn:
            conn.execute(
                """INSERT INTO projects
                   (id, name, description, status, priority, category, created_at, updated_at)
                   VALUES (?, ?, ?, 'active', 'normal', 'general', ?, ?)""",
                (pid, name, f"Auto-created from task import", now, now),
            )
        created += 1

    logger.info("absorb_task_projects: %d project(s) created", created)
    return created


# ── Helpers ──────────────────────────────────────────────────────────────────

def _safe_read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


# ── Orchestrator ─────────────────────────────────────────────────────────────

def absorb_all(dry_run: bool = False, only: str = "") -> dict:
    results = {}

    if not only or only == "inbox":
        results["inbox"] = absorb_inbox(dry_run=dry_run)
    if not only or only == "finances":
        results["finances"] = absorb_finances(dry_run=dry_run)
    if not only or only == "projects":
        results["projects"] = absorb_task_projects(dry_run=dry_run)

    return results


def _format_summary(results: dict):
    print("\nAbsorption Summary:")
    for key, val in results.items():
        print(f"  {key:12s} → {val} item(s)")


def main():
    parser = argparse.ArgumentParser(
        description="Absorb command/ data into SQLite databases"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview only, no DB writes")
    parser.add_argument("--only", choices=["inbox", "finances", "projects"],
                        help="Migrate only one section")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(levelname)s %(message)s")

    if args.dry_run:
        print("DRY RUN — No changes written")

    results = absorb_all(dry_run=args.dry_run, only=args.only or "")
    _format_summary(results)

    if not args.dry_run:
        db.checkpoint_all()


if __name__ == "__main__":
    main()
