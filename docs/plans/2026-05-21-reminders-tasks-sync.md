# Reminders-Tasks Bidirectional Sync — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers-optimized:subagent-driven-development (recommended) or superpowers-optimized:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement bidirectional sync between Apple Reminders and `tasks.db`, where Reminders lists map to projects and reminder items map to tasks, running via CLI or hourly cron.

**Architecture:** A standalone Python script `engine/sync/sync_reminders.py` that uses the `reminders-bridge` CLI to read/write Reminders and `db_manager` to read/write `tasks.db`. Identity tracking uses the existing `sync_state` table with compound keys `<list>::<title>`.

**Tech Stack:** Python 3, SQLite (via db_manager), reminders-bridge CLI (`~/.claude/reminders-bridge`)

**Assumptions:** reminders-bridge returns item output in the documented format (`[x] / [ ]` prefix, `(due: DD.MM.YY, HH:MM)` format, list name in final bracket). The sync_state table exists in tasks.db. The `tasks` and `projects` tables use UUID hex strings for ids. Reminder renames are not handled — a renamed reminder breaks the compound key mapping (accepting this as a known limitation from the spec).

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `engine/sync/sync_reminders.py` | Create | Full bidirectional sync: parse reminders-bridge output, upsert tasks, push task changes back to reminders |
| `crontab` (or `personal-ai-space/cron/crontab`) | Modify | Add hourly cron entry |

---

### Task 1: Create `sync_reminders.py` — Complete Sync Script

**Files:**
- Create: `engine/sync/sync_reminders.py`

**Security flag:** `none` (no auth, credentials, or input validation — handles internal data only)

**Does NOT cover:** Reminder renames (breaks compound key — known limitation from spec). Tasks without sync_state entries are never synced to Reminders (opt-in only).

- [x] **Step 1: Create the sync script**

Write the complete `sync_reminders.py` with these classes/functions:

```python
"""
sync_reminders.py — Bidirectional sync between Apple Reminders and tasks.db.

Syncs Reminders lists ↔ projects and reminder items ↔ tasks.
Uses sync_state table for identity tracking.
Follows the same pattern as sync_calendar.py.

Usage:
    python3 sync_reminders.py                      # Full bidirectional sync
    python3 sync_reminders.py --dry-run             # Preview only
    python3 sync_reminders.py --one-way=r2t         # Reminders → Tasks only
    python3 sync_reminders.py --one-way=t2r         # Tasks → Reminders only
"""
import argparse
import hashlib
import json
import logging
import re
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Allow running from anywhere by resolving engine/ sibling dir
_ENGINE_DIR = Path(__file__).resolve().parent.parent
if str(_ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(_ENGINE_DIR))

import db_manager as db

logger = logging.getLogger("engine.sync_reminders")

_REMINDERS_BRIDGE = Path.home() / ".claude" / "reminders-bridge"

# ── Regex Patterns ──────────────────────────────────────────────────────────

# Matches a reminder item line:
#   [x] Title (due: DD.MM.YY, HH:MM) [repeats: weekly] [ListName]
# Groups: 1=status([x]/[ ]), 2=priority(!!/!/empty), 3=title,
#         4=due_str(optional), 5=recurrence(optional), 6=list_name
_ITEM_LINE_RE = re.compile(
    r'^\[([ x])\]\s*'                 # status: [x] or [ ]
    r'(!{0,2})\s*'                    # priority: !! or ! or empty
    r'(.+?)'                           # title (non-greedy)
    r'(?:\s*\(due:\s*(.+?)\))?'       # due date (optional)
    r'(?:\s*\[repeats:\s*(.+?)\])?'   # recurrence (optional)
    r'\s*\[([^\]]+)\]\s*$'            # list name
)

# Matches a notes line following a reminder item line
_NOTES_LINE_RE = re.compile(r'^\s*Notes:\s*(.*)', re.IGNORECASE)

# Parses due date from "DD.MM.YY, HH:MM" to "YYYY-MM-DD HH:MM"
_DUE_DATE_RE = re.compile(r'(\d{2})\.(\d{2})\.(\d{2}),\s*(\d{2}):(\d{2})')

# ── Priority Mapping ────────────────────────────────────────────────────────

_REMINDER_PRIORITY_MAP = {
    "!!": "critical",
    "!": "high",
    "": "normal",
}

_TASK_PRIORITY_MAP = {
    "critical": "!!",
    "high": "!",
    "normal": "",
}

_STATUS_MAP_REMINDER_TO_TASK = {
    "x": "completed",
    " ": "pending",
}

_STATUS_MAP_TASK_TO_REMINDER = {
    "completed": True,
    "cancelled": True,
    "pending": False,
    "in_progress": False,
    "blocked": False,
}


# ── Helpers ─────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _parse_due_date(due_str: Optional[str]) -> Optional[str]:
    """Parse 'DD.MM.YY, HH:MM' → 'YYYY-MM-DD HH:MM' or None."""
    if not due_str:
        return None
    m = _DUE_DATE_RE.match(due_str.strip())
    if m:
        day, month, year, hour, minute = m.groups()
        full_year = 2000 + int(year)
        return f"{full_year:04d}-{month}-{day} {hour}:{minute}"
    return None


def _format_due_date(dt_str: Optional[str]) -> Optional[str]:
    """Format 'YYYY-MM-DD HH:MM' or 'YYYY-MM-DD' → 'YYYY-MM-DD HH:MM' for set-due."""
    if not dt_str:
        return None
    # Already has time component
    if " " in dt_str:
        return dt_str
    return dt_str  # date only, bridge handles it


def _reminder_hash(reminder: dict) -> str:
    """SHA-256 hash of reminder fields for change detection."""
    fields = {
        "title": reminder.get("title", ""),
        "notes": reminder.get("notes", ""),
        "due_date": reminder.get("due_date", ""),
        "priority": reminder.get("priority", ""),
        "completed": reminder.get("completed", False),
    }
    return hashlib.sha256(
        json.dumps(fields, sort_keys=True).encode()
    ).hexdigest()[:16]


# ── Bridge Communication ────────────────────────────────────────────────────

def _run_bridge(args: list[str], timeout: int = 10) -> Optional[subprocess.CompletedProcess]:
    """Run reminders-bridge with retries and timeout.

    Retries up to 3 times with exponential backoff (2s, 4s, 8s).
    Returns CompletedProcess on success, None on persistent failure.
    """
    for attempt in range(3):
        try:
            result = subprocess.run(
                [_REMINDERS_BRIDGE] + args,
                capture_output=True, text=True, timeout=timeout,
            )
            if result.returncode == 0:
                return result
            # Non-zero exit — log and retry
            logger.debug("bridge attempt %d/3 failed (rc=%d): %s",
                         attempt + 1, result.returncode, result.stderr.strip())
        except subprocess.TimeoutExpired:
            logger.debug("bridge attempt %d/3 timed out after %ds", attempt + 1, timeout)
        except FileNotFoundError:
            logger.error("reminders-bridge not found at %s", _REMINDERS_BRIDGE)
            return None

        if attempt < 2:
            import time
            time.sleep(2 ** attempt * 2)  # 2s, 4s

    return None


# ── Reminder Parsing ────────────────────────────────────────────────────────

def _parse_reminder_output(output: str) -> dict[str, list[dict]]:
    """Parse full reminders-bridge items output into structured data.

    Returns:
        Dict mapping list_name → list of reminder dicts with keys:
            title, notes, due_date, priority, completed, list_name
    """
    lists: dict[str, list[dict]] = {}
    lines = output.strip().split("\n")
    current_reminder = None

    for line in lines:
        if not line.strip():
            continue

        # Check if it's a reminder item line
        m = _ITEM_LINE_RE.match(line)
        if m:
            # Save previous reminder if exists
            if current_reminder and current_reminder.get("title"):
                list_name = current_reminder["list_name"]
                lists.setdefault(list_name, []).append(current_reminder)

            status_ch = m.group(1)      # "x" or " "
            priority_str = m.group(2)   # "!!" / "!" / ""
            title = m.group(3).strip()
            due_str = m.group(4)
            recurrence = m.group(5)
            list_name = m.group(6)

            current_reminder = {
                "title": title,
                "notes": "",
                "due_date": _parse_due_date(due_str),
                "priority": _REMINDER_PRIORITY_MAP.get(priority_str, "normal"),
                "completed": status_ch == "x",
                "status": _STATUS_MAP_REMINDER_TO_TASK.get(status_ch, "pending"),
                "list_name": list_name,
                "recurrence": recurrence,
            }
            continue

        # Check if it's a notes line for the current reminder
        n = _NOTES_LINE_RE.match(line)
        if n and current_reminder:
            notes = n.group(1).strip()
            if current_reminder["notes"]:
                current_reminder["notes"] += "\n" + notes
            else:
                current_reminder["notes"] = notes
            continue

    # Don't forget the last reminder
    if current_reminder and current_reminder.get("title"):
        list_name = current_reminder["list_name"]
        lists.setdefault(list_name, []).append(current_reminder)

    return lists


# ── Database Operations ────────────────────────────────────────────────────

def _find_or_create_project(list_name: str) -> str:
    """Look up project by name in tasks.db, creating if not found. Returns project_id."""
    rows = db.query("tasks", "SELECT id FROM projects WHERE name = ?", (list_name,))
    if rows:
        return rows[0]["id"]

    project_id = uuid.uuid4().hex
    now = _now()
    try:
        db.execute("tasks",
            """INSERT INTO projects (id, name, status, priority, category, created_at, updated_at)
               VALUES (?, 'active', 'normal', 'general', ?, ?)""",
            (project_id, now, now))
        logger.info("Created project: %s (id=%s)", list_name, project_id)
    except Exception as e:
        # Race condition — another sync may have created it
        rows = db.query("tasks", "SELECT id FROM projects WHERE name = ?", (list_name,))
        if rows:
            return rows[0]["id"]
        raise
    return project_id


def _upsert_task(
    task_id: Optional[str],
    title: str,
    description: Optional[str],
    project_id: str,
    due_date: Optional[str],
    priority: str,
    status: str,
) -> str:
    """Create or update a task. Returns task_id."""
    now = _now()
    if task_id:
        # Update existing
        db.execute("tasks",
            """UPDATE tasks SET title=?, description=?, project_id=?,
               due_date=?, priority=?, status=?, updated_at=?
               WHERE id=?""",
            (title, description, project_id, due_date, priority, status, now, task_id))
        return task_id
    else:
        # Create new
        task_id = uuid.uuid4().hex
        db.execute("tasks",
            """INSERT INTO tasks (id, title, description, project_id,
               due_date, priority, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (task_id, title, description, project_id, due_date, priority, status, now, now))
        return task_id


def _upsert_sync_state(compound_key: str, task_id: str, reminder: dict):
    """Create or update sync_state entry linking a task to a reminder."""
    content_hash = _reminder_hash(reminder)
    now = _now()

    # Delete existing entry for this entity_id or file_path
    db.execute("tasks",
        "DELETE FROM sync_state WHERE entity_type='apple-reminder' AND (entity_id=? OR file_path=?)",
        (task_id, compound_key))

    db.execute("tasks",
        """INSERT INTO sync_state (id, entity_type, entity_id, file_path, file_hash, last_modified, direction)
           VALUES (?, 'apple-reminder', ?, ?, ?, ?, 'bidirectional')""",
        (uuid.uuid4().hex, task_id, compound_key, content_hash, now))


def _get_sync_state_by_file_path(file_path: str) -> Optional[dict]:
    """Look up sync_state by compound key."""
    rows = db.query("tasks",
        "SELECT * FROM sync_state WHERE entity_type='apple-reminder' AND file_path=? LIMIT 1",
        (file_path,))
    return rows[0] if rows else None


def _get_sync_state_rows() -> list[dict]:
    """Get all apple-reminder sync_state rows."""
    return db.query("tasks",
        "SELECT * FROM sync_state WHERE entity_type='apple-reminder' AND direction='bidirectional'")


def _get_task(task_id: str) -> Optional[dict]:
    """Fetch a single task by ID."""
    rows = db.query("tasks", "SELECT * FROM tasks WHERE id=?", (task_id,))
    return rows[0] if rows else None


def _update_sync_state_hash(compound_key: str, reminder: dict):
    """Update the file_hash and last_modified in sync_state."""
    content_hash = _reminder_hash(reminder)
    now = _now()
    db.execute("tasks",
        """UPDATE sync_state SET file_hash=?, last_modified=?, last_synced=?
           WHERE entity_type='apple-reminder' AND file_path=?""",
        (content_hash, now, now, compound_key))


def _update_sync_state_modified(file_path: str):
    """Update last_modified timestamp after pushing changes to reminder."""
    now = _now()
    db.execute("tasks",
        "UPDATE sync_state SET last_modified=?, last_synced=? WHERE entity_type='apple-reminder' AND file_path=?",
        (now, now, file_path))


# ── Sync: Reminders → Tasks ────────────────────────────────────────────────

class RemindersSync:
    """Bidirectional sync between Apple Reminders and tasks.db."""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.stats = {
            "r_to_t_created": 0,
            "r_to_t_updated": 0,
            "r_to_t_skipped": 0,
            "t_to_r_completed": 0,
            "t_to_r_updated": 0,
            "lists_found": 0,
            "projects_created": 0,
        }

    def sync_all(self) -> dict:
        """Full bidirectional sync: R→T then T→R."""
        self.sync_reminders_to_tasks()
        self.sync_tasks_to_reminders()
        return self.stats

    def sync_reminders_to_tasks(self) -> dict:
        """Push Reminders → tasks.db.

        For each Reminders list, ensure a matching project exists. For each reminder
        item, look up the compound key in sync_state. If changed or new, upsert the task.
        """
        logger.info("=== Reminders → Tasks ===")

        # Fetch all reminders
        result = _run_bridge(["items", "--all"])
        if result is None:
            logger.warning("Cannot fetch reminders — bridge unavailable")
            return self.stats

        raw_output = result.stdout
        if not raw_output.strip():
            logger.info("No reminders found")
            return self.stats

        lists = _parse_reminder_output(raw_output)
        self.stats["lists_found"] = len(lists)

        for list_name, reminders in lists.items():
            logger.info("Processing list: %s (%d items)", list_name, len(reminders))

            # Find/create project
            project_id = _find_or_create_project(list_name)
            if not self.dry_run:
                # Track if we created a project
                pass  # _find_or_create_project logs internally

            for reminder in reminders:
                compound_key = f"{list_name}::{reminder['title']}"
                sync_row = _get_sync_state_by_file_path(compound_key)

                # If sync_row exists and hash matches, skip
                if sync_row and sync_row["file_hash"] == _reminder_hash(reminder):
                    self.stats["r_to_t_skipped"] += 1
                    continue

                if self.dry_run:
                    action = "UPDATE" if sync_row else "CREATE"
                    print(f"  [{action}] {list_name} :: {reminder['title']} "
                          f"(priority={reminder['priority']}, "
                          f"status={reminder['status']}, "
                          f"due={reminder['due_date'] or 'none'})")
                    self.stats["r_to_t_created" if not sync_row else "r_to_t_updated"] += 1
                    continue

                if sync_row:
                    # Update existing task
                    task_id = sync_row["entity_id"]
                    _upsert_task(
                        task_id=task_id,
                        title=reminder["title"],
                        description=reminder["notes"] or None,
                        project_id=project_id,
                        due_date=reminder["due_date"],
                        priority=reminder["priority"],
                        status=reminder["status"],
                    )
                    self.stats["r_to_t_updated"] += 1
                else:
                    # Create new task
                    task_id = _upsert_task(
                        task_id=None,
                        title=reminder["title"],
                        description=reminder["notes"] or None,
                        project_id=project_id,
                        due_date=reminder["due_date"],
                        priority=reminder["priority"],
                        status=reminder["status"],
                    )
                    self.stats["r_to_t_created"] += 1

                # Update sync state
                _upsert_sync_state(compound_key, task_id, reminder)

        return self.stats

    def sync_tasks_to_reminders(self) -> dict:
        """Push tasks.db changes → Apple Reminders.

        For each task tracked in sync_state, check if it was modified after
        the last sync. If completed, mark the reminder complete. If other fields
        changed, update notes, due date, and priority on the reminder.
        """
        logger.info("=== Tasks → Reminders ===")

        sync_rows = _get_sync_state_rows()
        logger.info("Checking %d tracked tasks for changes", len(sync_rows))

        for sync_row in sync_rows:
            task = _get_task(sync_row["entity_id"])
            if not task:
                logger.debug("Task %s not found (deleted?), skipping", sync_row["entity_id"])
                continue

            compound_key = sync_row["file_path"]
            if "::" not in compound_key:
                logger.warning("Invalid compound key: %s", compound_key)
                continue
            list_name, reminder_title = compound_key.split("::", 1)

            # Check if task was modified after last sync
            task_updated = task.get("updated_at", "")
            last_modified = sync_row.get("last_modified", "")

            if task_updated and last_modified and str(task_updated) <= str(last_modified):
                # Task hasn't changed — skip
                continue

            if self.dry_run:
                if task["status"] in ("completed", "cancelled"):
                    print(f"  WOULD_COMPLETE: {list_name} :: {reminder_title}")
                else:
                    print(f"  WOULD_UPDATE: {list_name} :: {reminder_title} "
                          f"(notes={task.get('description', '')[:40]}, "
                          f"due={task.get('due_date', 'none')})")
                continue

            # Push changes to Reminders
            if task["status"] in ("completed", "cancelled"):
                self._complete_reminder(list_name, reminder_title)
                self.stats["t_to_r_completed"] += 1
            else:
                self._update_reminder(list_name, reminder_title, task)
                self.stats["t_to_r_updated"] += 1

            # Update sync state timestamp
            _update_sync_state_modified(compound_key)

        return self.stats

    def _complete_reminder(self, list_name: str, title: str):
        """Mark a reminder as complete in Apple Reminders."""
        result = _run_bridge(["complete", list_name, title])
        if result is None:
            logger.warning("Failed to complete reminder: %s :: %s", list_name, title)
        else:
            logger.info("Completed reminder: %s :: %s", list_name, title)

    def _update_reminder(self, list_name: str, title: str, task: dict):
        """Update reminder fields (notes, due date) from task data.

        Only updates fields the bridge supports:
          - set-due: due_date
          - set-notes: description (notes)
        Title and priority changes are NOT supported by the bridge.
        """
        # Update notes from task description
        description = task.get("description") or ""
        if description:
            result = _run_bridge(["set-notes", list_name, title, description])
            if result is None:
                logger.warning("Failed to set notes for: %s :: %s", list_name, title)

        # Update due date
        due_date = task.get("due_date")
        if due_date:
            formatted = _format_due_date(str(due_date))
            result = _run_bridge(["set-due", list_name, title, formatted])
            if result is None:
                logger.warning("Failed to set due date for: %s :: %s", list_name, title)


# ── CLI ────────────────────────────────────────────────────────────────────

def _format_stats(stats: dict):
    print("\nSync Summary:")
    print(f"  Lists found:             {stats.get('lists_found', 0)}")
    print(f"  Tasks created (R→T):     {stats.get('r_to_t_created', 0)}")
    print(f"  Tasks updated (R→T):     {stats.get('r_to_t_updated', 0)}")
    print(f"  Tasks skipped (R→T):     {stats.get('r_to_t_skipped', 0)}")
    print(f"  Reminders completed (T→R): {stats.get('t_to_r_completed', 0)}")
    print(f"  Reminders updated (T→R):   {stats.get('t_to_r_updated', 0)}")


def main():
    parser = argparse.ArgumentParser(
        description="Bidirectional sync between Apple Reminders and tasks.db"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview only, no changes written")
    parser.add_argument("--one-way", choices=["r2t", "t2r"],
                        help="Run only one direction: r2t (Reminders→Tasks) or t2r (Tasks→Reminders)")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )

    if not _REMINDERS_BRIDGE.exists():
        logger.error("reminders-bridge not found at %s", _REMINDERS_BRIDGE)
        sys.exit(1)

    if args.dry_run:
        print("DRY RUN — No changes written\n")

    syncer = RemindersSync(dry_run=args.dry_run)

    if args.one_way == "r2t":
        syncer.sync_reminders_to_tasks()
    elif args.one_way == "t2r":
        syncer.sync_tasks_to_reminders()
    else:
        syncer.sync_all()

    _format_stats(syncer.stats)
    db.checkpoint_all()


if __name__ == "__main__":
    main()
```

- [x] **Step 2: Verify the script parses and runs with --help**

Run:
```bash
python3 "personal-ai-space/engine/sync/sync_reminders.py" --help
```
Expected: Shows usage with --dry-run, --one-way arguments. Exit code 0.

- [x] **Step 3: Run script with --dry-run**

Run:
```bash
python3 "personal-ai-space/engine/sync/sync_reminders.py" --dry-run
```
Expected: Shows "DRY RUN — No changes written" followed by sync summary with 0 counts (or existing reminders scanned). Exit code 0.

- [x] **Step 4: Run live sync**

Run:
```bash
python3 "personal-ai-space/engine/sync/sync_reminders.py"
```
Expected: Shows sync summary with tasks created. Exit code 0.

---

### Task 2: Register Hourly Cron Job

**Files:**
- Modify: `crontab` (pending discovery of location)

- [x] **Step 1: Find existing cron-related files**

Run:
```bash
crontab -l 2>/dev/null || echo "no crontab"
```

- [x] **Step 2: Add hourly cron entry**

Added to system crontab via `script -q /dev/null crontab <file>`:
```
0 * * * * /Users/paulorezende/.local/bin/sync-reminders.sh >> /tmp/sync-reminders.cron.log 2>&1
```

Also created helper shell wrapper: `~/.local/bin/sync-reminders.sh` (executable, passes args through).
