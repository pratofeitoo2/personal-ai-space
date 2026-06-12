"""Tests for the engine orchestrator."""

import pytest


class TestEngine:
    def test_create_engine(self):
        from engine import Engine
        eng = Engine()
        assert eng.VERSION == "0.1.0"
        assert eng._agents == {}

    def test_start_initializes_agents(self, init_test_db):
        from engine import Engine
        eng = Engine()
        ok = eng.start()
        assert ok is True
        assert len(eng._agents) >= 4

    def test_health_returns_expected_keys(self, init_test_db):
        from engine import Engine
        eng = Engine()
        eng.start()
        h = eng.health()
        assert h["version"] == "0.1.0"
        assert "uptime_seconds" in h
        assert len(h["agents"]) >= 4
        assert len(h["databases"]) >= 4

    def test_send_to_known_agent(self, init_test_db):
        from engine import Engine
        eng = Engine()
        eng.start()
        result = eng.send("knowledge-indexer", "stats")
        assert result["status"] == "success"
        payload = result.get("payload", {})
        assert "articles" in payload
        assert "notes" in payload

    def test_send_to_unknown_agent(self, init_test_db):
        from engine import Engine
        eng = Engine()
        eng.start()
        result = eng.send("ghost-agent", "ping")
        assert result["status"] == "error"
        assert "not found" in result["error"]

    def test_todays_tasks(self, init_test_db):
        from engine import Engine
        eng = Engine()
        eng.start()
        tasks = eng.todays_tasks()
        assert isinstance(tasks, list)

    def test_log_habit_unknown(self, init_test_db):
        from engine import Engine
        eng = Engine()
        eng.start()
        ok = eng.log_habit("nonexistent_habit")
        assert ok is False

    def test_add_note(self, init_test_db):
        from engine import Engine
        eng = Engine()
        eng.start()
        note_id = eng.add_note("Test Note", "Test content", "test", "general")
        assert note_id.startswith("note_")

    def test_stop_cleans_up(self, init_test_db):
        from engine import Engine
        eng = Engine()
        eng.start()
        eng.stop()
        for agent in eng._agents.values():
            assert agent.state == "stopped"

    def test_multiple_send_sequential(self, init_test_db):
        from engine import Engine
        eng = Engine()
        eng.start()
        for _ in range(3):
            r = eng.send("knowledge-indexer", "stats")
            assert r["status"] == "success"
