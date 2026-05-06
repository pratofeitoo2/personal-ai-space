"""
Base agent class. All agents inherit from this.
"""
import uuid
import time
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional

from log_manager import get_logger, audit, perf


class BaseAgent(ABC):
    def __init__(self, agent_id: str):
        self.observer = None
        self.id = agent_id
        self.state = "idle"
        self.logger = get_logger(agent_id)
        self._start_time = None

    def initialize(self) -> bool:
        """Override to set up agent resources. Return True on success."""
        self.state = "ready"
        return True

    def handle(self, message: dict) -> dict:
        """Route incoming message to correct handler. Wraps process() with timing."""
        self._start_time = time.monotonic()
        msg_id = message.get("id", str(uuid.uuid4()))
        command = message.get("payload", {}).get("command", "unknown")
        self.logger.info(f"Handling [{command}] msg={msg_id}")
        self.state = "active"
        try:
            result = self.process(message)
            elapsed = (time.monotonic() - self._start_time) * 1000
            perf(self.id, elapsed, f"cmd={command}")
            return result
        except Exception as e:
            self.logger.error(f"Error handling [{command}]: {e}", exc_info=True)
            return self._error(str(e))
        finally:
            self.state = "idle"

    @abstractmethod
    def process(self, message: dict) -> dict:
        """Implement agent logic here."""
        ...

    def shutdown(self) -> None:
        self.logger.info(f"Agent {self.id} shutting down")
        self.state = "stopped"

    # ── helpers ────────────────────────────────────────────────────────────

    @staticmethod
    def _ok(payload: Any) -> dict:
        return {"status": "success", "payload": payload}

    @staticmethod
    def _error(message: str) -> dict:
        return {"status": "error", "error": message}

    def _unknown(self, command: str) -> dict:
        self.logger.warning(f"Unknown command: {command}")
        return self._error(f"Unknown command: {command}")

    def set_observer(self, observer):
        """Wire in the behavior observer (called by engine)."""
        self.observer = observer
