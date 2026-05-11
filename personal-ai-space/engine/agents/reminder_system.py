"""
Reminder System Agent.
Checks upcoming deadlines and overdue items.
"""
import uuid
from pathlib import Path
from datetime import datetime, timedelta

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.base_agent import BaseAgent
import db_manager as db


class ReminderSystem(BaseAgent):
    def __init__(self):
        super().__init__("reminder-system")

    def initialize(self) -> bool:
        self.state = "ready"
        self.logger.info("Reminder System ready")
        return True

    # ── checks ────────────────────────────────────────────────────────────

    def due_today(self) -> list[dict]:
        today = datetime.now().strftime("%Y-%m-%d")
        return db.query(
            "tasks",
            "SELECT id, title, due_date, priority, status FROM tasks "
            "WHERE date(due_date) = ? AND status NOT IN ('completed','cancelled') "
            "ORDER BY priority DESC",
            (today,)
        )

    def overdue(self) -> list[dict]:
        today = datetime.now().strftime("%Y-%m-%d")
        return db.query(
            "tasks",
            "SELECT id, title, due_date, priority, status FROM tasks "
            "WHERE date(due_date) < ? AND status NOT IN ('completed','cancelled') "
            "ORDER BY due_date ASC",
            (today,)
        )

    def due_soon(self, hours: int = 48) -> list[dict]:
        now = datetime.now().isoformat()
        cutoff = (datetime.now() + timedelta(hours=hours)).isoformat()
        return db.query(
            "tasks",
            "SELECT id, title, due_date, priority, status FROM tasks "
            "WHERE due_date BETWEEN ? AND ? "
            "AND status NOT IN ('completed','cancelled') "
            "ORDER BY due_date ASC",
            (now, cutoff)
        )

    def upcoming_events(self, days: int = 7) -> list[dict]:
        now = datetime.now().isoformat()
        cutoff = (datetime.now() + timedelta(days=days)).isoformat()
        return db.query(
            "tasks",
            "SELECT * FROM calendar_events "
            "WHERE start_time BETWEEN ? AND ? "
            "ORDER BY start_time ASC",
            (now, cutoff)
        )

    def snapshot(self) -> dict:
        return {
            "overdue":    self.overdue(),
            "due_today":  self.due_today(),
            "due_soon":   self.due_soon(48),
            "events_week": self.upcoming_events(7),
            "checked_at": datetime.now().isoformat(),
        }

    # ── router ────────────────────────────────────────────────────────────

    def process(self, message: dict) -> dict:
        cmd = message.get("payload", {}).get("command", "")

        if cmd == "snapshot":
            return self._ok(self.snapshot())
        if cmd == "overdue":
            return self._ok(self.overdue())
        if cmd == "due_today":
            return self._ok(self.due_today())
        if cmd == "due_soon":
            hours = message.get("payload", {}).get("hours", 48)
            return self._ok(self.due_soon(hours))
        if cmd == "upcoming_events":
            days = message.get("payload", {}).get("days", 7)
            return self._ok(self.upcoming_events(days))

        return self._unknown(cmd)
