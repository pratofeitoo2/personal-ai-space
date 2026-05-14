"""
MCP Client — Communicate with external MCP servers via JSON-RPC 2.0.

Two transports:
  - stdio: spawn subprocess, send/receive JSON-RPC with Content-Length headers
  - http:  POST JSON-RPC to a remote endpoint

Usage:
    client = MCPClient.from_config({
        "id": "mail",
        "transport": "stdio",
        "command": "python3",
        "args": ["-m", "mail_mcp"],
    })
    tools = client.list_tools()
    result = client.call_tool("send_email", {"to": "maria@..."})
    client.close()
"""
import json
import json5
import logging
import os
import subprocess
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Optional

import requests

logger = logging.getLogger("engine.mcp_tools.client")

REQUEST_ID = 0


def _next_id() -> int:
    global REQUEST_ID
    REQUEST_ID += 1
    return REQUEST_ID


# ── Data types ──────────────────────────────────────────────────────────────

@dataclass
class MCPTool:
    name: str
    description: str = ""
    input_schema: dict = field(default_factory=dict)


@dataclass
class MCPResult:
    success: bool
    content: list[dict] = field(default_factory=list)
    error: str = ""


# ── JSON-RPC helpers ────────────────────────────────────────────────────────

def _make_request(method: str, params: dict = None) -> str:
    return json.dumps({
        "jsonrpc": "2.0",
        "id": _next_id(),
        "method": method,
        "params": params or {},
    })


def _parse_response(raw: str) -> dict:
    data = json.loads(raw)
    if "error" in data and data["error"]:
        raise RuntimeError(data["error"].get("message", str(data["error"])))
    return data.get("result", data)


# ── Content-Length framing (MCP stdio protocol) ────────────────────────────

def _encode_message(body: str) -> bytes:
    encoded = body.encode("utf-8")
    return f"Content-Length: {len(encoded)}\r\nContent-Type: application/json\r\n\r\n".encode() + encoded


def _decode_message(stream) -> Optional[str]:
    """Read one message from a binary stream.

    Handles two formats:
      1. Content-Length framing (MCP standard):
           Content-Length: N\r\n\r\n{body}
      2. JSON-line format (used by FastMCP servers):
           {json}\n

    Detects format by peeking at the first byte.
    """
    first_byte = stream.read(1)
    if not first_byte:
        return None

    # Peek: if it starts with '{', it's JSON-line format
    if first_byte == b'{':
        rest = stream.readline()
        raw = first_byte + rest
        return raw.decode("utf-8").strip()

    # Content-Length framing
    headers = {}
    line = first_byte + stream.readline()
    while line:
        line = line.strip()
        if isinstance(line, bytes):
            line = line.decode("utf-8")
        if not line:
            break
        if ":" in line:
            key, val = line.split(":", 1)
            headers[key.strip().lower()] = val.strip()
        line = stream.readline()
    length = int(headers.get("content-length", 0))
    if length == 0:
        return None
    body = stream.read(length)
    if isinstance(body, bytes):
        body = body.decode("utf-8")
    return body


# ── Clients ─────────────────────────────────────────────────────────────────

class StdioMCPClient:
    """MCP client over stdio transport. Spawns a subprocess."""

    def __init__(self, config: dict):
        self._config = config
        self._proc: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()
        self._tools_cache: Optional[list[MCPTool]] = None

    def connect(self) -> bool:
        if self._proc and self._proc.poll() is None:
            return True  # already running
        env = {**os.environ, **self._config.get("env", {})}
        try:
            self._proc = subprocess.Popen(
                [self._config["command"]] + self._config.get("args", []),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                text=False,
            )
            # Send initialize request
            self._send("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "personal-ai-engine", "version": "0.1.0"},
            })
            resp = self._recv()
            logger.info("MCP stdio client connected: %s", self._config["id"])
            return True
        except Exception as e:
            logger.error("MCP stdio connect failed [%s]: %s", self._config["id"], e)
            return False

    def _send(self, method: str, params: dict = None):
        if not self._proc or self._proc.stdin is None:
            raise RuntimeError("Not connected")
        raw = _make_request(method, params)
        # FastMCP servers read stdin as JSON-line format.
        # Send raw JSON with newline — the standard Content-Length
        # framing confuses their parser.
        self._proc.stdin.write((raw + "\n").encode())
        self._proc.stdin.flush()

    def _recv(self) -> dict:
        """Read the next JSON-RPC response, skipping notifications.

        MCP servers may emit notifications (no "id" field) before or
        between responses. This method reads messages until it finds
        one with an "id" field (the actual response).
        """
        if not self._proc or self._proc.stdout is None:
            raise RuntimeError("Not connected")
        for _ in range(50):  # safety limit
            raw = _decode_message(self._proc.stdout)
            if raw is None:
                stderr = self._proc.stderr.read().decode() if self._proc.stderr else ""
                raise RuntimeError(f"No response from MCP server. Stderr: {stderr[:200]}")
            data = json.loads(raw)
            if "id" in data:
                if "error" in data and data["error"]:
                    raise RuntimeError(data["error"].get("message", str(data["error"])))
                return data.get("result", data)
        raise RuntimeError("Exceeded notification skip limit (50)")

    def list_tools(self) -> list[MCPTool]:
        if self._tools_cache:
            return self._tools_cache
        with self._lock:
            self._send("tools/list")
            result = self._recv()
            tools = result.get("tools", [])
            self._tools_cache = [
                MCPTool(name=t["name"], description=t.get("description", ""),
                        input_schema=t.get("inputSchema", {}))
                for t in tools
            ]
            return self._tools_cache

    def call_tool(self, name: str, arguments: dict = None) -> MCPResult:
        with self._lock:
            try:
                self._send("tools/call", {"name": name, "arguments": arguments or {}})
                result = self._recv()
                content = result.get("content", [])
                is_error = result.get("isError", False)
                if is_error:
                    err_text = " ".join(
                        c.get("text", "") for c in content if c.get("type") == "text"
                    ) or "Tool returned error"
                    return MCPResult(success=False, content=content, error=err_text)
                return MCPResult(success=True, content=content)
            except Exception as e:
                logger.error("Tool call failed [%s.%s]: %s", self._config["id"], name, e)
                return MCPResult(success=False, error=str(e))

    def close(self):
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._proc.kill()
            logger.info("MCP stdio client closed: %s", self._config["id"])

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        self.close()


class HTTPMCPClient:
    """MCP client over HTTP POST transport."""

    def __init__(self, config: dict):
        self._config = config
        self._tools_cache: Optional[list[MCPTool]] = None
        self._session = requests.Session()
        # Set default headers
        headers = config.get("headers", {})
        # Resolve env vars in header values
        resolved = {}
        for k, v in headers.items():
            if isinstance(v, str) and "${" in v:
                import re
                for match in re.findall(r"\$\{([^}]+)\}", v):
                    v = v.replace(f"${{{match}}}", os.environ.get(match, ""))
            resolved[k] = v
        self._session.headers.update(resolved)

    def connect(self) -> bool:
        # HTTP is stateless — just check the URL is reachable
        try:
            r = self._session.get(self._config["url"].replace("/mcp", "/health"),
                                  timeout=5)
            return r.ok
        except (requests.ConnectionError, requests.Timeout):
            # No health endpoint; assume it might work
            logger.debug("HTTP MCP health check skipped for %s", self._config["id"])
            return True

    def _post(self, method: str, params: dict = None) -> dict:
        payload = json.loads(_make_request(method, params))
        r = self._session.post(
            self._config["url"],
            json=payload,
            timeout=self._config.get("timeout_seconds", 30),
        )
        r.raise_for_status()
        return _parse_response(r.text)

    def list_tools(self) -> list[MCPTool]:
        if self._tools_cache:
            return self._tools_cache
        result = self._post("tools/list")
        tools = result.get("tools", [])
        self._tools_cache = [
            MCPTool(name=t["name"], description=t.get("description", ""),
                    input_schema=t.get("inputSchema", {}))
            for t in tools
        ]
        return self._tools_cache

    def call_tool(self, name: str, arguments: dict = None) -> MCPResult:
        try:
            result = self._post("tools/call", {"name": name, "arguments": arguments or {}})
            content = result.get("content", [])
            is_error = result.get("isError", False)
            if is_error:
                err_text = " ".join(
                    c.get("text", "") for c in content if c.get("type") == "text"
                ) or "Tool returned error"
                return MCPResult(success=False, content=content, error=err_text)
            return MCPResult(success=True, content=content)
        except Exception as e:
            logger.error("HTTP tool call failed [%s.%s]: %s", self._config["id"], name, e)
            return MCPResult(success=False, error=str(e))

    def close(self):
        self._session.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


# ── Factory ─────────────────────────────────────────────────────────────────

class MCPClient:
    """Factory that returns the right client for a given config."""

    @staticmethod
    def from_config(config: dict):
        transport = config.get("transport", "stdio")
        if transport == "http":
            return HTTPMCPClient(config)
        return StdioMCPClient(config)


# ── Registry loader ─────────────────────────────────────────────────────────

def load_registry(path: str = None) -> list[dict]:
    """Load MCP server configurations from registry.json."""
    if path is None:
        path = os.path.join(os.path.dirname(__file__), "..", "config", "mcp_registry.json5")
    with open(path) as f:
        data = json5.load(f)
    return data.get("servers", [])


def discover_tools(configs: list[dict]) -> dict[str, list[MCPTool]]:
    """Connect to all enabled servers and discover their tools."""
    all_tools: dict[str, list[MCPTool]] = {}
    for cfg in configs:
        if not cfg.get("enabled", False):
            continue
        client = MCPClient.from_config(cfg)
        try:
            ok = client.connect()
            if ok:
                tools = client.list_tools()
                all_tools[cfg["id"]] = tools
                logger.info("Discovered %d tools from %s", len(tools), cfg["id"])
            else:
                logger.warning("Failed to connect to MCP server: %s", cfg["id"])
        except Exception as e:
            logger.warning("Error discovering tools from %s: %s", cfg["id"], e)
        finally:
            client.close()
    return all_tools
