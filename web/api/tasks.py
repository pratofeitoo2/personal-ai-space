"""Tasks API — read-only endpoints for tasks.db."""
from flask import Blueprint, jsonify, request
from web.app import get_db, rows_to_dicts

tasks_bp = Blueprint("tasks", __name__)


@tasks_bp.route("/")
def list_tasks():
    """List tasks with optional filters.

    Query params:
        status: pending | in_progress | completed | cancelled
        priority: critical | high | normal | low
        project: project name (partial match)
        due: today | overdue | upcoming | all (default: all non-completed)
        limit: max results (default: 50)
    """
    status = request.args.get("status")
    priority = request.args.get("priority")
    project = request.args.get("project")
    due = request.args.get("due", "active")
    limit = int(request.args.get("limit", 50))

    query = """
        SELECT t.*, p.name AS project_name
        FROM tasks t
        LEFT JOIN projects p ON t.project_id = p.id
        WHERE 1=1
    """
    params = []

    if status:
        query += " AND t.status = ?"
        params.append(status)
    elif due == "active":
        query += " AND t.status IN ('pending', 'in_progress')"

    if priority:
        query += " AND t.priority = ?"
        params.append(priority)

    if project:
        query += " AND p.name LIKE ?"
        params.append(f"%{project}%")

    if due == "today":
        query += " AND t.due_date = date('now', 'localtime')"
    elif due == "overdue":
        query += " AND t.due_date < date('now', 'localtime') AND t.status != 'completed'"
    elif due == "upcoming":
        query += " AND t.due_date >= date('now', 'localtime')"

    query += " ORDER BY CASE t.priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'normal' THEN 2 ELSE 3 END, t.due_date ASC NULLS LAST"
    query += f" LIMIT {limit}"

    with get_db("tasks") as conn:
        rows = conn.execute(query, params).fetchall()
    return jsonify(rows_to_dicts(rows))


@tasks_bp.route("/summary")
def task_summary():
    """Task completion summary by project."""
    with get_db("tasks") as conn:
        rows = conn.execute("""
            SELECT
                p.name AS project,
                COUNT(*) AS total,
                SUM(CASE WHEN t.status = 'completed' THEN 1 ELSE 0 END) AS completed,
                SUM(CASE WHEN t.status = 'pending' THEN 1 ELSE 0 END) AS pending,
                SUM(CASE WHEN t.status = 'in_progress' THEN 1 ELSE 0 END) AS in_progress
            FROM tasks t
            LEFT JOIN projects p ON t.project_id = p.id
            GROUP BY p.name
            ORDER BY p.name
        """).fetchall()
    return jsonify(rows_to_dicts(rows))


@tasks_bp.route("/overdue")
def overdue_tasks():
    """List overdue tasks."""
    with get_db("tasks") as conn:
        rows = conn.execute("""
            SELECT t.*, p.name AS project_name
            FROM tasks t
            LEFT JOIN projects p ON t.project_id = p.id
            WHERE t.due_date < date('now', 'localtime')
              AND t.status IN ('pending', 'in_progress')
            ORDER BY t.due_date ASC
        """).fetchall()
    return jsonify(rows_to_dicts(rows))


@tasks_bp.route("/today")
def today_tasks():
    """List tasks due today."""
    with get_db("tasks") as conn:
        rows = conn.execute("""
            SELECT t.*, p.name AS project_name
            FROM tasks t
            LEFT JOIN projects p ON t.project_id = p.id
            WHERE t.due_date = date('now', 'localtime')
              AND t.status IN ('pending', 'in_progress')
            ORDER BY CASE t.priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1 ELSE 2 END
        """).fetchall()
    return jsonify(rows_to_dicts(rows))


@tasks_bp.route("/<task_id>/complete", methods=["POST"])
def complete_task(task_id):
    """Mark a task as completed (proxied to daemon)."""
    import urllib.request
    from web.config import DAEMON_BASE
    payload = {"method": "send", "args": [], "kwargs": {
        "agent": "task-coordinator",
        "command": "update_status",
        "data": {"task_id": task_id, "new_status": "completed"}
    }}
    try:
        req = urllib.request.Request(
            f"{DAEMON_BASE}/execute",
            data=__import__("json").dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        resp = urllib.request.urlopen(req, timeout=5)
        return jsonify(resp.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 503
