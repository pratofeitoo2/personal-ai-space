"""Phase 5: Align goals table schema with schema_self.sql, add progress tracking columns.

All changes are additive (ALTER TABLE ADD COLUMN). No data loss risk.
Idempotent — safe to re-run.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "self.db"


def column_exists(cursor, table, column):
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())


def add_column(cursor, table, column, definition):
    if not column_exists(cursor, table, column):
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        print(f"  + Added {table}.{column}")
    else:
        print(f"  = {table}.{column} already exists (skipped)")


def main():
    print("=== Migrating self.db goals table ===\n")
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    add_column(cursor, "goals", "progress", "REAL DEFAULT 0")
    add_column(cursor, "goals", "target_date", "TEXT")
    add_column(cursor, "goals", "progress_source", "TEXT DEFAULT 'independent'")

    # Add UNIQUE index on title if not present
    cursor.execute(
        "SELECT count(*) FROM sqlite_master WHERE type='index' AND name='idx_goals_title_unique'"
    )
    if cursor.fetchone()[0] == 0:
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_goals_title_unique ON goals(title)")
        print("  + Created idx_goals_title_unique")
    else:
        print("  = idx_goals_title_unique already exists (skipped)")

    # Verify final schema
    cursor.execute("PRAGMA table_info(goals)")
    cols = [row[1] for row in cursor.fetchall()]
    print(f"\n  Final goals columns: {', '.join(cols)}")

    conn.commit()
    conn.close()
    print("\n✓ Goals migration complete. Ready for user input.")


if __name__ == "__main__":
    main()
