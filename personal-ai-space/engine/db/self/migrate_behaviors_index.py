"""Migration: Replace behaviors unique index to include observed_date.

Old: UNIQUE INDEX idx_behaviors_unique ON behaviors(behavior_type, response)
New: UNIQUE INDEX idx_behaviors_unique ON behaviors(behavior_type, response, observed_date)

This enables per-day analytics records — the same word on different dates
is no longer a duplicate.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "self.db"


def main():
    print("=== Migrating behaviors unique index ===\n")
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # Check old index exists
    cursor.execute(
        "SELECT count(*) FROM sqlite_master WHERE type='index' AND name='idx_behaviors_unique'"
    )
    old_exists = cursor.fetchone()[0] > 0

    if old_exists:
        cursor.execute(
            "SELECT sql FROM sqlite_master WHERE type='index' AND name='idx_behaviors_unique'"
        )
        old_sql = cursor.fetchone()[0]
        print(f"  Found existing index: {old_sql}")

        if "observed_date" in old_sql:
            print("  = Index already includes observed_date (skipped)")
        else:
            cursor.execute("DROP INDEX idx_behaviors_unique")
            cursor.execute(
                "CREATE UNIQUE INDEX idx_behaviors_unique ON behaviors(behavior_type, response, observed_date)"
            )
            print("  + Dropped old index, created new index with observed_date")
    else:
        cursor.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_behaviors_unique ON behaviors(behavior_type, response, observed_date)"
        )
        print("  + Created new index with observed_date (no old index found)")

    # Verify
    cursor.execute(
        "SELECT sql FROM sqlite_master WHERE type='index' AND name='idx_behaviors_unique'"
    )
    new_sql = cursor.fetchone()[0]
    print(f"\n  Final index: {new_sql}")

    conn.commit()
    conn.close()
    print("\n✓ Behaviors index migration complete.")


if __name__ == "__main__":
    main()
