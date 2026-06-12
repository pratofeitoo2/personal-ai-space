"""
Transport layer — modular data transport for Personal AI Powerhouse.

Provides:
  - EventBus: in-memory pub/sub with Pydantic-validated message envelopes
  - DataHub: typed facade for all SQLite database operations
  - SafeMCPTransport: resilient MCP server communication with circuit breaker
  - AppConfig: centralized configuration from environment variables

Usage:
    from transport.types import EventEnvelope, ActionType, Priority
    from transport.event_bus import EventBus
    from transport.data_hub import DataHub
    from transport.mcp_transport import MCPTransportManager, SafeMCPTransport
    from transport.config import AppConfig
"""
from transport.config import AppConfig
from transport.event_bus import EventBus
from transport.types import ActionType, EventEnvelope, EventResponse, Priority, make_envelope

__all__ = [
    "AppConfig",
    "EventBus",
    "EventEnvelope",
    "EventResponse",
    "ActionType",
    "Priority",
    "make_envelope",
    # Lazy imports for heavier modules
    "DataHub",
    "SafeMCPTransport",
    "MCPTransportManager",
]