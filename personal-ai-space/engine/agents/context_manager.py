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
import sys
from pathlib import Path
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.base_agent import BaseAgent
from log_manager import audit
import db_manager as db
from memory.mcp_bridge import MCPMemoryBridge

PROFILE_PATH = Path(__file__).parent.parent.parent / "self" / "profile.json"
CACHE_TTL_SECONDS = 300


class ContextManager(BaseAgent):
    def __init__(self):
        super().__init__("context-manager")
        self._cache: dict = {}
        self._cache_time: float = 0
        self._mcp: MCPMemoryBridge | None = None

    def initialize(self) -> bool:
        try:
            # Try to connect MCP memory — non-fatal if unavailable
            try:
                self._mcp = MCPMemoryBridge()
                if self._mcp.health_check():
                    self.logger.info("MCP memory bridge connected")
                    self._sync_profile_to_mcp()
                else:
                    self.logger.warning("MCP memory bridge unhealthy — running without it")
                    self._mcp = None
            except Exception as mcp_err:
                self.logger.warning(f"MCP bridge init failed (non-fatal): {mcp_err}")
                self._mcp = None

            self._load_profile()
            self.state = "ready"
            self.logger.info("Context Manager ready")
            return True
        except Exception as e:
            self.logger.error(f"Init failed: {e}")
            return False

    # ── core ──────────────────────────────────────────────────────────────

    def _load_profile(self) -> dict:
        """Load user profile. Prefer DB; fall back to JSON."""
        rows = db.query("self", "SELECT * FROM profile LIMIT 1")
        if rows:
            return rows[0]
        if PROFILE_PATH.exists():
            with open(PROFILE_PATH) as f:
                return json.load(f)
        return {}

    def _sync_profile_to_mcp(self):
        """Push flat profile fields to MCP semantic memory."""
        if not self._mcp:
            return
        profile = self._load_profile()
        if profile:
            count = self._mcp.sync_profile_facts(profile)
            self.logger.info(f"Synced {count} profile facts to MCP memory")
            audit(f"[context-manager] mcp_sync: synced {count} profile facts")

    def get_context(self) -> dict:
        """Return full user context. Cached for CACHE_TTL_SECONDS."""
        now = time.monotonic()
        if now - self._cache_time < CACHE_TTL_SECONDS and self._cache:
            return self._cache

        profile = self._load_profile()
        habits  = db.query("self", "SELECT * FROM habits WHERE status='active'")
        needs   = db.query("self", "SELECT * FROM needs WHERE status='active'")
        recent  = db.get_recent_interactions(10)

        # Enrich context with MCP semantic memory snapshot
        mcp_facts: dict = {}
        if self._mcp:
            try:
                mcp_facts = self._mcp.get_context_snapshot(prefix="user.")
            except Exception as e:
                self.logger.warning(f"MCP context snapshot failed: {e}")

        self._cache = {
            "profile": profile,
            "habits":  habits,
            "needs":   needs,
            "recent_interactions": recent,
            "mcp_facts": mcp_facts,
            "generated_at": datetime.now().isoformat(),
        }
        self._cache_time = now
        return self._cache

    def invalidate_cache(self):
        self._cache = {}
        self._cache_time = 0

    # ── router ────────────────────────────────────────────────────────────

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
            if not self._mcp:
                return self._error("MCP memory not available")
            key   = payload.get("key", "")
            value = payload.get("value", "")
            conf  = float(payload.get("confidence", 0.8))
            cat   = payload.get("category")
            ok    = self._mcp.add_fact(key, value, conf, cat)
            return self._ok({"stored": ok}) if ok else self._error("MCP add_fact failed")

        if cmd == "add_lesson":
            if not self._mcp:
                return self._error("MCP memory not available")
            text     = payload.get("text", "")
            negative = bool(payload.get("negative", False))
            cat      = payload.get("category")
            ok       = self._mcp.add_lesson(text, negative, cat)
            return self._ok({"stored": ok}) if ok else self._error("MCP add_lesson failed")

        if cmd == "list_facts":
            if not self._mcp:
                return self._error("MCP memory not available")
            prefix = payload.get("prefix")
            facts  = self._mcp.list_facts(prefix=prefix)
            return self._ok({"facts": facts, "count": len(facts)})

        if cmd == "list_lessons":
            if not self._mcp:
                return self._error("MCP memory not available")
            cat  = payload.get("category")
            neg  = payload.get("negative_only", False)
            lessons = self._mcp.list_lessons(category=cat, negative_only=neg)
            return self._ok({"lessons": lessons, "count": len(lessons)})

        if cmd == "mcp_stats":
            if not self._mcp:
                return self._error("MCP memory not available")
            return self._ok(self._mcp.get_stats())

        if cmd == "sync_profile":
            self._sync_profile_to_mcp()
            return self._ok({"message": "Profile synced to MCP memory"})

        return self._unknown(cmd)

