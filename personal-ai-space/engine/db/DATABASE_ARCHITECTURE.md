# Database Architecture

## Overview

Five SQLite databases, each with a distinct responsibility. `tasks.db` is the hub for task
management; the other four serve supporting roles. This document maps every table, its
relationships, and how data propagates between databases.

```
┌──────────────┐     ┌──────────────┐
│   self.db    │     │  tasks.db    │ ←── hub
│  profile     │     │  projects    │
│  habits      │     │  tasks       │
│  habit_logs  │     │  subtasks    │
│  traits      │     │  deps        │
│  needs       │     │  history     │
│  behaviors   │     │  doc_links   │
│  goals       │     │  sync_state  │
│  relations.  │     │  cal_events  │
└──────┬───────┘     └──────┬───────┘
       │                    │
       │  (goal ↔ project)  │  (interactions log)
       └────────┬───────────┘
                │
       ┌────────┴───────────┐
       │   memories.db      │
       │  interactions      │ ← audit log for everything
       │  context_window    │
       │  agent_memory      │ ← pattern_learner + behavior_observer
       └────────┬───────────┘
                │
       ┌────────┴───────────┐
       │  agent_memory.db   │ ← MCP key-value memory (pi-memory server)
       │  semantic          │
       │  lessons           │
       │  events            │
       └────────┬───────────┘
                │
       ┌────────┴───────────┐
       │  knowledge.db      │
       │  articles          │
       │  notes             │
       │  refs / "refs"     │ ← duplicated (to consolidate)
       │  projects_knowledge│
       │  knowledge_index   │
       │  cross_references  │
       └────────────────────┘
```

---

## 1. `tasks.db` — Task Management Hub

**Path:** `engine/db/tasks.db`
**Schema:** `engine/db/schema_tasks.sql`
**Rows:** 33 tasks, 5 projects, 0 deps/history/doc_links/sync_state

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `projects` | Work streams | id, name, status, priority, progress_pct, category |
| `tasks` | Work items + subtasks | id, project_id, **parent_task_id** (self-ref for subtasks), title, status, priority, **progress_pct**, **sort_order**, effort_hours |
| `task_dependencies` | Task blocking/relating | task_id, depends_on, dependency_type (blocked_by, relates_to, etc.) |
| `task_history` | Status/progress change log | task_id, field, old_value, new_value, changed_by |
| `calendar_events` | Time-bound task slots | task_id, start_time, end_time, status |
| `doc_links` | .md file → entity mapping | entity_type/entity_id, file_path, link_type, frontmatter_status |
| `sync_state` | File ↔ DB sync tracking | entity, file_path, file_hash, last_modified, direction |

**Cross-database links:**
- `tasks.projects.name` ↔ `self.db.goals.title` (project maps to goal by name)
- `tasks.tasks.id` is referenced in `memories.db.interactions.context` as `task:<id>`
- `tasks.doc_links.file_path` points to `.md` files anywhere in `personal-ai-space/`

**Propagation rules (when a task/project changes):**
1. `tasks.task_history` — new row logged
2. `memories.db.interactions` — interaction logged (via `engine.send()`)
3. `agent_memory.db.semantic` — fact upserted (via MCP bridge, e.g. `task.<id>.status`)
4. `self.db.goals.progress` — recalculated if project name matches a goal title
5. `.md` file frontmatter — updated if `sync_state.direction` allows file writes

---

## 2. `self.db` — User Identity & Self-Model

**Path:** `engine/db/self.db`
**Schema:** `engine/db/schema_self.sql`
**Rows:** 1 profile, 5 habits, 25 traits, 4 needs, 20 behaviors, 6 relationships, 90 goals

| Table | Purpose | Notes |
|-------|---------|-------|
| `profile` | User identity data | name, age, timezone, work_style, energy_peak_hours, etc. |
| `habits` | Tracked habits | frequency, current_streak, target_streak, status |
| `habit_logs` | Habit completion records | 0 rows — not yet wired |
| `traits` | Inferred personality traits | from `comprehensive_extractor.py` |
| `needs` | User needs/pain points | priority, status, linked_tasks |
| `behaviors` | Observed behavior patterns | trigger, response, frequency, effectiveness |
| `goals` | Life/career goals | title, category, status, progress, target_date |
| `relationships` | People in user's life | name, email, phone, relationship_type |

**Cross-database links:**
- `goals.title` ↔ `tasks.projects.name` (loose: project → goal by matching title)
- `needs.linked_tasks` contains task IDs as comma-separated text

---

## 3. `memories.db` — Agent Audit Log & Agent Memory

**Path:** `engine/db/memories.db`
**Schema:** `engine/db/schema_memories.sql`
**Rows:** 76 interactions, 0 context_window, 25 agent_memory

| Table | Purpose | Notes |
|-------|---------|-------|
| `interactions` | Every CLI command + engine call | agent_id, action, input, output, duration_ms, status |
| `context_window` | Session context snapshots | 0 rows — not yet wired |
| `agent_memory` | Observer/pattern-learner key-value store | populated by behavior_observer + pattern_learner |

**Cross-database links:**
- `interactions.context` references task IDs as `task:<uuid>` in JSON
- `agent_memory.key` overlaps with `agent_memory.db.semantic.key` naming (e.g. `pattern.*`, `workflow.*`)

---

## 4. `agent_memory.db` — MCP Key-Value Semantic Memory

**Path:** `engine/db/agent_memory.db`
**Schema:** `engine/db/schema_agent_memory.sql`
**Rows:** ~28 semantic facts, 2 lessons, ~24 events

| Table | Purpose | Notes |
|-------|---------|-------|
| `semantic` | Atomic facts about user/system | key-value with confidence, category, source |
| `lessons` | Learned do/don't rules | negative flag, used_count, source |
| `events` | Audit log of writes | append-only, action + details JSON |

**Managed by:** `personal-ai-space/engine/memory/mcp-server/` (Node.js pi-memory server)
**Accessed by:** `mcp_bridge.py` via MCP tools `memory_remember`, `memory_search`, `memory_forget`, `memory_lessons`, `memory_stats`

**Cross-database links:**
- `semantic.key` naming convention: `user.*`, `project.*`, `task.*`, `system.*`, `synthesis.*`
- Overlaps with `memories.db.agent_memory.key` for pattern/workflow entries

---

## 5. `knowledge.db` — Articles, Notes, References

**Path:** `engine/db/knowledge.db`
**Schema:** `engine/db/schema_knowledge.sql`
**Rows:** 24 articles, 6 notes, 0 refs/""refs"", 0 projects_knowledge, 206 knowledge_index, 0 cross_references

| Table | Purpose | Notes |
|-------|---------|-------|
| `articles` | Imported web articles | title, url, source, tags, summary |
| `notes` | User-written notes | title, content, tags, category |
| `refs` + `"references"` | Reference links | **DUPLICATE** — to consolidate |
| `projects_knowledge` | Project-specific knowledge | 0 rows |
| `knowledge_index` | Tag/keyword frequency index | 206 terms |
| `cross_references` | Entity cross-links | 0 rows |

**Needs consolidation:** `refs` and `"references"` serve the same purpose.

---

## Propagation Layer (wired — Phase 2)

A single `propagator` module routes task/project changes to all relevant databases.
It is wired into every code path that creates or updates tasks.

**Code paths routed through propagator:**

| Source | Function | Propagator call |
|--------|----------|----------------|
| `task_coordinator.py` | `create_task()` | `on_task_created(task_id)` |
| `task_coordinator.py` | `update_status()` | `on_task_updated(task_id, old_values)` |
| `comprehensive_extractor.py` | `_extract_implicit_tasks()` | `on_task_created(tid)` |
| `init_engine.py` | `seed_tasks()` | `on_task_created(tid)` |
| `engine.py` | `create_task()` | (via task_coordinator) |

**Propagation flow:**

```
on_task_created(task_id)
  ├── 1. Log to tasks.task_history (field='created')
  ├── 2. Recalculate project.progress_pct (avg of child tasks)
  ├── 3. If project name matches self.db goal title, update goal.progress
  └── 4. Upsert agent_memory.db semantic fact (task.<id>.status, task.<id>.title)

on_task_updated(task_id, old_values)
  ├── 1. Detect changed fields by comparing old_values vs current
  ├── 2. Log each changed field to tasks.task_history
  ├── 3. If status/progress_pct changed:
  │     ├── Recalculate project.progress_pct
  │     ├── Sync to self.db goal if matched
  │     └── Update agent_memory.db facts
  ├── 4. Touch tasks.updated_at timestamp
  └── 5. Log to memories.db.interactions

on_task_deleted(task_id)
  ├── 1. Log to tasks.task_history (field='deleted')
  ├── 2. Log to memories.db.interactions
  └── 3. Recalculate project.progress_pct
```

**Auto-sync on engine start** (planned for Phase 4):
1. Scan `.md` files with `status:` and `project:` in frontmatter
2. Compare `mtime` against `sync_state.last_modified`
3. File newer → update DB; DB newer → update file; both match → skip
4. Update `sync_state.last_synced` after each reconciliation

---

## Migration History

| File | Date | Change |
|------|------|--------|
| `migrate_schema_v2.py` | 2026-05-10 | Added parent_task_id, progress_pct, sort_order, updated_at to tasks; priority, progress_pct, category, updated_at to projects; dependency_type, created_at to task_deps; changed_by to task_history; created doc_links + sync_state tables |
| `propagator.py` + 4 code paths | 2026-05-10 | Propagation layer wired into task_coordinator, comprehensive_extractor, init_engine, engine.py. Routes task create/update/delete to task_history, project progress, goal sync, memories.db, agent_memory.db. |

---

## File Locations

| Database | Path |
|----------|------|
| tasks.db | `engine/db/tasks.db` |
| self.db | `engine/db/self.db` |
| memories.db | `engine/db/memories.db` |
| agent_memory.db | `engine/db/agent_memory.db` |
| knowledge.db | `engine/db/knowledge.db` |
| **Schema files** | |
| schema_tasks.sql | `engine/db/schema_tasks.sql` |
| schema_self.sql | `engine/db/schema_self.sql` |
| schema_memories.sql | `engine/db/schema_memories.sql` |
| schema_agent_memory.sql | `engine/db/schema_agent_memory.sql` |
| schema_knowledge.sql | `engine/db/schema_knowledge.sql` |
