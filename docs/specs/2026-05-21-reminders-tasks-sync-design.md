# Reminders-Tasks Bidirectional Sync

**Date:** 2026-05-21
**Status:** Design

## Overview

Bidirectional sync between Apple Reminders and `tasks.db` — reminders become tasks and vice versa, organized through projects.

## Scope

- Sync Apple Reminders lists ↔ tasks.db projects (1:1 mapping by name)
- Sync reminder items ↔ tasks (field-level mapping)
- Auto-create projects for new Reminders lists
- Run as periodic cron job (hourly)
- Use existing `sync_state` table for identity tracking

## Non-Goals

- Handle reminder renames gracefully (compound key limits this; mitigated via fallback matching)
- Two-way real-time sync (event-based) — polling-based via cron
- Sync attachments or location data — not supported by tasks schema
- GUI/UI for the sync process

## Architecture

```
┌─────────────────┐     ┌──────────────────────┐     ┌─────────────────┐
│  Apple Reminders │────▶│  sync_reminders.py   │◀────│    tasks.db      │
│  (EventKit)      │◀────│  (bidirectional)     │────▶│  ┌───────────┐  │
│                  │     │                      │     │  │ tasks      │  │
│  Lists           │     │  1. Fetch reminders  │     │  │ projects   │  │
│    └ Items       │     │  2. Fetch tasks      │     │  │ sync_state │  │
└─────────────────┘     │  3. Diff & resolve    │     └──┴───────────┴──┘
                         │  4. Write to both      │
                         └──────────────────────┘
```

## Reminder Output Format

```
[ ] Buy groceries (due: 01.03.26, 09:00) [repeats: weekly] [Shopping]
     Notes: Organic milk
[x] Complete task (due: 02.03.26, 14:00) [Work]
```

Markers: `[x]`=completed, `[ ]`=incomplete, `!!`=high, `!`=medium.

## Field Mapping

| Reminder | Task Field | Direction | Notes |
|----------|-----------|-----------|-------|
| Title | `title` | both | Exact match |
| Notes (2nd line) | `description` | both | |
| Due date | `due_date` | both | `YYYY-MM-DD HH:mm` |
| Priority `!!` | `priority='critical'` | both | |
| Priority `!` | `priority='high'` | both | |
| No priority | `priority='normal'` | both | Default |
| `[x]` (completed) | `status='completed'` | R→T | |
| `[ ]` (incomplete) | `status='pending'` | R→T | |
| Task status | Reminder complete/incomplete | T→R | |
| List name | `project_id` (looked up) | R→T | Auto-create project if missing |
| — | `tags` | T→R | Stored in reminder notes as `tags: tag1, tag2` |
| — | `category` | T→R | Stored in reminder notes |

## Identity Tracking via sync_state

Uses the existing `sync_state` table:

```
entity_type = 'apple-reminder'
entity_id   = '<task_uuid>'                   (the task's PK in tasks.db)
file_path   = '<list_name>::<reminder_title>' (compound key: reminder's identity)
file_hash   = '<sha256 of reminder fields>'   (change detection)
last_modified  = '<reminder's last change>'
direction   = 'bidirectional'
```

This allows lookup in both directions:
- **Given a reminder** (list + title) → query sync_state by `file_path` → get `entity_id` (task ID)
- **Given a task** → query sync_state by `entity_id` → get `file_path` (compound key) → parse list + title

## Sync Algorithm

### Reminders → Tasks (R→T)

```
for each list in reminders:
    list_name = list.name
    project_id = find_or_create_project(list_name)

    for each reminder in list.items:
        compound_key = f"{list_name}::{reminder.title}"
        sync_row = find_sync_state(file_path=compound_key, entity_type='apple-reminder')
        
        if sync_row and not changed(reminder, sync_row):
            continue    // no change, skip
        
        if sync_row:
            task_id = sync_row.entity_id    // task UUID stored here
        else:
            task_id = None    // new reminder, will create
        
        upsert_task(
            id=task_id,
            title=reminder.title,
            description=reminder.notes,
            project_id=project_id,
            due_date=reminder.due_date,
            priority=map_priority(reminder.priority),
            status=map_status(reminder.completed),
        )
        upsert_sync_state(...)
```

### Tasks → Reminders (T→R)

```
for each row in sync_state where entity_type='apple-reminder' AND direction='bidirectional':
    task = get_task(entity_id=row.entity_id)
    if not task:
        continue        // deleted task, skip

    last_reminder_change = get_last_change(sync_state)
    if task.updated_at <= last_reminder_change:
        continue        // reminder is newer, skip

    compound_key = sync_state.file_path
    list_name, reminder_title = compound_key.split("::", 1)

    if task.status == 'completed':
        complete_reminder(list_name, reminder_title)
    else:
        update_reminder(
            list_name, reminder_title, 
            title=task.title,
            notes=task.description,
            due_date=task.due_date,
            priority=reverse_map_priority(task.priority),
        )
```

## List ↔ Project Mapping

- On each sync cycle, scan all Reminders lists
- For each list, look up project by name in `projects` table
- If not found, auto-create a new project with `status='active'`
- This means the Reminders list is the **source of truth** for which projects exist

## File: `engine/sync/sync_reminders.py`

Follows the same pattern as `sync_calendar.py`:

```python
class RemindersSync:
    def __init__(self, dry_run=False):
        ...
    
    def sync_all(self) -> dict:
        """Full bidirectional sync."""
        stats = {"r_to_t": 0, "t_to_r": 0}
        stats["r_to_t"] = self.sync_reminders_to_tasks()
        stats["t_to_r"] = self.sync_tasks_to_reminders()
        return stats
    
    def sync_reminders_to_tasks(self) -> int:
        """Push reminders → tasks.db."""
        ...
    
    def sync_tasks_to_reminders(self) -> int:
        """Push tasks.db → reminders."""
        ...
```

### CLI

```
python3 sync_reminders.py              # Full bidirectional sync
python3 sync_reminders.py --dry-run     # Preview only
python3 sync_reminders.py --one-way=r2t # Reminders → Tasks only
```

## Error Handling

- **Timeout**: 10s per bridge command, 3 retries with 2s/4s/8s backoff
- **Bridge failure**: Log, skip that list, continue with next. Don't abort entire sync.
- **Parse failure**: Log warning, skip that reminder, continue.
- **Permission error**: Log clear message, exit gracefully.

## Rollout

1. Write and test `sync_reminders.py` manually
2. Run full sync: `python3 sync_reminders.py --dry-run` for preview
3. Run live sync
4. Register hourly cron job

## Files Changed

- `engine/sync/sync_reminders.py` (new)
- `crontab` (add hourly job)
