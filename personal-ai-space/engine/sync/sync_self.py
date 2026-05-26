"""
sync_self.py — Synchronise self/ JSON/CSV/MD data into self.db SQLite.

Bridges the gap between the human-editable files in personal-ai-space/self/
and the SQLite database that agents query. Run periodically (or after
editing self/ files) to keep both in sync.

Usage:
    python3 sync_self.py                          # Full sync, report to stdout
    python3 sync_self.py --dry-run                # Preview only, no writes
    python3 sync_self.py --quick                  # Profile + habits only
"""
import argparse
import csv
import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

import db_manager as db

logger = logging.getLogger("engine.sync_self")

# Resolve project root (this file lives at engine/sync_self.py)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_SELF_DIR = _PROJECT_ROOT / "self"


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
    """Return remaining text after removing the YAML frontmatter block."""
    if not text.startswith("---"):
        return text
    m = re.match(r"^---\s*\n.*?\n---\s*\n?", text, re.DOTALL)
    if m:
        return text[m.end():]
    return text


def _ensure_profile_columns():
    """Add missing profile columns if they don't already exist (safe migration)."""
    existing = {
        row["name"]
        for row in db.query("self", "PRAGMA table_info(profile)")
    }
    additions = {
        "core_values": "TEXT DEFAULT ''",
        "feedback_preference": "TEXT DEFAULT ''",
        "goals_current_year": "TEXT DEFAULT ''",
        "constraints": "TEXT DEFAULT ''",
        "created_at": "TEXT",
    }
    for col, coltype in additions.items():
        if col not in existing:
            db.execute(
                "self",
                f"ALTER TABLE profile ADD COLUMN {col} {coltype}"
            )
            logger.info("Added profile column: %s", col)


def _extract_canvas_text(file_path: Path) -> str:
    """Extract node labels/text from an Obsidian .canvas JSON file."""
    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
        nodes = data.get("nodes", [])
        parts = []
        for n in nodes:
            label = n.get("label", "")
            text = n.get("text", "")
            parts.append(f"{label}: {text}" if label else text)
        return "\n".join(parts) if parts else json.dumps(data, indent=2)
    except Exception as e:
        logger.debug("canvas extraction failed for %s: %s", file_path.name, e)
        return ""

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


# ── Profile ──────────────────────────────────────────────────────────────────

def sync_profile() -> int:
    """Sync profile.json → self.db profile table. Returns rows affected."""
    # Try new location first (self/profile/profile.json), fall back to old (self/profile.json)
    path = _SELF_DIR / "profile" / "profile.json"
    if not path.exists():
        path = _SELF_DIR / "profile.json"
    if not path.exists():
        logger.warning("profile.json not found at %s or %s", _SELF_DIR / "profile" / "profile.json", _SELF_DIR / "profile.json")
        return 0

    _ensure_profile_columns()

    with open(path) as f:
        p = json.load(f)

    prefs = p.get("preferences", {})
    with db.transaction("self") as conn:
        conn.execute(
            """INSERT OR REPLACE INTO profile
               (id, name, age, timezone, work_style, energy_peak_hours,
                communication_preference, decision_style, core_values,
                feedback_preference, goals_current_year, constraints,
                created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                p.get("id", "self_profile_001"),
                p.get("name", ""),
                p.get("age"),
                p.get("timezone", ""),
                p.get("work_style", ""),
                json.dumps(p.get("energy_peak_hours", [])),
                prefs.get("communication", ""),
                prefs.get("decision_making", ""),
                json.dumps(p.get("core_values", [])),
                prefs.get("feedback", ""),
                json.dumps(p.get("goals_current_year", [])),
                json.dumps(p.get("constraints", [])),
                p.get("created", ""),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
    logger.info("sync_profile: 1 row(s) affected")
    return 1


# ── Habits ───────────────────────────────────────────────────────────────────

def sync_habits() -> int:
    """Sync habits/tracking.csv → self.db habits table. Returns rows affected."""
    csv_path = _SELF_DIR / "habits" / "tracking.csv"
    if not csv_path.exists():
        logger.warning("tracking.csv not found at %s", csv_path)
        return 0

    total = 0
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            habit_id = row.get("id", "")
            if not habit_id or not row.get("habit"):
                continue
            with db.transaction("self") as conn:
                conn.execute(
                    """INSERT OR REPLACE INTO habits
                       (id, habit_name, category, frequency, start_date,
                        current_streak, total_completions, status)
                       VALUES (?, ?, ?, ?, ?, ?, ?, 'active')""",
                    (
                        habit_id,
                        row.get("habit", ""),
                        row.get("category", ""),
                        row.get("frequency", ""),
                        row.get("start_date"),
                        int(row.get("current_streak", 0)),
                        int(row.get("total_completions", 0)),
                    ),
                )
            total += 1
    logger.info("sync_habits: %d habit(s) synced", total)
    return total


# ── Goals ────────────────────────────────────────────────────────────────────

def sync_goals() -> int:
    """Sync goals/*.md and *.canvas frontmatter → self.db goals table.

    Extract description text from the body (excluding frontmatter),
    tags from frontmatter, and handle .canvas files as JSON node dumps.
    """
    goals_dir = _SELF_DIR / "goals"
    if not goals_dir.exists():
        logger.warning("goals/ directory not found")
        return 0

    # Ensure unique index on title (needed by ON CONFLICT)
    db.execute("self", "CREATE UNIQUE INDEX IF NOT EXISTS idx_goals_title ON goals(title)")

    # Ensure description and tags columns exist
    existing = {
        row["name"]
        for row in db.query("self", "PRAGMA table_info(goals)")
    }
    for col, coltype in {"description": "TEXT DEFAULT ''", "tags": "TEXT DEFAULT ''"}.items():
        if col not in existing:
            db.execute("self", f"ALTER TABLE goals ADD COLUMN {col} {coltype}")
            logger.info("Added goals column: %s", col)

    total = 0
    for fpath in sorted(goals_dir.iterdir()):
        # ── Canvas files ───────────────────────────────────────────────
        if fpath.suffix == ".canvas":
            title = fpath.stem.replace("-", " ").replace("_", " ").title()
            description = _extract_canvas_text(fpath)
            with db.transaction("self") as conn:
                conn.execute(
                    """INSERT INTO goals
                       (title, description, tags, status, created_at, updated_at, progress_source)
                       VALUES (?, ?, '[]', 'active', ?, ?, 'canvas')
                       ON CONFLICT(title) DO UPDATE SET
                           description = COALESCE(excluded.description, goals.description),
                           updated_at  = excluded.updated_at""",
                    (
                        title,
                        description[:2000] if description else "",
                        datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
                total += 1
            continue

        # ── Markdown files ─────────────────────────────────────────────
        if fpath.suffix not in (".md", ".markdown"):
            continue
        fm = _parse_frontmatter(fpath)
        if not fm or not fm.get("title"):
            continue
        title = str(fm["title"]).strip("\"'")

        full_text = fpath.read_text(encoding="utf-8")
        body = _strip_frontmatter(full_text).strip()
        description = body[:2000] if body else ""
        tags = json.dumps(fm.get("tags", [])) if isinstance(fm.get("tags"), list) else "[]"

        with db.transaction("self") as conn:
            conn.execute(
                """INSERT INTO goals
                   (title, description, tags, category, status, created_at, updated_at, progress_source)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 'sync')
                   ON CONFLICT(title) DO UPDATE SET
                       description    = COALESCE(excluded.description, goals.description),
                       tags           = excluded.tags,
                       category       = excluded.category,
                       status         = excluded.status,
                       updated_at     = excluded.updated_at""",
                (
                    title,
                    description,
                    tags,
                    str(fm.get("type", "")),
                    str(fm.get("status", "active")),
                    str(fm.get("created", "")),
                    str(fm.get("updated", "")),
                ),
            )
            total += 1
    logger.info("sync_goals: %d goal(s) synced", total)
    return total


# ── Relationships ────────────────────────────────────────────────────────────

def sync_relationships() -> int:
    """Sync relationships/*.md frontmatter + body → self.db relationships table."""
    rel_dir = _SELF_DIR / "relationships"
    if not rel_dir.exists():
        logger.warning("relationships/ directory not found")
        return 0

    # Ensure relationship_type and notes columns exist
    existing = {
        row["name"]
        for row in db.query("self", "PRAGMA table_info(relationships)")
    }
    for col, coltype in {"relationship_type": "TEXT DEFAULT ''", "notes": "TEXT DEFAULT ''"}.items():
        if col not in existing:
            db.execute("self", f"ALTER TABLE relationships ADD COLUMN {col} {coltype}")
            logger.info("Added relationships column: %s", col)

    total = 0
    for fpath in sorted(rel_dir.iterdir()):
        if fpath.suffix not in (".md", ".markdown"):
            continue
        # Skip template/base files
        if ".base" in fpath.suffixes or "base" in fpath.stem.lower():
            continue
        fm = _parse_frontmatter(fpath)
        if not fm:
            continue
        name = fm.get("Name") or fm.get("title")
        if not name:
            continue
        # Extract body text as notes
        full_text = fpath.read_text(encoding="utf-8")
        body = _strip_frontmatter(full_text).strip()
        notes = body[:2000] if body else ""
        rel_type = str(fm.get("type", "") or "")
        with db.transaction("self") as conn:
            conn.execute(
                """INSERT INTO relationships
                   (name, relationship_type, notes, email, phone, cpf, birth_date, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(name) DO UPDATE SET
                       relationship_type = COALESCE(excluded.relationship_type, relationships.relationship_type),
                       notes             = COALESCE(excluded.notes, relationships.notes),
                       email             = COALESCE(excluded.email, relationships.email),
                       phone             = COALESCE(excluded.phone, relationships.phone),
                       cpf               = COALESCE(excluded.cpf, relationships.cpf),
                       birth_date        = COALESCE(excluded.birth_date, relationships.birth_date),
                       updated_at        = excluded.updated_at""",
                (
                    name,
                    rel_type,
                    notes,
                    str(fm.get("email", "") or ""),
                    str(fm.get("number", "") or ""),
                    str(fm.get("CPF", "") or ""),
                    str(fm.get("birth_date", "") or ""),
                    str(fm.get("created", "") or ""),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            total += 1
    logger.info("sync_relationships: %d relationship(s) synced", total)
    return total


# ── Traits ───────────────────────────────────────────────────────────────────

def sync_traits() -> int:
    """Sync traits/inferred_personality.json → self.db traits table.

    Decomposes the JSON into individual trait rows so agents can query
    them individually by trait_name.
    """
    path = _SELF_DIR / "traits" / "inferred_personality.json"
    if not path.exists():
        logger.warning("inferred_personality.json not found")
        return 0

    with open(path) as f:
        data = json.load(f)

    now = datetime.now(timezone.utc).isoformat()
    rows: list[tuple[str, str, str, float, str, str, str]] = []

    # Personality type as a trait
    pt = data.get("personality_type", "")
    if pt:
        rows.append((f"personality_{pt}", pt, "personality_type", 0.95,
                      "personality_assessment", now[:10], now))

    # Core traits
    for i, trait in enumerate(data.get("core_traits", [])):
        rows.append((f"core_{trait}", trait.replace("_", " ").title(),
                      "core", 0.85, "personality_assessment", now[:10], now))

    # Work traits
    wt = data.get("work_traits", {})
    for key, val in wt.items():
        safe = key.replace("_", " ").title()
        rows.append((f"work_{key}", f"{safe}: {val}",
                      "work_style", 0.8, "behavior_analysis", now[:10], now))

    # Decision patterns
    dp = data.get("decision_patterns", {})
    for key, val in dp.items():
        safe = key.replace("_", " ").title()
        rows.append((f"decision_{key}", f"{safe}: {val}",
                      "decision_pattern", 0.75, "behavior_analysis", now[:10], now))

    total = 0
    for row in rows:
        with db.transaction("self") as conn:
            conn.execute(
                """INSERT OR REPLACE INTO traits
                   (id, trait_name, category, confidence_score,
                    inferred_from, discovered_date, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                row,
            )
            total += 1
    logger.info("sync_traits: %d trait(s) synced", total)
    return total


# ── Needs ────────────────────────────────────────────────────────────────────

def sync_needs() -> int:
    """Sync needs/current_needs.json → self.db needs table."""
    path = _SELF_DIR / "needs" / "current_needs.json"
    if not path.exists():
        logger.warning("current_needs.json not found")
        return 0

    with open(path) as f:
        needs = json.load(f)

    total = 0
    now = datetime.now(timezone.utc).isoformat()
    for need in needs:
        nid = need.get("id", "")
        if not nid:
            continue
        with db.transaction("self") as conn:
            conn.execute(
                """INSERT OR REPLACE INTO needs
                   (id, category, name, priority, status, description, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    nid,
                    need.get("category", ""),
                    need.get("name", ""),
                    need.get("priority", ""),
                    need.get("status", ""),
                    need.get("description", ""),
                    need.get("created_at", now),
                ),
            )
            total += 1
    logger.info("sync_needs: %d need(s) synced", total)
    return total


# ── Documents ────────────────────────────────────────────────────────────────

def sync_documents() -> int:
    """Sync documents/ metadata (index.json + .md frontmatter) → self.db documents table.

    Scans every subdirectory under self/documents/ for:
      - index.json — metadata entries for binary files (pdf, docx, png, jpeg, etc.)
      - *.md files — YAML frontmatter + body text (same pattern as relationships/)

    Returns total rows upserted.
    """
    docs_root = _SELF_DIR / "documents"
    if not docs_root.exists():
        logger.warning("documents/ directory not found at %s", docs_root)
        return 0

    # Ensure the documents table exists (safe to call repeatedly)
    db.execute("self", """
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            doc_type TEXT NOT NULL,
            subcategory TEXT DEFAULT '',
            tags TEXT DEFAULT '[]',
            file_path TEXT DEFAULT '',
            file_format TEXT DEFAULT '',
            content TEXT DEFAULT '',
            metadata TEXT DEFAULT '{}',
            created_at TEXT,
            updated_at TEXT
        )
    """)

    total = 0
    now_iso = datetime.now(timezone.utc).isoformat()

    for subdir in sorted(docs_root.iterdir()):
        if not subdir.is_dir():
            continue

        subcategory = subdir.name  # e.g. "resumes", "portfolios"

        # ── index.json entries (binary file metadata) ─────────────────
        index_path = subdir / "index.json"
        if index_path.exists():
            try:
                entries = json.loads(index_path.read_text(encoding="utf-8"))
                if isinstance(entries, list):
                    for entry in entries:
                        title = entry.get("title", "")
                        if not title:
                            continue
                        doc_id = entry.get("id", f"doc_{subcategory}_{title.lower().replace(' ', '_')}")
                        with db.transaction("self") as conn:
                            conn.execute(
                                """INSERT INTO documents
                                   (id, title, doc_type, subcategory, tags,
                                    file_path, file_format, content, metadata,
                                    created_at, updated_at)
                                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                   ON CONFLICT(id) DO UPDATE SET
                                       title        = excluded.title,
                                       doc_type     = excluded.doc_type,
                                       subcategory  = excluded.subcategory,
                                       tags         = excluded.tags,
                                       file_path    = excluded.file_path,
                                       file_format  = excluded.file_format,
                                       content      = COALESCE(excluded.content, documents.content),
                                       metadata     = excluded.metadata,
                                       updated_at   = excluded.updated_at""",
                                (
                                    doc_id,
                                    title,
                                    entry.get("doc_type", subcategory),
                                    subcategory,
                                    json.dumps(entry.get("tags", [])),
                                    entry.get("file", ""),
                                    entry.get("file_format", ""),
                                    entry.get("description", ""),
                                    json.dumps({k: v for k, v in entry.items()
                                                if k not in ("title", "doc_type", "tags", "file", "file_format", "description", "id")}),
                                    entry.get("created", now_iso),
                                    entry.get("updated", now_iso),
                                ),
                            )
                            total += 1
            except Exception as e:
                logger.warning("Failed to parse %s: %s", index_path, e)

        # ── .md files with frontmatter ────────────────────────────────
        for fpath in sorted(subdir.iterdir()):
            if fpath.suffix not in (".md", ".markdown"):
                continue
            fm = _parse_frontmatter(fpath)
            if not fm:
                continue
            title = fm.get("title") or fpath.stem
            doc_id = fm.get("id") or str(fpath.relative_to(_SELF_DIR))
            full_text = fpath.read_text(encoding="utf-8")
            body = _strip_frontmatter(full_text).strip()
            with db.transaction("self") as conn:
                conn.execute(
                    """INSERT INTO documents
                       (id, title, doc_type, subcategory, tags,
                        file_path, file_format, content, metadata,
                        created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                       ON CONFLICT(id) DO UPDATE SET
                           title        = excluded.title,
                           doc_type     = excluded.doc_type,
                           subcategory  = excluded.subcategory,
                           tags         = excluded.tags,
                           file_path    = excluded.file_path,
                           file_format  = excluded.file_format,
                           content      = excluded.content,
                           metadata     = excluded.metadata,
                           updated_at   = excluded.updated_at""",
                    (
                        doc_id,
                        title,
                        str(fm.get("doc_type", subcategory)),
                        subcategory,
                        json.dumps(fm.get("tags", [])),
                        str(fpath.relative_to(_SELF_DIR)),
                        "md",
                        body,
                        json.dumps({k: v for k, v in fm.items()
                                    if k not in ("title", "doc_type", "tags", "id")},
                                   default=str),
                        str(fm.get("created", "") or now_iso),
                        str(fm.get("updated", "") or now_iso),
                    ),
                )
                total += 1

    logger.info("sync_documents: %d document(s) synced", total)
    return total


# ── Orchestrator ─────────────────────────────────────────────────────────────

def sync_all(dry_run: bool = False) -> dict[str, Any]:
    """Run all sync operations. Returns a summary dict.

    Args:
        dry_run: When True, only preview what would be synced (no DB writes).

    Returns:
        Dict with keys: profile, habits, goals, relationships, traits, needs, documents
        each mapping to a row count or error message.
    """
    if dry_run:
        _log_dry_run()
        return {
            "profile": "DRY_RUN",
            "habits": "DRY_RUN",
            "goals": "DRY_RUN",
            "relationships": "DRY_RUN",
            "traits": "DRY_RUN",
            "needs": "DRY_RUN",
            "documents": "DRY_RUN",
        }

    return {
        "profile": sync_profile(),
        "habits": sync_habits(),
        "goals": sync_goals(),
        "relationships": sync_relationships(),
        "traits": sync_traits(),
        "needs": sync_needs(),
        "documents": sync_documents(),
    }


def sync_quick() -> dict[str, Any]:
    """Quick sync — profile + habits only (the most commonly changed files)."""
    return {
        "profile": sync_profile(),
        "habits": sync_habits(),
    }


def _log_dry_run():
    profile_ok = (_SELF_DIR / "profile.json").exists()
    habits_ok = (_SELF_DIR / "habits" / "tracking.csv").exists()
    goals_ok = any(f.suffix == ".md" for f in (_SELF_DIR / "goals").iterdir()) if (_SELF_DIR / "goals").exists() else False
    rel_ok = any(f.suffix == ".md" for f in (_SELF_DIR / "relationships").iterdir()) if (_SELF_DIR / "relationships").exists() else False
    traits_ok = (_SELF_DIR / "traits" / "inferred_personality.json").exists()
    needs_ok = (_SELF_DIR / "needs" / "current_needs.json").exists()
    docs_ok = (_SELF_DIR / "documents").exists() and any((_SELF_DIR / "documents").iterdir()) if (_SELF_DIR / "documents").exists() else False

    print("DRY RUN — No changes written")
    print(f"  profile.json           → profile table       {'✓ found' if profile_ok else '✗ missing'}")
    print(f"  habits/tracking.csv    → habits table        {'✓ found' if habits_ok else '✗ missing'}")
    print(f"  goals/*.md             → goals table          {'✓ found' if goals_ok else '✗ missing or empty'}")
    print(f"  relationships/*.md     → relationships table  {'✓ found' if rel_ok else '✗ missing or empty'}")
    print(f"  traits/*.json          → traits table         {'✓ found' if traits_ok else '✗ missing'}")
    print(f"  needs/*.json           → needs table          {'✓ found' if needs_ok else '✗ missing'}")
    print(f"  documents/*/index.json → documents table      {'✓ found' if docs_ok else '✗ missing or empty'}")


def _format_summary(results: dict[str, Any]):
    print("\nSync Summary:")
    print(f"  Profile        → {results.get('profile', '?')} row(s)")
    print(f"  Habits         → {results.get('habits', '?')} row(s)")
    print(f"  Goals          → {results.get('goals', '?')} row(s)")
    print(f"  Relationships  → {results.get('relationships', '?')} row(s)")
    print(f"  Traits         → {results.get('traits', '?')} row(s)")
    print(f"  Needs          → {results.get('needs', '?')} row(s)")
    print(f"  Documents      → {results.get('documents', '?')} row(s)")


def main():
    parser = argparse.ArgumentParser(description="Sync self/ data to self.db")
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    parser.add_argument("--quick", action="store_true", help="Profile + habits only")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    if args.dry_run:
        sync_all(dry_run=True)
        return

    if args.quick:
        results = sync_quick()
    else:
        results = sync_all()

    _format_summary(results)
    db.checkpoint_all()


if __name__ == "__main__":
    main()
