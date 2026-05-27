---
habit_name: Your Habit Name         # TEXT  → DB habit_name
id: habit_auto                      # TEXT  → DB id (unique, use habit_001, habit_002, ...)
category: health                    # TEXT  (health, productivity, learning, wellness, etc.)
frequency: daily                    # TEXT  (daily, weekly, monthly, custom schedule)
start_date: 2026-05-01             # DATE  when tracking began
current_streak: 0                   # INT   consecutive completions
total_completions: 0                # INT   all-time completions
last_completed:                     # DATETIME  most recent completion (empty if none)
target_streak:                      # INT   optional stretch goal
status: active                      # TEXT  (active, paused, archived)
---

Notes about this habit go below the frontmatter as body text.