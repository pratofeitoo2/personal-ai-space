"""Automations API — status and control for automation rules."""
import json
import urllib.request
from pathlib import Path
from flask import Blueprint, jsonify, request
from web.config import DAEMON_BASE, ENGINE_DIR

automations_bp = Blueprint("automations", __name__)

STATE_FILE = Path.home() / ".local" / "share" / "personal-ai-space" / "automation_state.json"


@automations_bp.route("/status")
def automation_status():
    """Get automation runner status."""
    try:
        result = json.loads(urllib.request.urlopen(
            f"{DAEMON_BASE}/engine", timeout=5,
            data=json.dumps({"method": "scheduler_status", "args": [], "kwargs": {}}).encode(),
            headers={"Content-Type": "application/json"},
        ).read())
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 503


@automations_bp.route("/rules")
def list_rules():
    """List automation rules from YAML config."""
    import yaml
    config_path = ENGINE_DIR / "config" / "automations.yaml"
    if not config_path.exists():
        return jsonify({"error": "automations.yaml not found"}), 404
    with open(config_path) as f:
        config = yaml.safe_load(f)
    return jsonify(config)


@automations_bp.route("/state")
def automation_state():
    """Get last automation run state."""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return jsonify(json.load(f))
    return jsonify({"last_runs": {}})


@automations_bp.route("/trigger", methods=["POST"])
def trigger_automation():
    """Manually trigger an automation rule."""
    data = request.get_json()
    rule_id = data.get("rule_id")
    if not rule_id:
        return jsonify({"error": "Missing rule_id"}), 400

    try:
        resp = urllib.request.Request(
            f"{DAEMON_BASE}/execute",
            data=json.dumps({
                "agent": "automation-runner",
                "command": "run_rule",
                "data": {"rule_id": rule_id}
            }).encode(),
            headers={"Content-Type": "application/json"},
        )
        result = urllib.request.urlopen(resp, timeout=30)
        return jsonify(result.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 503
