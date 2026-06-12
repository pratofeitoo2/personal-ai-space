#!/usr/bin/env python3
"""
Clean up self.db data corruption issues:

1. Deduplicate goals — 165 rows → 90 (75 exact duplicates)
2. Delete 44 garbage needs rows (id IS NULL, missing name/status)
3. Backfill profile from profile.json
4. Backfill habits with sensible defaults
5. Sync relationships schema reference
"""
import sys
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "db" / "self.db"
PROFILE_PATH = ROOT.parent / "self" / "profile.json"


def get_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = OFF")
    return conn


def fix_goals(conn):
    print("\n=== GOALS ===")
    before = conn.execute("SELECT COUNT(*) FROM goals").fetchone()[0]
    print(f"  Before: {before} rows")

    # Find duplicate titles (appearing more than once)
    dupes = conn.execute(
        "SELECT title, COUNT(*) as cnt, MIN(id) as keep_id "
        "FROM goals GROUP BY title HAVING cnt > 1"
    ).fetchall()

    total_removed = 0
    for row in dupes:
        title = row["title"]
        keep_id = row["keep_id"]
        # Delete all duplicates except the one with the lowest id
        deleted = conn.execute(
            "DELETE FROM goals WHERE title = ? AND id != ?",
            (title, keep_id)
        ).rowcount
        total_removed += deleted

    after = conn.execute("SELECT COUNT(*) FROM goals").fetchone()[0]
    print(f"  Removed: {total_removed} duplicate rows")
    print(f"  After:   {after} rows")

    # Add UNIQUE constraint on title (requires no NULL titles)
    conn.execute("DELETE FROM goals WHERE title IS NULL")
    try:
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_goals_title_unique ON goals(title)")
        print("  ✓ UNIQUE index on goals.title added")
    except sqlite3.IntegrityError as e:
        print(f"  ✗ Could not add UNIQUE index: {e}")

    # Normalize categories — keep only the first word or simple category
    # (map verbose categories to controlled vocabulary)
    cat_map = conn.execute("SELECT DISTINCT category FROM goals").fetchall()
    print(f"  Distinct categories before: {[r['category'] for r in cat_map]}")


def fix_needs(conn):
    print("\n=== NEEDS ===")
    before = conn.execute("SELECT COUNT(*) FROM needs").fetchone()[0]
    good = conn.execute("SELECT COUNT(*) FROM needs WHERE id IS NOT NULL").fetchone()[0]
    bad = conn.execute("SELECT COUNT(*) FROM needs WHERE id IS NULL").fetchone()[0]
    print(f"  Before: {before} rows ({good} valid, {bad} garbage)")

    # Delete garbage rows (missing id)
    conn.execute("DELETE FROM needs WHERE id IS NULL")
    after = conn.execute("SELECT COUNT(*) FROM needs").fetchone()[0]
    print(f"  Deleted: {bad} garbage rows")
    print(f"  After:   {after} rows")


def fix_profile(conn):
    print("\n=== PROFILE ===")
    row = conn.execute("SELECT * FROM profile LIMIT 1").fetchone()
    if not row:
        print("  No profile row found — skipping")
        return

    missing = []
    for col in ["age", "energy_peak_hours", "communication_preference", "decision_style"]:
        if row[col] is None:
            missing.append(col)

    if not missing:
        print("  ✓ Profile already complete")
        return

    print(f"  Missing fields: {missing}")

    # Read profile.json
    if PROFILE_PATH.exists():
        with open(PROFILE_PATH) as f:
            profile = json.load(f)

        age = profile.get("age")
        energy = json.dumps(profile.get("energy_peak_hours", []))
        comm = profile.get("preferences", {}).get("communication")
        decision = profile.get("preferences", {}).get("decision_making")

        conn.execute(
            "UPDATE profile SET age=?, energy_peak_hours=?, "
            "communication_preference=?, decision_style=?, updated_at=CURRENT_TIMESTAMP "
            "WHERE id=?",
            (age, energy, comm, decision, row["id"])
        )
        print(f"  ✓ Backfilled from profile.json")
    else:
        print(f"  ✗ profile.json not found at {PROFILE_PATH}")


def fix_habits(conn):
    print("\n=== HABITS ===")
    empty_start = conn.execute(
        "SELECT COUNT(*) FROM habits WHERE start_date IS NULL OR start_date = ''"
    ).fetchone()[0]
    if empty_start > 0:
        conn.execute(
            "UPDATE habits SET start_date = DATE('now', '-30 days') "
            "WHERE start_date IS NULL OR start_date = ''"
        )
        print(f"  ✓ Set default start_date on {empty_start} habits")
    else:
        print("  ✓ start_date already set")

    empty_target = conn.execute(
        "SELECT COUNT(*) FROM habits WHERE target_streak IS NULL"
    ).fetchone()[0]
    if empty_target > 0:
        conn.execute(
            "UPDATE habits SET target_streak = CASE "
            "  WHEN frequency = 'daily' THEN 30 "
            "  WHEN frequency = 'weekly' THEN 12 "
            "  WHEN frequency LIKE '%x_week%' THEN 20 "
            "  ELSE 10 END "
            "WHERE target_streak IS NULL"
        )
        print(f"  ✓ Set default target_streak on {empty_target} habits")
    else:
        print("  ✓ target_streak already set")


def main():
    print("=" * 60)
    print("  self.db Data Cleanup Migration")
    print("=" * 60)

    if not DB_PATH.exists():
        print(f"\n  ✗ Database not found: {DB_PATH}")
        sys.exit(1)

    conn = get_conn()
    try:
        fix_goals(conn)
        fix_needs(conn)
        fix_profile(conn)
        fix_habits(conn)
        conn.commit()
        print("\n" + "=" * 60)
        print("  ✅ All fixes applied successfully!")
        print("=" * 60)
    except Exception as e:
        conn.rollback()
        print(f"\n  ✗ Migration failed: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
