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
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
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


# ── Profile ──────────────────────────────────────────────────────────────────

def sync_profile() -> int:
    """Sync profile.json → self.db profile table. Returns rows affected."""
    path = _SELF_DIR / "profile.json"
    if not path.exists():
        logger.warning("profile.json not found at %s", path)
        return 0

    with open(path) as f:
        p = json.load(f)

    prefs = p.get("preferences", {})
    with db.transaction("self") as conn:
        conn.execute(
            """INSERT OR REPLACE INTO profile
               (id, name, age, timezone, work_style, energy_peak_hours,
                communication_preference, decision_style, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                p.get("id", "self_profile_001"),
                p.get("name", ""),
                p.get("age"),
                p.get("timezone", ""),
                p.get("work_style", ""),
                json.dumps(p.get("energy_peak_hours", [])),
                prefs.get("communication", ""),
                prefs.get("decision_making", ""),
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
    """Sync goals/*.md frontmatter → self.db goals table. Returns rows affected."""
    goals_dir = _SELF_DIR / "goals"
    if not goals_dir.exists():
        logger.warning("goals/ directory not found")
        return 0

    total = 0
    for fpath in sorted(goals_dir.iterdir()):
        if fpath.suffix not in (".md", ".markdown"):
            continue
        fm = _parse_frontmatter(fpath)
        if not fm or not fm.get("title"):
            continue
        title = str(fm["title"]).strip("\"'")
        with db.transaction("self") as conn:
            conn.execute(
                """INSERT INTO goals
                   (title, category, status, created_at, updated_at, progress_source)
                   VALUES (?, ?, ?, ?, ?, 'sync')
                   ON CONFLICT(title) DO UPDATE SET
                       category = excluded.category,
                       status   = excluded.status,
                       updated_at = excluded.updated_at""",
                (
                    title,
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
    """Sync relationships/*.md frontmatter → self.db relationships table.

    Only updates fields available in the markdown frontmatter; leaves
    relationship_type and notes untouched (they are set by other processes).
    """
    rel_dir = _SELF_DIR / "relationships"
    if not rel_dir.exists():
        logger.warning("relationships/ directory not found")
        return 0

    total = 0
    for fpath in sorted(rel_dir.iterdir()):
        if fpath.suffix not in (".md", ".markdown"):
            continue
        fm = _parse_frontmatter(fpath)
        if not fm:
            continue
        name = fm.get("Name") or fm.get("title")
        if not name:
            continue
        with db.transaction("self") as conn:
            conn.execute(
                """INSERT INTO relationships
                   (name, email, phone, cpf, birth_date, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(name) DO UPDATE SET
                       email      = COALESCE(excluded.email, relationships.email),
                       phone      = COALESCE(excluded.phone, relationships.phone),
                       cpf        = COALESCE(excluded.cpf, relationships.cpf),
                       birth_date = COALESCE(excluded.birth_date, relationships.birth_date),
                       updated_at = excluded.updated_at""",
                (
                    name,
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


# ── Orchestrator ─────────────────────────────────────────────────────────────

def sync_all(dry_run: bool = False) -> dict[str, Any]:
    """Run all sync operations. Returns a summary dict.

    Args:
        dry_run: When True, only preview what would be synced (no DB writes).

    Returns:
        Dict with keys: profile, habits, goals, relationships, traits, needs
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
        }

    return {
        "profile": sync_profile(),
        "habits": sync_habits(),
        "goals": sync_goals(),
        "relationships": sync_relationships(),
        "traits": sync_traits(),
        "needs": sync_needs(),
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

    print("DRY RUN — No changes written")
    print(f"  profile.json      → profile table    {'✓ found' if profile_ok else '✗ missing'}")
    print(f"  habits/tracking.csv  → habits table     {'✓ found' if habits_ok else '✗ missing'}")
    print(f"  goals/*.md        → goals table       {'✓ found' if goals_ok else '✗ missing or empty'}")
    print(f"  relationships/*.md  → relationships table {'✓ found' if rel_ok else '✗ missing or empty'}")
    print(f"  traits/*.json     → traits table      {'✓ found' if traits_ok else '✗ missing'}")
    print(f"  needs/*.json      → needs table       {'✓ found' if needs_ok else '✗ missing'}")


def _format_summary(results: dict[str, Any]):
    print("\nSync Summary:")
    print(f"  Profile        → {results.get('profile', '?')} row(s)")
    print(f"  Habits         → {results.get('habits', '?')} row(s)")
    print(f"  Goals          → {results.get('goals', '?')} row(s)")
    print(f"  Relationships  → {results.get('relationships', '?')} row(s)")
    print(f"  Traits         → {results.get('traits', '?')} row(s)")
    print(f"  Needs          → {results.get('needs', '?')} row(s)")


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
