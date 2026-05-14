"""
SafeMCPTransport — Resilient MCP server communication layer.

Wraps mcp_tools.base_client with:
- Circuit breaker pattern (3 failures → open, cooldown → half-open)
- Exponential backoff retry
- Graceful fallback on failure
- Connection pooling
- Health monitoring

This directly addresses the 503 provider_overloaded error by isolating
MCP server failures from the rest of the agent system.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from mcp_tools.base_client import MCPClient, MCPTool, MCPResult

logger = logging.getLogger("engine.transport.mcp")


# ── Circuit Breaker States ────────────────────────────────────────────────────

class CircuitState(str, Enum):
    CLOSED = "closed"       # Normal operation, requests pass through
    OPEN = "open"           # Too many failures, requests blocked
    HALF_OPEN = "half_open" # Testing if server recovered


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 3        # Consecutive failures before opening
    cooldown_seconds: float = 30.0    # Time in OPEN before trying HALF_OPEN
    success_threshold: int = 1        # Successes in HALF_OPEN before closing
    half_open_max_requests: int = 1   # Max concurrent requests in HALF_OPEN


# ── Circuit Breaker ───────────────────────────────────────────────────────────

class CircuitBreaker:
    """
    Per-server circuit breaker that tracks failure/success state.

    State transitions:
    CLOSED --[failures >= threshold]--> OPEN
    OPEN --[cooldown elapsed]--> HALF_OPEN
    HALF_OPEN --[success >= threshold]--> CLOSED
    HALF_OPEN --[failure]--> OPEN
    """

    def __init__(self, config: Optional[CircuitBreakerConfig] = None):
        self._config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: float = 0
        self._half_open_requests = 0

    @property
    def state(self) -> CircuitState:
        """Current circuit state, auto-transitioning based on time."""
        if self._state == CircuitState.OPEN:
            if time.monotonic() - self._last_failure_time >= self._config.cooldown_seconds:
                logger.info("Circuit breaker transitioning OPEN → HALF_OPEN")
                self._state = CircuitState.HALF_OPEN
                self._success_count = 0
                self._half_open_requests = 0
        return self._state

    def allow_request(self) -> bool:
        """Check if a request should be allowed through."""
        current = self.state
        if current == CircuitState.CLOSED:
            return True
        if current == CircuitState.HALF_OPEN:
            if self._half_open_requests < self._config.half_open_max_requests:
                self._half_open_requests += 1
                return True
            return False
        return False  # OPEN state

    def record_success(self):
        """Record a successful request."""
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self._config.success_threshold:
                logger.info("Circuit breaker transitioning HALF_OPEN → CLOSED")
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                self._success_count = 0
        elif self._state == CircuitState.CLOSED:
            self._failure_count = 0  # Reset on success

    def record_failure(self):
        """Record a failed request."""
        self._failure_count += 1
        self._last_failure_time = time.monotonic()

        if self._state == CircuitState.HALF_OPEN:
            logger.warning("Circuit breaker HALF_OPEN → OPEN (test request failed)")
            self._state = CircuitState.OPEN
        elif self._failure_count >= self._config.failure_threshold:
            logger.warning(
                "Circuit breaker CLOSED → OPEN after %d consecutive failures",
                self._failure_count,
            )
            self._state = CircuitState.OPEN

    def reset(self):
        """Manually reset the circuit breaker to CLOSED."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = 0

    def stats(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "last_failure_ago_sec": round(time.monotonic() - self._last_failure_time, 1)
            if self._last_failure_time > 0 else None,
        }


# ── Retry Policy ──────────────────────────────────────────────────────────────

def _retry_delays(max_retries: int, base_delay: float = 1.0) -> list[float]:
    """Generate exponential backoff delays: 1s, 2s, 4s, 8s, ..."""
    delays = []
    for i in range(max_retries):
        delays.append(base_delay * (2 ** i))
    return delays


# ── Safe MCP Transport ────────────────────────────────────────────────────────

@dataclass
class MCPServerConfig:
    """Configuration for a single MCP server."""
    id: str
    name: str
    transport: str = "stdio"  # "stdio" or "http"
    command: Optional[str] = None
    args: list[str] = field(default_factory=list)
    url: Optional[str] = None
    headers: dict[str, str] = field(default_factory=dict)
    env: dict[str, str] = field(default_factory=dict)
    enabled: bool = True
    timeout_seconds: int = 30
    max_retries: int = 2
    health_check_interval: float = 60.0
    circuit_breaker: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)


class SafeMCPTransport:
    """
    Wraps an MCP client with circuit breaker, retry, and fallback logic.

    Usage:
        transport = SafeMCPTransport(server_config)
        result = transport.call_tool("list_messages", {"mailbox": "INBOX"})
    """

    def __init__(self, config: MCPServerConfig):
        self._config = config
        self._circuit_breaker = CircuitBreaker(config.circuit_breaker)
        self._client: Optional[MCPClient] = None
        self._last_health_check: float = 0
        self._tools_cache: list[MCPTool] = []
        self._tools_cache_time: float = 0

    # ── Connection Management ─────────────────────────────────────────────────

    def connect(self) -> bool:
        """Establish connection to the MCP server."""
        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass

        try:
            if self._config.transport == "http":
                from mcp_tools.base_client import HTTPMCPClient
                self._client = HTTPMCPClient({
                    "id": self._config.id,
                    "transport": "http",
                    "url": self._config.url,
                    "headers": self._config.headers,
                })
            else:
                from mcp_tools.base_client import StdioMCPClient
                self._client = StdioMCPClient({
                    "id": self._config.id,
                    "transport": "stdio",
                    "command": self._config.command,
                    "args": self._config.args,
                    "env": self._config.env,
                })

            ok = self._client.connect()
            if ok:
                self._circuit_breaker.reset()
                logger.info("Connected to MCP server: %s (%s)", self._config.id, self._config.name)
            else:
                self._circuit_breaker.record_failure()
            return ok
        except Exception as e:
            logger.error("Failed to connect to MCP server %s: %s", self._config.id, e)
            self._circuit_breaker.record_failure()
            return False

    def close(self):
        """Close the connection gracefully."""
        if self._client is not None:
            try:
                self._client.close()
            except Exception as e:
                logger.debug("Error closing MCP client %s: %s", self._config.id, e)
            self._client = None

    # ── Tool Discovery ────────────────────────────────────────────────────────

    def list_tools(self) -> list[MCPTool]:
        """List available tools, with caching."""
        cache_ttl = 300  # 5 minutes
        now = time.monotonic()

        if self._tools_cache and (now - self._tools_cache_time) < cache_ttl:
            return self._tools_cache

        try:
            result = self._safe_call("tools/list", {})
            if result and result.success:
                tools_data = result.content[0] if result.content else {}
                self._tools_cache = [
                    MCPTool(
                        name=t.get("name", ""),
                        description=t.get("description", ""),
                        input_schema=t.get("inputSchema", {}),
                    )
                    for t in tools_data.get("tools", [])
                ]
                self._tools_cache_time = now
                logger.info("Discovered %d tools on %s", len(self._tools_cache), self._config.id)
        except Exception as e:
            logger.warning("Tool discovery failed for %s: %s", self._config.id, e)

        return self._tools_cache

    # ── Tool Calling ──────────────────────────────────────────────────────────

    def call_tool(self, tool_name: str, arguments: dict[str, Any] | None = None) -> MCPResult:
        """
        Call a tool on the MCP server with retry and circuit breaker.

        Returns:
            MCPResult with success/error info. Never raises (graceful fallback).
        """
        # Check circuit breaker
        if not self._circuit_breaker.allow_request():
            logger.warning("Circuit breaker OPEN for %s, returning fallback", self._config.id)
            return MCPResult(
                success=False,
                error=f"Circuit breaker open for server {self._config.id}",
            )

        # Retry loop
        delays = _retry_delays(self._config.max_retries)
        last_error: str = ""

        for attempt, delay in enumerate([0] + delays):
            if attempt > 0:
                logger.info("Retry %d/%d for %s.%s after %.1fs",
                            attempt, self._config.max_retries,
                            self._config.id, tool_name, delay)
                time.sleep(delay)

            try:
                if self._client is None:
                    if not self.connect():
                        last_error = "Connection failed"
                        self._circuit_breaker.record_failure()
                        continue

                result = self._client.call_tool(tool_name, arguments or {})

                if result.success:
                    self._circuit_breaker.record_success()
                    return result
                else:
                    last_error = result.error or "Unknown error"
                    self._circuit_breaker.record_failure()

            except Exception as e:
                last_error = str(e)
                logger.error("Tool call failed [%s.%s]: %s",
                             self._config.id, tool_name, e)
                self._circuit_breaker.record_failure()

        # All retries exhausted — return graceful fallback
        logger.error("All retries exhausted for %s.%s: %s",
                     self._config.id, tool_name, last_error)
        return MCPResult(
            success=False,
            error=f"Server {self._config.id} unavailable: {last_error}",
        )

    def _safe_call(self, method: str, params: dict) -> MCPResult | None:
        """Internal safe call for discovery operations."""
        if self._client is None:
            if not self.connect():
                return None
        try:
            return self._client.call_tool(method, params)
        except Exception as e:
            logger.error("Safe call failed: %s", e)
            return None

    # ── Health ────────────────────────────────────────────────────────────────

    def health_check(self) -> bool:
        """Check if the server is responsive."""
        now = time.monotonic()
        if now - self._last_health_check < self._config.health_check_interval:
            return self._circuit_breaker.state != CircuitState.OPEN

        self._last_health_check = now
        try:
            if self._client is None:
                return self.connect()
            result = self._safe_call("tools/list", {})
            return result is not None and result.success
        except Exception:
            return False

    # ── Diagnostics ───────────────────────────────────────────────────────────

    def status(self) -> dict[str, Any]:
        """Return server status for diagnostics."""
        return {
            "id": self._config.id,
            "name": self._config.name,
            "transport": self._config.transport,
            "enabled": self._config.enabled,
            "connected": self._client is not None,
            "circuit_breaker": self._circuit_breaker.stats(),
            "tools_count": len(self._tools_cache),
        }


# ── Transport Manager ─────────────────────────────────────────────────────────

class MCPTransportManager:
    """
    Manages multiple MCP server transports.

    Loads configuration from registry.json and provides a unified
    interface for tool discovery and execution across all servers.
    """

    def __init__(self, registry_path: str | None = None):
        from pathlib import Path
        from transport.config import AppConfig

        config = AppConfig.instance()
        self._registry_path = Path(registry_path or config.mcp_registry_path)
        self._servers: dict[str, SafeMCPTransport] = {}
        self._tool_index: dict[str, tuple[str, MCPTool]] = {}  # tool_name → (server_id, tool)
        self._load_registry()

    def _load_registry(self):
        """Load server configurations from registry.json."""
        if not self._registry_path.exists():
            logger.warning("Registry file not found: %s", self._registry_path)
            return

        import json5
        with open(self._registry_path) as f:
            data = json5.load(f)

        for server_cfg in data.get("servers", []):
            cfg = MCPServerConfig(
                id=server_cfg["id"],
                name=server_cfg.get("name", server_cfg["id"]),
                transport=server_cfg.get("transport", "stdio"),
                command=server_cfg.get("command"),
                args=server_cfg.get("args", []),
                url=server_cfg.get("url"),
                headers=server_cfg.get("headers", {}),
                env=server_cfg.get("env", {}),
                enabled=server_cfg.get("enabled", False),
            )
            if cfg.enabled:
                transport = SafeMCPTransport(cfg)
                self._servers[cfg.id] = transport
                logger.info("Registered MCP server: %s (%s)", cfg.id, cfg.name)

    # ── Discovery ─────────────────────────────────────────────────────────────

    def discover_tools(self) -> dict[str, list[str]]:
        """
        Connect to all enabled servers and discover their tools.

        Returns:
            Dict mapping server_id to list of tool names.
        """
        self._tool_index.clear()
        tools_by_server: dict[str, list[str]] = {}

        for server_id, transport in self._servers.items():
            tools = transport.list_tools()
            tool_names = [t.name for t in tools]
            tools_by_server[server_id] = tool_names

            for tool in tools:
                self._tool_index[tool.name] = (server_id, tool)

            logger.info("Discovered %d tools on %s", len(tools), server_id)

        return tools_by_server

    # ── Tool Execution ────────────────────────────────────────────────────────

    def call_tool(self, server_id: str, tool_name: str,
                  arguments: dict[str, Any] | None = None) -> MCPResult:
        """
        Call a specific tool on a specific server.

        Args:
            server_id: The server identifier from registry.
            tool_name: The tool name (as returned by tools/list).
            arguments: Tool arguments.

        Returns:
            MCPResult with success/error info. Never raises.
        """
        transport = self._servers.get(server_id)
        if transport is None:
            return MCPResult(
                success=False,
                error=f"Unknown MCP server: {server_id}",
            )
        return transport.call_tool(tool_name, arguments)

    # ── Utilities ─────────────────────────────────────────────────────────────

    def list_servers(self) -> list[dict[str, Any]]:
        """List all configured servers with their status."""
        return [t.status() for t in self._servers.values()]

    def list_tools(self) -> list[dict[str, Any]]:
        """List all discovered tools across all servers."""
        return [
            {"server_id": sid, "name": tool.name, "description": tool.description}
            for sid, tool in self._tool_index.values()
        ]

    def shutdown(self):
        """Close all server connections."""
        for transport in self._servers.values():
            transport.close()
        self._servers.clear()
        self._tool_index.clear()