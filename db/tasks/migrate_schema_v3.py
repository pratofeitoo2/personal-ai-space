#!/usr/bin/env python3
"""
migrate_schema_v3.py — Partition tasks into active + archive tables.

Design:
  - `tasks`           → only active tasks  (pending, in_progress, blocked)
  - `task_archive`     → completed/cancelled tasks (with archived_at timestamp)
  - `tasks_v`          → UNION ALL view over both tables (backward-compatible reads)

Why:
  - Active-task queries (daily view, overdue, reminder checks) scan only
    active rows — no index filtering needed, no completed rows to skip.
  - Analytics queries use `tasks_v` for the full picture.
  - Completed tasks accumulate in archive without slowing daily operations.

Migration steps:
  1. Create `task_archive` table (same columns + archived_at, no FK constraints)
  2. Move ALL completed/cancelled tasks from `tasks` → `task_archive`
  3. Clean up task_dependencies referencing archived tasks
  4. Add partial indexes on `tasks` (active-only) and `task_archive` (by date/project)
  5. Create `tasks_v` UNION ALL view
  6. Recreate the `tasks` status index (old full-index replaced by partial)

Run:
    python3 migrate_schema_v3.py        # Normal migration
    python3 migrate_schema_v3.py --dry-run   # Preview only

Canonical schema: engine/db/tasks/schema_tasks.sql
"""
import argparse
import sqlite3
import logging
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("migrate_v3")

DB_PATH = Path(__file__).parent / "tasks.db"


def get_conn(dry_run: bool = False):
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = OFF")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def table_exists(conn, name: str) -> bool:
    row = conn.execute(
        "SELECT count(*) as n FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    ).fetchone()
    return row["n"] > 0


def index_exists(conn, name: str) -> bool:
    row = conn.execute(
        "SELECT count(*) as n FROM sqlite_master WHERE type='index' AND name=?",
        (name,),
    ).fetchone()
    return row["n"] > 0


def view_exists(conn, name: str) -> bool:
    row = conn.execute(
        "SELECT count(*) as n FROM sqlite_master WHERE type='view' AND name=?",
        (name,),
    ).fetchone()
    return row["n"] > 0


def create_task_archive(conn, dry_run: bool):
    """Create task_archive table with same structure + archived_at."""
    logger.info("  [1/5] Creating task_archive table…")

    if table_exists(conn, "task_archive"):
        logger.info("    ✓ task_archive already exists — skipping")
        # Verify schema has archived_at
        cols = {row["name"] for row in conn.execute("PRAGMA table_info(task_archive)")}
        if "archived_at" not in cols:
            logger.info("    + Adding archived_at column…")
            if not dry_run:
                conn.execute(
                    "ALTER TABLE task_archive ADD COLUMN archived_at "
                    "DATETIME DEFAULT CURRENT_TIMESTAMP"
                )
        return

    if dry_run:
        logger.info("    ✓ WOULD CREATE task_archive")
        return

    conn.executescript("""
        CREATE TABLE task_archive (
            id              TEXT PRIMARY KEY,
            title           TEXT NOT NULL,
            description     TEXT,
            project_id      TEXT,
            parent_task_id  TEXT,
            priority        TEXT NOT NULL DEFAULT 'normal'
                CHECK(priority IN ('critical','high','normal','low')),
            status          TEXT NOT NULL DEFAULT 'completed'
                CHECK(status IN ('completed','cancelled')),
            progress_pct    INTEGER DEFAULT 0 CHECK(progress_pct BETWEEN 0 AND 100),
            estimated_hours REAL,
            actual_hours    REAL,
            sort_order      INTEGER DEFAULT 0,
            assigned_to     TEXT,
            tags            TEXT,
            recurrence      TEXT,
            category        TEXT DEFAULT 'general',
            due_date        DATETIME,
            completed_at    DATETIME,
            created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
            archived_at     DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """)
    logger.info("    ✓ Created task_archive")


def migrate_completed_tasks(conn, dry_run: bool):
    """Move all completed/cancelled tasks from tasks → task_archive."""
    logger.info("  [2/5] Moving completed/cancelled tasks to archive…")

    completed = conn.execute(
        "SELECT * FROM tasks WHERE status IN ('completed','cancelled')"
    ).fetchall()

    if not completed:
        logger.info("    ✓ No completed tasks to migrate")
        return

    logger.info("    Found %d completed/cancelled tasks", len(completed))

    if dry_run:
        for row in completed:
            logger.info("    WOULD ARCHIVE: %s | %s | %s",
                        row["id"][:8], row["title"][:50], row["status"])
        return

    moved = 0
    for row in completed:
        conn.execute(
            """INSERT OR IGNORE INTO task_archive
               (id, title, description, project_id, parent_task_id, priority, status,
                progress_pct, estimated_hours, actual_hours, sort_order, assigned_to,
                tags, recurrence, category, due_date, completed_at, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                row["id"], row["title"], row["description"], row["project_id"],
                row["parent_task_id"], row["priority"], row["status"],
                row["progress_pct"], row["estimated_hours"], row["actual_hours"],
                row["sort_order"], row["assigned_to"], row["tags"], row["recurrence"],
                row["category"], row["due_date"], row["completed_at"],
                row["created_at"], row["updated_at"],
            ),
        )
        conn.execute("DELETE FROM tasks WHERE id = ?", (row["id"],))
        moved += 1

    logger.info("    ✓ Archived %d tasks", moved)


def cleanup_dependencies(conn, dry_run: bool):
    """Remove dependency rows referencing archived tasks (blockers are resolved)."""
    logger.info("  [3/5] Cleaning up dependencies on archived tasks…")

    archived_ids = conn.execute(
        "SELECT id FROM task_archive"
    ).fetchall()
    if not archived_ids:
        logger.info("    ✓ No archive entries — nothing to clean")
        return

    ids = tuple(r["id"] for r in archived_ids)

    # Count deps to clean
    dep_rows = conn.execute(
        f"SELECT count(*) as n FROM task_dependencies "
        f"WHERE task_id IN ({','.join('?' * len(ids))}) "
        f"OR depends_on IN ({','.join('?' * len(ids))})",
        ids + ids,
    ).fetchone()

    count = dep_rows["n"] if dep_rows else 0
    if count == 0:
        logger.info("    ✓ No stale dependencies found")
        return

    if dry_run:
        logger.info("    WOULD DELETE %d stale dependency rows", count)
        return

    conn.execute(
        f"DELETE FROM task_dependencies "
        f"WHERE task_id IN ({','.join('?' * len(ids))}) "
        f"OR depends_on IN ({','.join('?' * len(ids))})",
        ids + ids,
    )
    logger.info("    ✓ Removed %d stale dependencies", count)


def add_partial_indexes(conn, dry_run: bool):
    """Add partial indexes for common query patterns."""
    logger.info("  [4/5] Adding partial indexes…")

    indexes = [
        # Active-task indexes (only on tasks table — which now holds only active)
        ("idx_tasks_status", "CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)"),
        ("idx_tasks_active_due", "CREATE INDEX IF NOT EXISTS idx_tasks_active_due ON tasks(due_date) WHERE status IN ('pending','in_progress','blocked')"),
        ("idx_tasks_active_priority", "CREATE INDEX IF NOT EXISTS idx_tasks_active_priority ON tasks(priority) WHERE status IN ('pending','in_progress','blocked')"),

        # Archive indexes (for querying history)
        ("idx_archive_completed_date", "CREATE INDEX IF NOT EXISTS idx_archive_completed_date ON task_archive(completed_at) WHERE status = 'completed'"),
        ("idx_archive_project", "CREATE INDEX IF NOT EXISTS idx_archive_project ON task_archive(project_id)"),
        ("idx_archive_archived_at", "CREATE INDEX IF NOT EXISTS idx_archive_archived_at ON task_archive(archived_at DESC)"),
        ("idx_archive_status", "CREATE INDEX IF NOT EXISTS idx_archive_status ON task_archive(status)"),
    ]

    for idx_name, ddl in indexes:
        if not index_exists(conn, idx_name):
            if dry_run:
                logger.info("    WOULD CREATE INDEX: %s", idx_name)
            else:
                conn.execute(ddl)
                logger.info("    ✓ Created index: %s", idx_name)
        else:
            logger.debug("    = Already exists: %s", idx_name)


def create_union_view(conn, dry_run: bool):
    """Create tasks_v UNION ALL view for backward-compatible reads."""
    logger.info("  [5/5] Creating tasks_v UNION ALL view…")

    view_ddl = """
        CREATE VIEW IF NOT EXISTS tasks_v AS
        SELECT
            id, title, description, project_id, parent_task_id,
            priority, status,
            progress_pct, estimated_hours, actual_hours,
            sort_order, assigned_to, tags, recurrence, category,
            due_date, completed_at, created_at, updated_at
        FROM tasks
        UNION ALL
        SELECT
            id, title, description, project_id, parent_task_id,
            priority, status,
            progress_pct, estimated_hours, actual_hours,
            sort_order, assigned_to, tags, recurrence, category,
            due_date, completed_at, created_at, updated_at
        FROM task_archive
    """

    if view_exists(conn, "tasks_v"):
        logger.info("    ✓ tasks_v already exists — recreating")
        if not dry_run:
            conn.execute("DROP VIEW IF EXISTS tasks_v")
            conn.execute(view_ddl)
    else:
        if dry_run:
            logger.info("    WOULD CREATE VIEW: tasks_v")
        else:
            conn.execute(view_ddl)
            logger.info("    ✓ Created tasks_v")


# ── Post-migration: archive running tasks ───────────────────────────────


def archive_completed_tasks() -> int:
    """
    Public helper: move any completed/cancelled tasks from `tasks`
    to `task_archive`. Designed to be called periodically (e.g. from
    scheduler) to keep the tasks table lean.
    """
    import db_manager as db

    completed = db.query(
        "tasks",
        "SELECT * FROM tasks WHERE status IN ('completed','cancelled')"
    )
    if not completed:
        return 0

    moved = 0
    for row in completed:
        db.execute("tasks", """
            INSERT OR IGNORE INTO task_archive
            (id, title, description, project_id, parent_task_id, priority, status,
             progress_pct, estimated_hours, actual_hours, sort_order, assigned_to,
             tags, recurrence, category, due_date, completed_at, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            row["id"], row["title"], row["description"], row["project_id"],
            row["parent_task_id"], row["priority"], row["status"],
            row["progress_pct"], row["estimated_hours"], row["actual_hours"],
            row["sort_order"], row["assigned_to"], row["tags"], row["recurrence"],
            row["category"], row["due_date"], row["completed_at"],
            row["created_at"], row["updated_at"],
        ))
        db.execute("tasks",
            "DELETE FROM task_dependencies WHERE task_id = ? OR depends_on = ?",
            (row["id"], row["id"]))
        db.execute("tasks", "DELETE FROM tasks WHERE id = ?", (row["id"],))
        moved += 1

    return moved


# ── CLI ──────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Migrate tasks.db v2 → v3: partition tasks into active + archive",
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview only, no changes written")
    args = parser.parse_args()

    if not DB_PATH.exists():
        logger.error("Database not found: %s", DB_PATH)
        return 1

    logger.info("=" * 55)
    logger.info("  Schema Migration v3 — Tasks Partition")
    logger.info("=" * 55)

    if args.dry_run:
        logger.info("  DRY RUN — No changes written\n")

    conn = get_conn(dry_run=args.dry_run)

    try:
        logger.info("")
        create_task_archive(conn, args.dry_run)
        migrate_completed_tasks(conn, args.dry_run)
        cleanup_dependencies(conn, args.dry_run)
        add_partial_indexes(conn, args.dry_run)
        create_union_view(conn, args.dry_run)

        if not args.dry_run:
            conn.commit()

            # Verify
            active = conn.execute("SELECT count(*) as n FROM tasks").fetchone()["n"]
            archived = conn.execute("SELECT count(*) as n FROM task_archive").fetchone()["n"]
            view_count = conn.execute("SELECT count(*) as n FROM tasks_v").fetchone()["n"]
            deps = conn.execute("SELECT count(*) as n FROM task_dependencies").fetchone()["n"]

            logger.info("")
            logger.info("=" * 55)
            logger.info("  ✓ Migration Complete")
            logger.info("=" * 55)
            logger.info("  Active tasks:      %d", active)
            logger.info("  Archived tasks:    %d", archived)
            logger.info("  Total (tasks_v):   %d", view_count)
            logger.info("  Dependencies:      %d", deps)
            logger.info("=" * 55)
        else:
            logger.info("")
            logger.info("  DRY RUN — No changes written")

    except Exception as e:
        conn.rollback()
        logger.error("Migration failed: %s", e)
        raise
    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    exit(main())
