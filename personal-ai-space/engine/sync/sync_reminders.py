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
from db.id_helpers import for_project, for_task_unique, for_sync_state
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
    r'\s*\[([^\]]+)\]'                # list name
    r'(?:\s*\{[^}]*\})?'              # optional EventKit metadata {id:...}
    r'\s*$'                            # end of line
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
    """Format 'YYYY-MM-DD HH:MM' or 'YYYY-MM-DD' for bridge set-due command."""
    if not dt_str:
        return None
    if " " in dt_str:
        return dt_str
    return dt_str


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
            logger.debug("bridge attempt %d/3 failed (rc=%d): %s",
                         attempt + 1, result.returncode, result.stderr.strip()[:200])
        except subprocess.TimeoutExpired:
            logger.debug("bridge attempt %d/3 timed out after %ds", attempt + 1, timeout)
        except FileNotFoundError:
            logger.error("reminders-bridge not found at %s", _REMINDERS_BRIDGE)
            return None

        if attempt < 2:
            import time
            time.sleep(2 ** attempt * 2)

    return None


def _get_existing_lists() -> list[str]:
    result = _run_bridge(["lists"])
    if result is None:
        return []
    return [l.strip() for l in result.stdout.strip().split("\n") if l.strip()]


def _ensure_list_exists(list_name: str, existing: set[str]) -> bool:
    if list_name in existing:
        return False
    result = _run_bridge(["create-list", list_name])
    if result is not None:
        existing.add(list_name)
        logger.info("Created Reminders list: %s", list_name)
        return True
    logger.warning("Failed to create Reminders list: %s", list_name)
    return False


# ── Reminder Parsing ────────────────────────────────────────────────────────

def _parse_reminder_output(output: str) -> dict[str, list[dict]]:
    """Parse full reminders-bridge items output into structured data.

    Args:
        output: Raw stdout from 'reminders-bridge items --all'

    Returns:
        Dict mapping list_name → list of reminder dicts with keys:
            title, notes, due_date, priority, completed, status, list_name, recurrence
    """
    lists: dict[str, list[dict]] = {}
    lines = output.strip().split("\n")
    current_reminder = None

    for line in lines:
        if not line.strip():
            continue

        m = _ITEM_LINE_RE.match(line)
        if m:
            if current_reminder and current_reminder.get("title"):
                list_name = current_reminder["list_name"]
                lists.setdefault(list_name, []).append(current_reminder)

            status_ch = m.group(1)
            priority_str = m.group(2)
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

        n = _NOTES_LINE_RE.match(line)
        if n and current_reminder:
            notes = n.group(1).strip()
            if current_reminder["notes"]:
                current_reminder["notes"] += "\n" + notes
            else:
                current_reminder["notes"] = notes
            continue

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

    project_id = for_project(list_name)
    now = _now()
    try:
        db.execute("tasks",
            """INSERT INTO projects (id, name, status, priority, category, created_at, updated_at)
               VALUES (?, ?, 'active', 'normal', 'general', ?, ?)""",
            (project_id, list_name, now, now))
        logger.info("Created project: %s (id=%s)", list_name, project_id)
    except Exception:
        # Race condition — another sync may have created it concurrently
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
        db.execute("tasks",
            """UPDATE tasks SET title=?, description=?, project_id=?,
               due_date=?, priority=?, status=?, updated_at=?
               WHERE id=?""",
            (title, description, project_id, due_date, priority, status, now, task_id))
        return task_id
    else:
        task_id = for_task_unique(title, project_id)
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

    db.execute("tasks",
        "DELETE FROM sync_state WHERE entity_type='apple-reminder' AND (entity_id=? OR file_path=?)",
        (task_id, compound_key))

    db.execute("tasks",
        """INSERT INTO sync_state (id, entity_type, entity_id, file_path, file_hash, last_modified, direction)
           VALUES (?, 'apple-reminder', ?, ?, ?, ?, 'bidirectional')""",
        (for_sync_state("apple-reminder", task_id), task_id, compound_key, content_hash, now))


def _get_sync_state_by_file_path(file_path: str) -> Optional[dict]:
    """Look up sync_state by compound key."""
    rows = db.query("tasks",
        "SELECT * FROM sync_state WHERE entity_type='apple-reminder' AND file_path=? LIMIT 1",
        (file_path,))
    return rows[0] if rows else None


def _get_sync_state_rows() -> list[dict]:
    return db.query("tasks",
        "SELECT * FROM sync_state WHERE entity_type='apple-reminder' AND direction='bidirectional'")


def _get_task(task_id: str) -> Optional[dict]:
    rows = db.query("tasks", "SELECT * FROM tasks_v WHERE id=?", (task_id,))
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


def _seed_sync_state_for_completed(compound_key: str, reminder: dict):
    """Create a sync_state entry for a completed reminder with no linked task.

    Prevents the sync from re-creating a task for this reminder on every cycle.
    Uses a unique entity_id per compound_key to avoid the DELETE-broadside
    problem in _upsert_sync_state.
    """
    content_hash = _reminder_hash(reminder)
    now = _now()
    dummy_id = f"completed::{compound_key.replace('::', '/')[:50]}"
    dummy_id = dummy_id.replace(" ", "_").lower()
    db.execute("tasks",
        """INSERT OR IGNORE INTO sync_state
           (id, entity_type, entity_id, file_path, file_hash, last_modified, direction)
           VALUES (?, 'apple-reminder', ?, ?, ?, ?, 'bidirectional')""",
        (for_sync_state("apple-reminder", dummy_id),
         dummy_id, compound_key, content_hash, now))


def _seed_sync_state_for_section_tile(compound_key: str, reminder: dict):
    """Seed sync_state for a per-briefing section tile so it stays out of tasks.db.

    Section tiles are intentional Reminder entries for the phone UI. They are
    NOT durable tasks — the underlying items already exist in tasks.db. We
    seed sync_state with a synthetic entity_id so subsequent sync cycles skip
    the reminder without re-creating it as a task.
    """
    content_hash = _reminder_hash(reminder)
    now = _now()
    dummy_id = f"section_tile::{compound_key.replace('::', '/')[:50]}"
    dummy_id = dummy_id.replace(" ", "_").lower()
    db.execute("tasks",
        """INSERT OR IGNORE INTO sync_state
           (id, entity_type, entity_id, file_path, file_hash, last_modified, direction)
           VALUES (?, 'apple-reminder', ?, ?, ?, ?, 'bidirectional')""",
        (for_sync_state("apple-reminder", dummy_id),
         dummy_id, compound_key, content_hash, now))


# ── Habit reminder detection ─────────────────────────────────────────────


def _is_habit_reminder(reminder: dict) -> bool:
    """Check if a reminder is a habit completion reminder.

    Habit reminders have JSON notes with {"type": "habit", "habit_id": "..."}.
    """
    notes = reminder.get("notes", "")
    if not notes:
        return False
    try:
        data = json.loads(notes)
        return isinstance(data, dict) and data.get("type") == "habit"
    except (json.JSONDecodeError, TypeError):
        return False


def _get_section_tile_prefixes() -> set[str]:
    """Return the set of section-tile title prefixes that should NOT become tasks.

    Section tiles are per-briefing snapshots created by
    `automations/delivery.py:send_section_reminders`. They are glanceable views
    for the Reminders app; the underlying data already lives in tasks.db as
    the individual tasks/habits/goals. Syncing them back as tasks pollutes the
    task list with duplicates.
    """
    try:
        from automations.delivery import _SECTION_TITLES  # type: ignore
        return {t for t in _SECTION_TITLES.values() if t}
    except (ImportError, AttributeError):
        # Fallback: hardcoded list matching delivery._SECTION_TITLES as of 2026-06-01
        return {
            "📋 Tarefas do Dia",
            "📋 Restam do Dia",
            "⚠️ Tarefas Atrasadas",
            "📅 Agenda de Hoje",
            "🔔 Em Breve na Agenda",
            "🎯 Hábitos em Risco",
            "💪 Hábitos Concluídos Hoje",
            "🎯 Status dos Hábitos",
            "🎯 Metas Ativas",
            "🎯 Metas Próximas do Prazo",
            "✅ Concluído Hoje",
        }


def _is_section_tile_reminder(reminder: dict) -> bool:
    """True if this reminder is a per-briefing section tile (ephemeral view).

    Detection: title starts with any prefix in `_SECTION_TITLES`. Tiles are
    formatted as `"{section_title} ({list_title})"` in delivery.py, so a
    startswith match is sufficient.
    """
    title = reminder.get("title", "") or ""
    if not title:
        return False
    return any(title.startswith(p) for p in _get_section_tile_prefixes())


def _parse_habit_id(reminder: dict) -> Optional[str]:
    """Extract habit_id from a habit reminder's notes.

    Returns the habit_id string, or None if not a habit reminder.
    """
    notes = reminder.get("notes", "")
    if not notes:
        return None
    try:
        data = json.loads(notes)
        if isinstance(data, dict) and data.get("type") == "habit":
            return data.get("habit_id")
    except (json.JSONDecodeError, TypeError):
        pass
    return None


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
            "initial_pushed": 0,
            "initial_skipped": 0,
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

        list_names = _get_existing_lists()
        if not list_names:
            logger.warning("Cannot fetch lists — bridge unavailable")
            return self.stats

        all_items_output = []
        for name in list_names:
            result = _run_bridge(["items", name])
            if result and result.stdout.strip():
                all_items_output.append(result.stdout)

        if not all_items_output:
            logger.info("No reminders found across %d lists", len(list_names))
            return self.stats

        lists = _parse_reminder_output("\n".join(all_items_output))
        self.stats["lists_found"] = len(lists)

        for list_name, reminders in lists.items():
            logger.info("Processing list: %s (%d items)", list_name, len(reminders))

            project_id = _find_or_create_project(list_name)

            for reminder in reminders:
                compound_key = f"{list_name}::{reminder['title']}"
                sync_row = _get_sync_state_by_file_path(compound_key)

                if sync_row and sync_row.get("file_hash") == _reminder_hash(reminder):
                    self.stats["r_to_t_skipped"] += 1
                    continue

                # Skip per-briefing section tiles. These are ephemeral glanceable
                # views in Apple Reminders; their underlying items already live
                # in tasks.db as individual tasks. Syncing them back as tasks
                # pollutes the task list with duplicates. Seed sync_state so
                # subsequent cycles skip them.
                if not sync_row and _is_section_tile_reminder(reminder):
                    if self.dry_run:
                        print(f"  SKIP (section tile): {compound_key}")
                    else:
                        _seed_sync_state_for_section_tile(compound_key, reminder)
                    self.stats["r_to_t_skipped"] += 1
                    self.stats["r_to_t_section_tile_skipped"] = (
                        self.stats.get("r_to_t_section_tile_skipped", 0) + 1
                    )
                    continue

                # Skip completed reminders without an existing sync_state entry.
                # These are legacy/automation items that should not create new tasks.
                if not sync_row and reminder.get("completed"):
                    if self.dry_run:
                        print(f"  SKIP (completed): {compound_key}")
                    else:
                        _seed_sync_state_for_completed(compound_key, reminder)
                    self.stats["r_to_t_skipped"] += 1
                    continue

                # Habit completion detection — route to self.db instead of tasks.db
                if _is_habit_reminder(reminder) and reminder.get("completed"):
                    habit_id = _parse_habit_id(reminder)
                    if habit_id:
                        try:
                            from sync.sync_habits import mark_habit_complete
                            mark_habit_complete(habit_id)
                            logger.info("Habit completed via reminder: %s", habit_id)
                        except ValueError as e:
                            logger.warning("Habit completion failed: %s", e)
                        except Exception as e:
                            logger.error("Habit completion error: %s", e)
                    # Seed sync_state so we don't process this again
                    if not self.dry_run:
                        _seed_sync_state_for_completed(compound_key, reminder)
                    self.stats["r_to_t_skipped"] += 1
                    continue

                if self.dry_run:
                    action = "UPDATE" if sync_row else "CREATE"
                    print(f"  [{action}] {list_name} :: {reminder['title']} "
                          f"(priority={reminder['priority']}, "
                          f"status={reminder['status']}, "
                          f"due={reminder['due_date'] or 'none'})")
                    if sync_row:
                        self.stats["r_to_t_updated"] += 1
                    else:
                        self.stats["r_to_t_created"] += 1
                    continue

                if sync_row:
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

                _upsert_sync_state(compound_key, task_id, reminder)

        return self.stats

    def sync_tasks_to_reminders(self) -> dict:
        """Push tasks.db changes → Apple Reminders.

        For each task tracked in sync_state, check if it was modified after
        the last sync. If completed, mark the reminder complete. If other fields
        changed, update notes and due date on the reminder.
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

            task_updated = task.get("updated_at", "")
            last_modified = sync_row.get("last_modified", "")

            if task_updated and last_modified and str(task_updated) <= str(last_modified):
                continue

            if self.dry_run:
                if task["status"] in ("completed", "cancelled"):
                    print(f"  WOULD_COMPLETE: {list_name} :: {reminder_title}")
                else:
                    print(f"  WOULD_UPDATE: {list_name} :: {reminder_title} "
                          f"(notes={task.get('description', '')[:40]}, "
                          f"due={task.get('due_date', 'none')})")
                continue

            if task["status"] in ("completed", "cancelled"):
                self._complete_reminder(list_name, reminder_title)
                self.stats["t_to_r_completed"] += 1
            else:
                self._update_reminder(list_name, reminder_title, task)
                self.stats["t_to_r_updated"] += 1

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
        description = task.get("description") or ""
        if description:
            result = _run_bridge(["set-notes", list_name, title, description])
            if result is None:
                logger.warning("Failed to set notes for: %s :: %s", list_name, title)

        due_date = task.get("due_date")
        if due_date:
            formatted = _format_due_date(str(due_date))
            result = _run_bridge(["set-due", list_name, title, formatted])
            if result is None:
                logger.warning("Failed to set due date for: %s :: %s", list_name, title)

    def initial_push(self) -> dict:
        """One-shot export: create reminders for all tasks not yet tracked in sync_state.

        For each task without an apple-reminder sync_state entry:
          1. Find/create the matching Reminders list (by project name)
          2. Create the reminder via bridge
          3. Set due date and completion status
          4. Create sync_state entry so future syncs work bidirectionally
        """
        logger.info("=== Initial Push (Tasks → Reminders) ===")

        tasks = db.query("tasks", """
            SELECT t.* FROM tasks t
            LEFT JOIN sync_state s
                ON s.entity_type='apple-reminder' AND s.entity_id=t.id
            WHERE s.id IS NULL
            ORDER BY t.created_at ASC
        """)
        logger.info("Found %d tasks to push", len(tasks))

        if not tasks:
            logger.info("No unlinked tasks — nothing to push")
            return self.stats

        existing_lists = set(_get_existing_lists())
        stats = {"initial_pushed": 0, "initial_skipped": 0, "lists_created": 0}

        for task in tasks:
            project_name = self._resolve_project_name(task)
            if not project_name:
                logger.warning("Task %s has no project, skipping", task.get("title", "?"))
                stats["initial_skipped"] += 1
                continue

            if _ensure_list_exists(project_name, existing_lists):
                stats["lists_created"] += 1

            title = task["title"]
            description = task.get("description") or ""
            compound_key = f"{project_name}::{title}"

            if self.dry_run:
                print(f"  WOULD_CREATE: {project_name} :: {title} "
                      f"(due={task.get('due_date') or 'none'}, "
                      f"status={task['status']})")
                stats["initial_pushed"] += 1
                continue

            result = _run_bridge(["add", project_name, title, description] if description
                                  else ["add", project_name, title])
            if result is None:
                logger.warning("Failed to create reminder: %s :: %s", project_name, title)
                stats["initial_skipped"] += 1
                continue

            due_date = task.get("due_date")
            if due_date:
                formatted = _format_due_date(str(due_date))
                _run_bridge(["set-due", project_name, title, formatted])

            if task["status"] in ("completed", "cancelled"):
                _run_bridge(["complete", project_name, title])

            reminder = {
                "title": title,
                "notes": description,
                "due_date": due_date,
                "priority": task.get("priority", "normal"),
                "completed": task["status"] in ("completed", "cancelled"),
                "list_name": project_name,
            }
            _upsert_sync_state(compound_key, task["id"], reminder)
            stats["initial_pushed"] += 1
            logger.info("Pushed: %s :: %s", project_name, title)

        self.stats.update(stats)
        return self.stats

    @staticmethod
    def _resolve_project_name(task: dict) -> Optional[str]:
        project_id = task.get("project_id")
        if not project_id:
            return None
        rows = db.query("tasks", "SELECT name FROM projects WHERE id=?", (project_id,))
        return rows[0]["name"] if rows else None


# ── CLI ────────────────────────────────────────────────────────────────────

def _format_stats(stats: dict):
    print("\nSync Summary:")
    print(f"  Lists found:             {stats.get('lists_found', 0)}")
    print(f"  Tasks created (R→T):     {stats.get('r_to_t_created', 0)}")
    print(f"  Tasks updated (R→T):     {stats.get('r_to_t_updated', 0)}")
    print(f"  Tasks skipped (R→T):     {stats.get('r_to_t_skipped', 0)}")
    print(f"  Reminders completed (T→R): {stats.get('t_to_r_completed', 0)}")
    print(f"  Reminders updated (T→R):   {stats.get('t_to_r_updated', 0)}")
    push = stats.get("initial_pushed", 0)
    skipped = stats.get("initial_skipped", 0)
    if push or skipped:
        print(f"  Initial push created:     {push}")
        print(f"  Initial push skipped:     {skipped}")


def main():
    parser = argparse.ArgumentParser(
        description="Bidirectional sync between Apple Reminders and tasks.db",
        epilog="Examples:\n"
               "  %(prog)s                        Full bidirectional sync\n"
               "  %(prog)s --dry-run               Preview only, no changes\n"
               "  %(prog)s --initial-push          Export all tasks as new reminders\n"
               "  %(prog)s --one-way=r2t           Reminders → Tasks only",
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview only, no changes written")
    parser.add_argument("--one-way", choices=["r2t", "t2r"],
                        help="Run only one direction: r2t (Reminders→Tasks) or t2r (Tasks→Reminders)")
    parser.add_argument("--initial-push", action="store_true",
                        help="One-shot: export all unlinked tasks as new reminders")
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

    if args.initial_push:
        syncer.initial_push()
    elif args.one_way == "r2t":
        syncer.sync_reminders_to_tasks()
    elif args.one_way == "t2r":
        syncer.sync_tasks_to_reminders()
    else:
        syncer.sync_all()

    _format_stats(syncer.stats)
    db.checkpoint_all()


if __name__ == "__main__":
    main()
