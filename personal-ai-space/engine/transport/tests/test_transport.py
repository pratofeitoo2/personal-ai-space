"""
Test suite for the transport layer.

Run with: pytest transport/tests/ -v
"""
from __future__ import annotations

import unittest.mock as mock

import pytest
import sys
import os

# Ensure transport package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from transport.types import EventEnvelope, ActionType, Priority, EventResponse, make_envelope
from transport.event_bus import EventBus
from transport.config import AppConfig


# ═══════════════════════════════════════════════════════════════════════════════
# types.py tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestEventEnvelope:
    """Test EventEnvelope Pydantic model."""

    def test_valid_envelope_creation(self):
        """Valid envelope creates without errors."""
        e = EventEnvelope(
            id="test-1",
            timestamp="2026-05-14T05:00:00+00:00",
            sender="test-agent",
            recipients=["recipient-1"],
            action=ActionType.REQUEST,
            priority=Priority.NORMAL,
            payload={"command": "test", "data": {"key": "value"}},
            context={"session_id": "sess-1", "user_id": "user-1", "request_chain": []},
            metadata={"timeout_ms": 30000, "require_response": True},
        )
        assert e.id == "test-1"
        assert e.sender == "test-agent"
        assert e.action == ActionType.REQUEST
        assert e.priority == Priority.NORMAL

    def test_invalid_envelope_raises_validation_error(self):
        """Invalid envelope raises ValidationError."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            EventEnvelope(
                id="",  # empty id
                timestamp="not-a-date",
                sender="",
                recipients=[],
                action="invalid_action",  # not a valid ActionType
                priority="invalid_priority",  # not a valid Priority
                payload=None,
                context={},
                metadata={},
            )

    def test_envelope_serialization_roundtrip(self):
        """Envelope can be serialized to JSON and deserialized back."""
        e = EventEnvelope(
            id="roundtrip-1",
            timestamp="2026-05-14T05:00:00+00:00",
            sender="agent-a",
            recipients=["agent-b"],
            action=ActionType.BROADCAST,
            priority=Priority.HIGH,
            payload={"event": "task_completed", "task_id": "task-42"},
        )
        json_str = e.model_dump_json()
        restored = EventEnvelope.model_validate_json(json_str)
        assert restored.id == e.id
        assert restored.sender == e.sender
        assert restored.action == e.action

    def test_recipients_string_conversion(self):
        """Single string recipient is converted to list."""
        e = EventEnvelope(
            id="test-2",
            timestamp="2026-05-14T05:00:00+00:00",
            sender="a",
            recipients="single-recipient",  # type: ignore
            action=ActionType.REQUEST,
            priority=Priority.NORMAL,
        )
        assert e.recipients == ["single-recipient"]


class TestEventResponse:
    """Test EventResponse Pydantic model."""

    def test_success_response(self):
        r = EventResponse(status="success", payload={"result": "ok"})
        assert r.status == "success"
        assert r.payload == {"result": "ok"}
        assert r.error is None

    def test_error_response(self):
        r = EventResponse(status="error", error="Something went wrong")
        assert r.status == "error"
        assert r.error == "Something went wrong"


class TestMakeEnvelope:
    """Test make_envelope convenience constructor."""

    def test_quick_build(self):
        e = make_envelope(
            sender="test-agent",
            recipients=["other-agent"],
            command="get_context",
            data={"user_id": "123"},
        )
        assert e.sender == "test-agent"
        assert e.recipients == ["other-agent"]
        assert e.payload["command"] == "get_context"
        # make_envelope spreads data into the payload dict
        assert e.payload["user_id"] == "123"
        assert e.id is not None
        assert len(e.id) == 32  # UUID hex

    def test_single_recipient_string(self):
        e = make_envelope(sender="a", recipients="b", command="test")
        assert e.recipients == ["b"]


class TestActionType:
    def test_all_values(self):
        assert ActionType.REQUEST.value == "request"
        assert ActionType.BROADCAST.value == "broadcast"
        assert ActionType.ASYNC_COMMAND.value == "async_command"


class TestPriority:
    def test_all_values(self):
        assert Priority.CRITICAL.value == "critical"
        assert Priority.HIGH.value == "high"
        assert Priority.NORMAL.value == "normal"
        assert Priority.LOW.value == "low"


# ═══════════════════════════════════════════════════════════════════════════════
# event_bus.py tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestEventBus:
    """Test EventBus pub/sub functionality."""

    def test_subscribe_and_publish(self):
        """Published events are delivered to subscribers."""
        bus = EventBus()
        received = []

        bus.subscribe("test.topic", lambda e: received.append(e))
        envelope = make_envelope(sender="a", recipients=["b"], command="test")
        count = bus.publish("test.topic", envelope)

        assert count == 1
        assert len(received) == 1
        assert received[0].id == envelope.id

    def test_publish_to_unsubscribed_topic(self):
        """Publishing to a topic with no subscribers returns 0."""
        bus = EventBus()
        envelope = make_envelope(sender="a", recipients=["b"], command="test")
        count = bus.publish("empty.topic", envelope)
        assert count == 0

    def test_multiple_subscribers(self):
        """Multiple subscribers all receive the event."""
        bus = EventBus()
        r1, r2 = [], []
        bus.subscribe("multi", lambda e: r1.append(e))
        bus.subscribe("multi", lambda e: r2.append(e))

        envelope = make_envelope(sender="a", recipients=["b"], command="test")
        bus.publish("multi", envelope)

        assert len(r1) == 1
        assert len(r2) == 1

    def test_unsubscribe(self):
        """Unsubscribed handlers no longer receive events."""
        bus = EventBus()
        received = []
        sub_id = bus.subscribe("test", lambda e: received.append(e))
        bus.unsubscribe("test", sub_id)

        envelope = make_envelope(sender="a", recipients=["b"], command="test")
        bus.publish("test", envelope)
        assert len(received) == 0

    def test_unsubscribe_all(self):
        """All subscribers for a topic are removed."""
        bus = EventBus()
        bus.subscribe("test", lambda e: None)
        bus.subscribe("test", lambda e: None)
        count = bus.unsubscribe_all("test")
        assert count == 2
        assert "test" not in bus._subscribers

    def test_broadcast_convenience(self):
        """broadcast() builds and publishes an envelope."""
        bus = EventBus()
        received = []
        bus.subscribe("event", lambda e: received.append(e))

        count = bus.broadcast("event", {"type": "test"}, sender="system")
        assert count == 1
        assert received[0].payload["type"] == "test"
        assert received[0].action == "broadcast"

    def test_stats(self):
        """Stats track published/delivered counts."""
        bus = EventBus()
        bus.subscribe("t", lambda e: None)
        envelope = make_envelope(sender="a", recipients=["b"], command="test")
        bus.publish("t", envelope)

        stats = bus.stats()
        assert stats["published"] == 1
        assert stats["delivered"] == 1
        assert stats["errors"] == 0

    def test_invalid_envelope_dropped(self):
        """Invalid envelopes are logged and dropped, not crashed."""
        bus = EventBus()
        bus.subscribe("t", lambda e: None)
        count = bus.publish("t", {"not": "a valid envelope"})
        assert count == 0
        assert bus.stats()["dropped"] >= 1

    def test_handler_error_isolation(self):
        """Errors in one handler don't affect others."""
        bus = EventBus()
        received = []

        def bad_handler(e):
            raise RuntimeError("boom")

        bus.subscribe("t", bad_handler)
        bus.subscribe("t", lambda e: received.append(e))

        envelope = make_envelope(sender="a", recipients=["b"], command="test")
        bus.publish("t", envelope)

        assert len(received) == 1  # Good handler still received it
        assert bus.stats()["errors"] == 1


# ═══════════════════════════════════════════════════════════════════════════════
# config.py tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestAppConfig:
    """Test AppConfig singleton."""

    def setup_method(self):
        """Reset singleton between tests."""
        AppConfig._instance = None
        # Clear env vars that might affect tests
        for key in ["OLLAMA_URL", "OLLAMA_MODEL", "MEMORY_DB_DIR",
                     "DATA_DIR", "MCP_REGISTRY_PATH", "LOG_LEVEL",
                     "CONTEXT_TTL_SECONDS", "PROFILE_PATH", "MCP_SERVER_DIR"]:
            os.environ.pop(key, None)

    def test_singleton_same_instance(self):
        """Multiple calls return the same instance."""
        c1 = AppConfig.instance()
        c2 = AppConfig.instance()
        assert c1 is c2

    def test_default_values(self):
        """Defaults match expected values."""
        c = AppConfig.instance()
        assert c.ollama_url == "http://localhost:11434/api/embed"
        assert c.ollama_model == "nomic-embed-text:137m-v1.5-fp16"
        assert c.log_level == "INFO"
        assert c.context_ttl_seconds == 300

    def test_env_var_override(self):
        """Environment variables override defaults."""
        os.environ["OLLAMA_URL"] = "http://custom:11434/api/embed"
        os.environ["LOG_LEVEL"] = "DEBUG"
        c = AppConfig.instance()
        assert c.ollama_url == "http://custom:11434/api/embed"
        assert c.log_level == "DEBUG"

    def test_reload(self):
        """reload() refreshes from environment."""
        c = AppConfig.instance()
        original_url = c.ollama_url
        os.environ["OLLAMA_URL"] = "http://reloaded:11434/api/embed"
        c.reload()
        assert c.ollama_url == "http://reloaded:11434/api/embed"

    def test_invalid_context_ttl_rejected(self):
        """Negative context_ttl_seconds is rejected."""
        with pytest.raises(Exception):
            AppConfig(context_ttl_seconds=-1)

    def test_invalid_mcp_timeout_rejected(self):
        """Zero or negative MCP timeout is rejected."""
        with pytest.raises(Exception):
            AppConfig(mcp_timeout_seconds=0)


# ═══════════════════════════════════════════════════════════════════════════════
# data_hub.py tests (mocked db_manager)
# ═══════════════════════════════════════════════════════════════════════════════

class TestDataHub:
    """Test DataHub facade with mocked db_manager."""

    def setup_method(self):
        """Set up DataHub with mocked db_manager."""
        import unittest.mock as mock
        import sys

        # Create mock db_manager
        self.mock_db = mock.MagicMock()
        sys.modules['db_manager'] = self.mock_db

        # Force reimport of data_hub with mocked db_manager
        if 'transport.data_hub' in sys.modules:
            del sys.modules['transport.data_hub']

        from transport.data_hub import DataHub
        self.DataHub = DataHub

    def teardown_method(self):
        """Clean up mocked modules."""
        import sys
        if 'db_manager' in sys.modules:
            del sys.modules['db_manager']
        if 'transport.data_hub' in sys.modules:
            del sys.modules['transport.data_hub']

    def test_get_user_profile(self):
        """get_user_profile returns profile data."""
        self.mock_db.query.return_value = [{"id": 1, "name": "Test User"}]
        hub = self.DataHub.__new__(self.DataHub)
        hub._config = mock.MagicMock()
        hub._db_dir = mock.MagicMock()

        result = hub.get_user_profile()
        assert result == {"id": 1, "name": "Test User"}

    def test_get_user_profile_empty(self):
        """get_user_profile returns None when no profile."""
        self.mock_db.query.return_value = []
        hub = self.DataHub.__new__(self.DataHub)
        hub._config = mock.MagicMock()
        hub._db_dir = mock.MagicMock()

        result = hub.get_user_profile()
        assert result is None

    def test_get_habits(self):
        """get_habits returns habit list."""
        self.mock_db.query.return_value = [
            {"id": 1, "habit_name": "exercise", "status": "active"}
        ]
        hub = self.DataHub.__new__(self.DataHub)
        hub._config = mock.MagicMock()
        hub._db_dir = mock.MagicMock()

        result = hub.get_habits(active_only=True)
        assert len(result) == 1
        assert result[0]["habit_name"] == "exercise"

    def test_query_escape_hatch(self):
        """query() escape hatch works for raw SQL."""
        self.mock_db.query.return_value = [{"count": 42}]
        hub = self.DataHub.__new__(self.DataHub)
        hub._config = mock.MagicMock()
        hub._db_dir = mock.MagicMock()

        result = hub.query("memories", "SELECT COUNT(*) as count FROM interactions")
        assert result == [{"count": 42}]

    def test_health_check(self):
        """health_check delegates to db_manager."""
        self.mock_db.health_check.return_value = {"memories": {"ok": True}}
        hub = self.DataHub.__new__(self.DataHub)
        hub._config = mock.MagicMock()
        hub._db_dir = mock.MagicMock()

        result = hub.health_check()
        assert result["memories"]["ok"] is True


# ═══════════════════════════════════════════════════════════════════════════════
# mcp_transport.py tests (mocked base_client)
# ═══════════════════════════════════════════════════════════════════════════════

class TestCircuitBreaker:
    """Test CircuitBreaker state machine."""

    def test_starts_closed(self):
        from transport.mcp_transport import CircuitBreaker
        cb = CircuitBreaker()
        assert cb.state.value == "closed"

    def test_opens_after_threshold(self):
        from transport.mcp_transport import CircuitBreaker, CircuitBreakerConfig
        cb = CircuitBreaker(CircuitBreakerConfig(
            failure_threshold=2
        ))
        cb.record_failure()
        assert cb.state.value == "closed"
        cb.record_failure()
        assert cb.state.value == "open"

    def test_half_open_after_cooldown(self):
        from transport.mcp_transport import CircuitBreaker, CircuitBreakerConfig
        cb = CircuitBreaker(CircuitBreakerConfig(
            failure_threshold=1,
            cooldown_seconds=0.1
        ))
        cb.record_failure()
        assert cb.state.value == "open"
        import time
        time.sleep(0.15)
        _ = cb.state  # trigger auto-transition
        assert cb.state.value == "half_open"

    def test_closes_on_success_in_half_open(self):
        import time
        from transport.mcp_transport import CircuitBreaker, CircuitBreakerConfig
        cb = CircuitBreaker(CircuitBreakerConfig(
            failure_threshold=1,
            cooldown_seconds=0.1,
            success_threshold=1
        ))
        cb.record_failure()
        time.sleep(0.15)
        _ = cb.state
        cb.record_success()
        assert cb.state.value == "closed"

    def test_opens_again_on_failure_in_half_open(self):
        import time
        from transport.mcp_transport import CircuitBreaker, CircuitBreakerConfig
        cb = CircuitBreaker(CircuitBreakerConfig(
            failure_threshold=1,
            cooldown_seconds=0.1,
        ))
        cb.record_failure()
        time.sleep(0.15)
        _ = cb.state
        cb.record_failure()
        assert cb.state.value == "open"

    def test_allow_request_respects_state(self):
        from transport.mcp_transport import CircuitBreaker, CircuitBreakerConfig
        cb = CircuitBreaker(CircuitBreakerConfig(
            failure_threshold=1
        ))
        assert cb.allow_request() is True
        cb.record_failure()
        assert cb.allow_request() is False

    def test_reset(self):
        from transport.mcp_transport import CircuitBreaker, CircuitBreakerConfig
        cb = CircuitBreaker(CircuitBreakerConfig(
            failure_threshold=1
        ))
        cb.record_failure()
        assert cb.state.value == "open"
        cb.reset()
        assert cb.state.value == "closed"


class TestSafeMCPTransport:
    """Test SafeMCPTransport with mocked client."""

    def test_call_tool_returns_fallback_on_circuit_open(self):
        from transport.mcp_transport import SafeMCPTransport, MCPServerConfig, CircuitBreakerConfig
        import unittest.mock as mock

        config = MCPServerConfig(
            id="test-server",
            name="Test Server",
            transport="stdio",
            command="fake",
            circuit_breaker=CircuitBreakerConfig(failure_threshold=1),
        )
        transport = SafeMCPTransport(config)

        # Force circuit open
        transport._circuit_breaker.record_failure()

        result = transport.call_tool("some_tool", {"arg": "val"})
        assert result.success is False
        assert "circuit breaker open" in result.error.lower()

    def test_status_report(self):
        from transport.mcp_transport import SafeMCPTransport, MCPServerConfig
        config = MCPServerConfig(id="test", name="Test", transport="stdio", command="fake")
        transport = SafeMCPTransport(config)
        status = transport.status()
        assert status["id"] == "test"
        assert status["name"] == "Test"


class TestMCPTransportManager:
    """Test MCPTransportManager."""

    def test_empty_registry(self, tmp_path):
        from transport.mcp_transport import MCPTransportManager
        registry = tmp_path / "registry.json"
        registry.write_text('{"servers": []}')

        mgr = MCPTransportManager(str(registry))
        assert len(mgr._servers) == 0
        assert mgr.discover_tools() == {}
        assert mgr.list_servers() == []

    def test_unknown_server_returns_error(self, tmp_path):
        from transport.mcp_transport import MCPTransportManager
        registry = tmp_path / "registry.json"
        registry.write_text('{"servers": []}')

        mgr = MCPTransportManager(str(registry))
        from mcp_tools.base_client import MCPResult
        result = mgr.call_tool("nonexistent", "some_tool")
        assert result.success is False
        assert "Unknown MCP server" in result.error