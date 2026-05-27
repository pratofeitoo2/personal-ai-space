---
title: Your Goal Title Here
type: life-management      # category in DB: life-management, career, health, finance, learning, project, social, spiritual
status: active             # lifecycle: active | in-progress | done | cancelled | on-hold | abandoned
tags:                      # JSON list → DB tags field
  - tag1
  - tag2
created: 2026-05-27        # → DB created_at (YYYY-MM-DD or ISO datetime)
updated: 2026-05-27        # → DB updated_at (YYYY-MM-DD or ISO datetime)
priority: 2                # INT 0-5 (DB: INTEGER DEFAULT 0)
progress: 30               # INT 0-100 (DB: REAL, CHECK 0-100)
target_date: 2026-12-31    # DATE (DB: TEXT)
completed:                 # DATE when done (DB: completed_at TEXT)
---

## DESCRIPTION 
Write the goal description, motivation, success criteria, etc.


**Why this matters:** [motivation]

**Success criteria:**
- [criterion 1]
- [criterion 2]

**Notes / context:**
[any additional details]
