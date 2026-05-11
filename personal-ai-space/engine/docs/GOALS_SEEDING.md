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

## What You Do Now

1. Run the SQL INSERTs for your goals when ready
2. Goals seeding + AI Goal Reviewer have been moved to STANDBY — see `engine/docs/STANDBY.md`

**Current goals table state:** 12 columns, 0 rows, UNIQUE on title, ready.
