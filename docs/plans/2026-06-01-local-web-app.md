# Personal AI Powerhouse — Local Web App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers-optimized:subagent-driven-development (recommended) or superpowers-optimized:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local web application accessible from any device on the local network, providing a unified interface for viewing data, triggering actions, and managing the Personal AI Powerhouse system.

**Architecture:** Extend the existing Flask dashboard server (`dashboard_server.py`) into a full-featured web app. The server reads from all 4 SQLite databases (read-only), proxies write operations to the engine daemon (port 19876), and serves a responsive SPA dashboard. The engine daemon handles all business logic, automations, and LLM queries.

**Tech Stack:** Python 3.x, Flask, Flask-SocketIO (WebSocket), SQLite, Tailwind CSS, Chart.js, HTMX, vanilla JavaScript

**Assumptions:**
- Engine daemon runs on port 19876 (start with `python cli.py daemon start`)
- SQLite databases are at `engine/db/{tasks,self,calendar,jobs}/` — assumes read-only access works
- Ollama runs on port 11434 for LLM queries — assumes Ollama is installed and running
- `reminders-bridge` CLI is at `~/.claude/reminders-bridge` — assumes it works
- Local network only — no external exposure, no HTTPS needed
- macOS host — `osascript` available for notifications

---

## File Structure

```
personal-ai-space/
├── web/                              # NEW — Web app package
│   ├── __init__.py
│   ├── app.py                        # Flask app factory + CORS
│   ├── config.py                     # Configuration (ports, DB paths, daemon URL)
│   ├── api/                          # API blueprint
│   │   ├── __init__.py
│   │   ├── tasks.py                  # /api/tasks/* endpoints
│   │   ├── habits.py                 # /api/habits/* endpoints
│   │   ├── calendar.py               # /api/calendar/* endpoints
│   │   ├── jobs.py                   # /api/jobs/* endpoints
│   │   ├── automations.py            # /api/automations/* endpoints
│   │   ├── engine.py                 # /api/engine/* proxy to daemon
│   │   └── chat.py                   # /api/chat/* NL query endpoint
│   ├── static/                       # Static assets
│   │   ├── css/
│   │   │   └── dashboard.css         # Custom styles (Tailwind extensions)
│   │   ├── js/
│   │   │   ├── app.js                # Main app logic
│   │   │   ├── dashboard.js          # Dashboard panel rendering
│   │   │   ├── chat.js               # Chat interface
│   │   │   └── automations.js        # Automation control panel
│   │   └── img/                      # Icons, logos
│   └── templates/
│       └── index.html                # SPA shell (Tailwind + HTMX + Socket.IO)
├── run_web.sh                        # Start script (daemon + web server)
└── engine/
    ├── db/                           # Existing databases (read-only)
    └── cli.py                        # Existing CLI (daemon commands)
```

---

## Task 1: Configuration Module

**Files:**
- Create: `personal-ai-space/web/__init__.py`
- Create: `personal-ai-space/web/config.py`

**Does NOT cover:** Database migrations, schema changes, or write operations.

- [ ] **Step 1: Create package init**

```python
# personal-ai-space/web/__init__.py
"""Personal AI Powerhouse — Local Web App."""
```

- [ ] **Step 2: Create config module**

```python
# personal-ai-space/web/config.py
"""Central configuration for the web app."""
import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent  # personal-ai-space/
ENGINE_DIR = BASE_DIR / "engine"
DB_DIR = ENGINE_DIR / "db"

# Database paths (read-only)
DB_PATHS = {
    "tasks": DB_DIR / "tasks" / "tasks.db",
    "self": DB_DIR / "self" / "self.db",
    "calendar": DB_DIR / "calendar" / "calendar.db",
    "jobs": DB_DIR / "jobs" / "jobs.db",
}

# Daemon HTTP API
DAEMON_BASE = os.environ.get("PAI_DAEMON_URL", "http://127.0.0.1:19876")

# Ollama LLM
OLLAMA_BASE = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")

# Web server
WEB_HOST = os.environ.get("PAI_WEB_HOST", "0.0.0.0")
WEB_PORT = int(os.environ.get("PAI_WEB_PORT", "5001"))

# Security: local network only (no auth for now, but rate limiting)
MAX_REQUESTS_PER_MINUTE = 60
```

- [ ] **Step 3: Verify config loads**

Run: `cd personal-ai-space && python -c "from web.config import DB_PATHS; print(DB_PATHS)"`
Expected: Dict with 4 Path objects, all pointing to existing .db files

---

## Task 2: Flask App Factory + Database Helpers

**Files:**
- Create: `personal-ai-space/web/app.py`
- Modify: `personal-ai-space/dashboard_server.py` (mark as deprecated)

**Does NOT cover:** API endpoints (Task 3+), frontend (Task 6+).

- [ ] **Step 1: Create app factory**

```python
# personal-ai-space/web/app.py
"""Flask app factory with database helpers."""
import sqlite3
from contextlib import contextmanager
from flask import Flask, jsonify
from flask_cors import CORS

from web.config import DB_PATHS, WEB_HOST, WEB_PORT


def create_app():
    """Create and configure the Flask application."""
    app = Flask(
        __name__,
        static_folder="static",
        template_folder="templates",
    )
    CORS(app)

    # Register blueprints (added in Task 3+)
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
            status["daemon"] = {"ok": True, "data": resp.json()}
        except Exception as e:
            status["daemon"] = {"ok": False, "error": str(e)}
        return jsonify(status)

    # Serve SPA
    @app.route("/")
    def index():
        return app.send_static_file("../templates/index.html")

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
```

- [ ] **Step 2: Verify app creates and routes register**

Run: `cd personal-ai-space && python -c "from web.app import create_app; app = create_app(); print([r.rule for r in app.url_map.iter_rules() if r.rule.startswith('/api')])"`
Expected: List of registered API routes (empty blueprints for now, but no import errors)

---

## Task 3: Tasks API Blueprint

**Files:**
- Create: `personal-ai-space/web/api/__init__.py`
- Create: `personal-ai-space/web/api/tasks.py`

**Does NOT cover:** Task creation/editing (write operations go through daemon). Only read endpoints here.

- [ ] **Step 1: Create API package init**

```python
# personal-ai-space/web/api/__init__.py
"""API blueprints for the Personal AI Powerhouse web app."""
```

- [ ] **Step 2: Create tasks blueprint**

```python
# personal-ai-space/web/api/tasks.py
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
```

- [ ] **Step 3: Verify tasks endpoints**

Run: `cd personal-ai-space && python -c "from web.api.tasks import tasks_bp; print('tasks_bp loaded:', tasks_bp.name)"`
Expected: `tasks_bp loaded: tasks`

---

## Task 4: Habits, Calendar, Jobs API Blueprints

**Files:**
- Create: `personal-ai-space/web/api/habits.py`
- Create: `personal-ai-space/web/api/calendar.py`
- Create: `personal-ai-space/web/api/jobs.py`

**Does NOT cover:** Habit completion (write) — that goes through daemon. Calendar event creation. Job application creation.

- [ ] **Step 1: Create habits blueprint**

```python
# personal-ai-space/web/api/habits.py
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
```

- [ ] **Step 2: Create calendar blueprint**

```python
# personal-ai-space/web/api/calendar.py
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
```

- [ ] **Step 3: Create jobs blueprint**

```python
# personal-ai-space/web/api/jobs.py
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
```

- [ ] **Step 4: Verify all blueprints load**

Run: `cd personal-ai-space && python -c "from web.app import create_app; app = create_app(); rules = [r.rule for r in app.url_map.iter_rules()]; print(f'{len(rules)} routes registered'); [print(r) for r in sorted(rules) if r.startswith('/api')]"`
Expected: 30+ API routes registered, no import errors

---

## Task 5: Engine Proxy + Automation + Chat API

**Files:**
- Create: `personal-ai-space/web/api/engine.py`
- Create: `personal-ai-space/web/api/automations.py`
- Create: `personal-ai-space/web/api/chat.py`

**Does NOT cover:** LLM prompt engineering (Ollama handles that). Automation rule editing.

- [ ] **Step 1: Create engine proxy blueprint**

```python
# personal-ai-space/web/api/engine.py
"""Engine API — proxy endpoints to the running daemon."""
import json
import urllib.request
from flask import Blueprint, jsonify, request
from web.config import DAEMON_BASE

engine_bp = Blueprint("engine", __name__)


def _proxy_to_daemon(method, args=None, kwargs=None):
    """Proxy a call to the engine daemon."""
    payload = json.dumps({
        "method": method,
        "args": args or [],
        "kwargs": kwargs or {},
    }).encode()
    req = urllib.request.Request(
        f"{DAEMON_BASE}/engine",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    resp = urllib.request.urlopen(req, timeout=15)
    return resp.json()


@engine_bp.route("/health")
def daemon_health():
    """Get daemon health status."""
    try:
        resp = urllib.request.urlopen(f"{DAEMON_BASE}/health", timeout=3)
        return jsonify(resp.json())
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 503


@engine_bp.route("/digest")
def daily_digest():
    """Get today's daily digest."""
    try:
        result = _proxy_to_daemon("daily_digest")
        return jsonify({"digest": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 503


@engine_bp.route("/reminders")
def reminders():
    """Get reminders snapshot."""
    try:
        result = _proxy_to_daemon("reminders_snapshot")
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 503


@engine_bp.route("/context")
def context():
    """Get engine context (profile, memory, etc.)."""
    try:
        result = _proxy_to_daemon("get_context")
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 503


@engine_bp.route("/execute", methods=["POST"])
def execute_agent_command():
    """Execute an agent command via the daemon.

    POST body: {"agent": "task-coordinator", "command": "get_today", "data": {}}
    """
    data = request.get_json()
    if not data or "agent" not in data or "command" not in data:
        return jsonify({"error": "Missing agent or command"}), 400

    try:
        resp = urllib.request.Request(
            f"{DAEMON_BASE}/execute",
            data=json.dumps(data).encode(),
            headers={"Content-Type": "application/json"},
        )
        result = urllib.request.urlopen(resp, timeout=15)
        return jsonify(result.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 503
```

- [ ] **Step 2: Create automations blueprint**

```python
# personal-ai-space/web/api/automations.py
"""Automations API — status and control for automation rules."""
import json
import urllib.request
from pathlib import Path
from flask import Blueprint, jsonify, request
from web.config import DAEMON_BASE, ENGINE_DIR

automations_bp = Blueprint("automations", __name__)

STATE_FILE = Path.home() / ".local" / "share" / "personal-ai-space" / "automation_state.json"


@automations_bp.route("/status")
def automation_status():
    """Get automation runner status."""
    try:
        result = json.loads(urllib.request.urlopen(
            f"{DAEMON_BASE}/engine", timeout=5,
            data=json.dumps({"method": "scheduler_status", "args": [], "kwargs": {}}).encode(),
            headers={"Content-Type": "application/json"},
        ).read())
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 503


@automations_bp.route("/rules")
def list_rules():
    """List automation rules from YAML config."""
    import yaml
    config_path = ENGINE_DIR / "config" / "automations.yaml"
    if not config_path.exists():
        return jsonify({"error": "automations.yaml not found"}), 404
    with open(config_path) as f:
        config = yaml.safe_load(f)
    return jsonify(config)


@automations_bp.route("/state")
def automation_state():
    """Get last automation run state."""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return jsonify(json.load(f))
    return jsonify({"last_runs": {}})


@automations_bp.route("/trigger", methods=["POST"])
def trigger_automation():
    """Manually trigger an automation rule."""
    data = request.get_json()
    rule_id = data.get("rule_id")
    if not rule_id:
        return jsonify({"error": "Missing rule_id"}), 400

    try:
        resp = urllib.request.Request(
            f"{DAEMON_BASE}/execute",
            data=json.dumps({
                "agent": "automation-runner",
                "command": "run_rule",
                "data": {"rule_id": rule_id}
            }).encode(),
            headers={"Content-Type": "application/json"},
        )
        result = urllib.request.urlopen(resp, timeout=30)
        return jsonify(result.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 503
```

- [ ] **Step 3: Create chat blueprint (NL queries via Ollama)**

```python
# personal-ai-space/web/api/chat.py
"""Chat API — natural language queries via Ollama LLM."""
import json
import urllib.request
from flask import Blueprint, jsonify, request
from web.config import OLLAMA_BASE, DAEMON_BASE

chat_bp = Blueprint("chat", __name__)

# Intent catalogue — maps user phrases to engine commands
INTENTS = [
    {"phrase": "tasks", "keywords": ["task", "todo", "to-do", "plate", "do today"], "agent": "task-coordinator", "command": "get_today"},
    {"phrase": "habits", "keywords": ["habit", "streak", "routine"], "agent": "insight-generator", "command": "analyse_habits"},
    {"phrase": "calendar", "keywords": ["calendar", "event", "meeting", "schedule"], "agent": "reminder-system", "command": "get_events"},
    {"phrase": "jobs", "keywords": ["job", "application", "apply", "career"], "agent": "task-coordinator", "command": "get_all_open"},
    {"phrase": "goals", "keywords": ["goal", "objective", "target"], "agent": "insight-generator", "command": "get_goals"},
    {"phrase": "digest", "keywords": ["digest", "summary", "overview", "what's on"], "agent": None, "command": "daily_digest"},
]


def classify_intent(text):
    """Simple keyword-based intent classification."""
    text_lower = text.lower()
    for intent in INTENTS:
        for kw in intent["keywords"]:
            if kw in text_lower:
                return intent
    return None


def query_ollama(prompt, model="llama3.2:3b"):
    """Query Ollama for text generation."""
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"num_ctx": 8192}
    }).encode()
    req = urllib.request.Request(
        f"{OLLAMA_BASE}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    resp = urllib.request.urlopen(req, timeout=120)
    return json.loads(resp.read())["response"]


@chat_bp.route("/", methods=["POST"])
def chat():
    """Process a natural language query.

    POST body: {"message": "what's on my plate today?"}
    """
    data = request.get_json()
    message = data.get("message", "").strip()
    if not message:
        return jsonify({"error": "Empty message"}), 400

    # Step 1: Try keyword classification
    intent = classify_intent(message)

    if intent:
        # Step 2: Execute the engine command
        try:
            if intent["command"] == "daily_digest":
                resp = urllib.request.Request(
                    f"{DAEMON_BASE}/engine",
                    data=json.dumps({"method": "daily_digest", "args": [], "kwargs": {}}).encode(),
                    headers={"Content-Type": "application/json"},
                )
                result = urllib.request.urlopen(resp, timeout=15)
                raw = result.json()
            else:
                resp = urllib.request.Request(
                    f"{DAEMON_BASE}/execute",
                    data=json.dumps({
                        "agent": intent["agent"],
                        "command": intent["command"],
                        "data": {},
                    }).encode(),
                    headers={"Content-Type": "application/json"},
                )
                result = urllib.request.urlopen(resp, timeout=15)
                raw = result.json()

            # Step 3: Format response
            return jsonify({
                "intent": intent["phrase"],
                "data": raw,
                "message": f"Here's what I found about {intent['phrase']}:"
            })
        except Exception as e:
            return jsonify({"error": f"Engine error: {str(e)}"}), 503

    # Step 4: Fallback to Ollama for free-form questions
    try:
        # Gather context
        context_parts = []
        try:
            resp = urllib.request.urlopen(f"{DAEMON_BASE}/engine", timeout=5,
                data=json.dumps({"method": "daily_digest", "args": [], "kwargs": {}}).encode(),
                headers={"Content-Type": "application/json"})
            context_parts.append("Daily digest: " + resp.read().decode()[:500])
        except Exception:
            pass

        context_str = "\n".join(context_parts) if context_parts else "No context available."
        full_prompt = f"""You are a personal AI assistant. Answer the user's question based on the context below.
Be concise and helpful. If you don't have enough information, say so.

Context:
{context_str}

User: {message}
:"""

        response = query_ollama(full_prompt)
        return jsonify({
            "intent": "llm",
            "message": response,
        })
    except Exception as e:
        return jsonify({
            "intent": "error",
            "message": f"I couldn't process that request. Error: {str(e)}",
        }), 503
```

- [ ] **Step 4: Verify all API blueprints load together**

Run: `cd personal-ai-space && python -c "from web.app import create_app; app = create_app(); rules = sorted([r.rule for r in app.url_map.iter_rules() if r.rule.startswith('/api')]); print(f'{len(rules)} API routes:'); [print(f'  {r}') for r in rules]"`
Expected: 40+ API routes, no import errors

---

## Task 6: SPA Shell + Dashboard Frontend

**Files:**
- Create: `personal-ai-space/web/templates/index.html`
- Create: `personal-ai-space/web/static/js/app.js`
- Create: `personal-ai-space/web/static/js/dashboard.js`
- Create: `personal-ai-space/web/static/css/dashboard.css`

**Does NOT cover:** Chat interface (Task 7), automation control (Task 8).

- [ ] **Step 1: Create SPA shell template**

```html
<!-- personal-ai-space/web/templates/index.html -->
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Personal AI Powerhouse</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/htmx.org@1.9.10"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link rel="stylesheet" href="/static/css/dashboard.css">
    <link rel="manifest" href="/static/manifest.json">
    <meta name="theme-color" content="#1e293b">
</head>
<body class="bg-gray-50 dark:bg-slate-900 min-h-screen transition-colors">
    <!-- Navigation -->
    <nav class="bg-white dark:bg-slate-800 shadow-sm border-b border-gray-200 dark:border-slate-700">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex justify-between h-16">
                <div class="flex items-center space-x-8">
                    <h1 class="text-xl font-bold text-gray-900 dark:text-white">🧠 PAI Powerhouse</h1>
                    <div class="hidden md:flex space-x-4">
                        <button onclick="showPanel('dashboard')" class="nav-btn active" data-panel="dashboard">Dashboard</button>
                        <button onclick="showPanel('tasks')" class="nav-btn" data-panel="tasks">Tasks</button>
                        <button onclick="showPanel('habits')" class="nav-btn" data-panel="habits">Habits</button>
                        <button onclick="showPanel('calendar')" class="nav-btn" data-panel="calendar">Calendar</button>
                        <button onclick="showPanel('jobs')" class="nav-btn" data-panel="jobs">Jobs</button>
                        <button onclick="showPanel('chat')" class="nav-btn" data-panel="chat">Chat</button>
                        <button onclick="showPanel('automations')" class="nav-btn" data-panel="automations">Automations</button>
                    </div>
                </div>
                <div class="flex items-center space-x-4">
                    <span id="daemon-status" class="text-xs text-gray-400">Checking...</span>
                    <button onclick="toggleTheme()" class="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-700">
                        <span id="theme-icon">🌙</span>
                    </button>
                </div>
            </div>
        </div>
    </nav>

    <!-- Main Content -->
    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <!-- Dashboard Panel -->
        <div id="panel-dashboard" class="panel">
            <div id="dashboard-content">Loading...</div>
        </div>

        <!-- Tasks Panel -->
        <div id="panel-tasks" class="panel hidden">
            <div id="tasks-content">Loading...</div>
        </div>

        <!-- Habits Panel -->
        <div id="panel-habits" class="panel hidden">
            <div id="habits-content">Loading...</div>
        </div>

        <!-- Calendar Panel -->
        <div id="panel-calendar" class="panel hidden">
            <div id="calendar-content">Loading...</div>
        </div>

        <!-- Jobs Panel -->
        <div id="panel-jobs" class="panel hidden">
            <div id="jobs-content">Loading...</div>
        </div>

        <!-- Chat Panel -->
        <div id="panel-chat" class="panel hidden">
            <div id="chat-content">Loading...</div>
        </div>

        <!-- Automations Panel -->
        <div id="panel-automations" class="panel hidden">
            <div id="automations-content">Loading...</div>
        </div>
    </main>

    <script src="/static/js/app.js"></script>
    <script src="/static/js/dashboard.js"></script>
</body>
</html>
```

- [ ] **Step 2: Create main app.js**

```javascript
// personal-ai-space/web/static/js/app.js
// Main application logic — panel switching, theme, daemon status

let currentPanel = 'dashboard';

function showPanel(name) {
    document.querySelectorAll('.panel').forEach(p => p.classList.add('hidden'));
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));

    const panel = document.getElementById(`panel-${name}`);
    if (panel) {
        panel.classList.remove('hidden');
        currentPanel = name;
    }

    const btn = document.querySelector(`[data-panel="${name}"]`);
    if (btn) btn.classList.add('active');

    // Load panel data
    loadPanelData(name);
}

async function loadPanelData(name) {
    switch (name) {
        case 'dashboard': await loadDashboard(); break;
        case 'tasks': await loadTasks(); break;
        case 'habits': await loadHabits(); break;
        case 'calendar': await loadCalendar(); break;
        case 'jobs': await loadJobs(); break;
        case 'chat': initChat(); break;
        case 'automations': await loadAutomations(); break;
    }
}

async function checkDaemonStatus() {
    const el = document.getElementById('daemon-status');
    try {
        const resp = await fetch('/api/engine/health');
        const data = await resp.json();
        if (data.ok) {
            el.textContent = '🟢 Daemon';
            el.className = 'text-xs text-green-500';
        } else {
            el.textContent = '🔴 Offline';
            el.className = 'text-xs text-red-500';
        }
    } catch {
        el.textContent = '🔴 Offline';
        el.className = 'text-xs text-red-500';
    }
}

function toggleTheme() {
    const html = document.documentElement;
    const isDark = html.classList.toggle('dark');
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
    document.getElementById('theme-icon').textContent = isDark ? '☀️' : '🌙';
}

// Init
document.addEventListener('DOMContentLoaded', () => {
    const saved = localStorage.getItem('theme');
    if (saved === 'dark') {
        document.documentElement.classList.add('dark');
        document.getElementById('theme-icon').textContent = '☀️';
    }
    checkDaemonStatus();
    setInterval(checkDaemonStatus, 30000);
    loadPanelData('dashboard');
});
```

- [ ] **Step 3: Create dashboard.js with all panel loaders**

```javascript
// personal-ai-space/web/static/js/dashboard.js
// Dashboard and panel data loaders

async function fetchJSON(url) {
    const resp = await fetch(url);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    return resp.json();
}

// ── Dashboard ──────────────────────────────────────────────
async function loadDashboard() {
    const el = document.getElementById('dashboard-content');
    try {
        const [tasks, habits, calendar, jobs] = await Promise.all([
            fetchJSON('/api/tasks/summary'),
            fetchJSON('/api/habits/streaks'),
            fetchJSON('/api/calendar/today'),
            fetchJSON('/api/jobs/pipeline'),
        ]);

        const totalTasks = tasks.reduce((s, p) => s + p.total, 0);
        const completedTasks = tasks.reduce((s, p) => s + p.completed, 0);
        const activeHabits = habits.length;
        const avgStreak = habits.length ? (habits.reduce((s, h) => s + h.current_streak, 0) / habits.length).toFixed(1) : 0;
        const todayEvents = calendar.length;
        const totalApps = jobs.reduce((s, j) => s + j.count, 0);

        el.innerHTML = `
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
                <div class="card p-6">
                    <h3 class="text-sm font-medium text-gray-500 dark:text-gray-400">Tasks</h3>
                    <p class="text-3xl font-bold text-gray-900 dark:text-white">${completedTasks}/${totalTasks}</p>
                    <p class="text-xs text-gray-400">completed</p>
                </div>
                <div class="card p-6">
                    <h3 class="text-sm font-medium text-gray-500 dark:text-gray-400">Habits</h3>
                    <p class="text-3xl font-bold text-gray-900 dark:text-white">${activeHabits}</p>
                    <p class="text-xs text-gray-400">avg streak: ${avgStreak} days</p>
                </div>
                <div class="card p-6">
                    <h3 class="text-sm font-medium text-gray-500 dark:text-gray-400">Calendar</h3>
                    <p class="text-3xl font-bold text-gray-900 dark:text-white">${todayEvents}</p>
                    <p class="text-xs text-gray-400">events today</p>
                </div>
                <div class="card p-6">
                    <h3 class="text-sm font-medium text-gray-500 dark:text-gray-400">Job Applications</h3>
                    <p class="text-3xl font-bold text-gray-900 dark:text-white">${totalApps}</p>
                    <p class="text-xs text-gray-400">total applications</p>
                </div>
            </div>
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div class="card p-6">
                    <h3 class="text-lg font-medium text-gray-900 dark:text-white mb-4">Habit Streaks</h3>
                    <canvas id="streaksChart" height="200"></canvas>
                </div>
                <div class="card p-6">
                    <h3 class="text-lg font-medium text-gray-900 dark:text-white mb-4">Job Pipeline</h3>
                    <canvas id="pipelineChart" height="200"></canvas>
                </div>
            </div>
        `;

        // Render charts
        if (habits.length) {
            new Chart(document.getElementById('streaksChart'), {
                type: 'bar',
                data: {
                    labels: habits.map(h => h.habit_name),
                    datasets: [{ label: 'Streak (days)', data: habits.map(h => h.current_streak), backgroundColor: '#3b82f6' }]
                },
                options: { responsive: true, plugins: { legend: { display: false } } }
            });
        }
        if (jobs.length) {
            new Chart(document.getElementById('pipelineChart'), {
                type: 'doughnut',
                data: {
                    labels: jobs.map(j => j.status),
                    datasets: [{ data: jobs.map(j => j.count), backgroundColor: ['#94a3b8', '#3b82f6', '#f59e0b', '#10b981', '#ef4444'] }]
                },
                options: { responsive: true }
            });
        }
    } catch (e) {
        el.innerHTML = `<div class="text-red-500">Error loading dashboard: ${e.message}</div>`;
    }
}

// ── Tasks ──────────────────────────────────────────────────
async function loadTasks() {
    const el = document.getElementById('tasks-content');
    try {
        const tasks = await fetchJSON('/api/tasks/?due=active&limit=50');
        el.innerHTML = `
            <h2 class="text-2xl font-bold text-gray-900 dark:text-white mb-6">Tasks</h2>
            <div class="space-y-3">
                ${tasks.map(t => `
                    <div class="card p-4 flex items-center justify-between">
                        <div class="flex items-center space-x-3">
                            <span class="priority-badge priority-${t.priority}">${t.priority}</span>
                            <span class="text-gray-900 dark:text-white">${t.title}</span>
                            <span class="text-xs text-gray-400">${t.project_name || ''}</span>
                        </div>
                        <div class="flex items-center space-x-3">
                            <span class="text-xs text-gray-500">${t.due_date || 'No due date'}</span>
                            <button onclick="completeTask('${t.id}')" class="text-green-500 hover:text-green-700">✓</button>
                        </div>
                    </div>
                `).join('')}
                ${tasks.length === 0 ? '<p class="text-gray-500 dark:text-gray-400">No pending tasks</p>' : ''}
            </div>
        `;
    } catch (e) {
        el.innerHTML = `<div class="text-red-500">Error: ${e.message}</div>`;
    }
}

async function completeTask(taskId) {
    await fetch(`/api/tasks/${taskId}/complete`, { method: 'POST' });
    loadTasks();
}

// ── Habits ─────────────────────────────────────────────────
async function loadHabits() {
    const el = document.getElementById('habits-content');
    try {
        const [habits, atRisk] = await Promise.all([
            fetchJSON('/api/habits/today'),
            fetchJSON('/api/habits/at-risk'),
        ]);
        el.innerHTML = `
            <h2 class="text-2xl font-bold text-gray-900 dark:text-white mb-6">Habits</h2>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div class="card p-6">
                    <h3 class="text-lg font-medium mb-4">Today</h3>
                    <div class="space-y-3">
                        ${habits.map(h => `
                            <div class="flex items-center justify-between p-3 rounded-lg ${h.today_status === 'completed' ? 'bg-green-50 dark:bg-green-900/20' : 'bg-gray-50 dark:bg-slate-700'}">
                                <div>
                                    <span class="font-medium text-gray-900 dark:text-white">${h.habit_name}</span>
                                    <span class="text-xs text-gray-400 ml-2">streak: ${h.current_streak}</span>
                                </div>
                                ${h.today_status === 'completed'
                                    ? '<span class="text-green-500">✅</span>'
                                    : `<button onclick="completeHabit('${h.id}')" class="text-gray-400 hover:text-green-500">⬜</button>`
                                }
                            </div>
                        `).join('')}
                    </div>
                </div>
                <div class="card p-6">
                    <h3 class="text-lg font-medium mb-4">⚠️ At Risk</h3>
                    <div class="space-y-3">
                        ${atRisk.map(h => `
                            <div class="p-3 rounded-lg bg-yellow-50 dark:bg-yellow-900/20">
                                <span class="font-medium text-yellow-800 dark:text-yellow-200">${h.habit_name}</span>
                                <span class="text-xs text-yellow-600 ml-2">streak: ${h.current_streak}</span>
                                <span class="text-xs text-yellow-500 ml-2">last: ${h.last_completed || 'never'}</span>
                            </div>
                        `).join('')}
                        ${atRisk.length === 0 ? '<p class="text-green-500">All habits on track! 🎉</p>' : ''}
                    </div>
                </div>
            </div>
        `;
    } catch (e) {
        el.innerHTML = `<div class="text-red-500">Error: ${e.message}</div>`;
    }
}

async function completeHabit(habitId) {
    await fetch(`/api/habits/${habitId}/complete`, { method: 'POST' });
    loadHabits();
}

// ── Calendar ───────────────────────────────────────────────
async function loadCalendar() {
    const el = document.getElementById('calendar-content');
    try {
        const [today, week] = await Promise.all([
            fetchJSON('/api/calendar/today'),
            fetchJSON('/api/calendar/week'),
        ]);
        el.innerHTML = `
            <h2 class="text-2xl font-bold text-gray-900 dark:text-white mb-6">Calendar</h2>
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div class="card p-6">
                    <h3 class="text-lg font-medium mb-4">Today</h3>
                    <div class="space-y-3">
                        ${today.map(e => `
                            <div class="p-3 rounded-lg bg-blue-50 dark:bg-blue-900/20">
                                <span class="font-medium text-blue-800 dark:text-blue-200">${e.event_name}</span>
                                <span class="text-xs text-blue-600 ml-2">${e.event_time} (${e.duration_hours}h)</span>
                            </div>
                        `).join('')}
                        ${today.length === 0 ? '<p class="text-gray-500">No events today</p>' : ''}
                    </div>
                </div>
                <div class="card p-6">
                    <h3 class="text-lg font-medium mb-4">This Week</h3>
                    <div class="space-y-3">
                        ${week.map(e => `
                            <div class="p-3 rounded-lg bg-gray-50 dark:bg-slate-700">
                                <span class="font-medium text-gray-900 dark:text-white">${e.event_name}</span>
                                <span class="text-xs text-gray-500 ml-2">${e.event_date} ${e.event_time}</span>
                            </div>
                        `).join('')}
                        ${week.length === 0 ? '<p class="text-gray-500">No upcoming events</p>' : ''}
                    </div>
                </div>
            </div>
        `;
    } catch (e) {
        el.innerHTML = `<div class="text-red-500">Error: ${e.message}</div>`;
    }
}

// ── Jobs ───────────────────────────────────────────────────
async function loadJobs() {
    const el = document.getElementById('jobs-content');
    try {
        const [apps, pipeline] = await Promise.all([
            fetchJSON('/api/jobs/?limit=20'),
            fetchJSON('/api/jobs/pipeline'),
        ]);
        el.innerHTML = `
            <h2 class="text-2xl font-bold text-gray-900 dark:text-white mb-6">Job Applications</h2>
            <div class="card p-6 mb-6">
                <h3 class="text-lg font-medium mb-4">Pipeline</h3>
                <div class="flex flex-wrap gap-4">
                    ${pipeline.map(p => `
                        <div class="text-center">
                            <div class="text-2xl font-bold text-gray-900 dark:text-white">${p.count}</div>
                            <div class="text-xs text-gray-500">${p.status}</div>
                        </div>
                    `).join('')}
                </div>
            </div>
            <div class="card p-6">
                <h3 class="text-lg font-medium mb-4">Recent Applications</h3>
                <div class="space-y-3">
                    ${apps.map(a => `
                        <div class="p-3 rounded-lg bg-gray-50 dark:bg-slate-700">
                            <div class="font-medium text-gray-900 dark:text-white">${a.job_title}</div>
                            <div class="text-sm text-gray-500">${a.company_name || 'Unknown'} · ${a.status} · ${a.location || 'N/A'}</div>
                        </div>
                    `).join('')}
                    ${apps.length === 0 ? '<p class="text-gray-500">No applications yet</p>' : ''}
                </div>
            </div>
        `;
    } catch (e) {
        el.innerHTML = `<div class="text-red-500">Error: ${e.message}</div>`;
    }
}

// ── Automations ────────────────────────────────────────────
async function loadAutomations() {
    const el = document.getElementById('automations-content');
    try {
        const [status, state] = await Promise.all([
            fetchJSON('/api/automations/status'),
            fetchJSON('/api/automations/state'),
        ]);
        el.innerHTML = `
            <h2 class="text-2xl font-bold text-gray-900 dark:text-white mb-6">Automations</h2>
            <div class="card p-6">
                <h3 class="text-lg font-medium mb-4">Last Runs</h3>
                <div class="space-y-3">
                    ${Object.entries(state.last_runs || {}).map(([rule, time]) => `
                        <div class="flex justify-between p-3 rounded-lg bg-gray-50 dark:bg-slate-700">
                            <span class="font-medium text-gray-900 dark:text-white">${rule}</span>
                            <span class="text-xs text-gray-500">${time}</span>
                        </div>
                    `).join('')}
                    ${Object.keys(state.last_runs || {}).length === 0 ? '<p class="text-gray-500">No runs recorded</p>' : ''}
                </div>
            </div>
        `;
    } catch (e) {
        el.innerHTML = `<div class="text-red-500">Error: ${e.message}</div>`;
    }
}

// ── Chat ───────────────────────────────────────────────────
let chatInitialized = false;
function initChat() {
    if (chatInitialized) return;
    chatInitialized = true;
    const el = document.getElementById('chat-content');
    el.innerHTML = `
        <h2 class="text-2xl font-bold text-gray-900 dark:text-white mb-6">Chat</h2>
        <div class="card p-6">
            <div id="chat-messages" class="space-y-4 mb-4 h-96 overflow-y-auto"></div>
            <div class="flex space-x-2">
                <input id="chat-input" type="text" placeholder="Ask me anything..."
                    class="flex-1 p-3 rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-gray-900 dark:text-white"
                    onkeypress="if(event.key==='Enter')sendChat()">
                <button onclick="sendChat()" class="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700">Send</button>
            </div>
        </div>
    `;
}

async function sendChat() {
    const input = document.getElementById('chat-input');
    const msg = input.value.trim();
    if (!msg) return;
    input.value = '';

    const messages = document.getElementById('chat-messages');
    messages.innerHTML += `<div class="text-right"><span class="inline-block p-3 rounded-lg bg-blue-100 dark:bg-blue-900 text-gray-900 dark:text-white">${msg}</span></div>`;

    try {
        const resp = await fetch('/api/chat/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: msg }),
        });
        const data = await resp.json();
        messages.innerHTML += `<div><span class="inline-block p-3 rounded-lg bg-gray-100 dark:bg-slate-700 text-gray-900 dark:text-white">${data.message || data.error || 'No response'}</span></div>`;
    } catch (e) {
        messages.innerHTML += `<div><span class="inline-block p-3 rounded-lg bg-red-100 text-red-700">Error: ${e.message}</span></div>`;
    }
    messages.scrollTop = messages.scrollHeight;
}
```

- [ ] **Step 4: Create dashboard.css**

```css
/* personal-ai-space/web/static/css/dashboard.css */
.card {
    @apply bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-200 dark:border-slate-700 transition-all;
}
.card:hover {
    @apply shadow-md;
}
.nav-btn {
    @apply px-3 py-2 text-sm font-medium text-gray-600 dark:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors;
}
.nav-btn.active {
    @apply bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400;
}
.priority-badge {
    @apply px-2 py-1 text-xs font-semibold rounded-full;
}
.priority-critical { @apply bg-red-100 text-red-700; }
.priority-high { @apply bg-orange-100 text-orange-700; }
.priority-normal { @apply bg-yellow-100 text-yellow-700; }
.priority-low { @apply bg-gray-100 text-gray-500; }
```

- [ ] **Step 5: Verify app serves HTML**

Run: `cd personal-ai-space && timeout 3 python -c "from web.app import create_app; app = create_app(); print('App created, routes:', len(list(app.url_map.iter_rules())))" 2>&1 || true`
Expected: App created, routes: 40+

---

## Task 7: Start Script + Final Integration

**Files:**
- Create: `personal-ai-space/run_web.sh`

**Does NOT cover:** Systemd/launchd service (manual start for now).

- [ ] **Step 1: Create start script**

```bash
#!/bin/bash
# personal-ai-space/run_web.sh
# Start the Personal AI Powerhouse web app
# Usage: ./run_web.sh [--daemon] [--port 5001]

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENGINE_DIR="$SCRIPT_DIR/engine"
WEB_DIR="$SCRIPT_DIR"
PORT="${PAI_WEB_PORT:-5001}"
START_DAEMON=false

# Parse args
while [[ $# -gt 0 ]]; do
    case $1 in
        --daemon) START_DAEMON=true; shift ;;
        --port) PORT="$2"; shift 2 ;;
        *) shift ;;
    esac
done

echo "🧠 Personal AI Powerhouse — Web App"
echo "────────────────────────────────────"

# Start daemon if requested
if $START_DAEMON; then
    echo "🚀 Starting engine daemon..."
    cd "$ENGINE_DIR"
    python3 cli.py daemon start 2>/dev/null || echo "  (daemon may already be running)"
    cd "$SCRIPT_DIR"
fi

# Check daemon
echo "🔍 Checking daemon..."
if curl -s http://127.0.0.1:19876/health > /dev/null 2>&1; then
    echo "  ✅ Daemon is running"
else
    echo "  ⚠️  Daemon not running — start with: cd engine && python3 cli.py daemon start"
    echo "  Dashboard will work but engine proxy features will be unavailable"
fi

# Start web server
echo ""
echo "🌐 Starting web server on http://0.0.0.0:$PORT"
echo "   Access from any device on your network"
echo "   Press Ctrl+C to stop"
echo ""

cd "$WEB_DIR"
python3 -c "
from web.app import create_app
from web.config import WEB_HOST
app = create_app()
app.run(host='0.0.0.0', port=$PORT, debug=False)
"
```

- [ ] **Step 2: Make script executable**

Run: `chmod +x personal-ai-space/run_web.sh`

- [ ] **Step 3: Verify start script works**

Run: `cd personal-ai-space && bash run_web.sh --port 5002 &
sleep 3
curl -s http://127.0.0.1:5002/api/health | python3 -m json.tool
kill %1 2>/dev/null`
Expected: JSON response showing database health status

- [ ] **Step 4: Verify dashboard serves**

Run: `cd personal-ai-space && python3 -c "
from web.app import create_app
app = create_app()
with app.test_client() as c:
    r = c.get('/')
    print(f'GET / → {r.status_code}, content-type: {r.content_type}')
    r = c.get('/api/tasks/summary')
    print(f'GET /api/tasks/summary → {r.status_code}, data: {r.json[:2] if r.status_code==200 else r.data[:100]}')
    r = c.get('/api/habits/')
    print(f'GET /api/habits/ → {r.status_code}, count: {len(r.json) if r.status_code==200 else \"error\"}')
    r = c.get('/api/calendar/today')
    print(f'GET /api/calendar/today → {r.status_code}, count: {len(r.json) if r.status_code==200 else \"error\"}')
    r = c.get('/api/jobs/pipeline')
    print(f'GET /api/jobs/pipeline → {r.status_code}, data: {r.json if r.status_code==200 else \"error\"}')
"`
Expected: All endpoints return 200 with data

---

## Verification Checklist

After all tasks complete, verify:

1. **Start script**: `./run_web.sh --daemon` starts without errors
2. **Dashboard loads**: Open `http://YOUR_IP:5001` from phone/tablet
3. **Data displays**: Tasks, habits, calendar, jobs panels show real data
4. **Habit completion**: Click ✓ on a habit → it marks complete
5. **Task completion**: Click ✓ on a task → it marks complete
6. **Chat works**: Type "what's on my plate?" → get task list
7. **Dark mode**: Toggle works, persists across reload
8. **Mobile responsive**: Works on iPhone/Android browser
9. **Network access**: Access from another device on local network
10. **Daemon status**: Green indicator when daemon is running

---

## Future Enhancements (Not in This Plan)

- **WebSocket** for real-time updates (dashboard auto-refresh)
- **PWA manifest** for home screen install
- **Authentication** (simple password or mDNS)
- **FullCalendar** integration for calendar panel
- **Voice input** (Web Speech API)
- **WhatsApp chat** from browser (via MCP)
