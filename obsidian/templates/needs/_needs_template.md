---
name: Your Need Name Here
id: need_auto             # omit to auto-generate from name
category: health          # professional, personal, health, growth, finance, connection, purpose, spiritual, environment
priority: medium          # critical | high | medium | low
status: active            # active | in_progress | monitoring | satisfied | archived
linked_tasks:             # comma-separated task IDs (DB: TEXT)
  - task_id_1
  - task_id_2
created: 2026-05-27       # DB: created_at (YYYY-MM-DD or ISO datetime)
---

## DESCRIPTION
  DESCRIPTION — The body text gets stored as the `description`
  column in self.db (truncated to 2000 chars).
  

**Why this matters:**
[explain the need]

**Evidence / signals:**
- [what indicates this need]

**Current gaps:**
- [what's missing today]
