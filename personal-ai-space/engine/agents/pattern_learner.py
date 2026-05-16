"""
Pattern Learner — Infers workflows, preferences, and routines from observations.

Analyzes historical data to extract:
  - Time-based patterns (when do you work?)
  - Tool usage (which tools do you use most?)
  - Task categories (what do you prioritize?)
  - Workflow sequences (what's your routine?)
"""
from datetime import datetime, timedelta
from collections import Counter
from typing import Optional

from log_manager import get_logger, audit
from transport.data_hub import DataHub
from agents.base_agent import BaseAgent

logger = get_logger("engine.pattern_learner")


class PatternLearner(BaseAgent):
    """Infers patterns from historical data and agent observations."""

    def __init__(self):
        super().__init__("pattern-learner")
        self._hub = DataHub()
        self.learned_patterns = {}
        self.state = "ready"
        logger.info("PatternLearner initialized")

    # ── BaseAgent interface ───────────────────────────────────────────

    def get_capabilities(self) -> list:
        return ["infer_all_patterns", "get_top_patterns", "get_workflow_recommendation"]

    def get_metadata(self) -> dict:
        return {"name": "Pattern Learner", "version": "1.0", "type": "learner"}

    def process(self, message: dict) -> dict:
        command = message.get("payload", {}).get("command", "")
        data = message.get("payload", {}).get("data", {})
        if command == "infer":
            return self._ok(self.infer_all_patterns())
        if command == "top_patterns":
            return self._ok(self.get_top_patterns(data.get("limit", 5)))
        if command == "workflow":
            return self._ok({"recommendation": self.get_workflow_recommendation()})
        return self._unknown(command)

    # ── Time-Based Patterns ───────────────────────────────────────────

    def learn_time_patterns(self) -> dict:
        """When do you typically perform activities?"""
        patterns = {}

        try:
            tasks = self._hub.query("tasks", """
                SELECT datetime(created_at) as ct FROM tasks
                WHERE created_at > datetime('now', '-30 days')
                ORDER BY created_at DESC
            """)

            if tasks:
                hours = Counter()
                for t in tasks:
                    try:
                        dt = datetime.fromisoformat(t['ct'])
                        hours[dt.hour] += 1
                    except Exception:
                        logger.debug("Failed to parse task timestamp for hour")

                if hours:
                    most_common_hour = hours.most_common(1)[0][0]
                    patterns['task_creation_hour'] = most_common_hour
                    logger.info(f"Learned: tasks created most at {most_common_hour}:00")

        except Exception as e:
            logger.warning(f"Failed to learn time patterns: {e}")

        return patterns

    def learn_category_preferences(self) -> dict:
        """Which task categories dominate your work?"""
        patterns = {}

        try:
            tasks = self._hub.query("tasks", """
                SELECT COALESCE(category, 'uncategorized') as category, COUNT(*) as count FROM tasks
                GROUP BY category
                ORDER BY count DESC
                LIMIT 5
            """)

            if tasks:
                categories = [t['category'] for t in tasks]
                patterns['top_categories'] = categories
                logger.info(f"Learned: primary category = {categories[0]}")

        except Exception as e:
            logger.warning(f"Failed to learn category preferences: {e}")

        return patterns

    def learn_task_completion_rates(self) -> dict:
        """What completion rates by category/priority?"""
        patterns = {}

        try:
            tasks = self._hub.query("tasks", """
                SELECT
                    COALESCE(category, 'uncategorized') as category,
                    COALESCE(priority, 'normal') as priority,
                    COUNT(*) as total,
                    SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) as completed
                FROM tasks
                WHERE created_at > datetime('now', '-60 days')
                GROUP BY category, priority
            """)

            if tasks:
                for t in tasks:
                    rate = t['completed'] / t['total'] if t['total'] > 0 else 0
                    cat = t['category']
                    pri = t['priority']
                    key = f"completion_rate_{cat}_{pri}"
                    patterns[key] = rate

        except Exception as e:
            logger.warning(f"Failed to learn completion rates: {e}")

        return patterns

    def learn_habit_consistency(self) -> dict:
        """Which habits do you maintain consistently?"""
        patterns = {}

        try:
            habits = self._hub.query("self", """
                SELECT
                    habit_name,
                    current_streak,
                    frequency,
                    status
                FROM habits
                WHERE status = 'active'
                ORDER BY current_streak DESC
                LIMIT 5
            """)

            if habits:
                for h in habits:
                    patterns[h['habit_name']] = h['current_streak']

        except Exception as e:
            logger.warning(f"Failed to learn habit consistency: {e}")

        return patterns

    # ── Inference ─────────────────────────────────────────────────────

    def _persist_patterns(self) -> None:
        """Store learned patterns to agent_memory table via DataHub."""
        try:
            for key, value in self.learned_patterns.items():
                val = str(value) if not isinstance(value, str) else value
                self._hub.store_agent_memory("pattern_learner", f"pattern.{key}", val)
            audit(f"[pattern_learner] persisted {len(self.learned_patterns)} patterns to memory db")
        except Exception as e:
            logger.warning(f"Failed to persist patterns: {e}")

    def infer_all_patterns(self) -> dict:
        """Run all learners and compile patterns."""
        logger.info("Running pattern inference...")

        self.learned_patterns = {
            **self.learn_time_patterns(),
            **self.learn_category_preferences(),
            **self.learn_task_completion_rates(),
            **self.learn_habit_consistency(),
        }

        self._persist_patterns()

        logger.info(f"Inference complete: {len(self.learned_patterns)} patterns learned")
        return self.learned_patterns

    def get_top_patterns(self, limit: int = 5) -> dict:
        """Return top N learned patterns."""
        items = list(self.learned_patterns.items())[:limit]
        return dict(items)

    def get_workflow_recommendation(self) -> str:
        """Suggest a workflow based on learned patterns."""
        try:
            primary = self.learned_patterns.get('top_categories', ['general'])[0]
            time_hint = self.learned_patterns.get('task_creation_hour', 9)
            return f"Your typical workflow: start {time_hint}:00 -> focus on {primary} work"
        except Exception as e:
            logger.debug("Workflow recommendation unavailable: %s", e)
            return "No workflow recommendation available yet"
