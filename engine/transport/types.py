"""
Transport layer types — Pydantic-validated message schemas.

Matches the COMMUNICATION_PROTOCOL.md spec exactly.
All inter-agent communication MUST use these types.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


# ── Enums ──────────────────────────────────────────────────────────────────────

class ActionType(str, Enum):
    REQUEST = "request"
    BROADCAST = "broadcast"
    ASYNC_COMMAND = "async_command"


class Priority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


# ── Message Envelope ───────────────────────────────────────────────────────────

class EventEnvelope(BaseModel):
    """
    Typed message envelope for all inter-agent communication.
    Matches COMMUNICATION_PROTOCOL.md spec.
    """
    model_config = {"validate_default": True}

    id: str = Field(..., description="Unique message ID (UUID hex)")
    timestamp: str = Field(..., description="ISO-8601 timestamp")
    sender: str = Field(..., min_length=1, description="Sending agent ID")
    recipients: list[str] = Field(default_factory=list, description="Target agent IDs")
    action: ActionType = ActionType.REQUEST
    priority: Priority = Priority.NORMAL
    payload: dict[str, Any] = Field(default_factory=dict, description="Command + parameters + data")
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Session context: session_id, user_id, request_chain",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Timeout, retry policy, response requirements",
    )

    @field_validator("recipients", mode="before")
    @classmethod
    def _ensure_recipients_list(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            return [v]
        return list(v) if v else []


class EventResponse(BaseModel):
    """Response returned by an agent after processing a message."""
    model_config = {"validate_default": True}

    status: str = "success"  # "success" | "error"
    payload: dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    elapsed_ms: int = 0
    original_id: Optional[str] = None  # Links back to request envelope ID


# ── Convenience constructors ───────────────────────────────────────────────────

def make_envelope(
    sender: str,
    recipients: list[str] | str,
    command: str,
    data: dict[str, Any] | None = None,
    priority: Priority = Priority.NORMAL,
    action: ActionType = ActionType.REQUEST,
    **extra_payload,
) -> EventEnvelope:
    """Quick-build an envelope with sensible defaults."""
    import uuid
    from datetime import datetime, timezone

    if isinstance(recipients, str):
        recipients = [recipients]

    return EventEnvelope(
        id=uuid.uuid4().hex,
        timestamp=datetime.now(timezone.utc).isoformat(),
        sender=sender,
        recipients=recipients,
        action=action,
        priority=priority,
        payload={"command": command, **(data or {}), **extra_payload},
        context={"session_id": "", "user_id": "system", "request_chain": [sender]},
        metadata={"timeout_ms": 30_000, "retry_policy": "none", "require_response": True},
    )