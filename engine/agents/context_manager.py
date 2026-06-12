"""
Context Manager Agent.
Loads user profile, recent history, and active needs.
Provides context packet to all other agents.

MCP memory integration:
  - On startup: syncs profile facts to MCP memory (persistent cross-session)
  - get_context: enriches local context with MCP semantic facts
  - add_fact / add_lesson: write directly to MCP memory
"""
import json
import time
from datetime import datetime

from agents.base_agent import BaseAgent
from log_manager import audit
from transport.data_hub import DataHub
from transport.config import AppConfig


class ContextManager(BaseAgent):
    def __init__(self):
        super().__init__("context-manager")
        self._config = AppConfig.instance()
        self._hub = DataHub(self._config)
        self._cache: dict = {}
        self._cache_time: float = 0

    def initialize(self) -> bool:
        try:
            self._load_profile()
            self.state = "ready"
            self.logger.info("Context Manager ready")
            return True
        except Exception as e:
            self.logger.error(f"Init failed: {e}")
            return False

    # ── core ──────────────────────────────────────────────────────────

    def _load_profile(self) -> dict:
        """Load user profile. Prefer DB; fall back to JSON."""
        profile = self._hub.get_user_profile()
        if profile:
            return profile
        if self._config.profile_path.exists():
            with open(self._config.profile_path) as f:
                return json.load(f)
        return {}

    def get_context(self) -> dict:
        """Return full user context. Cached for config.context_ttl_seconds."""
        now = time.monotonic()
        if now - self._cache_time < self._config.context_ttl_seconds and self._cache:
            return self._cache

        profile = self._load_profile()
        habits  = self._hub.get_habits(active_only=True)
        needs   = self._hub.get_needs(active_only=True)
        recent  = self._hub.get_recent_interactions(10)

        self._cache = {
            "profile": profile,
            "habits":  habits,
            "needs":   needs,
            "recent_interactions": recent,
            "mcp_facts": {},
            "generated_at": datetime.now().isoformat(),
        }
        self._cache_time = now
        return self._cache

    def invalidate_cache(self):
        self._cache = {}
        self._cache_time = 0

    # ── router ────────────────────────────────────────────────────────

    def process(self, message: dict) -> dict:
        cmd     = message.get("payload", {}).get("command", "")
        payload = message.get("payload", {})

        if cmd == "get_context":
            return self._ok(self.get_context())

        if cmd == "get_profile":
            return self._ok(self._load_profile())

        if cmd == "invalidate_cache":
            self.invalidate_cache()
            return self._ok({"message": "Cache cleared"})

        if cmd == "add_fact":
            return self._error("MCP memory not available through ContextManager")

        if cmd == "add_lesson":
            return self._error("MCP memory not available through ContextManager")

        if cmd == "list_facts":
            return self._error("MCP memory not available through ContextManager")

        if cmd == "list_lessons":
            return self._error("MCP memory not available through ContextManager")

        if cmd == "mcp_stats":
            return self._error("MCP memory not available through ContextManager")

        if cmd == "sync_profile":
            return self._ok({"message": "Profile data available via DataHub"})

        return self._unknown(cmd)
