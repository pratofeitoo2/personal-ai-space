#!/usr/bin/env python3
"""Bridge: stdio MCP ↔ TablePro Streamable HTTP MCP server."""
import json, os, sys, urllib.request, urllib.error

HANDSHAKE_PATH = os.path.expanduser(
    "~/Library/Application Support/TablePro/mcp-handshake.json"
)
MCP_PATH = "/mcp"


def get_server():
    if not os.path.exists(HANDSHAKE_PATH):
        print("Handshake file not found", file=sys.stderr)
        sys.exit(1)
    with open(HANDSHAKE_PATH) as f:
        h = json.load(f)
    proto = "https" if h.get("tls") else "http"
    return f"{proto}://127.0.0.1:{h['port']}{MCP_PATH}", h["token"]


url, token = get_server()
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {token}",
}

ctx = None
if url.startswith("https"):
    ctx = __import__("ssl").create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = __import__("ssl").CERT_NONE

session_id = None

for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    try:
        headers = dict(HEADERS)
        if session_id:
            headers["Mcp-Session-Id"] = session_id
        req = urllib.request.Request(
            url, data=line.encode(), headers=headers, method="POST"
        )
        resp = urllib.request.urlopen(req, timeout=10, context=ctx)
        body = resp.read().decode()
        if not session_id:
            sid = resp.headers.get("Mcp-Session-Id")
            if sid:
                session_id = sid
        if body.strip():
            print(body.strip(), flush=True)
    except urllib.error.HTTPError as e:
        err_body = e.read().decode() if e.fp else ""
        if err_body.strip():
            print(err_body.strip(), flush=True)
    except Exception as e:
        print(f'{{"jsonrpc":"2.0","error":{{"message":"{e}"}}}}', file=sys.stderr)
