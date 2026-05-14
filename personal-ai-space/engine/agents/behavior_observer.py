"""
Behavior Observer — Autonomous learning infrastructure.

Passively logs agent decisions, user actions, and system behavior.
Stores observations as MCP memory facts for pattern learning.

Observation types:
  - task_created: category, urgency, time, tool
  - task_completed: time_to_complete, actual_urgency, category
  - context_accessed: what fields, when, frequency
  - command_executed: which command, sequence, time
  - habit_logged: which habit, time, streak
"""
import json
from datetime import datetime, timedelta

from log_manager import get_logger
from transport.data_hub import DataHub

logger = get_logger("engine.observer")


class BehaviorObserver:
    """
    Tracks user behavior and agent decisions autonomously.

    Design: Passive. Every agent call triggers an observation.
    No agent logic changes — observer is transparent.
    Uses DataHub for all persistent storage.
    """

    def __init__(self):
        self._hub = DataHub()
        self.observation_buffer = []
        self.session_start = datetime.now()
        logger.info("BehaviorObserver initialized")

    # ── Observation Methods ───────────────────────────────────────────

    def observe_task_created(self, task: dict) -> None:
        """Log task creation: category, urgency signals, time."""
        obs = {
            "type": "task_created",
            "timestamp": datetime.now().isoformat(),
            "task_id": task.get("id", "?"),
            "category": task.get("category", "unknown"),
            "title": task.get("title", "")[:60],
            "priority": task.get("priority", "normal"),
        }
        self._buffer_and_learn(obs)
        logger.debug(f"Observed: task created in {obs['category']}")

    def observe_task_completed(self, task: dict, duration_seconds: float) -> None:
        """Log task completion: time taken, category, priority."""
        obs = {
            "type": "task_completed",
            "timestamp": datetime.now().isoformat(),
            "task_id": task.get("id", "?"),
            "category": task.get("category", "unknown"),
            "duration_seconds": duration_seconds,
            "priority": task.get("priority", "normal"),
        }
        self._buffer_and_learn(obs)
        logger.debug(f"Observed: task completed in {duration_seconds}s")

    def observe_habit_logged(self, habit: dict, completed: bool) -> None:
        """Log habit check-in: which habit, completed or skipped."""
        obs = {
            "type": "habit_logged",
            "timestamp": datetime.now().isoformat(),
            "habit_id": habit.get("id", "?"),
            "habit_name": habit.get("habit_name", "")[:40],
            "completed": completed,
            "streak": habit.get("current_streak", 0),
        }
        self._buffer_and_learn(obs)
        logger.debug(f"Observed: habit logged — {habit.get('habit_name')} = {completed}")

    def observe_context_accessed(self, context_type: str) -> None:
        """Log context retrieval: what was accessed, when."""
        obs = {
            "type": "context_accessed",
            "timestamp": datetime.now().isoformat(),
            "context_type": context_type,
        }
        self._buffer_and_learn(obs)
        logger.debug(f"Observed: context accessed — {context_type}")

    def observe_cli_command(self, command: str, args: list = None) -> None:
        """Log CLI command execution: which command, args, time."""
        obs = {
            "type": "cli_command",
            "timestamp": datetime.now().isoformat(),
            "command": command,
            "arg_count": len(args) if args else 0,
        }
        self._buffer_and_learn(obs)
        logger.debug(f"Observed: CLI command — {command}")

    def observe_memory_operation(self, operation: str, key: str = None) -> None:
        """Log memory access: add_fact, add_lesson, get_fact, etc."""
        obs = {
            "type": "memory_operation",
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "key": key,
        }
        self._buffer_and_learn(obs)
        logger.debug(f"Observed: memory operation — {operation}")

    def observe_anomaly_detected(self, anomaly_type: str, severity: str) -> None:
        """Log anomaly: what deviation was detected, severity."""
        obs = {
            "type": "anomaly_detected",
            "timestamp": datetime.now().isoformat(),
            "anomaly_type": anomaly_type,
            "severity": severity,
        }
        self._buffer_and_learn(obs)
        logger.debug(f"Observed: anomaly detected — {anomaly_type} ({severity})")

    # ── Buffer & Learning ─────────────────────────────────────────────

    def _buffer_and_learn(self, observation: dict) -> None:
        """Buffer observation and attempt pattern learning."""
        self.observation_buffer.append(observation)

        if len(self.observation_buffer) >= 10:
            self._infer_from_buffer()

    def _infer_from_buffer(self) -> None:
        """Analyze buffered observations for learnable patterns."""
        type_counts = {}
        category_counts = {}
        time_patterns = {}

        for obs in self.observation_buffer:
            obs_type = obs.get("type", "unknown")
            type_counts[obs_type] = type_counts.get(obs_type, 0) + 1

            if obs.get("category"):
                cat = obs["category"]
                category_counts[cat] = category_counts.get(cat, 0) + 1

            timestamp = obs.get("timestamp", "")
            if timestamp:
                try:
                    hour = datetime.fromisoformat(timestamp).hour
                    time_key = f"hour_{hour}"
                    time_patterns[time_key] = time_patterns.get(time_key, 0) + 1
                except Exception:
                    pass

        self._persist_to_memory_db(type_counts, category_counts, time_patterns)
        self.observation_buffer.clear()

    def _persist_to_memory_db(self, type_counts: dict, category_counts: dict, time_patterns: dict) -> None:
        """Persist learned observations to agent_memory table via DataHub."""
        try:
            if type_counts:
                top_type = max(type_counts, key=type_counts.get)
                self._hub.store_agent_memory("observer", "behavior.top_action_type", top_type)
                logger.info(f"Learned: primary action type = {top_type}")

            if category_counts:
                top_cat = max(category_counts, key=category_counts.get)
                self._hub.store_agent_memory("observer", "behavior.primary_category", top_cat)
                logger.info(f"Learned: primary category = {top_cat}")

            if time_patterns:
                top_time = max(time_patterns, key=time_patterns.get)
                self._hub.store_agent_memory("observer", "behavior.active_time", top_time)
                logger.info(f"Learned: most active during {top_time}")

            buffer_size = len(self.observation_buffer)
            self._hub.store_agent_memory("observer", "behavior.last_buffer_size", str(buffer_size))
        except Exception as e:
            logger.warning(f"Failed to persist to agent_memory: {e}")

    def get_buffer_stats(self) -> dict:
        """Return current buffer state (for debugging)."""
        type_counts = {}
        for obs in self.observation_buffer:
            t = obs.get("type", "unknown")
            type_counts[t] = type_counts.get(t, 0) + 1

        return {
            "buffer_size": len(self.observation_buffer),
            "observation_types": type_counts,
            "session_age_seconds": (datetime.now() - self.session_start).total_seconds(),
        }

    def dump_observations(self, limit: int = 20) -> list:
        """Return recent observations (for inspection)."""
        return self.observation_buffer[-limit:]
