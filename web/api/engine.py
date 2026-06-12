"""Engine API — proxy endpoints to the running daemon."""
import json
import urllib.request
from flask import Blueprint, jsonify, request
from web.config import DAEMON_BASE

engine_bp = Blueprint("engine", __name__)


def _proxy_to_daemon(method, args=None, kwargs=None):
    """Proxy a call to the engine daemon."""
    payload = json.dumps({
        "method": method,
        "args": args or [],
        "kwargs": kwargs or {},
    }).encode()
    req = urllib.request.Request(
        f"{DAEMON_BASE}/engine",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    resp = urllib.request.urlopen(req, timeout=15)
    return resp.json()


@engine_bp.route("/health")
def daemon_health():
    """Get daemon health status."""
    try:
        resp = urllib.request.urlopen(f"{DAEMON_BASE}/health", timeout=3)
        return jsonify(resp.json())
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 503


@engine_bp.route("/digest")
def daily_digest():
    """Get today's daily digest."""
    try:
        result = _proxy_to_daemon("daily_digest")
        return jsonify({"digest": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 503


@engine_bp.route("/reminders")
def reminders():
    """Get reminders snapshot."""
    try:
        result = _proxy_to_daemon("reminders_snapshot")
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 503


@engine_bp.route("/context")
def context():
    """Get engine context (profile, memory, etc.)."""
    try:
        result = _proxy_to_daemon("get_context")
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 503


@engine_bp.route("/execute", methods=["POST"])
def execute_agent_command():
    """Execute an agent command via the daemon.

    POST body: {"agent": "task-coordinator", "command": "get_today", "data": {}}
    """
    data = request.get_json()
    if not data or "agent" not in data or "command" not in data:
        return jsonify({"error": "Missing agent or command"}), 400

    try:
        resp = urllib.request.Request(
            f"{DAEMON_BASE}/execute",
            data=json.dumps(data).encode(),
            headers={"Content-Type": "application/json"},
        )
        result = urllib.request.urlopen(resp, timeout=15)
        return jsonify(result.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 503
