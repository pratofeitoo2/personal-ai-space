# Automation Briefing Data Quality & Query Expansion Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers-optimized:subagent-driven-development (recommended) or superpowers-optimized:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Fix broken automation queries (NULL due_dates, empty habit_logs) and add new queries to surface jobs, needs, and relationship data in daily briefings.
**Architecture:** Modify `automations/runner.py` QUERIES dict, `config/automations.yaml` rules, add indexes to self.db and tasks.db, implement `mark_habit_complete()` wrapper in sync code.
**Tech Stack:** Python 3.13, SQLite3, YAML, FastAPI, cron
**Assumptions:** Engine runs on macOS with Apple Reminders/Calendar bridges. `sync_reminders.py` and `sync_self.py` are working. Cron jobs handle periodic syncs.

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `engine/automations/runner.py` | Modify | Add/fix QUERIES dict entries, add `_format_item()` branches |
| `engine/config/automations.yaml` | Modify | Add new sections to briefings, add new interval rules |
| `engine/db/self/schema_self.sql` | Modify | Add indexes for habit_logs and goals queries |
| `engine/db/tasks/schema_tasks.sql` | Modify | Add composite index for due_date+priority |
| `engine/sync/sync_habits.py` | Create | Habit completion API with atomic habit_logs write |
| `engine/cli.py` | Modify | Add `habit complete` CLI command |
| `engine/db/db_manager.py` | Modify | Register sync_habits module |

---

## Wave 1: Critical Fixes (unblocks existing briefings)

### Task 1: Assign due_dates to all pending tasks

**Files:**
- Modify: `engine/db/tasks/tasks.db` (direct SQL)

**Does NOT cover:** Creating new tasks, modifying task titles, or changing project assignments.

- [x] **Step 1: Check current state**

Run:
```bash
PYTHONPATH=engine python3 -c "
import db_manager as db
tasks = db.query('tasks', \"SELECT id, title, project_id FROM tasks WHERE status='pending'\", ())
for t in tasks:
    print(f'{t[\"id\"]:<55} {t[\"title\"][:40]}')
print(f'Total: {len(tasks)}')
"
```
Expected: 7-8 tasks with NULL due_date

- [x] **Step 2: Assign due_dates via SQL**

Run:
```bash
PYTHONPATH=engine python3 -c "
import db_manager as db
from datetime import datetime, timedelta

now = datetime.now()
today = now.strftime('%Y-%m-%d')
tomorrow = (now + timedelta(days=1)).strftime('%Y-%m-%d')
monday = (now + timedelta(days=(7 - now.weekday()) % 7 or 7)).strftime('%Y-%m-%d')

assignments = [
    ('task-data-pipeline-add-due-dates-to-tasks', today),
    ('task-everyday-estender-roupa', today),
    ('task-everyday-lavar-panos-de-chao', tomorrow),
    ('task-groceries-comprar-pregador', tomorrow),
    ('task-groceries-comprar-saco-de-lixo', tomorrow),
    ('task-job-applications-apply-my-profile-on-the-job-position', monday),
    ('task-work-look-the-diversematch-lp-copy-for-ta', monday),
]

for task_id, due in assignments:
    db.execute('tasks', 'UPDATE tasks SET due_date=?, updated_at=? WHERE id=?', (due, now.isoformat(), task_id))
    print(f'  Updated {task_id[:40]} → due {due}')

db.checkpoint_all()
print('Done')
"
```
Expected: All 7 tasks updated

- [x] **Step 3: Verify queries now return data**

Run:
```bash
PYTHONPATH=engine python3 -c "
import db_manager as db
# tasks_due_today should return today's tasks
rows = db.query('tasks', \"SELECT t.title, t.due_date, p.name AS project FROM tasks t LEFT JOIN projects p ON t.project_id=p.id WHERE t.status NOT IN ('completed','cancelled') AND t.due_date = date('now','localtime') ORDER BY t.priority\", ())
print(f'tasks_due_today: {len(rows)} rows')
for r in rows:
    print(f'  {r[\"title\"][:40]} due={r[\"due_date\"]} proj={r[\"project\"]}')
"
```
Expected: 3 tasks due today (estender-roupa, add-due-dates, groceries items if today)

---

### Task 2: Add indexes for automation queries

**Files:**
- Modify: `engine/db/self/schema_self.sql`
- Modify: `engine/db/tasks/schema_tasks.sql`

**Does NOT cover:** Query logic changes, new queries, or data migrations.

- [x] **Step 1: Add self.db indexes**

Run:
```bash
PYTHONPATH=engine python3 -c "
import db_manager as db

indexes = [
    'self',
    'CREATE INDEX IF NOT EXISTS idx_habits_active_last_completed ON habits(last_completed) WHERE status = \"active\"',
    'CREATE INDEX IF NOT EXISTS idx_habit_logs_completed_at ON habit_logs(completed_at)',
    'CREATE INDEX IF NOT EXISTS idx_goals_target_date_active ON goals(target_date) WHERE status IN (\"active\",\"in_progress\")',
]

for i in range(1, len(indexes), 2):
    db.execute('self', indexes[i], ())
    print(f'  Created: {indexes[i][:60]}')

db.checkpoint_all()
print('self.db indexes done')
"
```
Expected: 3 indexes created

- [x] **Step 2: Add tasks.db index**

Run:
```bash
PYTHONPATH=engine python3 -c "
import db_manager as db

db.execute('tasks', 'CREATE INDEX IF NOT EXISTS idx_tasks_active_due_priority ON tasks(due_date, priority) WHERE status IN (\"pending\",\"in_progress\",\"blocked\")', ())
db.checkpoint_all()
print('tasks.db index created')
"
```
Expected: 1 index created

- [x] **Step 3: Verify indexes exist**

Run:
```bash
PYTHONPATH=engine python3 -c "
import db_manager as db
for db_name in ['self', 'tasks']:
    rows = db.query(db_name, 'SELECT name FROM sqlite_master WHERE type=\"index\" AND name LIKE \"idx_%\"', ())
    print(f'{db_name}: {len(rows)} custom indexes')
    for r in rows:
        print(f'  {r[\"name\"]}')
"
```
Expected: 3 self.db indexes + 1 tasks.db index

---

### Task 3: Implement mark_habit_complete() wrapper

**Files:**
- Create: `engine/sync/sync_habits.py`
- Modify: `engine/cli.py`

**Does NOT cover:** Obsidian sync integration, habit creation, habit deletion.

- [x] **Step 1: Create sync_habits.py**

```python
"""sync_habits.py — Atomic habit completion tracking.

Writes to both habits table (streak update) and habit_logs table
in a single transaction to keep them in sync.
"""
import sys
from pathlib import Path

_ENGINE_DIR = Path(__file__).resolve().parent.parent
if str(_ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(_ENGINE_DIR))

import db_manager as db
from db.id_helpers import for_habit_log
from datetime import datetime, timezone


def mark_habit_complete(habit_id: str, notes: str = None, confidence: float = 1.0) -> dict:
    """Mark a habit as completed for today. Atomic: updates habits + inserts habit_log.
    
    Returns: {"status": "ok", "habit_id": str, "log_id": str, "new_streak": int}
    Raises: ValueError if habit not found or already completed today.
    """
    now = datetime.now(timezone.utc).isoformat()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    with db.transaction("self") as conn:
        # Check habit exists and not already completed today
        row = conn.execute(
            "SELECT id, habit_name, current_streak, last_completed FROM habits WHERE id = ?",
            (habit_id,)
        ).fetchone()
        
        if not row:
            raise ValueError(f"Habit not found: {habit_id}")
        
        if row["last_completed"] and row["last_completed"].startswith(today):
            raise ValueError(f"Habit already completed today: {row['habit_name']}")
        
        # Update habits table
        new_streak = (row["current_streak"] or 0) + 1
        conn.execute(
            """UPDATE habits 
               SET last_completed = ?, 
                   current_streak = ?,
                   total_completions = COALESCE(total_completions, 0) + 1
               WHERE id = ?""",
            (now, new_streak, habit_id)
        )
        
        # Insert into habit_logs
        log_id = for_habit_log(habit_id)
        conn.execute(
            """INSERT INTO habit_logs (id, habit_id, completed_at, notes, confidence_level)
               VALUES (?, ?, ?, ?, ?)""",
            (log_id, habit_id, now, notes, confidence)
        )
    
    return {
        "status": "ok",
        "habit_id": habit_id,
        "log_id": log_id,
        "new_streak": new_streak,
    }


def get_habits_at_risk() -> list[dict]:
    """Get habits that need attention (not completed recently)."""
    return db.query("self",
        """SELECT id, habit_name, current_streak, last_completed 
           FROM habits 
           WHERE status = 'active' 
           AND (last_completed IS NULL OR last_completed < date('now','localtime','-1 day'))""",
        ()
    )


def get_habits_today_status() -> list[dict]:
    """Get today's completion status for all active habits."""
    return db.query("self",
        """SELECT h.id, h.habit_name, 
                  CASE WHEN hl.id IS NOT NULL THEN 'completed' ELSE 'pending' END as status
           FROM habits h 
           LEFT JOIN habit_logs hl ON hl.habit_id=h.id AND date(hl.completed_at)=date('now','localtime') 
           WHERE h.status='active'""",
        ()
    )


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Habit tracking")
    sub = parser.add_subparsers(dest="cmd")
    
    complete = sub.add_parser("complete", help="Mark habit as done")
    complete.add_argument("habit_id", help="Habit ID (e.g. h-journal)")
    complete.add_argument("--notes", help="Optional notes")
    
    sub.add_parser("at-risk", help="Show habits needing attention")
    sub.add_parser("today", help="Show today's status")
    
    args = parser.parse_args()
    
    if args.cmd == "complete":
        result = mark_habit_complete(args.habit_id, args.notes)
        print(f"✅ {result['habit_id']} — streak: {result['new_streak']}")
    elif args.cmd == "at-risk":
        habits = get_habits_at_risk()
        for h in habits:
            print(f"  ⚠️ {h['habit_name']} — streak: {h['current_streak']}, last: {h['last_completed'] or 'never'}")
    elif args.cmd == "today":
        habits = get_habits_today_status()
        for h in habits:
            icon = "✅" if h["status"] == "completed" else "⬜"
            print(f"  {icon} {h['habit_name']}")
    else:
        parser.print_help()
```

- [x] **Step 2: Test mark_habit_complete()**

Run:
```bash
PYTHONPATH=engine python3 sync/sync_habits.py complete h-journal --notes "Test entry"
```
Expected: `✅ h-journal — streak: 4`

- [x] **Step 3: Verify habit_logs populated**

Run:
```bash
PYTHONPATH=engine python3 -c "
import db_manager as db
logs = db.query('self', 'SELECT * FROM habit_logs ORDER BY completed_at DESC LIMIT 3', ())
print(f'habit_logs rows: {len(logs)}')
for l in logs:
    print(f'  {l[\"habit_id\"]} at {l[\"completed_at\"][:19]}')
"
```
Expected: 1 row with h-journal entry

- [x] **Step 4: Test duplicate prevention**

Run:
```bash
PYTHONPATH=engine python3 sync/sync_habits.py complete h-journal
```
Expected: Error "Habit already completed today"

---

## Wave 2: Query Expansion (adds new briefing sections)

### Task 4: Add new automation queries to runner.py

**Files:**
- Modify: `engine/automations/runner.py`

**Does NOT cover:** automations.yaml changes (Task 5), formatting logic (Task 6).

- [x] **Step 1: Add new queries to QUERIES dict**

Add after existing QUERIES entries in `runner.py`:

```python
    # New queries for expanded briefings
    "habits_streaks": (
        "self",
        "SELECT habit_name, current_streak, total_completions FROM habits WHERE status='active' AND current_streak > 0 ORDER BY current_streak DESC",
        "habit_name",
        (),
    ),
    "needs_active": (
        "self",
        "SELECT name, category, priority FROM needs WHERE status='active' ORDER BY CASE priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END",
        "name",
        (),
    ),
    "jobs_status_summary": (
        "jobs",
        "SELECT status, COUNT(*) as cnt FROM applications GROUP BY status ORDER BY cnt DESC",
        "status",
        (),
    ),
    "applications_stale": (
        "jobs",
        "SELECT a.job_title, c.name AS company, a.status, CAST(julianday('now','localtime') - julianday(a.updated_at) AS INTEGER) AS days_stale FROM applications a JOIN companies c ON a.company_id=c.id WHERE a.status='saved' AND a.updated_at < date('now','localtime','-7 days') ORDER BY a.updated_at ASC LIMIT 5",
        "job_title",
        (),
    ),
    "tasks_unscheduled": (
        "tasks",
        "SELECT t.title, t.priority, p.name AS project FROM tasks t LEFT JOIN projects p ON t.project_id=p.id WHERE t.due_date IS NULL AND t.status NOT IN ('completed','cancelled') ORDER BY CASE t.priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1 ELSE 2 END",
        "title",
        (),
    ),
```

- [x] **Step 2: Verify queries execute without error**

Run:
```bash
PYTHONPATH=engine python3 -c "
from automations.runner import QUERIES
import db_manager as db

for qname in ['habits_streaks', 'needs_active', 'jobs_status_summary', 'applications_stale', 'tasks_unscheduled']:
    spec = QUERIES.get(qname)
    if spec:
        db_name, sql, _, params = spec
        rows = db.query(db_name, sql, params)
        print(f'{qname}: {len(rows)} rows')
    else:
        print(f'{qname}: NOT FOUND')
"
```
Expected: All 5 queries return data (0+ rows each)

---

### Task 5: Add _format_item() branches for new queries

**Files:**
- Modify: `engine/automations/runner.py`

**Does NOT cover:** Query logic (Task 4), YAML config (Task 7).

- [x] **Step 1: Add formatting branches**

In `_format_item()` method, add after existing `if query_name in (...)` blocks:

```python
        if query_name == "habits_streaks":
            if row.get("current_streak") is not None:
                extras.append(f"🔥{row['current_streak']}")
            if row.get("total_completions") is not None:
                extras.append(f"total:{row['total_completions']}")
        if query_name == "needs_active":
            if row.get("priority"):
                extras.append(f"[{row['priority']}]")
            if row.get("category"):
                extras.append(f"({row['category']})")
        if query_name == "jobs_status_summary":
            return f"  {val}: {row.get('cnt', 0)}"
        if query_name == "applications_stale":
            if row.get("days_stale") is not None:
                extras.append(f"{row['days_stale']}d sem update")
            if row.get("company"):
                extras.append(f"@{row['company']}")
        if query_name == "tasks_unscheduled":
            if row.get("priority") and row["priority"] not in (None, "normal"):
                extras.append(f"[{row['priority']}]")
```

- [x] **Step 2: Verify formatting works**

Run:
```bash
PYTHONPATH=engine python3 -c "
from automations.runner import AutomationRunner
import db_manager as db
from automations.runner import QUERIES

# Simulate formatting
for qname in ['habits_streaks', 'needs_active', 'jobs_status_summary']:
    spec = QUERIES.get(qname)
    if spec:
        db_name, sql, field, params = spec
        rows = db.query(db_name, sql, params)
        if rows:
            # Create minimal runner instance for formatting
            class FakeRunner:
                pass
            r = FakeRunner()
            r._query_db = lambda q: db.query(*QUERIES[q][:2], QUERIES[q][3]) if q in QUERIES else []
            formatted = r._format_item(rows[0], qname)
            print(f'{qname}: {formatted}')
"
```
Expected: Formatted strings without errors

---

### Task 6: Update automations.yaml with new briefing sections

**Files:**
- Modify: `engine/config/automations.yaml`

**Does NOT cover:** Query logic (Task 4), formatting (Task 5).

- [x] **Step 1: Update morning_brief sections**

Replace the morning_brief sections with:

```yaml
  - id: morning_brief
    name: "Briefing Matinal"
    schedule: "07:00"
    sections:
      - {type: greeting}
      - {type: llm_opener}
      - {query: tasks_due_today,      label: "📋 Tarefas do dia",     empty_msg: "Nenhuma tarefa para hoje"}
      - {query: tasks_unscheduled,    label: "📝 Para agendar",       empty_msg: ""}
      - {query: calendar_today,       label: "📅 Agenda de hoje",     empty_msg: "Sem compromissos hoje"}
      - {query: jobs_status_summary,  label: "💼 Pipeline de vagas",   empty_msg: ""}
      - {query: habits_at_risk,       label: "🎯 Hábitos em risco",   empty_msg: "Todos os hábitos em dia"}
      - {query: habits_streaks,       label: "🔥 Sequências ativas",  empty_msg: ""}
      - {query: needs_active,         label: "🧭 Necessidades",       empty_msg: ""}
      - {query: goals_active,         label: "🎯 Metas ativas",       empty_msg: "Nenhuma meta ativa no momento"}
```

- [x] **Step 2: Update midday_checkpoint sections**

```yaml
  - id: midday_checkpoint
    name: "Checkpoint Meio-dia"
    schedule: "12:00"
    sections:
      - {type: greeting}
      - {query: tasks_remaining,      label: "📋 Restam do dia",      empty_msg: "Tarefas todas concluídas!"}
      - {query: habits_today_status,  label: "🎯 Hábitos hoje",       empty_msg: "Nenhum hábito registrado ainda hoje"}
      - {query: habits_at_risk,       label: "⚠️ Hábitos em risco",   empty_msg: ""}
```

- [x] **Step 3: Add new interval alert for stale applications**

```yaml
  - id: alert_stale_applications
    name: "Vagas Paradas"
    schedule: {type: interval, seconds: 3600}
    state_track: true
    min_items: 1
    sections:
      - {query: applications_stale,   label: "📦 Vagas sem update (7d+)", empty_msg: ""}
```

- [x] **Step 4: Verify YAML parses correctly**

Run:
```bash
cd engine && python3 -c "
import yaml
with open('config/automations.yaml') as f:
    data = yaml.safe_load(f)
rules = data.get('automations', [])
print(f'Loaded {len(rules)} rules')
for r in rules:
    sections = len(r.get('sections', []))
    print(f'  {r[\"id\"]}: {sections} sections')
"
```
Expected: 8 rules (3 briefings + 5 alerts), morning_brief has 10 sections

---

## Wave 3: Quality of Life

### Task 7: Add habit complete CLI command

**Files:**
- Modify: `engine/cli.py`

**Does NOT cover:** Web API endpoints, Obsidian integration.

- [x] **Step 1: Add habit subcommand to cli.py**

Add after existing subcommands in cli.py:

```python
    # Habit tracking
    habit_parser = subparsers.add_parser("habit", help="Habit tracking")
    habit_sub = habit_parser.add_subparsers(dest="habit_cmd")
    
    habit_complete = habit_sub.add_parser("complete", help="Mark habit as done")
    habit_complete.add_argument("habit_id", help="Habit ID (e.g. h-journal)")
    habit_complete.add_argument("--notes", help="Optional notes")
    
    habit_sub.add_parser("today", help="Show today's habit status")
    habit_sub.add_parser("at-risk", help="Show habits needing attention")
```

And add handler:

```python
    if args.command == "habit":
        from sync.sync_habits import mark_habit_complete, get_habits_today_status, get_habits_at_risk
        
        if args.habit_cmd == "complete":
            result = mark_habit_complete(args.habit_id, args.notes)
            print(f"✅ {result['habit_id']} — streak: {result['new_streak']}")
        elif args.habit_cmd == "today":
            habits = get_habits_today_status()
            for h in habits:
                icon = "✅" if h["status"] == "completed" else "⬜"
                print(f"  {icon} {h['habit_name']}")
        elif args.habit_cmd == "at-risk":
            habits = get_habits_at_risk()
            for h in habits:
                print(f"  ⚠️ {h['habit_name']} — streak: {h['current_streak']}, last: {h['last_completed'] or 'never'}")
        else:
            habit_parser.print_help()
```

- [x] **Step 2: Test CLI command**

Run:
```bash
cd engine && python3 cli.py habit today
```
Expected: Shows 4 habits with ⬜/✅ status

---

### Task 8: Documentation — DATABASES.md

**Files:**
- Create: `docs/DATABASES.md`

**Does NOT cover:** API docs, architecture docs, troubleshooting docs.

- [x] **Step 1: Create DATABASES.md**

```markdown
# Database Schemas

## tasks.db

### tasks (19 columns)
| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | TEXT | PK | — | Semantic ID (e.g. `task-everyday-estender-roupa`) |
| title | TEXT | NOT NULL | — | Task title |
| description | TEXT | yes | '' | Extended description |
| project_id | TEXT | FK→projects.id | NULL | Owning project |
| parent_task_id | TEXT | FK→tasks.id | NULL | Parent task for subtasks |
| priority | TEXT | NOT NULL | 'normal' | critical/high/normal/low |
| status | TEXT | NOT NULL | 'pending' | pending/in_progress/completed/cancelled |
| progress_pct | INTEGER | NOT NULL | 0 | 0-100 completion |
| due_date | DATETIME | yes | NULL | Due date (YYYY-MM-DD) |
| created_at | DATETIME | yes | CURRENT_TIMESTAMP | Creation timestamp |
| updated_at | DATETIME | yes | CURRENT_TIMESTAMP | Last update timestamp |

### projects (13 columns)
| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | TEXT | PK | — | Semantic ID (e.g. `proj-everyday`) |
| name | TEXT | NOT NULL | — | Project name |
| status | TEXT | yes | 'active' | active/paused/completed |
| priority | TEXT | yes | 'normal' | Priority level |

## self.db

### habits (10 columns)
| Column | Type | Description |
|--------|------|-------------|
| id | TEXT | PK (e.g. `h-journal`) |
| habit_name | TEXT | Display name |
| category | TEXT | Category tag |
| frequency | TEXT | daily/weekly |
| current_streak | INTEGER | Current consecutive days |
| total_completions | INTEGER | All-time count |
| last_completed | DATETIME | Last completion timestamp |
| status | TEXT | active/paused |

### habit_logs (5 columns)
| Column | Type | Description |
|--------|------|-------------|
| id | TEXT | PK (e.g. `hl-h-journal-20260530`) |
| habit_id | FK→habits.id | Which habit |
| completed_at | DATETIME | When completed |
| notes | TEXT | Optional notes |
| confidence_level | FLOAT | 0.0-1.0 confidence |

### goals (13 columns)
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | PK |
| title | TEXT | Goal title |
| status | TEXT | active/in_progress/completed |
| priority | INTEGER | 0=highest |
| progress | REAL | 0.0-1.0 |
| target_date | TEXT | Deadline |

### needs (8 columns)
| Column | Type | Description |
|--------|------|-------------|
| id | TEXT | PK (e.g. `need_001`) |
| name | TEXT | Need name |
| category | TEXT | functional/physical/emotional |
| priority | TEXT | critical/high/medium/low |
| status | TEXT | active/in_progress |

## jobs.db

### applications (13 columns)
| Column | Type | Description |
|--------|------|-------------|
| id | TEXT | PK |
| company_id | FK→companies.id | Company reference |
| job_title | TEXT | Position title |
| status | TEXT | saved/applied/interview/offer/rejected |
| applied_date | DATE | When applied |
| salary_range | TEXT | Salary info |
| location | TEXT | Job location |

## Calendar

### upcoming (13 columns)
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | PK |
| event_name | TEXT | Event title |
| event_date | TEXT | YYYY-MM-DD |
| event_time | TEXT | HH:MM |
| category | TEXT | personal/work |
| status | TEXT | confirmed/tentative |
```

- [x] **Step 2: Verify file created**

Run: `ls -la docs/DATABASES.md`
Expected: File exists with 150+ lines

---

## Verification Checklist

After all tasks complete, verify:

1. `tasks_due_today` returns 3+ tasks (those with today's due_date)
2. `habits_at_risk` returns 2-3 habits (after marking one complete, it should decrease)
3. `habits_completed_today` returns the habit you completed in Task 3
4. `habits_today_status` shows ✅ for completed habits
5. `needs_active` returns 4 needs
6. `jobs_status_summary` returns status counts
7. `tasks_unscheduled` returns tasks without due_dates (should be 0 after Task 1)
8. Morning briefing (07:00) includes all new sections
9. `python3 cli.py habit today` works

---

## Commit Strategy

```
Wave 1:
  git add engine/db/ && git commit -m "fix(db): add indexes for automation queries"
  git add engine/sync/sync_habits.py && git commit -m "feat(habits): add atomic habit completion tracking"
  git add engine/cli.py && git commit -m "feat(cli): add habit complete/today/at-risk commands"

Wave 2:
  git add engine/automations/runner.py && git commit -m "feat(automations): add jobs/needs/habits streaks queries"
  git add engine/config/automations.yaml && git commit -m "feat(automations): expand morning briefing with new sections"

Wave 3:
  git add docs/DATABASES.md && git commit -m "docs: add database schema reference"
```
