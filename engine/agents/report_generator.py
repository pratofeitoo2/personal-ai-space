"""
Report Generator Agent.
Builds daily digest, weekly review, and monthly analysis as text.
"""
import uuid
from pathlib import Path
from datetime import datetime, timedelta

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.base_agent import BaseAgent
from agents.insight_generator import InsightGenerator
from agents.task_coordinator import TaskCoordinator
from agents.reminder_system import ReminderSystem
import db_manager as db


PRIORITY_ICON = {"critical": "🔴", "high": "🟠", "normal": "🟡", "low": "⚪"}
RATING_ICON   = {"excellent": "✅", "good": "✅", "fair": "⚠️", "poor": "❌"}


class ReportGenerator(BaseAgent):
    def __init__(self):
        super().__init__("report-generator")
        self._insights = InsightGenerator()
        self._tasks    = TaskCoordinator()
        self._reminder = ReminderSystem()

    def initialize(self) -> bool:
        self.state = "ready"
        self.logger.info("Report Generator ready")
        return True

    # ── daily digest ──────────────────────────────────────────────────────

    def daily_digest(self) -> str:
        now   = datetime.now()
        data  = self._insights.daily_digest_data()
        today = self._tasks.get_todays_tasks()
        snap  = self._reminder.snapshot()

        lines = [
            f"# Daily Digest — {now.strftime('%B %-d, %Y')}",
            "",
            "## 🎯 Today at a Glance",
            f"- **Tasks due today**: {len(snap['due_today'])}",
            f"- **Overdue**: {len(snap['overdue'])}",
            f"- **Habits at risk**: {len(data['at_risk_habits'])}",
            f"- **Anomalies detected**: {len(data['anomalies'])}",
            "",
        ]

        # Tasks
        lines += ["## 📋 Today's Priority Tasks"]
        if today:
            lines.append("| # | Task | Priority | Due |")
            lines.append("|---|------|----------|-----|")
            for i, t in enumerate(today[:8], 1):
                icon = PRIORITY_ICON.get(t.get("priority", "normal"), "⚪")
                due  = (t.get("due_date") or "—")[:10]
                lines.append(f"| {i} | {t['title']} | {icon} {t.get('priority','—')} | {due} |")
        else:
            lines.append("_No tasks due today — you're clear!_")
        lines.append("")

        # Habits
        lines += ["## 💪 Habit Status (Last 7 Days)"]
        weekly = data["habits_week"]["insights"]
        if weekly:
            for h in weekly:
                icon = RATING_ICON.get(h["rating"], "⚪")
                streak = h.get("streak") or 0
                lines.append(f"- {icon} **{h['habit']}** — {h['completion_pct']}% ({streak} day streak)")
                if h.get("recommendation"):
                    lines.append(f"  - _{h['recommendation']}_")
        else:
            lines.append("_No habits tracked yet. Add habits to see insights._")
        lines.append("")

        # Alerts
        if snap["overdue"]:
            lines += ["## 🚨 Overdue Items"]
            for t in snap["overdue"][:5]:
                lines.append(f"- **{t['title']}** (was due {str(t.get('due_date','?'))[:10]})")
            lines.append("")

        # Anomalies
        if data["anomalies"]:
            lines += ["## ⚡ Anomalies"]
            for a in data["anomalies"]:
                lines.append(f"- [{a['severity'].upper()}] {a['type']}: **{a.get('habit', a.get('task','?'))}**")
            lines.append("")

        # Task metrics
        tm = data["task_metrics"]
        lines += [
            "## 📊 Metrics",
            f"- Overall completion rate: **{tm['completion_rate']}%**",
            f"- Completed this week: **{tm['completed_this_week']}** tasks",
            f"- Total tasks tracked: **{tm['total_tasks']}**",
            "",
            "---",
            f"_Generated: {now.strftime('%Y-%m-%d %H:%M')} | Next digest: {(now + timedelta(days=1)).strftime('%Y-%m-%d 08:00')}_",
        ]
        return "\n".join(lines)

    # ── weekly review ─────────────────────────────────────────────────────

    def weekly_review(self) -> str:
        now    = datetime.now()
        data   = self._insights.analyse_habits(7)
        tasks  = self._tasks.summary()
        snap   = self._reminder.snapshot()

        lines = [
            f"# Weekly Review — Week {now.isocalendar().week}, {now.year}",
            "",
            "## 📈 Week Summary",
            f"- **Tasks completed**: {tasks['completed']} / {tasks['total']} ({tasks['completion_rate']}%)",
            f"- **Habits tracked**: {data['habits_analyzed']}",
            f"- **Anomalies**: {len(data['anomalies'])}",
            "",
            "## 💪 Habit Performance",
        ]
        for h in data["insights"]:
            icon = RATING_ICON.get(h["rating"], "⚪")
            lines.append(
                f"- {icon} **{h['habit']}** — {h['completion_pct']}% "
                f"| streak: {h.get('streak', 0)} days"
            )
            if h.get("recommendation"):
                lines.append(f"  - _{h['recommendation']}_")

        lines += [
            "",
            "## 🎯 Next Week Priorities",
        ]
        next_week = self._tasks.get_all_open()[:5]
        for t in next_week:
            icon = PRIORITY_ICON.get(t.get("priority", "normal"), "⚪")
            lines.append(f"- [ ] {icon} {t['title']}")

        lines += [
            "",
            "---",
            f"_Generated: {now.strftime('%Y-%m-%d %H:%M')}_",
        ]
        return "\n".join(lines)

    # ── router ────────────────────────────────────────────────────────────

    def process(self, message: dict) -> dict:
        cmd = message.get("payload", {}).get("command", "")

        if cmd == "daily_digest":
            return self._ok({"report": self.daily_digest()})
        if cmd == "weekly_review":
            return self._ok({"report": self.weekly_review()})

        return self._unknown(cmd)
