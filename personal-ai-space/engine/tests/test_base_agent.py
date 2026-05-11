"""Tests for base agent message routing and lifecycle."""

import pytest


class TestBaseAgent:
    def make_agent(self):
        from agents.base_agent import BaseAgent
        from abc import ABC
        class TestAgent(BaseAgent):
            def process(self, message):
                cmd = message.get("payload", {}).get("command", "")
                if cmd == "ping":
                    return self._ok("pong")
                if cmd == "error":
                    raise ValueError("simulated error")
                return self._unknown(cmd)

        return TestAgent("test-agent")

    def test_initial_state(self):
        agent = self.make_agent()
        assert agent.id == "test-agent"
        assert agent.state == "idle"

    def test_initialize_sets_ready(self):
        agent = self.make_agent()
        assert agent.initialize() is True
        assert agent.state == "ready"

    def test_handle_known_command(self):
        agent = self.make_agent()
        agent.initialize()
        result = agent.handle({
            "id": "msg_1",
            "payload": {"command": "ping"},
        })
        assert result["status"] == "success"
        assert result["payload"] == "pong"

    def test_handle_unknown_command(self):
        agent = self.make_agent()
        agent.initialize()
        result = agent.handle({
            "id": "msg_2",
            "payload": {"command": "nonexistent"},
        })
        assert result["status"] == "error"
        assert "Unknown command" in result["error"]

    def test_handle_error_returns_error(self):
        agent = self.make_agent()
        agent.initialize()
        result = agent.handle({
            "id": "msg_3",
            "payload": {"command": "error"},
        })
        assert result["status"] == "error"
        assert "simulated error" in result["error"]

    def test_shutdown_sets_stopped(self):
        agent = self.make_agent()
        agent.initialize()
        agent.shutdown()
        assert agent.state == "stopped"

    def test_handle_sets_active_then_idle(self):
        agent = self.make_agent()
        agent.initialize()
        assert agent.state == "ready"
        agent.handle({"id": "x", "payload": {"command": "ping"}})
        assert agent.state == "idle"

    def test_ok_helper_returns_correct_format(self):
        agent = self.make_agent()
        result = agent._ok({"key": "value"})
        assert result["status"] == "success"
        assert result["payload"]["key"] == "value"

    def test_error_helper_returns_correct_format(self):
        agent = self.make_agent()
        result = agent._error("something broke")
        assert result["status"] == "error"
        assert result["error"] == "something broke"

    def test_observer_can_be_set(self):
        agent = self.make_agent()
        observer = object()
        agent.set_observer(observer)
        assert agent.observer is observer
