"""Jobs API — read-only endpoints for jobs.db."""
from flask import Blueprint, jsonify, request
from web.app import get_db, rows_to_dicts

jobs_bp = Blueprint("jobs", __name__)


@jobs_bp.route("/")
def list_applications():
    """List job applications with optional status filter."""
    status = request.args.get("status")
    query = """
        SELECT a.*, c.name AS company_name, c.website AS company_website
        FROM applications a
        LEFT JOIN companies c ON a.company_id = c.id
    """
    params = []
    if status:
        query += " WHERE a.status = ?"
        params.append(status)
    query += " ORDER BY a.updated_at DESC"

    with get_db("jobs") as conn:
        rows = conn.execute(query, params).fetchall()
    return jsonify(rows_to_dicts(rows))


@jobs_bp.route("/pipeline")
def job_pipeline():
    """Job application pipeline summary (count by status)."""
    with get_db("jobs") as conn:
        rows = conn.execute("""
            SELECT status, COUNT(*) AS count
            FROM applications
            GROUP BY status
            ORDER BY CASE status
                WHEN 'saved' THEN 1
                WHEN 'applied' THEN 2
                WHEN 'interview' THEN 3
                WHEN 'offer' THEN 4
                WHEN 'rejected' THEN 5
                ELSE 6
            END
        """).fetchall()
    return jsonify(rows_to_dicts(rows))


@jobs_bp.route("/stale")
def stale_applications():
    """Applications saved >7 days ago with no action."""
    with get_db("jobs") as conn:
        rows = conn.execute("""
            SELECT a.*, c.name AS company_name
            FROM applications a
            LEFT JOIN companies c ON a.company_id = c.id
            WHERE a.status = 'saved'
              AND a.created_at < datetime('now', 'localtime', '-7 days')
            ORDER BY a.created_at ASC
        """).fetchall()
    return jsonify(rows_to_dicts(rows))


@jobs_bp.route("/stats")
def job_stats():
    """Job application statistics."""
    with get_db("jobs") as conn:
        total = conn.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
        by_status = conn.execute("""
            SELECT status, COUNT(*) AS count FROM applications GROUP BY status
        """).fetchall()
        recent = conn.execute("""
            SELECT COUNT(*) FROM applications
            WHERE created_at >= date('now', 'localtime', '-7 days')
        """).fetchone()[0]
    return jsonify({
        "total": total,
        "by_status": rows_to_dicts(by_status),
        "last_7_days": recent,
    })
