"""Tests for automations/runner.py"""
import json
from datetime import datetime
from unittest.mock import Mock, patch, PropertyMock
import pytest

from automations.runner import AutomationRunner


SAMPLE_RULES = """
settings:
  whatsapp_recipient: "+5511999999999"
  timezone: "America/Sao_Paulo"

automations:
  - id: test_brief
    name: "Test"
    schedule: "07:00"
    sections:
      - {type: greeting}
      - {query: tasks_due_today, label: "📋 Test", empty_msg: ""}

  - id: test_alert
    name: "Test Alert"
    schedule: {type: interval, seconds: 60}
    state_track: true
    min_items: 1
    sections:
      - {query: overdue_tasks, label: "⚠️ Overdue", empty_msg: ""}
"""


@pytest.fixture
def runner(tmp_path):
    eng = Mock()
    eng._hub = Mock()
    cfg = tmp_path / "automations.yaml"
    cfg.write_text(SAMPLE_RULES)
    r = AutomationRunner.__new__(AutomationRunner)
    r._engine = eng
    r._rules = []
    r._state = {}
    r._settings = {}
    r._last_state_write = datetime.min
    r.STATE_FILE = tmp_path / "state.json"
    def noop_load(): pass
    r._load_rules = noop_load
    r._load_state = lambda: None
    return r


class TestIsDue:
    def test_daily_time_exact_match(self, runner):
        runner._rules = [{"schedule": "07:00"}]
        dt = datetime(2026, 5, 29, 7, 0, 0)
        assert runner._is_due(runner._rules[0], dt)

    def test_daily_time_wrong_hour(self, runner):
        runner._rules = [{"schedule": "07:00"}]
        dt = datetime(2026, 5, 29, 8, 0, 0)
        assert not runner._is_due(runner._rules[0], dt)

    def test_interval_within_window(self, runner):
        runner._rules = [{"schedule": {"type": "interval", "seconds": 60}}]
        dt = datetime(2026, 5, 29, 10, 0, 15)
        assert runner._is_due(runner._rules[0], dt)

    def test_interval_outside_window(self, runner):
        runner._rules = [{"schedule": {"type": "interval", "seconds": 60}}]
        dt = datetime(2026, 5, 29, 10, 0, 45)
        assert not runner._is_due(runner._rules[0], dt)


class TestStateChange:
    def test_detects_change(self, runner):
        runner._state["alert"] = {"fingerprint": json.dumps(["a"], sort_keys=True)}
        changed = runner._state_changed("alert", json.dumps(["b"], sort_keys=True))
        assert changed is True

    def test_no_change(self, runner):
        runner._state["alert"] = {"fingerprint": json.dumps(["a"], sort_keys=True)}
        changed = runner._state_changed("alert", json.dumps(["a"], sort_keys=True))
        assert changed is False

    def test_first_run_detects_change(self, runner):
        changed = runner._state_changed("new_alert", json.dumps(["a"], sort_keys=True))
        assert changed is True


class TestLoadRules:
    def test_parses_valid_yaml(self, tmp_path):
        cfg = tmp_path / "automations.yaml"
        cfg.write_text(SAMPLE_RULES)
        eng = Mock()
        r = AutomationRunner(eng)
        with patch("automations.runner.CONFIG_PATH", cfg), \
             patch("automations.runner.STATE_FILE", tmp_path / "state.json"):
            r._load_rules()
            assert len(r._rules) == 2
            assert r._settings["whatsapp_recipient"] == "+5511999999999"

    def test_no_file_doesnt_crash(self, tmp_path):
        eng = Mock()
        with patch("automations.runner.CONFIG_PATH", tmp_path / "nonexistent.yaml"), \
             patch("automations.runner.STATE_FILE", tmp_path / "state.json"):
            r = AutomationRunner(eng)
            assert r._rules == []


class TestStatePersistence:
    def test_saves_and_loads_state(self, tmp_path):
        sf = tmp_path / "state.json"
        eng = Mock()
        with patch("automations.runner.CONFIG_PATH", tmp_path / "nonexistent.yaml"), \
             patch("automations.runner.STATE_FILE", sf):
            r = AutomationRunner(eng)
            r._state = {"alert": {"fingerprint": "abc", "last_alerted": "2026-01-01"}}
            r._save_state()
        with patch("automations.runner.CONFIG_PATH", tmp_path / "nonexistent.yaml"), \
             patch("automations.runner.STATE_FILE", sf):
            r2 = AutomationRunner(eng)
            assert r2._state.get("alert", {}).get("fingerprint") == "abc"
