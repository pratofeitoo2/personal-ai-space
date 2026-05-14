"""
DataHub — Typed facade for all database operations.

Replaces scattered db.query()/db.execute() calls with type-safe methods.
Every method logs to audit trail via log_manager.

Usage:
    hub = DataHub()
    profile = hub.get_user_profile()
    habits = hub.get_habits(active_only=True)
    hub.store_agent_memory("context-manager", "last_action", "daily_digest")
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import db_manager as db
from log_manager import audit, get_logger

from transport.config import AppConfig

logger = get_logger("engine.transport.data_hub")


# ── Type aliases ───────────────────────────────────────────────────────────────

# These are dict-based records from SQLite rows (dict_factory)
Record = dict[str, Any]
RecordList = list[Record]


class DataHub:
    """
    Central data access facade for the Personal AI engine.

    Wraps db_manager with typed methods, audit logging, and schema versioning.
    All agents should use DataHub instead of importing db_manager directly.
    """

    def __init__(self, config: Optional[AppConfig] = None):
        self._config = config or AppConfig.instance()
        self._db_dir = self._config.memory_db_dir
        self._ensure_db_dir()

    # ── Initialization ────────────────────────────────────────────────────────

    def _ensure_db_dir(self):
        """Ensure the database directory exists."""
        self._db_dir.mkdir(parents=True, exist_ok=True)

    def _db_path(self, name: str) -> Path:
        """Resolve a database name to its file path."""
        return self._db_dir / f"{name}.db"

    def _db_exists(self, name: str) -> bool:
        """Check if a database file exists."""
        return self._db_path(name).exists()

    # ── User Profile ──────────────────────────────────────────────────────────

    def get_user_profile(self) -> Optional[Record]:
        """
        Load the user profile from self.db.
        Returns the first row or None if no profile exists.
        """
        try:
            rows = db.query("self", "SELECT * FROM profile LIMIT 1")
            result = rows[0] if rows else None
            audit(f"[datahub] get_user_profile: {'found' if result else 'empty'}")
            return result
        except Exception as e:
            logger.error("Failed to get user profile: %s", e)
            return None

    def update_user_profile(self, **fields) -> bool:
        """
        Update user profile fields. Creates profile if none exists.

        Args:
            **fields: Column names and values to set.

        Returns:
            True if successful.
        """
        try:
            existing = self.get_user_profile()
            columns = ", ".join(fields.keys())
            placeholders = ", ".join("?" for _ in fields)
            values = list(fields.values())

            if existing:
                set_clause = ", ".join(f"{k} = ?" for k in fields)
                db.execute("self", f"UPDATE profile SET {set_clause}", tuple(values))
            else:
                db.execute("self", f"INSERT INTO profile ({columns}) VALUES ({placeholders})", tuple(values))

            audit(f"[datahub] update_user_profile: fields={list(fields.keys())}")
            return True
        except Exception as e:
            logger.error("Failed to update user profile: %s", e)
            return False

    # ── Habits ────────────────────────────────────────────────────────────────

    def get_habits(self, active_only: bool = True) -> RecordList:
        """
        Get habits from self.db.

        Args:
            active_only: If True, only return habits with status='active'.

        Returns:
            List of habit records.
        """
        try:
            status_filter = "WHERE status='active'" if active_only else ""
            rows = db.query("self", f"SELECT * FROM habits {status_filter}")
            audit(f"[datahub] get_habits: count={len(rows)}, active_only={active_only}")
            return rows
        except Exception as e:
            logger.error("Failed to get habits: %s", e)
            return []

    def log_habit_completion(self, habit_name: str, duration_min: int = 0,
                             notes: str = "") -> bool:
        """
        Log a habit completion and update streak.

        This is a convenience wrapper that combines the insert + streak update
        logic from engine.py::log_habit.

        Args:
            habit_name: Name of the habit.
            duration_min: Duration in minutes (0 if not time-based).
            notes: Optional notes.

        Returns:
            True if logged successfully.
        """
        try:
            habit_rows = db.query("self",
                "SELECT id, current_streak, last_completed, target_streak FROM habits WHERE habit_name=? LIMIT 1",
                (habit_name,))
            if not habit_rows:
                logger.warning("Habit not found: %s", habit_name)
                return False

            habit = habit_rows[0]
            habit_id = habit["id"]
            now_iso = datetime.now(timezone.utc).isoformat()
            today = datetime.now(timezone.utc).date()

            # Compute streak before starting the transaction
            last = habit.get("last_completed")
            streak = habit.get("current_streak", 0)
            if last:
                try:
                    last_date = datetime.fromisoformat(last).date()
                    delta = (today - last_date).days
                    streak = streak + 1 if delta <= 1 else 1
                except ValueError:
                    streak = 1
            else:
                streak = 1

            # Wrap INSERT + UPDATE in a single atomic transaction
            with db.transaction("self") as conn:
                log_id = uuid.uuid4().hex
                conn.execute(
                    "INSERT INTO habit_logs (id, habit_id, completed_at, notes, confidence_level) VALUES (?,?,?,?,?)",
                    (log_id, habit_id, now_iso, notes, duration_min / 60.0 if duration_min else None),
                )
                conn.execute(
                    "UPDATE habits SET total_completions = total_completions + 1, "
                    "current_streak = ?, last_completed = ? WHERE id = ?",
                    (streak, now_iso, habit_id),
                )

            audit(f"[datahub] log_habit_completion: {habit_name}, streak={streak}")
            return True
        except Exception as e:
            logger.error("Failed to log habit completion: %s", e)
            return False

    # ── Needs ─────────────────────────────────────────────────────────────────

    def get_needs(self, active_only: bool = True) -> RecordList:
        """
        Get current needs/goals from self.db.

        Args:
            active_only: If True, only active needs.

        Returns:
            List of need records.
        """
        try:
            status_filter = "WHERE status='active'" if active_only else ""
            rows = db.query("self", f"SELECT * FROM needs {status_filter}")
            audit(f"[datahub] get_needs: count={len(rows)}")
            return rows
        except Exception as e:
            logger.error("Failed to get needs: %s", e)
            return []

    # ── Interactions ──────────────────────────────────────────────────────────

    def get_recent_interactions(self, limit: int = 10) -> RecordList:
        """
        Get most recent agent interactions from memories.db.

        Args:
            limit: Max number of interactions to return.

        Returns:
            List of interaction records, newest first.
        """
        try:
            rows = db.query("memories",
                "SELECT * FROM interactions ORDER BY timestamp DESC LIMIT ?", (limit,))
            audit(f"[datahub] get_recent_interactions: count={len(rows)}")
            return rows
        except Exception as e:
            logger.error("Failed to get recent interactions: %s", e)
            return []

    def log_interaction(self, agent_id: str, action: str,
                        input_data: Any = None, output_data: Any = None,
                        duration_ms: int = 0, status: str = "success",
                        error_message: str | None = None) -> str:
        """
        Log an agent interaction to memories.db.

        Returns the interaction ID.
        """
        try:
            interaction_id = db.log_interaction(
                agent_id=agent_id,
                action=action,
                input_data=input_data,
                output_data=output_data,
                duration_ms=duration_ms,
                status=status,
                error_message=error_message,
            )
            audit(f"[datahub] log_interaction: agent={agent_id}, action={action}, id={interaction_id}")
            return interaction_id
        except Exception as e:
            logger.error("Failed to log interaction: %s", e)
            return ""

    # ── Context Snapshots ─────────────────────────────────────────────────────

    def store_context_snapshot(self, session_id: str, content: Any,
                               relevance: float = 1.0,
                               ttl_hours: int = 24) -> str:
        """
        Store a context snapshot with expiry.

        Args:
            session_id: Session identifier.
            content: Snapshot content (will be JSON-serialized if not a string).
            relevance: Relevance score (0.0-1.0).
            ttl_hours: Time-to-live in hours.

        Returns:
            Snapshot ID.
        """
        try:
            cid = db.store_context_snapshot(
                session_id=session_id,
                content=content,
                relevance=relevance,
                ttl_hours=ttl_hours,
            )
            audit(f"[datahub] store_context_snapshot: session={session_id}, id={cid}")
            return cid
        except Exception as e:
            logger.error("Failed to store context snapshot: %s", e)
            return ""

    # ── Agent Memory ──────────────────────────────────────────────────────────

    def store_agent_memory(self, agent_id: str, key: str, value: str,
                           ttl_seconds: int | None = None) -> bool:
        """
        Store a key-value pair in agent memory.

        Args:
            agent_id: Which agent owns this memory.
            key: Memory key.
            value: Memory value.
            ttl_seconds: Optional time-to-live.

        Returns:
            True if stored successfully.
        """
        try:
            ok = db.store_agent_memory(agent_id, key, value, ttl_seconds)
            audit(f"[datahub] store_agent_memory: agent={agent_id}, key={key}")
            return ok
        except Exception as e:
            logger.error("Failed to store agent memory: %s", e)
            return False

    def get_agent_memory(self, agent_id: str, key: str | None = None) -> RecordList:
        """
        Retrieve agent memory entries.

        Args:
            agent_id: Which agent's memory to retrieve.
            key: Optional key filter.

        Returns:
            List of memory records.
        """
        try:
            rows = db.get_agent_memory(agent_id, key)
            audit(f"[datahub] get_agent_memory: agent={agent_id}, key={key}, count={len(rows)}")
            return rows
        except Exception as e:
            logger.error("Failed to get agent memory: %s", e)
            return []

    # ── Knowledge Base ────────────────────────────────────────────────────────

    def search_knowledge(self, query: str, limit: int = 10) -> RecordList:
        """
        Search the knowledge base for matching content.

        Args:
            query: Search query string.
            limit: Max results.

        Returns:
            List of matching knowledge records.
        """
        try:
            rows = db.query("knowledge",
                "SELECT * FROM knowledge WHERE content LIKE ? ORDER BY created_at DESC LIMIT ?",
                (f"%{query}%", limit))
            audit(f"[datahub] search_knowledge: query='{query}', count={len(rows)}")
            return rows
        except Exception as e:
            logger.error("Failed to search knowledge: %s", e)
            return []

    # ── Raw Escape Hatch ──────────────────────────────────────────────────────

    def query(self, db_name: str, sql: str, params: tuple = ()) -> RecordList:
        """
        Raw SQL query escape hatch. Use typed methods above when possible.

        Args:
            db_name: Database name (memories, self, tasks, knowledge, git).
            sql: SQL query string.
            params: Query parameters.

        Returns:
            List of result rows as dicts.
        """
        try:
            rows = db.query(db_name, sql, params)
            return rows
        except Exception as e:
            logger.error("Raw query failed on %s: %s", db_name, e)
            return []

    # ── Health ────────────────────────────────────────────────────────────────

    def health_check(self) -> dict[str, Any]:
        """Run health checks on all databases."""
        return db.health_check()

    def get_stats(self) -> dict[str, Any]:
        """Get aggregate statistics across all databases."""
        try:
            stats = db.health_check()
            total_interactions = db.query("memories",
                "SELECT COUNT(*) as n FROM interactions")[0]["n"]
            total_memories = db.query("memories",
                "SELECT COUNT(*) as n FROM agent_memory")[0]["n"]
            return {
                "databases": stats,
                "total_interactions": total_interactions,
                "total_agent_memories": total_memories,
                "checked_at": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            logger.error("Failed to get stats: %s", e)
            return {"error": str(e)}