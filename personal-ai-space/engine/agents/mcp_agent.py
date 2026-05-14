"""
MCP Agent — Routes tool calls to external MCP servers.

Provides a unified interface for the engine and LLM to interact with
external MCP servers (mail, calendar, WhatsApp, etc.) without needing
to know their transport or protocol details.

Uses the SafeMCPTransport / MCPTransportManager for resilient communication
with circuit breaker, retry, and graceful fallback.

Registered commands:
  mcp_status     — List all configured servers and their connectivity
  mcp_tools      — List all available tools from connected servers
  mcp_call       — Call a specific tool on a specific server
  mcp_discover   — Re-discover tools from all enabled servers
"""
import json
from typing import Optional

from agents.base_agent import BaseAgent
from log_manager import audit
from transport.mcp_transport import MCPTransportManager


class MCPAgent(BaseAgent):
    """Routes tool calls to registered external MCP servers."""

    def __init__(self):
        super().__init__("mcp-agent")
        self._transport: Optional[MCPTransportManager] = None

    def initialize(self) -> bool:
        try:
            self._transport = MCPTransportManager()
            tools_by_server = self._transport.discover_tools()
            total_tools = sum(len(tools) for tools in tools_by_server.values())
            self.state = "ready"
            self.logger.info(
                "MCP Agent ready — %d servers, %d tools indexed",
                len(tools_by_server), total_tools,
            )
            return True
        except Exception as e:
            self.logger.error("MCP Agent init failed: %s", e)
            return False

    def shutdown(self):
        if self._transport:
            self._transport.shutdown()
        self._transport = None
        super().shutdown()

    # ── tool discovery ─────────────────────────────────────────────────

    def list_connected_servers(self) -> list[dict]:
        if not self._transport:
            return []
        return self._transport.list_servers()

    def list_available_tools(self) -> list[dict]:
        if not self._transport:
            return []
        return self._transport.list_tools()

    def call_tool(self, server_id: str, tool_name: str, arguments: dict = None) -> dict:
        if not self._transport:
            return {"status": "error", "error": "MCP transport not initialized"}
        result = self._transport.call_tool(server_id, tool_name, arguments or {})
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
        if not self._transport:
            return {"servers_connected": 0, "tools_total": 0, "tools_by_server": {}}
        tools_by_server = self._transport.discover_tools()
        total_tools = sum(len(tools) for tools in tools_by_server.values())
        return {
            "servers_connected": len(tools_by_server),
            "tools_total": total_tools,
            "tools_by_server": tools_by_server,
        }

    # ── router ─────────────────────────────────────────────────────────

    def process(self, message: dict) -> dict:
        cmd = message.get("payload", {}).get("command", "")
        data = message.get("payload", {}).get("data", {})

        if cmd == "mcp_status":
            return self._ok({
                "servers": self.list_connected_servers(),
                "tools_total": len(self.list_available_tools()),
            })

        if cmd == "mcp_tools":
            tools = self.list_available_tools()
            return self._ok({
                "tools": tools,
                "total": len(tools),
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
