"""
MCP Agent — Routes tool calls to external MCP servers.

Provides a unified interface for the engine and LLM to interact with
external MCP servers (mail, calendar, WhatsApp, etc.) without needing
to know their transport or protocol details.

Registered commands:
  mcp_status     — List all configured servers and their connectivity
  mcp_tools      — List all available tools from connected servers
  mcp_call       — Call a specific tool on a specific server
  mcp_discover   — Re-discover tools from all enabled servers
"""
import json
import os
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.base_agent import BaseAgent
from log_manager import audit
import mcp_tools.base_client as mcp


def _load_configs() -> list[dict]:
    registry_path = Path(__file__).parent.parent / "mcp_tools" / "registry.json"
    return mcp.load_registry(str(registry_path))


class MCPAgent(BaseAgent):
    """Routes tool calls to registered external MCP servers."""

    def __init__(self):
        super().__init__("mcp-agent")
        self._configs: list[dict] = []
        self._clients: dict[str, any] = {}
        self._tool_index: dict[str, tuple[str, any]] = {}  # tool_name → (server_id, tool_def)

    def initialize(self) -> bool:
        self._configs = _load_configs()
        # Connect to enabled servers
        connected = 0
        for cfg in self._configs:
            if not cfg.get("enabled", False):
                continue
            client = mcp.MCPClient.from_config(cfg)
            ok = client.connect()
            if ok:
                self._clients[cfg["id"]] = client
                connected += 1
                self.logger.info("Connected to MCP server: %s", cfg["id"])
            else:
                self.logger.warning("Failed to connect to MCP server: %s", cfg["id"])
        self._rebuild_tool_index()
        self.state = "ready"
        self.logger.info(
            "MCP Agent ready — %d servers (%d connected), %d tools indexed",
            len(self._configs), connected, len(self._tool_index),
        )
        return True

    def shutdown(self):
        for sid, client in self._clients.items():
            try:
                client.close()
                self.logger.info("Disconnected MCP server: %s", sid)
            except Exception as e:
                self.logger.warning("Error disconnecting %s: %s", sid, e)
        self._clients.clear()
        self._tool_index.clear()
        super().shutdown()

    # ── tool index ──────────────────────────────────────────────────────────

    def _rebuild_tool_index(self):
        self._tool_index.clear()
        for sid, client in self._clients.items():
            try:
                tools = client.list_tools()
                for tool in tools:
                    self._tool_index[tool.name] = (sid, tool)
            except Exception as e:
                self.logger.warning("Failed to list tools from %s: %s", sid, e)

    def list_connected_servers(self) -> list[dict]:
        return [
            {
                "id": cfg["id"],
                "name": cfg.get("name", cfg["id"]),
                "description": cfg.get("description", ""),
                "connected": cfg["id"] in self._clients,
                "transport": cfg.get("transport", "stdio"),
                "tools_count": len([t for t in self._tool_index.values() if t[0] == cfg["id"]]),
            }
            for cfg in self._configs
        ]

    def list_available_tools(self) -> list[dict]:
        return [
            {
                "server_id": sid,
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema,
            }
            for sid, tool in self._tool_index.values()
        ]

    def call_tool(self, server_id: str, tool_name: str, arguments: dict = None) -> dict:
        client = self._clients.get(server_id)
        if not client:
            return {"status": "error", "error": f"MCP server not connected: {server_id}"}
        result = client.call_tool(tool_name, arguments or {})
        audit(f"MCP_TOOL_CALL server={server_id} tool={tool_name} success={result.success}")
        content_texts = [
            c.get("text", json.dumps(c)) for c in result.content
            if c.get("type") in ("text", "resource")
        ]
        return {
            "status": "success" if result.success else "error",
            "error": result.error,
            "tool": tool_name,
            "server": server_id,
            "content": content_texts,
            "raw": result.content,
        }

    def discover_tools(self) -> dict:
        """Reconnect to all enabled servers and re-index tools."""
        for cfg in self._configs:
            if not cfg.get("enabled", False):
                continue
            if cfg["id"] in self._clients:
                self._clients[cfg["id"]].close()
            client = mcp.MCPClient.from_config(cfg)
            ok = client.connect()
            if ok:
                self._clients[cfg["id"]] = client
            else:
                self._clients.pop(cfg["id"], None)
        self._rebuild_tool_index()
        tools_by_server = {}
        for sid, tool in self._tool_index.values():
            tools_by_server.setdefault(sid, []).append(tool.name)
        return {
            "servers_connected": len(self._clients),
            "tools_total": len(self._tool_index),
            "tools_by_server": tools_by_server,
        }

    # ── router ──────────────────────────────────────────────────────────────

    def process(self, message: dict) -> dict:
        cmd = message.get("payload", {}).get("command", "")
        data = message.get("payload", {}).get("data", {})

        if cmd == "mcp_status":
            return self._ok({
                "servers": self.list_connected_servers(),
                "tools_total": len(self._tool_index),
            })

        if cmd == "mcp_tools":
            return self._ok({
                "tools": self.list_available_tools(),
                "total": len(self._tool_index),
            })

        if cmd == "mcp_call":
            server_id = data.get("server_id")
            tool_name = data.get("tool_name")
            args = data.get("arguments", {})
            if not server_id or not tool_name:
                return self._error("Required: server_id and tool_name")
            return self.call_tool(server_id, tool_name, args)

        if cmd == "mcp_discover":
            result = self.discover_tools()
            return self._ok(result)

        return self._unknown(cmd)
