"""Calendar API — read-only endpoints for calendar.db."""
from flask import Blueprint, jsonify, request
from web.app import get_db, rows_to_dicts

calendar_bp = Blueprint("calendar", __name__)


@calendar_bp.route("/today")
def today_events():
    """Today's calendar events."""
    with get_db("calendar") as conn:
        rows = conn.execute("""
            SELECT * FROM upcoming
            WHERE event_date = date('now', 'localtime')
            ORDER BY event_time ASC
        """).fetchall()
    return jsonify(rows_to_dicts(rows))


@calendar_bp.route("/upcoming")
def upcoming_events():
    """Events in the next N hours (default: 24)."""
    hours = int(request.args.get("hours", 24))
    with get_db("calendar") as conn:
        rows = conn.execute("""
            SELECT * FROM upcoming
            WHERE event_date || ' ' || event_time
                  >= datetime('now', 'localtime')
              AND event_date || ' ' || event_time
                  <= datetime('now', 'localtime', ?)
            ORDER BY event_date, event_time ASC
        """, (f"+{hours} hours",)).fetchall()
    return jsonify(rows_to_dicts(rows))


@calendar_bp.route("/week")
def week_events():
    """Events for the next 7 days."""
    with get_db("calendar") as conn:
        rows = conn.execute("""
            SELECT * FROM upcoming
            WHERE event_date BETWEEN date('now', 'localtime')
                                 AND date('now', 'localtime', '+7 days')
            ORDER BY event_date, event_time ASC
        """).fetchall()
    return jsonify(rows_to_dicts(rows))
