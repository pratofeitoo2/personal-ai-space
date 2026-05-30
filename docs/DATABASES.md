# Database Schemas

> Reference documentation for all SQLite databases in the Personal AI Powerhouse engine.

---

## tasks.db

Location: `engine/db/tasks/tasks.db`

### tasks (19 columns)

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | TEXT | PK | — | Semantic ID (e.g. `task-everyday-estender-roupa`) |
| title | TEXT | NOT NULL | — | Task title |
| description | TEXT | yes | `''` | Extended description |
| project_id | TEXT | FK→projects.id | NULL | Owning project |
| parent_task_id | TEXT | FK→tasks.id | NULL | Parent task for subtasks |
| priority | TEXT | NOT NULL | `'normal'` | `critical` / `high` / `normal` / `low` |
| status | TEXT | NOT NULL | `'pending'` | `pending` / `in_progress` / `completed` / `cancelled` |
| progress_pct | INTEGER | NOT NULL | `0` | 0-100 completion percentage |
| estimated_hours | FLOAT | yes | NULL | Time estimate |
| actual_hours | FLOAT | yes | NULL | Time spent |
| sort_order | INTEGER | yes | `0` | Display ordering |
| assigned_to | TEXT | yes | NULL | Assignee |
| tags | TEXT | yes | NULL | Comma-separated tags |
| recurrence | TEXT | yes | NULL | Recurrence rule |
| category | TEXT | yes | `'general'` | Task category |
| due_date | DATETIME | yes | NULL | Due date (YYYY-MM-DD) |
| completed_at | DATETIME | yes | NULL | Completion timestamp |
| created_at | DATETIME | yes | CURRENT_TIMESTAMP | Creation timestamp |
| updated_at | DATETIME | yes | CURRENT_TIMESTAMP | Last update timestamp |

**Indexes:** `idx_tasks_active_due_priority` on (due_date, priority) WHERE status IN ('pending','in_progress','blocked')

### projects (13 columns)

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | TEXT | PK | — | Semantic ID (e.g. `proj-everyday`) |
| name | TEXT | NOT NULL | — | Project name |
| description | TEXT | yes | NULL | Project description |
| status | TEXT | yes | `'active'` | `active` / `paused` / `completed` |
| priority | TEXT | yes | `'normal'` | Priority level |
| start_date | DATE | yes | NULL | Project start |
| end_date | DATE | yes | NULL | Project end |
| progress_pct | INTEGER | yes | `0` | 0-100 completion |
| total_tasks | INTEGER | yes | `0` | Task count |
| completed_tasks | INTEGER | yes | `0` | Completed count |
| category | TEXT | yes | `'general'` | Category |
| created_at | DATETIME | yes | CURRENT_TIMESTAMP | Creation |
| updated_at | DATETIME | yes | CURRENT_TIMESTAMP | Last update |

### task_archive (20 columns)

Same schema as `tasks` plus `archived_at` (DATETIME). Stores completed/cancelled tasks.

### sync_state (8 columns)

Tracks bidirectional sync between tasks.db and Apple Reminders.

| Column | Type | Description |
|--------|------|-------------|
| id | TEXT | PK |
| entity_type | TEXT | `'apple-reminder'` |
| entity_id | TEXT | Task ID |
| file_path | TEXT | Compound key: `ListName::ReminderTitle` |
| file_hash | TEXT | SHA-256 hash for change detection |
| last_modified | DATETIME | Last modification |
| last_synced | DATETIME | Last sync timestamp |
| direction | TEXT | `'bidirectional'` |

---

## self.db

Location: `engine/db/self/self.db`

### habits (10 columns)

| Column | Type | Description |
|--------|------|-------------|
| id | TEXT | PK (e.g. `h-journal`) |
| habit_name | TEXT | Display name |
| category | TEXT | Category tag |
| frequency | TEXT | `daily` / `weekly` |
| start_date | DATE | When habit started |
| current_streak | INTEGER | Current consecutive completions |
| total_completions | INTEGER | All-time count |
| last_completed | DATETIME | Last completion timestamp |
| target_streak | INTEGER | Goal streak length |
| status | TEXT | `active` / `paused` |

**Indexes:** `idx_habits_active_last_completed` on (last_completed) WHERE status = 'active'

### habit_logs (5 columns)

| Column | Type | Description |
|--------|------|-------------|
| id | TEXT | PK (e.g. `hl-h-journal-20260530`) |
| habit_id | FK→habits.id | Which habit |
| completed_at | DATETIME | When completed |
| notes | TEXT | Optional notes |
| confidence_level | FLOAT | 0.0-1.0 confidence |

**Indexes:** `idx_habit_logs_completed_at` on (completed_at)

### goals (13 columns)

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | PK |
| title | TEXT | Goal title |
| description | TEXT | Details |
| category | TEXT | Category |
| status | TEXT | `active` / `in_progress` / `completed` |
| priority | INTEGER | 0=highest |
| progress | REAL | 0.0-1.0 |
| target_date | TEXT | Deadline (YYYY-MM-DD) |
| progress_source | TEXT | How progress is measured |
| created_at | TEXT | Creation timestamp |
| updated_at | TEXT | Last update |
| completed_at | TEXT | Completion timestamp |
| tags | TEXT | Comma-separated tags |

**Indexes:** `idx_goals_target_date_active` on (target_date) WHERE status IN ('active','in_progress')

### needs (8 columns)

| Column | Type | Description |
|--------|------|-------------|
| id | TEXT | PK (e.g. `need_001`) |
| category | TEXT | `functional` / `physical` / `emotional` |
| name | TEXT | Need name |
| priority | TEXT | `critical` / `high` / `medium` / `low` |
| status | TEXT | `active` / `in_progress` |
| description | TEXT | Details |
| linked_tasks | TEXT | Comma-separated task IDs |
| created_at | DATETIME | Creation timestamp |

### relationships (10 columns)

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | PK |
| name | TEXT | Person's name |
| email | TEXT | Email address |
| phone | TEXT | Phone number |
| cpf | TEXT | CPF (Brazilian ID) |
| birth_date | TEXT | Birthday |
| relationship_type | TEXT | `person` / `colleague` / etc. |
| notes | TEXT | Free-form notes |
| created_at | TEXT | Creation timestamp |
| updated_at | TEXT | Last update |

### documents (11 columns)

| Column | Type | Description |
|--------|------|-------------|
| id | TEXT | PK |
| title | TEXT | Document title |
| doc_type | TEXT | `academic` / `gov_docs` / `professional` |
| subcategory | TEXT | Subcategory |
| tags | TEXT | JSON array of tags |
| file_path | TEXT | File location |
| file_format | TEXT | File format |
| content | TEXT | Extracted text |
| metadata | TEXT | JSON metadata |
| created_at | TEXT | Creation timestamp |
| updated_at | TEXT | Last update |

### behaviors (7 columns)

| Column | Type | Description |
|--------|------|-------------|
| id | TEXT | PK |
| behavior_type | TEXT | `emotion` / `activity` / etc. |
| trigger | TEXT | What triggered the behavior |
| response | TEXT | Observed response |
| frequency | INTEGER | How often observed |
| effectiveness | FLOAT | Impact score |
| observed_date | DATE | When observed |

### profile (14 columns)

| Column | Type | Description |
|--------|------|-------------|
| id | TEXT | PK |
| name | TEXT | User's name |
| age | INTEGER | Age |
| timezone | TEXT | Timezone |
| work_style | TEXT | Work style preference |
| energy_peak_hours | TEXT | Peak energy times |
| communication_preference | TEXT | Preferred communication |
| decision_style | TEXT | Decision-making style |
| core_values | TEXT | Core values |
| feedback_preference | TEXT | How to receive feedback |
| goals_current_year | TEXT | Current year goals |
| constraints | TEXT | Known constraints |
| created_at | DATETIME | Creation |
| updated_at | DATETIME | Last update |

### observations (6 columns)

| Column | Type | Description |
|--------|------|-------------|
| id | TEXT | PK |
| obs_type | TEXT | `cli_command` / `context_accessed` / `task_created` |
| observed_at | DATETIME | When observed |
| data | TEXT | Observation data |
| source | TEXT | Source (default: `engine`) |
| created_at | DATETIME | Creation |

---

## calendar.db

Location: `engine/db/calendar/calendar.db`

### upcoming (13 columns)

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | PK |
| event_name | TEXT | Event title |
| event_date | TEXT | YYYY-MM-DD |
| event_time | TEXT | HH:MM |
| duration_hours | REAL | Duration |
| category | TEXT | `personal` / `work` |
| status | TEXT | `confirmed` / `tentative` |
| created_at | DATETIME | Creation |
| updated_at | DATETIME | Last update |
| account | TEXT | Calendar account |
| calendar_name | TEXT | Calendar name |
| location | TEXT | Event location |
| source | TEXT | Data source |

---

## jobs.db

Location: `engine/db/jobs/jobs.db`

### applications (13 columns)

| Column | Type | Description |
|--------|------|-------------|
| id | TEXT | PK |
| company_id | FK→companies.id | Company reference |
| job_title | TEXT | Position title |
| job_url | TEXT | Job posting URL |
| job_description | TEXT | Job description |
| salary_range | TEXT | Salary info |
| location | TEXT | Job location |
| remote | BOOLEAN | Remote work flag |
| status | TEXT | `saved` / `applied` / `interview` / `offer` / `rejected` |
| applied_date | DATE | When applied |
| notes | TEXT | Notes |
| created_at | DATETIME | Creation |
| updated_at | DATETIME | Last update |

---

## Automation Queries

| Query | DB | Purpose |
|-------|-----|---------|
| `tasks_due_today` | tasks | Tasks due today |
| `overdue_tasks` | tasks | Tasks past due date |
| `tasks_remaining` | tasks | Tasks due today or earlier |
| `tasks_completed_today` | tasks | Tasks completed today |
| `tasks_unscheduled` | tasks | Tasks without due_date |
| `habits_at_risk` | self | Habits needing attention |
| `habits_completed_today` | self | Today's completions |
| `habits_today_status` | self | Today's status per habit |
| `habits_streaks` | self | Active streaks |
| `goals_active` | self | Active goals |
| `goals_near_deadline` | self | Goals due within 7 days |
| `needs_active` | self | Active personal needs |
| `calendar_today` | calendar | Today's events |
| `calendar_upcoming` | calendar | Events in next 30 min |
| `jobs_status_summary` | jobs | Application status counts |
| `applications_stale` | jobs | Saved apps >7 days old |
