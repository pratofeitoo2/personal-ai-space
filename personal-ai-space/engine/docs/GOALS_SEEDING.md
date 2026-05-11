# Goals Seeding — User Instructions + AI Integration Plan

## Your Job: Seed the Goals Table

The `self.db` goals table is ready (12 columns, UNIQUE on title). Currently 0 rows.
You need to populate it. Use either method:

### Method A — SQL (fastest, recommended)

```sql
INSERT INTO goals (title, description, category, status, priority, progress, target_date, progress_source)
VALUES ('Clinical Sex Therapist Career', 'Become a licensed clinical sex therapist', 'career', 'active', 1, 0, '2027-12-31', 'independent');
```

Add as many as you want. `title` must be unique. Column reference:

| Column | Type | Default | Purpose |
|--------|------|---------|---------|
| title | TEXT | (required) | Goal name — matched by AI to projects/tasks |
| description | TEXT | null | Free text |
| category | TEXT | null | e.g. career, health, learning, financial |
| status | TEXT | 'active' | active, paused, completed, cancelled |
| priority | INTEGER | 0 | Higher = more important |
| progress | REAL | 0 | 0–100 (auto-synced if progress_source is set) |
| target_date | TEXT | null | ISO date: '2027-12-31' |
| progress_source | TEXT | 'independent' | **See integration below** |
| completed_at | TEXT | null | ISO date when completed |

### Method B — CLI command (once built)

A `python cli.py goal add "..."` command will be added later. For now, use Method A.

---

## AI Integration Plan (not yet built)

After you seed goals, the **Goal Reviewer Agent** will:

### Trigger
On engine start OR `python cli.py goal review` — scans `self.db.goals` for rows where the AI hasn't reviewed them yet (tracked via a `reviewed_at` timestamp or `sync_state`).

### Pipeline

```
┌─ Your input ─────────────────────────────────────────┐
│  INSERT INTO goals (title, description, category)     │
│  VALUES ('Clinical Sex Therapist', '...', 'career')   │
└────────────────────────┬──────────────────────────────┘
                         ▼
┌─ Goal Reviewer Agent ─────────────────────────────────┐
│                                                        │
│  1. Read unreviewed goals from self.db                 │
│                                                        │
│  2. For each goal, LLM analyzes:                       │
│     ├── Which project(s) match? (by title similarity)  │
│     ├── Which task(s) relate?                          │
│     ├── Should progress be shared?                     │
│     │   ('independent' | 'project:X' | 'task:Y')      │
│     └── Suggest priority, category, target_date        │
│                                                        │
│  3. Present suggestions to user (confirm/reject):      │
│     ┌─────────────────────────────────────────────────┐│
│     │ Goal: "Clinical Sex Therapist Career"           ││
│     │ → Link to project: Clinical Sexology Spec ✓     ││
│     │ → Share progress: Yes (tied to project) ✓       ││
│     │ → Suggest priority: 1 ✓                         ││
│     │ → Create subtask: "Get certification" ✗         ││
│     └─────────────────────────────────────────────────┘│
│                                                        │
│  4. On confirmation, execute links:                    │
│     ├── Update goals.progress_source = 'project:X'     │
│     ├── Seed doc_links (goal ↔ project)                │
│     ├── Update sync_state                              │
│     ├── Call propagator to sync progress               │
│     └── Mark goal as reviewed                          │
│                                                        │
└────────────────────────┬──────────────────────────────┘
                         ▼
              ┌─ Propagator auto-syncs ────┐
              │  goal.progress = project   │
              │  progress (if shared)      │
              └────────────────────────────┘
```

### Key Design Decisions

| Question | Answer |
|----------|--------|
| **LLM model** | `SmolLM2-135M-Instruct` (fastest local) — intent classification only |
| **Auto-execute vs confirm** | Confirm first. Auto after 3+ correct suggestions in a row |
| **Progress sharing** | Controlled by `progress_source` column. `independent` = manual. `project:X` = auto from project |
| **Matching method** | Title → project name via LLM fuzzy match + keyword overlap |
| **Retry on wrong match** | User corrects → correction stored as lesson in agent_memory.db |

### Files to create (future)

| File | Purpose |
|------|---------|
| `engine/agents/goal_reviewer.py` | Goal Reviewer Agent |
| `engine/agents/goal_reviewer_integration_plan.md` | This plan as executable spec |

---

## What You Do Now

1. Run the SQL INSERTs for your goals
2. Tell me when done
3. I'll check the data, update DATABASE_ARCHITECTURE.md, and proceed to Phase 4

**Current goals table state:** 12 columns, 0 rows, UNIQUE on title, ready.
