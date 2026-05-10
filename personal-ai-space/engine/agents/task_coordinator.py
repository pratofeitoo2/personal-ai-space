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
        return task_id

    def update_status(self, task_id: str, new_status: str) -> bool:
        rows = db.execute(
            "tasks",
            "UPDATE tasks SET status=? WHERE id=?",
            (new_status, task_id)
        )
        if rows:
            audit(f"STATUS_CHANGE task={task_id} new_status={new_status}")
            self.logger.info(f"Task {task_id} → {new_status}")
            # Log to history
            db.execute(
                "tasks",
                "INSERT INTO task_history (id, task_id, changed_at, field, new_value) "
                "VALUES (?,?,?,?,?)",
                (uuid.uuid4().hex, task_id, datetime.now().isoformat(), "status", new_status)
            )
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

        return self._unknown(cmd)
