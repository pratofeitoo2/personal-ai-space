"""
Migrate command/calendar/upcoming.csv → calendar.db.

Run once to seed the database from the existing CSV file.
After migration, agents should use DataHub or db_manager to read/write calendar events.
"""
import csv
import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger("engine.db.calendar.migrate")

_CALENDAR_DB = Path(__file__).parent / "calendar.db"
_SCHEMA_FILE = Path(__file__).parent / "schema_calendar.sql"
_CSV_SOURCE = Path(__file__).parent.parent.parent.parent / "command" / "calendar" / "upcoming.csv"


def migrate():
    """Read CSV and populate calendar.db."""
    if not _CSV_SOURCE.exists():
        logger.warning("Source CSV not found at %s — skipping migration", _CSV_SOURCE)
        return 0

    if _CALENDAR_DB.exists():
        logger.warning("calendar.db already exists — run with --force to re-migrate")
        return -1

    conn = sqlite3.connect(str(_CALENDAR_DB))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    with open(_SCHEMA_FILE) as f:
        conn.executescript(f.read())

    count = 0
    with open(_CSV_SOURCE, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            conn.execute(
                """INSERT INTO upcoming
                   (event_date, event_name, event_time, duration_hours, category, status)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    row.get("date", ""),
                    row.get("event", ""),
                    row.get("time", ""),
                    float(row.get("duration_hours", 1)),
                    row.get("category", "general"),
                    row.get("status", "scheduled"),
                ),
            )
            count += 1

    conn.commit()

    row = conn.execute("SELECT COUNT(*) AS n FROM upcoming").fetchone()
    logger.info("Migrated %d events to calendar.db (expected=%d, actual=%d)", count, count, row["n"])
    conn.close()
    return count


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    result = migrate()
    if result > 0:
        print(f"Migration complete: {result} event(s) inserted.")
    elif result == 0:
        print("Nothing to migrate (source CSV not found).")
    else:
        print("Migration skipped (database already exists).")
