"""Flask app factory with database helpers."""
import json
import sqlite3
from contextlib import contextmanager
from flask import Flask, jsonify, render_template
from flask_cors import CORS

from web.config import DB_PATHS, DAEMON_BASE, WEB_HOST, WEB_PORT


def create_app():
    """Create and configure the Flask application."""
    app = Flask(
        __name__,
        static_folder="static",
        template_folder="templates",
    )
    CORS(app)

    # Register blueprints
    from web.api.tasks import tasks_bp
    from web.api.habits import habits_bp
    from web.api.calendar import calendar_bp
    from web.api.jobs import jobs_bp
    from web.api.automations import automations_bp
    from web.api.engine import engine_bp
    from web.api.chat import chat_bp

    app.register_blueprint(tasks_bp, url_prefix="/api/tasks")
    app.register_blueprint(habits_bp, url_prefix="/api/habits")
    app.register_blueprint(calendar_bp, url_prefix="/api/calendar")
    app.register_blueprint(jobs_bp, url_prefix="/api/jobs")
    app.register_blueprint(automations_bp, url_prefix="/api/automations")
    app.register_blueprint(engine_bp, url_prefix="/api/engine")
    app.register_blueprint(chat_bp, url_prefix="/api/chat")

    # Health endpoint
    @app.route("/api/health")
    def health():
        """Check health of all databases and daemon."""
        status = {}
        for name, db_path in DB_PATHS.items():
            status[name] = {
                "exists": db_path.exists(),
                "size_kb": db_path.stat().st_size // 1024 if db_path.exists() else 0,
            }
        # Check daemon
        import urllib.request
        try:
            resp = urllib.request.urlopen(f"{DAEMON_BASE}/health", timeout=2)
            status["daemon"] = {"ok": True, "data": json.loads(resp.read().decode())}
        except Exception as e:
            status["daemon"] = {"ok": False, "error": str(e)}
        return jsonify(status)

    # Serve SPA
    @app.route("/")
    def index():
        return render_template("index.html")

    return app


@contextmanager
def get_db(db_name: str):
    """Context manager for read-only database connections.

    Usage:
        with get_db("tasks") as conn:
            rows = conn.execute("SELECT * FROM tasks").fetchall()
    """
    db_path = DB_PATHS.get(db_name)
    if db_path is None:
        raise ValueError(f"Unknown database: {db_name}")
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def dict_from_row(row):
    """Convert sqlite3.Row to dict."""
    return dict(row) if row else None


def rows_to_dicts(rows):
    """Convert list of sqlite3.Row to list of dicts."""
    return [dict(r) for r in rows]


if __name__ == "__main__":
    app = create_app()
    print(f"Starting web app on http://{WEB_HOST}:{WEB_PORT}")
    app.run(host=WEB_HOST, port=WEB_PORT, debug=True)
