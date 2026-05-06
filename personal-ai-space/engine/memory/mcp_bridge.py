"""
mcp_bridge.py — Python ↔ MCP memory server bridge

Wraps the Node.js pi-memory MemoryStore via a headless JSON CLI script
(`engine/memory/mcp-server/headless.js`).

All calls spawn a short-lived `node headless.js <op> [args]` subprocess
and parse the JSON response. No persistent Node.js process required.

Usage:
    bridge = MCPMemoryBridge()
    bridge.add_fact("user.language", "Portuguese", confidence=0.95)
    bridge.add_fact("user.timezone", "America/Sao_Paulo")
    facts = bridge.list_facts(prefix="user.")
    bridge.add_lesson("Always confirm before deleting tasks")
    stats = bridge.get_stats()
"""

import json
import subprocess
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("engine.memory.mcp_bridge")

MCP_SERVER_DIR = Path(__file__).parent / "mcp-server"
HEADLESS_SCRIPT = MCP_SERVER_DIR / "headless.js"
NODE = "node"


def _run(op: str, *args: str, timeout: int = 8) -> dict:
    """Execute headless.js <op> [args...] and return parsed JSON."""
    cmd = [NODE, str(HEADLESS_SCRIPT), op, *[str(a) for a in args]]
    try:
        result = subprocess.run(
            cmd,
            cwd=MCP_SERVER_DIR,
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**__import__("os").environ, "NODE_NO_WARNINGS": "1"},
        )
        raw = result.stdout.strip()
        if not raw:
            err = result.stderr.strip()
            return {"ok": False, "error": err or "no output"}
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"ok": result.returncode == 0, "output": raw}
    except subprocess.TimeoutExpired:
        logger.error("MCP bridge timeout: %s %s", op, args)
        return {"ok": False, "error": "timeout"}
    except Exception as exc:
        logger.error("MCP bridge error: %s %s — %s", op, args, exc)
        return {"ok": False, "error": str(exc)}


class MCPMemoryBridge:
    """
    High-level interface to the pi-memory MemoryStore via headless.js.

    Methods:
      add_fact / get_fact / list_facts / delete_fact
      add_lesson / list_lessons / delete_lesson
      get_stats / health_check
    """

    def __init__(self):
        if not MCP_SERVER_DIR.exists():
            raise RuntimeError(f"MCP server directory not found: {MCP_SERVER_DIR}")
        if not HEADLESS_SCRIPT.exists():
            raise RuntimeError(f"headless.js not found: {HEADLESS_SCRIPT}")
        if not (MCP_SERVER_DIR / "dist").exists():
            raise RuntimeError(
                "MCP server not built. Run: "
                f"cd {MCP_SERVER_DIR} && npm install && npm run build"
            )
        logger.info("MCPMemoryBridge initialized (server: %s)", MCP_SERVER_DIR)

    # ── Semantic facts ────────────────────────────────────────────────────────

    def add_fact(
        self,
        key: str,
        value: str,
        confidence: float = 0.8,
        category: Optional[str] = None,
        source: str = "engine",
    ) -> bool:
        result = _run("add-fact", key, value, str(confidence), category or "", source)
        ok = result.get("ok", False)
        if ok:
            logger.debug("MCP fact added: %s = %s", key, value[:60])
        else:
            logger.warning("MCP add_fact failed: %s", result)
        return ok

    def get_fact(self, key: str) -> Optional[dict]:
        result = _run("get-fact", key)
        if result.get("ok") and result.get("found") is not False:
            return result
        return None

    def list_facts(
        self,
        prefix: Optional[str] = None,
        limit: int = 100,
        order_by: str = "updated",
    ) -> list[dict]:
        result = _run("list-facts", prefix or "", str(limit), order_by)
        return result.get("facts", [])

    def delete_fact(self, key: str) -> bool:
        result = _run("delete-fact", key)
        return result.get("deleted", False)

    # ── Lessons ───────────────────────────────────────────────────────────────

    def add_lesson(
        self,
        text: str,
        negative: bool = False,
        category: Optional[str] = None,
        source: str = "engine",
    ) -> bool:
        result = _run("add-lesson", text, "1" if negative else "0", category or "", source)
        ok = result.get("ok", False)
        if ok:
            logger.debug("MCP lesson added: %s", text[:80])
        else:
            logger.warning("MCP add_lesson failed: %s", result)
        return ok

    def list_lessons(
        self,
        category: Optional[str] = None,
        negative_only: bool = False,
        limit: int = 100,
    ) -> list[dict]:
        neg = "1" if negative_only else ""
        result = _run("list-lessons", category or "", neg, str(limit))
        return result.get("lessons", [])

    def delete_lesson(self, lesson_id: str) -> bool:
        result = _run("delete-lesson", lesson_id)
        return result.get("deleted", False)

    # ── Stats & health ────────────────────────────────────────────────────────

    def get_stats(self) -> dict:
        result = _run("stats")
        return result

    def health_check(self) -> bool:
        result = _run("stats", timeout=5)
        ok = result.get("ok", False)
        if not ok:
            logger.warning("MCP health check failed: %s", result)
        return ok

    # ── Context helpers ───────────────────────────────────────────────────────

    def sync_profile_facts(self, profile: dict) -> int:
        """Push flat profile dict as semantic facts under 'user.' namespace."""
        count = 0
        for key, value in profile.items():
            if value is None:
                continue
            mcp_key = f"user.{key}" if not key.startswith("user.") else key
            if self.add_fact(mcp_key, str(value), confidence=0.9, category="profile", source="system"):
                count += 1
        logger.info("Synced %d profile facts to MCP memory", count)
        return count

    def get_context_snapshot(self, prefix: str = "user.") -> dict[str, str]:
        """Return flat dict of facts under prefix — for agent prompt injection."""
        facts = self.list_facts(prefix=prefix, limit=200)
        return {
            f["key"]: f["value"]
            for f in facts
            if isinstance(f, dict) and "key" in f and "value" in f
        }

