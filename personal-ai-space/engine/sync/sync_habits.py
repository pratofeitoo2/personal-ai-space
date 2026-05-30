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
