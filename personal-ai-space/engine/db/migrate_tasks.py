#!/usr/bin/env python3
"""
Clean up tasks.db data inconsistencies:

1. Fix project_id references (name -> ID)
2. Sync completion_status with actual status
3. Add missing Knowledge Management project
4. Backfill missing columns on existing tasks
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "tasks.db"


def get_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = OFF")
    return conn


def fix_project_references(conn):
    print("\n=== PROJECT REFERENCES ===")
    projects = {
        row["id"]: row["name"]
        for row in conn.execute("SELECT id, name FROM projects").fetchall()
    }
    # Build reverse map: name -> id
    name_to_id = {name: pid for pid, name in projects.items()}
    print(f"  Project IDs: {list(projects.keys())}")
    print(f"  Project names: {list(name_to_id.keys())}")

    tasks = conn.execute(
        "SELECT id, project_id FROM tasks WHERE project_id IS NOT NULL"
    ).fetchall()
    for task in tasks:
        pid = task["project_id"]

        if pid in projects:
            continue  # Already a valid project ID

        if pid in name_to_id:
            conn.execute(
                "UPDATE tasks SET project_id = ? WHERE id = ?",
                (name_to_id[pid], task["id"]),
            )
            print(f"  ✓ Fixed {task['id']}: '{pid}' -> '{name_to_id[pid]}'")
            continue

        # Try case-insensitive match
        matched = [n for n in name_to_id if n.lower() == pid.lower()]
        if matched:
            conn.execute(
                "UPDATE tasks SET project_id = ? WHERE id = ?",
                (name_to_id[matched[0]], task["id"]),
            )
            print(f"  ✓ Fixed {task['id']}: '{pid}' -> '{name_to_id[matched[0]]}'")
        else:
            print(f"  ? {task['id']}: project_id '{pid}' has no matching project")


def ensure_knowledge_project(conn):
    """Create Knowledge Management project if referenced but missing."""
    missing = conn.execute(
        "SELECT DISTINCT project_id FROM tasks "
        "WHERE project_id IS NOT NULL AND project_id NOT IN "
        "(SELECT id FROM projects)"
    ).fetchall()
    for row in missing:
        pid = row["project_id"]
        if pid == "knowledge" or pid == "Knowledge Management":
            conn.execute(
                "INSERT OR IGNORE INTO projects "
                "(id, name, description, status, start_date, total_tasks, completed_tasks) "
                "VALUES (?, ?, ?, ?, date('now'), 0, 0)",
                ("knowledge", "Knowledge Management", "Curate and manage the knowledge base", "active"),
            )
            print(f"  ✓ Created missing project: {pid}")
            conn.execute(
                "UPDATE tasks SET project_id = 'knowledge' WHERE project_id = ?",
                (pid,),
            )
            print(f"  ✓ Re-linked tasks from '{pid}' -> 'knowledge'")


def sync_completion_status(conn):
    print("\n=== COMPLETION STATUS ===")
    # Drop the redundant column (SQLite 3.35+)
    has_col = conn.execute(
        "SELECT COUNT(*) FROM pragma_table_info('tasks') WHERE name='completion_status'"
    ).fetchone()[0]
    if has_col:
        conn.execute("ALTER TABLE tasks DROP COLUMN completion_status")
        print("  ✓ Dropped redundant 'completion_status' column (use 'status' instead)")
    else:
        print("  ✓ No redundant column to drop")


def backfill_categories(conn):
    print("\n=== CATEGORIES ===")
    null_cat = conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE category IS NULL OR category = ''"
    ).fetchone()[0]
    if null_cat:
        conn.execute("UPDATE tasks SET category = 'general' WHERE category IS NULL OR category = ''")
        print(f"  ✓ Backfilled {null_cat} tasks with category='general'")
    else:
        print("  ✓ All tasks have a category")


def main():
    print("=" * 60)
    print("  tasks.db Data Cleanup Migration")
    print("=" * 60)

    if not DB_PATH.exists():
        print(f"\n  ✗ Database not found: {DB_PATH}")
        return

    conn = get_conn()
    try:
        ensure_knowledge_project(conn)
        fix_project_references(conn)
        sync_completion_status(conn)
        backfill_categories(conn)
        conn.commit()

        print("\n" + "=" * 60)
        print("  ✅ All fixes applied successfully!")
        print("=" * 60)

        # Print final state
        print("\n  Final state:")
        for row in conn.execute(
            "SELECT id, title, project_id, priority, status, category FROM tasks"
        ).fetchall():
            print(f"    {row['id']:10} | {row['title']:40} | {row['project_id']:15} | {row['priority']:10} | {row['status']:15} | {row['category']}")
    except Exception as e:
        conn.rollback()
        print(f"\n  ✗ Migration failed: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
