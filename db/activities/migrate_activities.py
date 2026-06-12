"""
Migrate command/activities/disciplined_routines.json → activities.db.

Run once to seed the database from the existing JSON file.
After migration, agents should use DataHub or db_manager to read/write activities.
"""
import json
import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger("engine.db.activities.migrate")

_ACTIVITIES_DB = Path(__file__).parent / "activities.db"
_SCHEMA_FILE = Path(__file__).parent / "schema_activities.sql"
_JSON_SOURCE = Path(__file__).parent.parent.parent.parent / "command" / "activities" / "disciplined_routines.json"


def migrate():
    """Read JSON and populate activities.db."""
    if not _JSON_SOURCE.exists():
        logger.warning("Source JSON not found at %s — skipping migration", _JSON_SOURCE)
        return 0

    if _ACTIVITIES_DB.exists():
        logger.warning("activities.db already exists — run with --force to re-migrate")
        return -1

    with open(_JSON_SOURCE) as f:
        routines = json.load(f)

    conn = sqlite3.connect(str(_ACTIVITIES_DB))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    with open(_SCHEMA_FILE) as f:
        conn.executescript(f.read())

    count = 0
    for entry in routines:
        conn.execute(
            """INSERT OR REPLACE INTO disciplined_routines
               (id, name, frequency, time, duration_minutes, discipline_level, status)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                entry.get("id", ""),
                entry.get("name", ""),
                entry.get("frequency", ""),
                entry.get("time", ""),
                entry.get("duration_minutes", 0),
                entry.get("discipline_level", "medium"),
                entry.get("status", "active"),
            ),
        )
        count += 1

    conn.commit()

    # Verify
    row = conn.execute("SELECT COUNT(*) AS n FROM disciplined_routines").fetchone()
    logger.info("Migrated %d routines to activities.db (expected=%d, actual=%d)", count, len(routines), row["n"])
    conn.close()
    return count


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    result = migrate()
    if result > 0:
        print(f"Migration complete: {result} routine(s) inserted.")
    elif result == 0:
        print("Nothing to migrate (source JSON not found).")
    else:
        print("Migration skipped (database already exists). Run with --force to re-migrate.")
