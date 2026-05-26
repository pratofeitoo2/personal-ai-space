"""
sync_calendar.py — Sync Apple Calendar events into calendar.db.

Fetches events from all macOS calendars (iCloud, Google, etc.) via the
calendar-bridge CLI tool and upserts them into the SQLite database.

Schema: schema_calendar.sql defines the base table; ensure_schema() adds
columns idiempotently for existing databases.

Usage:
    python3 sync_calendar.py                     # Full sync (past 90d + next 365d)
    python3 sync_calendar.py --quick             # Quick sync (past 7d + next 30d)
    python3 sync_calendar.py --dry-run           # Preview only
    python3 sync_calendar.py --from 2026-01-01   # Custom start date
"""
import argparse
import logging
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

# Allow running from anywhere by resolving engine/ sibling dir
_ENGINE_DIR = Path(__file__).resolve().parent.parent
if str(_ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(_ENGINE_DIR))

import db_manager as db

logger = logging.getLogger("engine.sync_calendar")

_CALENDAR_BRIDGE = Path.home() / ".claude" / "calendar-bridge"

_EVENT_LINE_RE = re.compile(
    r'^  \[(.+?)\] (.+)  \(([^)]+)\)$'
)

_TIME_RANGE_RE = re.compile(
    r'^(\d{2}:\d{2}) – (\d{2}:\d{2})$'
)


def _datetime_to_minutes(dt_str: str) -> int:
    parts = dt_str.split(":")
    return int(parts[0]) * 60 + int(parts[1])


def _calculate_duration(time_bracket: str) -> float:
    """Calculate duration in hours from the time bracket content."""
    if time_bracket.strip().lower() == "all day":
        return 24.0
    m = _TIME_RANGE_RE.match(time_bracket.strip())
    if m:
        start_min = _datetime_to_minutes(m.group(1))
        end_min = _datetime_to_minutes(m.group(2))
        if end_min >= start_min:
            return round((end_min - start_min) / 60.0, 2)
    return 1.0


def _parse_event_time(time_bracket: str) -> str:
    """Return start time from the bracket content, or empty string for all-day."""
    if time_bracket.strip().lower() == "all day":
        return ""
    m = _TIME_RANGE_RE.match(time_bracket.strip())
    if m:
        return m.group(1)
    return ""


def _parse_event_info(info_str: str) -> tuple[str, str]:
    """Split event info into (title, location).

    Event info can contain:
      - A location after ' @ '
      - Parenthetical extras after the title
    """
    info = info_str.strip()
    location = ""
    if " @ " in info:
        parts = info.split(" @ ", 1)
        info = parts[0].strip()
        location = parts[1].strip()
    return info, location


def _calendar_to_category(calendar_name: str) -> str:
    """Map calendar names to general categories for the DB."""
    name_lower = calendar_name.lower().strip()
    mapping = {
        "home": "personal",
        "família": "family",
        "familia": "family",
        "feriados": "holiday",
        "trabalho": "work",
        "work": "work",
        "birthdays": "social",
        "pfrezendehs@gmail.com": "general",
    }
    return mapping.get(name_lower, "general")


def _calendar_to_account(calendar_name: str, known_calendars: dict) -> str:
    return known_calendars.get(calendar_name, "")


def fetch_calendars() -> dict[str, str]:
    """Fetch all calendars and return a dict of {name: account}.

    Runs 'calendar-bridge calendars' and infers the account from
    the calendar name (standard iCloud calendars vs Google ones).

    Returns:
        Dict mapping calendar name to account label.
    """
    try:
        result = subprocess.run(
            [_CALENDAR_BRIDGE, "calendars"],
            capture_output=True, text=True, timeout=30,
        )
        lines = [l.strip() for l in result.stdout.strip().split("\n") if l.strip()]
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        logger.warning("Cannot fetch calendars: %s", e)
        return {}

    calendars = {}
    for name in lines:
        clean = name.replace(" (read-only)", "")
        calendars[clean] = clean
    return calendars


def fetch_events_for_date(date_str: str) -> list[dict]:
    """Fetch events for a specific date using calendar-bridge.

    Args:
        date_str: Date in 'YYYY-MM-DD' format.

    Returns:
        List of dicts with keys:
            event_date, event_name, event_time, duration_hours,
            category, account, calendar_name, location, source, status
    """
    try:
        result = subprocess.run(
            [_CALENDAR_BRIDGE, "events", date_str],
            capture_output=True, text=True, timeout=30,
        )
        output = result.stdout.strip()
    except subprocess.TimeoutExpired:
        logger.debug("Timeout fetching %s", date_str)
        return []
    except FileNotFoundError:
        logger.error("calendar-bridge not found at %s", _CALENDAR_BRIDGE)
        return []

    if "(no events)" in output:
        return []

    events = []
    for line in output.split("\n"):
        m = _EVENT_LINE_RE.match(line)
        if not m:
            continue

        time_bracket = m.group(1).strip()
        info_str = m.group(2).strip()
        calendar_name = m.group(3).strip()

        _skip_calendars = {"birthdays", "feriados", "holidays", "feriados brasileiros"}
        if calendar_name.lower() in _skip_calendars:
            continue

        event_time = _parse_event_time(time_bracket)
        duration = _calculate_duration(time_bracket)
        title, location = _parse_event_info(info_str)
        category = _calendar_to_category(calendar_name)

        events.append({
            "event_date": date_str,
            "event_name": title,
            "event_time": event_time,
            "duration_hours": duration,
            "category": category,
            "status": "scheduled",
            "account": calendar_name,
            "calendar_name": calendar_name,
            "location": location,
            "source": "apple-calendar",
        })

    return events


def ensure_schema():
    """Idempotently add columns to the upcoming table for existing databases."""
    with db.get_conn("calendar") as conn:
        cur = conn.execute("SELECT name FROM pragma_table_info('upcoming')")
        existing = {row["name"] for row in cur.fetchall()}

        additions = [
            ("account", "TEXT DEFAULT ''"),
            ("calendar_name", "TEXT DEFAULT ''"),
            ("location", "TEXT DEFAULT ''"),
            ("source", "TEXT DEFAULT 'manual'"),
        ]
        for col, col_def in additions:
            if col not in existing:
                conn.execute(f"ALTER TABLE upcoming ADD COLUMN {col} {col_def}")
                logger.info("Added column: upcoming.%s", col)

        for idx in ["idx_upcoming_source", "idx_upcoming_account"]:
            if idx not in {r["name"] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            ).fetchall()}:
                col_name = idx.replace("idx_upcoming_", "")
                conn.execute(
                    f"CREATE INDEX IF NOT EXISTS {idx} ON upcoming({col_name})"
                )


def sync_date_range(start_date: datetime, end_date: datetime, dry_run: bool = False) -> dict:
    """Fetch events for each date in range and upsert into DB.

    Uses a DELETE-then-INSERT approach per date to handle adds, updates,
    and removals. Only affects rows with source='apple-calendar'.

    Args:
        start_date: Inclusive start date.
        end_date: Inclusive end date.
        dry_run: If True, only print what would be done.

    Returns:
        Dict with keys: dates_scanned, events_found, events_written.
    """
    stats = {"dates_scanned": 0, "events_found": 0, "events_written": 0}
    total_days = (end_date - start_date).days + 1

    for i in range(total_days):
        current = start_date + timedelta(days=i)
        date_str = current.strftime("%Y-%m-%d")
        stats["dates_scanned"] += 1

        events = fetch_events_for_date(date_str)
        if not events:
            continue

        stats["events_found"] += len(events)

        if dry_run:
            for ev in events:
                print(f"  WOULD_SYNC: {date_str} | {ev['event_time']:5s} | "
                      f"{ev['event_name'][:50]:50s} | {ev['calendar_name']}")
            stats["events_written"] += len(events)
            continue

        # In a transaction per date: delete existing apple-calendar rows
        # for this date, then insert current snapshot.
        with db.transaction("calendar") as conn:
            conn.execute(
                "DELETE FROM upcoming WHERE event_date = ? AND source = 'apple-calendar'",
                (date_str,),
            )
            for ev in events:
                conn.execute(
                    """INSERT INTO upcoming
                       (event_date, event_name, event_time, duration_hours,
                        category, status, account, calendar_name, location, source)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        ev["event_date"],
                        ev["event_name"],
                        ev["event_time"],
                        ev["duration_hours"],
                        ev["category"],
                        ev["status"],
                        ev["account"],
                        ev["calendar_name"],
                        ev["location"],
                        ev["source"],
                    ),
                )
            stats["events_written"] += len(events)

        if (i + 1) % 50 == 0:
            logger.info("Progress: %d/%d dates scanned (%d events found)",
                        i + 1, total_days, stats["events_found"])

    return stats


def sync_full(dry_run: bool = False, from_date: Optional[str] = None) -> dict:
    now = datetime.now(timezone.utc)
    if from_date:
        start = datetime.strptime(from_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    else:
        start = now - timedelta(days=90)
    end = now + timedelta(days=365)

    total_days = (end - start).days + 1
    logger.info("Syncing %d days (%s to %s)", total_days,
                start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))

    if dry_run:
        print("DRY RUN — No changes written")
        print(f"  Range: {start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')} ({total_days} days)")

    stats = sync_date_range(start, end, dry_run=dry_run)
    return stats


def sync_quick(dry_run: bool = False) -> dict:
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=7)
    end = now + timedelta(days=30)

    total_days = (end - start).days + 1
    logger.info("Quick sync: %d days (%s to %s)", total_days,
                start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))

    stats = sync_date_range(start, end, dry_run=dry_run)
    return stats


def ensure_past_events_table():
    """Create past_events table if it doesn't exist."""
    with db.get_conn("calendar") as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS past_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_date TEXT NOT NULL,
                event_name TEXT NOT NULL,
                event_time TEXT NOT NULL DEFAULT '',
                duration_hours REAL DEFAULT 1.0,
                category TEXT NOT NULL DEFAULT 'general',
                account TEXT DEFAULT '',
                calendar_name TEXT DEFAULT '',
                location TEXT DEFAULT '',
                source TEXT DEFAULT 'manual',
                notes TEXT DEFAULT '',
                outcome TEXT DEFAULT '',
                completed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        for idx, col in [("idx_past_events_date", "event_date"),
                         ("idx_past_events_category", "category"),
                         ("idx_past_events_source", "source")]:
            conn.execute(
                f"CREATE INDEX IF NOT EXISTS {idx} ON past_events({col})"
            )


def archive_past_events(dry_run: bool = False) -> int:
    """Move past-dated entries from upcoming to past_events.

    Only archives rows with event_date before today. Skips rows that
    already exist in past_events (matched by event_date + event_name).
    Returns count of archived entries.
    """
    from datetime import timezone
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    past = db.query(
        "calendar",
        "SELECT * FROM upcoming WHERE event_date < ?",
        (today,),
    )
    if not past:
        return 0

    count = 0
    for row in past:
        if dry_run:
            print(f"  WOULD_ARCHIVE: {row['event_date']} | {row['event_name']}")
            count += 1
            continue

        exists = db.query(
            "calendar",
            "SELECT 1 FROM past_events WHERE event_date=? AND event_name=? LIMIT 1",
            (row["event_date"], row["event_name"]),
        )
        if exists:
            db.execute("calendar", "DELETE FROM upcoming WHERE id=?", (row["id"],))
            count += 1
            continue

        db.execute("calendar", """
            INSERT INTO past_events
            (event_date, event_name, event_time, duration_hours, category,
             account, calendar_name, location, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            row["event_date"], row["event_name"], row["event_time"],
            row["duration_hours"], row["category"], row["account"],
            row["calendar_name"], row["location"], row["source"],
        ))
        db.execute("calendar", "DELETE FROM upcoming WHERE id=?", (row["id"],))
        count += 1

    return count


def _format_stats(stats: dict):
    print("\nSync Summary:")
    print(f"  Dates scanned:  {stats.get('dates_scanned', 0)}")
    print(f"  Events found:   {stats.get('events_found', 0)}")
    print(f"  Events written: {stats.get('events_written', 0)}")


def main():
    parser = argparse.ArgumentParser(
        description="Sync Apple Calendar events to calendar.db"
    )
    parser.add_argument("--quick", action="store_true",
                        help="Quick sync: past 7d to next 30d")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview only, no DB writes")
    parser.add_argument("--from", dest="from_date", type=str,
                        help="Custom start date YYYY-MM-DD (full sync)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(levelname)s %(message)s")

    if not _CALENDAR_BRIDGE.exists():
        logger.error("calendar-bridge not found at %s", _CALENDAR_BRIDGE)
        sys.exit(1)

    ensure_schema()
    ensure_past_events_table()
    archived = archive_past_events(dry_run=args.dry_run)
    if archived:
        print(f"  Archived past events: {archived}")

    if args.quick:
        stats = sync_quick(dry_run=args.dry_run)
    else:
        stats = sync_full(dry_run=args.dry_run, from_date=args.from_date)

    _format_stats(stats)
    db.checkpoint_all()


if __name__ == "__main__":
    main()
