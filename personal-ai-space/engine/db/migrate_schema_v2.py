"""Phase 1: Add progress tracking, subtask support, doc_links, and sync_state.

All changes are additive (ALTER TABLE ADD COLUMN + CREATE TABLE).
No data loss risk. Idempotent — safe to re-run.
"""

import sqlite3
import uuid
from datetime import datetime

DB_PATH = "engine/db/tasks.db"


def column_exists(cursor: sqlite3.Cursor, table: str, column: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())


def add_column(cursor: sqlite3.Cursor, table: str, column: str, definition: str):
    if not column_exists(cursor, table, column):
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        print(f"  + Added {table}.{column}")
    else:
        print(f"  = {table}.{column} already exists (skipped)")


def now() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def run():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("=== tasks table ===")
    add_column(cursor, "tasks", "parent_task_id", "TEXT REFERENCES tasks(id)")
    add_column(cursor, "tasks", "progress_pct", "INTEGER DEFAULT 0")
    add_column(cursor, "tasks", "sort_order", "INTEGER DEFAULT 0")
    add_column(cursor, "tasks", "updated_at", "DATETIME")

    cursor.execute(
        "UPDATE tasks SET progress_pct = 100 WHERE status = 'completed' AND (progress_pct IS NULL OR progress_pct = 0)"
    )
    cursor.execute("UPDATE tasks SET progress_pct = 0 WHERE progress_pct IS NULL")
    cursor.execute(
        "UPDATE tasks SET updated_at = COALESCE(completed_at, created_at) WHERE updated_at IS NULL"
    )
    print(f"  ~ Backfilled progress_pct (completed→100, others→0)")
    print(f"  ~ Backfilled updated_at from completed_at/created_at")

    print("=== projects table ===")
    add_column(cursor, "projects", "priority", "TEXT DEFAULT 'normal'")
    add_column(cursor, "projects", "progress_pct", "INTEGER DEFAULT 0")
    add_column(cursor, "projects", "category", "TEXT DEFAULT 'general'")
    add_column(cursor, "projects", "updated_at", "DATETIME")

    cursor.execute("UPDATE projects SET progress_pct = 0 WHERE progress_pct IS NULL")
    cursor.execute("UPDATE projects SET updated_at = created_at WHERE updated_at IS NULL")
    print(f"  ~ Backfilled projects fields")

    print("=== task_dependencies table ===")
    add_column(cursor, "task_dependencies", "dependency_type", "TEXT DEFAULT 'blocks'")
    add_column(cursor, "task_dependencies", "created_at", "DATETIME")
    cursor.execute(
        "UPDATE task_dependencies SET created_at = (SELECT MIN(created_at) FROM tasks WHERE id = task_id) WHERE created_at IS NULL"
    )

    print("=== task_history table ===")
    add_column(cursor, "task_history", "changed_by", "TEXT DEFAULT 'system'")

    print("=== doc_links table (NEW) ===")
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS doc_links (
            id TEXT PRIMARY KEY,
            entity_type TEXT NOT NULL CHECK(entity_type IN ('project','task')),
            entity_id TEXT NOT NULL,
            file_path TEXT NOT NULL,
            link_type TEXT DEFAULT 'documents'
                CHECK(link_type IN ('documents','specifies','notes','journal','reference','goal')),
            frontmatter_status TEXT,
            last_synced DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(entity_type, entity_id, file_path)
        )"""
    )
    print("  + Created doc_links")

    print("=== sync_state table (NEW) ===")
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS sync_state (
            id TEXT PRIMARY KEY,
            entity_type TEXT NOT NULL,
            entity_id TEXT,
            file_path TEXT NOT NULL,
            file_hash TEXT,
            last_modified DATETIME,
            last_synced DATETIME,
            direction TEXT DEFAULT 'bidirectional'
                CHECK(direction IN ('db_to_file','file_to_db','bidirectional')),
            UNIQUE(entity_type, entity_id, file_path)
        )"""
    )
    print("  + Created sync_state")

    print("=== indexes ===")
    cursor.executescript(
        """
        CREATE INDEX IF NOT EXISTS idx_tasks_parent      ON tasks(parent_task_id);
        CREATE INDEX IF NOT EXISTS idx_tasks_progress     ON tasks(progress_pct);
        CREATE INDEX IF NOT EXISTS idx_tasks_updated      ON tasks(updated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_projects_priority  ON projects(priority);
        CREATE INDEX IF NOT EXISTS idx_projects_updated   ON projects(updated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_doclinks_entity    ON doc_links(entity_type, entity_id);
        CREATE INDEX IF NOT EXISTS idx_doclinks_file      ON doc_links(file_path);
        CREATE INDEX IF NOT EXISTS idx_sync_file          ON sync_state(file_path);
        CREATE INDEX IF NOT EXISTS idx_sync_entity        ON sync_state(entity_type, entity_id);
    """
    )
    print("  + Created indexes")

    conn.commit()
    conn.close()
    print("\n✓ Migration complete. All changes additive, no data lost.")


if __name__ == "__main__":
    run()
