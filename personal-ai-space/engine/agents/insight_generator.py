"""
Insight Generator Agent.
Analyses habits, detects patterns, generates recommendations.
"""
import uuid
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.base_agent import BaseAgent
import db_manager as db


COMPLETION_THRESHOLDS = {
    "excellent": 90,
    "good": 70,
    "fair": 50,
    "poor": 0,
}


def _rate(pct: float) -> str:
    for label, threshold in COMPLETION_THRESHOLDS.items():
        if pct >= threshold:
            return label
    return "poor"


class InsightGenerator(BaseAgent):
    def __init__(self):
        super().__init__("insight-generator")

    def initialize(self) -> bool:
        self.state = "ready"
        self.logger.info("Insight Generator ready")
        return True

    # ── analysis ──────────────────────────────────────────────────────────

    def analyse_habits(self, days: int = 7) -> dict:
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        habits = db.query(
            "self",
            "SELECT h.id, h.habit_name, h.category, h.current_streak, h.total_completions, "
            "(SELECT count(*) FROM habit_logs l WHERE l.habit_id = h.id AND l.completed_at >= ?) "
            "as completions_in_period FROM habits h WHERE h.status='active'",
            (cutoff,)
        )

        insights = []
        anomalies = []
        for h in habits:
            completions = h["completions_in_period"] or 0
            pct = round(completions / days * 100, 1)
            rating = _rate(pct)
            rec = self._recommend(pct, h["habit_name"])
            entry = {
                "habit": h["habit_name"],
                "category": h["category"],
                "streak": h["current_streak"],
                "period_completions": completions,
                "completion_pct": pct,
                "rating": rating,
                "recommendation": rec,
            }
            insights.append(entry)
            if pct == 0 and h["current_streak"] and h["current_streak"] > 3:
                anomalies.append({
                    "type": "habit_dropped",
                    "habit": h["habit_name"],
                    "previous_streak": h["current_streak"],
                    "severity": "high",
                })

        return {
            "period_days": days,
            "habits_analyzed": len(insights),
            "insights": insights,
            "anomalies": anomalies,
        }

    def task_velocity(self) -> dict:
        rows = db.query(
            "tasks",
            "SELECT "
            "  count(*) FILTER (WHERE status='completed') as completed, "
            "  count(*) as total, "
            "  count(*) FILTER (WHERE status='completed' AND completed_at IS NOT NULL "
            "      AND completed_at >= date('now','-7 days')) as completed_week "
            "FROM tasks"
        )
        r = rows[0] if rows else {}
        total = r.get("total") or 1
        completed = r.get("completed") or 0
        return {
            "total_tasks": total,
            "completed": completed,
            "completion_rate": round(completed / total * 100, 1),
            "completed_this_week": r.get("completed_week") or 0,
        }

    def daily_digest_data(self) -> dict:
        habits  = self.analyse_habits(days=1)
        week    = self.analyse_habits(days=7)
        tasks   = self.task_velocity()
        at_risk = [h for h in week["insights"] if h["rating"] in ("fair", "poor")]

        return {
            "habits_today": habits,
            "habits_week": week,
            "task_metrics": tasks,
            "at_risk_habits": at_risk,
            "anomalies": habits["anomalies"] + week["anomalies"],
        }

    # ── helpers ───────────────────────────────────────────────────────────

    def _recommend(self, pct: float, name: str) -> Optional[str]:
        if pct == 0:
            return f"⚠️  '{name}' not done at all — schedule a specific slot"
        if pct < 50:
            return f"Try stacking '{name}' onto an existing routine"
        if pct < 70:
            return f"Almost there with '{name}' — commit to 3x this week"
        return None  # Doing well, no recommendation

    # ── router ────────────────────────────────────────────────────────────

    def process(self, message: dict) -> dict:
        cmd  = message.get("payload", {}).get("command", "")
        days = message.get("payload", {}).get("days", 7)

        if cmd == "analyse_habits":
            return self._ok(self.analyse_habits(days))
        if cmd == "task_velocity":
            return self._ok(self.task_velocity())
        if cmd == "daily_digest_data":
            return self._ok(self.daily_digest_data())

        return self._unknown(cmd)
