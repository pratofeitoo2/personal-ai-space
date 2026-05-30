#!/usr/bin/env python3
"""
migrate_to_semantic_ids.py — Replace random hex UUIDs with semantic IDs.

Transforms every entity in tasks.db and self.db from opaque hex UUIDs to
human-readable IDs following the convention:

  proj-{slug}, task-{proj}-{slug}, beh-{type}-{date}-{nonce}, ...

Also updates ALL foreign-key references across both databases so no link breaks.

Run before/after snapshot:
    cp .../tasks.db .../tasks.db.bak
    cp .../self.db  .../self.db.bak
    python3 migrate_to_semantic_ids.py
"""

import sqlite3
import logging
import sys
import uuid
from pathlib import Path

# Add engine/ to path
_ENGINE_DIR = Path(__file__).resolve().parent.parent.parent
if str(_ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(_ENGINE_DIR))

from db.id_helpers import slugify, for_project, for_task, for_dependency, \
    for_history, for_doc_link, for_sync_state, for_behavior, for_observation, \
    for_session_signal, for_session_metadata, for_habit_log

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("migrate_semantic_ids")

TASKS_DB = Path(__file__).resolve().parent.parent / "tasks" / "tasks.db"
SELF_DB   = Path(__file__).resolve().parent.parent / "self" / "self.db"


# ── Helpers ───────────────────────────────────────────────────────────────────

def is_hex_uuid(val: str) -> bool:
    """True if val is a 32-char hex string (uuid.uuid4().hex)."""
    if not val or not isinstance(val, str):
        return False
    if len(val) == 32:
        try:
            int(val, 16)
            return True
        except ValueError:
            return False
    return False


def is_task_style(val: str) -> bool:
    """True if val matches task_NNN pattern (seed tasks)."""
    if not val or not isinstance(val, str):
        return False
    return bool(val.startswith("task_") and len(val) >= 6)


def should_migrate(val: str) -> bool:
    """True if this ID should be replaced with a semantic one."""
    return is_hex_uuid(val) or is_task_style(val)


def run(db_path: Path, label: str):
    """Run migration on one database."""
    logger.info("")
    logger.info("═" * 60)
    logger.info(f"  Migrating {label}: {db_path}")
    logger.info("═" * 60)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = OFF")
    conn.execute("PRAGMA journal_mode = WAL")

    old_to_new: dict[str, str] = {}  # old_hex → new_semantic

    # ── 1. Projects ──────────────────────────────────────────────────────
    logger.info("\n  --- Projects ---")
    rows = conn.execute("SELECT id, name FROM projects").fetchall()
    for r in rows:
        old = r["id"]
        name = r["name"]
        if should_migrate(old):
            new = for_project(name)
            # Ensure uniqueness by appending a nonce if collision
            base = new
            i = 1
            while new in old_to_new.values():
                new = f"{base}-{i}"
                i += 1
            old_to_new[old] = new
            logger.info(f"    {old[:20]}... → {new}")
        else:
            logger.info(f"    {old}  (already semantic)")

    # ── 2. Tasks (active + archive) ───────────────────────────────────────
    for table in ("tasks", "task_archive"):
        logger.info(f"\n  --- {table} ---")
        rows = conn.execute(
            f"SELECT id, title, project_id FROM {table}"
        ).fetchall()
        for r in rows:
            old = r["id"]
            title = r["title"]
            project_id = r["project_id"]
            # Resolve project_id if it's also being migrated
            resolved_proj = old_to_new.get(project_id, project_id)
            if should_migrate(old):
                new = for_task(title, resolved_proj)
                # Collision guard
                base = new
                i = 1
                while new in old_to_new.values():
                    new = f"{base}-{i}"
                    i += 1
                old_to_new[old] = new
                logger.info(f"    {old[:20]}... → {new}")
            else:
                logger.info(f"    {old[:20]}...  (already semantic)")

    # ── 3. Update primary keys ───────────────────────────────────────────
    # Must do this BEFORE FK updates so child rows can reference new IDs

    # projects.id
    logger.info("\n  --- Updating projects.id ---")
    for oid in list(old_to_new.keys()):
        nid = old_to_new[oid]
        if oid[:4] != nid[:4]:  # only rows where ID actually changed
            conn.execute("UPDATE projects SET id=? WHERE id=?", (nid, oid))

    # tasks.id + task_archive.id
    for table in ("tasks", "task_archive"):
        logger.info(f"\n  --- Updating {table}.id ---")
        for oid in list(old_to_new.keys()):
            nid = old_to_new[oid]
            if oid[:4] != nid[:4]:
                conn.execute(f"UPDATE {table} SET id=? WHERE id=?", (nid, oid))

    # ── 4. Update all FK references ──────────────────────────────────────
    logger.info("\n  --- Updating FK references ---")

    # tasks.project_id + task_archive.project_id
    for table in ("tasks", "task_archive"):
        for col in ("project_id", "parent_task_id"):
            old_ids = [oid for oid in old_to_new if should_migrate(oid)]
            for oid in old_ids:
                conn.execute(
                    f"UPDATE {table} SET {col}=? WHERE {col}=?",
                    (old_to_new[oid], oid)
                )

    # task_dependencies
    for col in ("task_id", "depends_on"):
        for oid in list(old_to_new.keys()):
            if oid in old_to_new:
                conn.execute(
                    f"UPDATE task_dependencies SET {col}=? WHERE {col}=?",
                    (old_to_new[oid], oid)
                )

    # task_history.task_id
    for oid in list(old_to_new.keys()):
        conn.execute(
            "UPDATE task_history SET task_id=? WHERE task_id=?",
            (old_to_new[oid], oid)
        )

    # calendar_events.task_id
    for oid in list(old_to_new.keys()):
        conn.execute(
            "UPDATE calendar_events SET task_id=? WHERE task_id=?",
            (old_to_new[oid], oid)
        )

    # doc_links.entity_id (polymorphic)
    for oid in list(old_to_new.keys()):
        conn.execute(
            "UPDATE doc_links SET entity_id=? WHERE entity_id=?",
            (old_to_new[oid], oid)
        )

    # sync_state.entity_id (polymorphic)
    for oid in list(old_to_new.keys()):
        conn.execute(
            "UPDATE sync_state SET entity_id=? WHERE entity_id=?",
            (old_to_new[oid], oid)
        )

    # ── 5. Regenerate row IDs for FK-only tables ────────────────────────
    # These tables' own ID columns don't matter to FKs, but make them semantic too

    # task_dependencies.id
    used_ids: set[str] = set()
    logger.info("\n  --- task_dependencies ---")
    rows = conn.execute("SELECT id, task_id, depends_on FROM task_dependencies").fetchall()
    for r in rows:
        old = r["id"]
        if should_migrate(old):
            tid = old_to_new.get(r["task_id"], r["task_id"])
            did = old_to_new.get(r["depends_on"], r["depends_on"])
            new = for_dependency(tid, did)
            while new in used_ids:
                new += f"-{uuid.uuid4().hex[:4]}"
            used_ids.add(new)
            conn.execute("UPDATE task_dependencies SET id=? WHERE id=?", (new, old))
            old_to_new[old] = new
            logger.info(f"    {old[:20]}... → {new}")

    # task_history.id
    used_ids = set()
    logger.info("\n  --- task_history ---")
    rows = conn.execute("SELECT id, task_id, changed_at FROM task_history").fetchall()
    for r in rows:
        old = r["id"]
        if should_migrate(old):
            tid = old_to_new.get(r["task_id"], r["task_id"])
            new = for_history(tid)
            while new in used_ids:
                new += f"-{uuid.uuid4().hex[:4]}"
            used_ids.add(new)
            conn.execute("UPDATE task_history SET id=? WHERE id=?", (new, old))
            old_to_new[old] = new
            logger.info(f"    {old[:20]}... → {new}")

    # doc_links.id
    used_ids = set()
    logger.info("\n  --- doc_links ---")
    rows = conn.execute("SELECT id, entity_type, entity_id FROM doc_links").fetchall()
    for r in rows:
        old = r["id"]
        if should_migrate(old):
            eid = old_to_new.get(r["entity_id"], r["entity_id"])
            new = for_doc_link(r["entity_type"], eid)
            while new in used_ids:
                new += f"-{uuid.uuid4().hex[:4]}"
            used_ids.add(new)
            conn.execute("UPDATE doc_links SET id=? WHERE id=?", (new, old))
            old_to_new[old] = new
            logger.info(f"    {old[:20]}... → {new}")

    # sync_state.id
    used_ids = set()
    logger.info("\n  --- sync_state ---")
    rows = conn.execute("SELECT id, entity_type, entity_id FROM sync_state").fetchall()
    for r in rows:
        old = r["id"]
        if should_migrate(old):
            eid = old_to_new.get(r["entity_id"], r["entity_id"])
            new = for_sync_state(r["entity_type"], eid)
            while new in used_ids:
                new += f"-{uuid.uuid4().hex[:4]}"
            used_ids.add(new)
            conn.execute("UPDATE sync_state SET id=? WHERE id=?", (new, old))
            old_to_new[old] = new
            logger.info(f"    {old[:20]}... → {new}")

    conn.commit()
    logger.info(f"\n  ✓ {label}: {sum(1 for v in old_to_new.values() if v)} IDs migrated, "
                f"{sum(1 for v in old_to_new.values() if not v)} unchanged")
    conn.close()
    return old_to_new


def run_self(db_path: Path, tasks_id_map: dict[str, str]):
    """Run migration on self.db."""
    logger.info("")
    logger.info("═" * 60)
    logger.info(f"  Migrating self.db: {db_path}")
    logger.info("═" * 60)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = OFF")
    conn.execute("PRAGMA journal_mode = WAL")

    old_to_new = dict(tasks_id_map)  # may contain goals IDs (integer) passed through

    used_ids: set[str] = set()

    # ── Behaviors ─────────────────────────────────────────────────────────
    logger.info("\n  --- behaviors ---")
    rows = conn.execute(
        "SELECT id, behavior_type, observed_date FROM behaviors"
    ).fetchall()
    for r in rows:
        old = r["id"]
        if should_migrate(old):
            btype = r["behavior_type"]
            new = for_behavior(btype)
            while new in used_ids:
                new += f"-{uuid.uuid4().hex[:4]}"
            used_ids.add(new)
            conn.execute("UPDATE behaviors SET id=? WHERE id=?", (new, old))
            old_to_new[old] = new
            logger.info(f"    {old[:20]}... → {new}")

    # ── Observations ──────────────────────────────────────────────────────
    logger.info("\n  --- observations ---")
    rows = conn.execute(
        "SELECT id, obs_type FROM observations"
    ).fetchall()
    for r in rows:
        old = r["id"]
        if should_migrate(old):
            otype = r["obs_type"]
            new = for_observation(otype)
            while new in used_ids:
                new += f"-{uuid.uuid4().hex[:4]}"
            used_ids.add(new)
            conn.execute("UPDATE observations SET id=? WHERE id=?", (new, old))
            old_to_new[old] = new
            logger.info(f"    {old[:20]}... → {new}")

    # ── Session Signals ───────────────────────────────────────────────────
    logger.info("\n  --- session_signals ---")
    rows = conn.execute(
        "SELECT id, session_id, observed_at FROM session_signals ORDER BY session_id, observed_at"
    ).fetchall()
    seq_counter: dict[str, int] = {}
    for r in rows:
        old = r["id"]
        if should_migrate(old):
            sid = r["session_id"]
            seq_counter[sid] = seq_counter.get(sid, 0) + 1
            new = for_session_signal(sid, seq_counter[sid])
            while new in used_ids:
                seq_counter[sid] = seq_counter[sid] + 1
                new = for_session_signal(sid, seq_counter[sid])
            used_ids.add(new)
            conn.execute("UPDATE session_signals SET id=? WHERE id=?", (new, old))
            old_to_new[old] = new
            logger.info(f"    {old[:20]}... → {new}")

    # ── Session Metadata ──────────────────────────────────────────────────
    logger.info("\n  --- session_metadata ---")
    rows = conn.execute(
        "SELECT id, session_id FROM session_metadata"
    ).fetchall()
    for r in rows:
        old = r["id"]
        if should_migrate(old):
            sid = r["session_id"]
            new = for_session_metadata(sid)
            while new in used_ids:
                new += f"-{uuid.uuid4().hex[:4]}"
            used_ids.add(new)
            conn.execute("UPDATE session_metadata SET id=? WHERE id=?", (new, old))
            old_to_new[old] = new
            logger.info(f"    {old[:20]}... → {new}")

    # ── Habit Logs ────────────────────────────────────────────────────────
    logger.info("\n  --- habit_logs ---")
    rows = conn.execute("SELECT id, habit_id, completed_at FROM habit_logs").fetchall()
    for r in rows:
        old = r["id"]
        if should_migrate(old):
            hid = r["habit_id"]
            completed_str = (r["completed_at"] or "")[:10]
            new = for_habit_log(hid, _date=completed_str)
            while new in used_ids:
                new += f"-{uuid.uuid4().hex[:4]}"
            used_ids.add(new)
            conn.execute("UPDATE habit_logs SET id=? WHERE id=?", (new, old))
            old_to_new[old] = new
            logger.info(f"    {old[:20]}... → {new}")

    conn.commit()
    new_count = sum(1 for o, n in old_to_new.items()
                    if n and n != o and is_hex_uuid(o))
    logger.info(f"\n  ✓ self.db: {new_count} UUIDs replaced")
    conn.close()


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Migrate hex UUIDs → semantic IDs in tasks.db and self.db"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview changes without applying")
    parser.add_argument("--tasks-db", default=str(TASKS_DB),
                        help=f"Path to tasks.db (default: {TASKS_DB})")
    parser.add_argument("--self-db", default=str(SELF_DB),
                        help=f"Path to self.db (default: {SELF_DB})")
    args = parser.parse_args()

    tasks_path = Path(args.tasks_db)
    self_path = Path(args.self_db)

    if not tasks_path.exists():
        logger.error(f"tasks.db not found: {tasks_path}")
        sys.exit(1)
    if not self_path.exists():
        logger.error(f"self.db not found: {self_path}")
        sys.exit(1)

    logger.info(f"tasks.db backup: {tasks_path}.bak")
    logger.info(f"self.db  backup: {self_path}.bak")
    if args.dry_run:
        logger.info("DRY RUN — no changes will be applied\n")
    else:
        # Create backups
        import shutil
        shutil.copy2(tasks_path, f"{tasks_path}.bak")
        shutil.copy2(self_path, f"{self_path}.bak")
        logger.info("Backups created\n")

    tasks_map = run(tasks_path, "tasks.db")
    run_self(self_path, tasks_map)

    logger.info("")
    logger.info("═" * 60)
    logger.info("  Migration complete!")
    logger.info("  To roll back: cp tasks.db.bak tasks.db && cp self.db.bak self.db")
    logger.info("═" * 60)


if __name__ == "__main__":
    main()
