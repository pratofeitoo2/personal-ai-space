"""
FallbackMemoryBridge — Resilient MCP memory layer with automatic failover.

Tries the Node.js pi-memory MCP server first; falls back to SQLite via DataHub
if the MCP server is unavailable. On MCP recovery, syncs queued fallback data.

Usage:
    bridge = FallbackMemoryBridge()
    bridge.add_fact("user.language", "Portuguese")   # tries MCP → falls back to SQLite
    facts = bridge.list_facts(prefix="user.")
    stats = bridge.get_stats()
"""
from __future__ import annotations

import json
import logging
from typing import Any, Optional

from memory.mcp_bridge import MCPMemoryBridge
from transport.data_hub import DataHub

logger = logging.getLogger("engine.memory.fallback_bridge")


class FallbackMemoryBridge:
    """
    Dual-path memory bridge with automatic failover.

    Primary: Node.js pi-memory MCP server (MCPMemoryBridge)
    Fallback: SQLite via DataHub (agent_memory table)

    All public methods match MCPMemoryBridge's API exactly for drop-in replacement.
    """

    def __init__(self):
        self._hub = DataHub()
        self._mcp: Optional[MCPMemoryBridge] = None
        self._mcp_available = False
        self._fallback_queue: list[dict] = []
        self._init_mcp()

    def _init_mcp(self):
        """Attempt to initialize MCP bridge — non-fatal if it fails."""
        try:
            self._mcp = MCPMemoryBridge()
            if self._mcp.health_check():
                self._mcp_available = True
                logger.info("FallbackMemoryBridge: MCP primary available")
            else:
                logger.warning("FallbackMemoryBridge: MCP health check failed, using fallback")
                self._mcp = None
        except Exception as e:
            logger.warning("FallbackMemoryBridge: MCP init failed (%s), using SQLite fallback", e)
            self._mcp = None

    def health_check(self) -> bool:
        """Check if MCP primary is available; auto-recover if possible."""
        if self._mcp:
            try:
                ok = self._mcp.health_check()
                if ok:
                    if not self._mcp_available:
                        logger.info("FallbackMemoryBridge: MCP recovered — syncing fallback queue")
                        self._mcp_available = True
                        self._sync_fallback_queue()
                    return True
                else:
                    self._mcp_available = False
                    return False
            except Exception:
                self._mcp_available = False
                return False
        return False

    def _sync_fallback_queue(self):
        """Push queued fallback data to MCP now that it's available."""
        if not self._mcp or not self._mcp_available:
            return
        queued = list(self._fallback_queue)
        self._fallback_queue.clear()
        for item in queued:
            op = item.get("op")
            try:
                if op == "add_fact":
                    self._mcp.add_fact(
                        item["key"], item["value"],
                        item.get("confidence", 0.8),
                        item.get("category"),
                    )
                elif op == "add_lesson":
                    self._mcp.add_lesson(
                        item["text"],
                        item.get("negative", False),
                        item.get("category"),
                    )
            except Exception as e:
                logger.warning("Fallback sync failed for %s: %s", op, e)
        logger.info("FallbackMemoryBridge: synced %d queued items to MCP", len(queued))

    def _is_fallback(self) -> bool:
        """Return True if we should use SQLite fallback."""
        return not self._mcp_available or self._mcp is None

    # ── Semantic facts ────────────────────────────────────────────────────

    def add_fact(
        self,
        key: str,
        value: str,
        confidence: float = 0.8,
        category: Optional[str] = None,
        source: str = "engine",
    ) -> bool:
        if not self._is_fallback():
            try:
                ok = self._mcp.add_fact(key, value, confidence, category, source)
                if ok:
                    return True
                self._mcp_available = False
            except Exception:
                self._mcp_available = False

        # Fallback to SQLite
        try:
            fact_key = f"mcp_fallback.{key}"
            fact_value = json.dumps({"value": value, "confidence": confidence, "category": category})
            self._hub.store_agent_memory("mcp_fallback", fact_key, fact_value)
            self._fallback_queue.append({
                "op": "add_fact", "key": key, "value": value,
                "confidence": confidence, "category": category,
            })
            logger.debug("Fallback: stored fact %s via DataHub", key)
            return True
        except Exception as e:
            logger.error("Fallback add_fact failed: %s", e)
            return False

    def get_fact(self, key: str) -> Optional[dict]:
        if not self._is_fallback():
            try:
                result = self._mcp.get_fact(key)
                if result is not None:
                    return result
            except Exception:
                logger.debug("MCP get_fact unavailable, using fallback")

        # Fallback: look up in agent_memory
        try:
            rows = self._hub.get_agent_memory("mcp_fallback", f"mcp_fallback.{key}")
            if rows:
                data = json.loads(rows[0]["value"])
                return {
                    "key": key,
                    "value": data.get("value", ""),
                    "confidence": data.get("confidence", 0.8),
                    "category": data.get("category"),
                }
        except Exception:
            logger.debug("Fallback get_fact lookup failed")
        return None

    def list_facts(
        self,
        prefix: Optional[str] = None,
        limit: int = 100,
        order_by: str = "updated",
    ) -> list[dict]:
        if not self._is_fallback():
            try:
                result = self._mcp.list_facts(prefix, limit, order_by)
                if result:
                    return result
            except Exception:
                logger.debug("MCP list_facts unavailable, using fallback")

        # Fallback
        try:
            search_prefix = f"mcp_fallback.{prefix}" if prefix else "mcp_fallback."
            rows = self._hub.get_agent_memory("mcp_fallback")
            results = []
            for row in rows:
                agent_key = row.get("key", "")
                if agent_key.startswith(search_prefix):
                    fact_key = agent_key.replace("mcp_fallback.", "", 1)
                    try:
                        data = json.loads(row.get("value", "{}"))
                        results.append({
                            "key": fact_key,
                            "value": data.get("value", ""),
                            "confidence": data.get("confidence", 0.8),
                            "category": data.get("category"),
                        })
                    except Exception:
                        logger.debug("Failed to parse fallback fact JSON")
            return results[:limit]
        except Exception as e:
            logger.error("Fallback list_facts failed: %s", e)
            return []

    def delete_fact(self, key: str) -> bool:
        if not self._is_fallback():
            try:
                return self._mcp.delete_fact(key)
            except Exception:
                logger.debug("MCP delete_fact unavailable, skipping")
        return False

    # ── Lessons ───────────────────────────────────────────────────────────

    def add_lesson(
        self,
        text: str,
        negative: bool = False,
        category: Optional[str] = None,
        source: str = "engine",
    ) -> bool:
        if not self._is_fallback():
            try:
                ok = self._mcp.add_lesson(text, negative, category, source)
                if ok:
                    return True
                self._mcp_available = False
            except Exception:
                self._mcp_available = False

        # Fallback to SQLite
        try:
            lesson_key = f"mcp_fallback.lesson.{category or 'general'}"
            self._hub.store_agent_memory("mcp_fallback", lesson_key, text)
            self._fallback_queue.append({
                "op": "add_lesson", "text": text,
                "negative": negative, "category": category,
            })
            logger.debug("Fallback: stored lesson via DataHub")
            return True
        except Exception as e:
            logger.error("Fallback add_lesson failed: %s", e)
            return False

    def list_lessons(
        self,
        category: Optional[str] = None,
        negative_only: bool = False,
        limit: int = 100,
    ) -> list[dict]:
        if not self._is_fallback():
            try:
                result = self._mcp.list_lessons(category, negative_only, limit)
                if result:
                    return result
            except Exception:
                logger.debug("MCP list_lessons unavailable, using fallback")
        return []

    def delete_lesson(self, lesson_id: str) -> bool:
        if not self._is_fallback():
            try:
                return self._mcp.delete_lesson(lesson_id)
            except Exception:
                logger.debug("MCP delete_lesson unavailable, skipping")
        return False

    # ── Stats & context helpers ───────────────────────────────────────────

    def get_stats(self) -> dict:
        if not self._is_fallback():
            try:
                return self._mcp.get_stats()
            except Exception:
                logger.debug("MCP get_stats unavailable, returning fallback stats")
        return {"ok": True, "mode": "fallback", "queue_size": len(self._fallback_queue)}

    def sync_profile_facts(self, profile: dict) -> int:
        """Push flat profile dict as semantic facts. Tries MCP, falls back."""
        count = 0
        for key, value in profile.items():
            if value is None:
                continue
            mcp_key = f"user.{key}" if not key.startswith("user.") else key
            if self.add_fact(mcp_key, str(value), confidence=0.9, category="profile", source="system"):
                count += 1
        logger.info("Synced %d profile facts (%s)", count, "MCP" if not self._is_fallback() else "fallback")
        return count

    def get_context_snapshot(self, prefix: str = "user.") -> dict[str, str]:
        """Return flat dict of facts under prefix."""
        facts = self.list_facts(prefix=prefix, limit=200)
        return {
            f["key"]: f["value"]
            for f in facts
            if isinstance(f, dict) and "key" in f and "value" in f
        }
