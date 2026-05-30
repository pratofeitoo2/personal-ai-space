# Habit Tracking System — Execution Plan

## Problem
Habit completions on Apple Reminders never flow back to self.db. No individual habit reminders exist. The "at-risk" detection has no data source.

## Design Decisions
- **Individual reminders per habit** (not grouped checklist)
- **Auto-mark in self.db immediately** on completion (no review queue)

## Architecture

```
Morning (07:00):
  self.db habits → reminders-bridge → Apple Reminders
  Each habit = 1 reminder: "🔲 Diário Pessoal"
  Notes: {"habit_id":"h-journal","type":"habit"}

User taps complete on phone:
  Apple Reminders → sync_reminders.py → detects habit type
  → parse habit_id from notes
  → mark_habit_complete(habit_id) → self.db (streak + log)
  → skip task creation

Result:
  self.db always reflects today's completions
  Automation queries return real-time data
  Behavioral sketch builds from habit_logs
```

## Tasks (TDD order)

### Task 1: Habit reminder creation
**File:** `engine/automations/delivery.py`
**Behavior:** `create_habit_reminders(habits)` creates one reminder per active habit
- Title: `🔲 {habit_name}`
- Notes: `{"habit_id":"{id}","type":"habit"}`
- Due: today 07:00
- Called from morning_brief delivery

### Task 2: Habit completion detection
**File:** `engine/sync/sync_reminders.py`
**Behavior:** In `sync_reminders_to_tasks()`, when a completed reminder has `{"type":"habit"}` in notes:
- Parse `habit_id` from notes JSON
- Call `mark_habit_complete(habit_id)`
- Seed sync_state to prevent re-processing
- Skip task creation

### Task 3: Integration
**File:** `engine/automations/runner.py`
**Behavior:** Morning brief includes habit reminder creation step

## Verification
1. Run failing tests (RED)
2. Implement (GREEN)
3. Run integration test suite
4. Run full pipeline against real data
