"""
Task Coordinator Agent.
Manages tasks, projects, priority scoring, and deadlines.
"""
import uuid
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.base_agent import BaseAgent
from log_manager import audit
import db_manager as db
import propagator


PRIORITY_WEIGHTS = {"critical": 40, "high": 30, "normal": 20, "low": 10}
STATUS_OPEN      = ("pending", "in_progress", "blocked")


class TaskCoordinator(BaseAgent):
    def __init__(self):
        super().__init__("task-coordinator")

    def initialize(self) -> bool:
        db.health_check()
        self.state = "ready"
        self.logger.info("Task Coordinator ready")
        return True

    # ── public methods ─────────────────────────────────────────────────────

    def get_todays_tasks(self) -> list[dict]:
        today = datetime.now().strftime("%Y-%m-%d")
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        tasks = db.query(
            "tasks",
            "SELECT * FROM tasks WHERE status IN ('pending','in_progress') "
            "AND date(due_date) <= ? ORDER BY due_date ASC",
            (tomorrow,)
        )
        return sorted(tasks, key=self._score, reverse=True)

    def get_all_open(self) -> list[dict]:
        tasks = db.query(
            "tasks",
            "SELECT * FROM tasks WHERE status IN ('pending','in_progress','blocked') "
            "ORDER BY due_date ASC"
        )
        return sorted(tasks, key=self._score, reverse=True)

    def create_task(self, data: dict) -> str:
        task_id = data.get("id") or f"task_{uuid.uuid4().hex[:8]}"
        now = datetime.now().isoformat()
        db.execute(
            "tasks",
            "INSERT INTO tasks "
            "(id, title, description, project_id, priority, status, "
            "created_at, due_date, estimated_hours, actual_hours, "
            "assigned_to, tags, recurrence, category) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                task_id,
                data.get("title", "Untitled"),
                data.get("description", ""),
                data.get("project_id", "personal"),
                data.get("priority", "normal"),
                data.get("status", "pending"),
                now,
                data.get("due_date"),
                data.get("estimated_hours"),
                data.get("actual_hours"),
                data.get("assigned_to"),
                data.get("tags", ""),
                data.get("recurrence"),
                data.get("category", "general"),
            )
        )
        audit(f"CREATED task={task_id} title={data.get('title')}")
        self.logger.info(f"Task created: {task_id}")
        propagator.on_task_created(task_id)
        return task_id

    def update_status(self, task_id: str, new_status: str) -> bool:
        old = db.query("tasks", "SELECT status FROM tasks WHERE id=?", (task_id,))
        old_status = old[0]["status"] if old else None
        rows = db.execute(
            "tasks",
            "UPDATE tasks SET status=?, completed_at=CASE WHEN ?='completed' THEN ? ELSE completed_at END WHERE id=?",
            (new_status, new_status, datetime.now().isoformat(), task_id)
        )
        if rows:
            audit(f"STATUS_CHANGE task={task_id} new_status={new_status}")
            self.logger.info(f"Task {task_id} → {new_status}")
            propagator.on_task_updated(task_id, {"status": old_status} if old_status else None)
        return bool(rows)

    def summary(self) -> dict:
        rows = db.query(
            "tasks",
            "SELECT status, count(*) as cnt FROM tasks GROUP BY status"
        )
        totals = {r["status"]: r["cnt"] for r in rows}
        completed = totals.get("completed", 0)
        total = sum(totals.values())
        return {
            "total": total,
            "completed": completed,
            "pending": totals.get("pending", 0),
            "in_progress": totals.get("in_progress", 0),
            "blocked": totals.get("blocked", 0),
            "completion_rate": round(completed / total * 100, 1) if total else 0,
        }

    # ── internals ─────────────────────────────────────────────────────────

    def _score(self, task: dict) -> float:
        score = PRIORITY_WEIGHTS.get(task.get("priority", "normal"), 20)
        due = task.get("due_date")
        if due:
            try:
                due_dt = datetime.fromisoformat(str(due))
                days_left = (due_dt - datetime.now()).days
                score += max(0, 40 - days_left * 4)
            except ValueError:
                pass
        est = task.get("estimated_hours") or 2
        if est < 1:
            score += 15
        elif est < 3:
            score += 8
        return min(100.0, score)

    # ── task dependencies ────────────────────────────────────────────────

    def create_dependency(self, task_id: str, depends_on: str, dep_type: str = "blocks") -> bool:
        """Create a dependency: task_id depends_on depends_on.
        If the source is not completed, auto-mark task_id as blocked.
        """
        dep_id = uuid.uuid4().hex
        db.execute("tasks", """
            INSERT OR IGNORE INTO task_dependencies
            (id, task_id, depends_on, dependency_type, created_at)
            VALUES (?,?,?,?,?)
        """, (dep_id, task_id, depends_on, dep_type, datetime.now().isoformat()))
        audit(f"DEPENDENCY task={task_id} depends_on={depends_on} type={dep_type}")
        self._recheck_blocked(task_id)
        return True

    def remove_dependency(self, task_id: str, depends_on: str) -> bool:
        """Remove a dependency between two tasks."""
        rows = db.execute("tasks",
            "DELETE FROM task_dependencies WHERE task_id=? AND depends_on=?",
            (task_id, depends_on))
        if rows:
            audit(f"DEPENDENCY_REMOVED task={task_id} depends_on={depends_on}")
            self._recheck_blocked(task_id)
        return bool(rows)

    def get_blockers(self, task_id: str) -> list[dict]:
        """Return all tasks that block the given task."""
        return db.query("tasks", """
            SELECT t.* FROM tasks t
            JOIN task_dependencies d ON d.depends_on = t.id
            WHERE d.task_id = ?
        """, (task_id,))

    def get_dependents(self, task_id: str) -> list[dict]:
        """Return all tasks that depend on the given task."""
        return db.query("tasks", """
            SELECT t.* FROM tasks t
            JOIN task_dependencies d ON d.task_id = t.id
            WHERE d.depends_on = ?
        """, (task_id,))

    def _recheck_blocked(self, task_id: str):
        """If any blocker is not completed, mark task as blocked. Else pending."""
        blockers = db.query("tasks", """
            SELECT COUNT(*) as n FROM task_dependencies d
            JOIN tasks t ON t.id = d.depends_on
            WHERE d.task_id = ? AND t.status != 'completed'
        """, (task_id,))
        is_blocked = blockers[0]["n"] > 0
        current = db.query("tasks", "SELECT status FROM tasks WHERE id=?", (task_id,))
        if not current:
            return
        current_status = current[0]["status"]
        if is_blocked and current_status != "blocked":
            db.execute("tasks", "UPDATE tasks SET status=? WHERE id=?",
                       ("blocked", task_id))
            propagator.on_task_updated(task_id, {"status": current_status})
        elif not is_blocked and current_status == "blocked":
            db.execute("tasks", "UPDATE tasks SET status=? WHERE id=?",
                       ("pending", task_id))
            propagator.on_task_updated(task_id, {"status": "blocked"})

    # ── router ────────────────────────────────────────────────────────────

    def process(self, message: dict) -> dict:
        cmd = message.get("payload", {}).get("command", "")
        data = message.get("payload", {}).get("data", {})

        if cmd == "get_today":
            return self._ok(self.get_todays_tasks())
        if cmd == "get_all_open":
            return self._ok(self.get_all_open())
        if cmd == "create_task":
            return self._ok({"task_id": self.create_task(data)})
        if cmd == "update_status":
            ok = self.update_status(data["task_id"], data["new_status"])
            return self._ok({"updated": ok})
        if cmd == "summary":
            return self._ok(self.summary())
        if cmd == "create_dependency":
            ok = self.create_dependency(data["task_id"], data["depends_on"], data.get("dep_type", "blocks"))
            return self._ok({"created": ok})
        if cmd == "remove_dependency":
            ok = self.remove_dependency(data["task_id"], data["depends_on"])
            return self._ok({"removed": ok})
        if cmd == "get_blockers":
            return self._ok(self.get_blockers(data["task_id"]))
        if cmd == "get_dependents":
            return self._ok(self.get_dependents(data["task_id"]))

        return self._unknown(cmd)
