"""Habits API — read-only endpoints for self.db habits tables."""
from flask import Blueprint, jsonify, request
from web.app import get_db, rows_to_dicts

habits_bp = Blueprint("habits", __name__)


@habits_bp.route("/")
def list_habits():
    """List all habits with optional status filter."""
    status = request.args.get("status")  # active | paused
    query = "SELECT * FROM habits"
    params = []
    if status:
        query += " WHERE status = ?"
        params.append(status)
    query += " ORDER BY habit_name"

    with get_db("self") as conn:
        rows = conn.execute(query, params).fetchall()
    return jsonify(rows_to_dicts(rows))


@habits_bp.route("/today")
def habits_today():
    """Today's habit completion status."""
    with get_db("self") as conn:
        rows = conn.execute("""
            SELECT h.*,
                   CASE WHEN hl.id IS NOT NULL THEN 'completed' ELSE 'pending' END AS today_status,
                   hl.completed_at AS today_completed_at
            FROM habits h
            LEFT JOIN habit_logs hl ON hl.habit_id = h.id
                AND date(hl.completed_at) = date('now', 'localtime')
            WHERE h.status = 'active'
            ORDER BY h.habit_name
        """).fetchall()
    return jsonify(rows_to_dicts(rows))


@habits_bp.route("/at-risk")
def habits_at_risk():
    """Habits with streak at risk (not completed yesterday)."""
    with get_db("self") as conn:
        rows = conn.execute("""
            SELECT habit_name, current_streak, last_completed, category
            FROM habits
            WHERE status = 'active'
              AND (last_completed IS NULL
                   OR last_completed < date('now', 'localtime', '-1 day'))
            ORDER BY current_streak ASC
        """).fetchall()
    return jsonify(rows_to_dicts(rows))


@habits_bp.route("/logs")
def habit_logs():
    """Habit completion logs with optional date range."""
    days = int(request.args.get("days", 30))
    with get_db("self") as conn:
        rows = conn.execute("""
            SELECT hl.*, h.habit_name, h.category
            FROM habit_logs hl
            JOIN habits h ON hl.habit_id = h.id
            WHERE hl.completed_at >= date('now', 'localtime', ?)
            ORDER BY hl.completed_at DESC
        """, (f"-{days} days",)).fetchall()
    return jsonify(rows_to_dicts(rows))


@habits_bp.route("/streaks")
def habit_streaks():
    """Active habit streaks."""
    with get_db("self") as conn:
        rows = conn.execute("""
            SELECT habit_name, current_streak, total_completions,
                   last_completed, target_streak, category
            FROM habits
            WHERE status = 'active'
            ORDER BY current_streak DESC
        """).fetchall()
    return jsonify(rows_to_dicts(rows))


@habits_bp.route("/<habit_id>/complete", methods=["POST"])
def complete_habit(habit_id):
    """Mark habit complete (proxied to daemon via sync_habits)."""
    import subprocess
    from pathlib import Path
    engine_dir = Path(__file__).resolve().parent.parent.parent / "engine"
    result = subprocess.run(
        ["python3", "-c", f"""
import sys; sys.path.insert(0, '{engine_dir}')
from sync.sync_habits import mark_habit_complete
result = mark_habit_complete('{habit_id}')
print(result)
"""],
        capture_output=True, text=True, timeout=10,
        cwd=str(engine_dir),
    )
    if result.returncode == 0:
        import json
        return jsonify(json.loads(result.stdout.strip()))
    return jsonify({"error": result.stderr}), 500
