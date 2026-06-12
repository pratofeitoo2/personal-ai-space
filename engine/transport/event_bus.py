"""
EventBus — In-memory publish/subscribe message router.

Replaces direct agent-to-agent imports with a decoupled event system.
All messages are Pydantic-validated EventEnvelope instances.

Usage:
    bus = EventBus()

    # Subscribe
    bus.subscribe("context.ready", my_handler)

    # Publish (fire-and-forget)
    bus.publish("context.ready", envelope)

    # Request-reply (synchronous, with timeout)
    response = bus.request(envelope, timeout=30)
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from collections import defaultdict
from typing import Any, Callable, Optional

from transport.types import EventEnvelope, EventResponse, Priority

logger = logging.getLogger("engine.transport.event_bus")


class EventBus:
    """
    Thread-safe(ish) in-memory event bus for inter-agent communication.

    Features:
    - Topic-based pub/sub with wildcard support (topic.* matches topic.anything)
    - Request-reply pattern with configurable timeouts
    - Pydantic validation on all inbound envelopes
    - Error isolation: malformed messages are logged and discarded
    - Priority queueing: CRITICAL messages bypass the queue
    """

    def __init__(self, max_queue_size: int = 10_000):
        self._subscribers: dict[str, list[Callable]] = defaultdict(list)
        self._max_queue_size = max_queue_size
        self._pending_responses: dict[str, asyncio.Event] = {}
        self._response_data: dict[str, EventResponse] = {}
        self._stats = {
            "published": 0,
            "delivered": 0,
            "dropped": 0,
            "errors": 0,
        }

    # ── Subscription ──────────────────────────────────────────────────────────

    def subscribe(self, topic: str, handler: Callable[[EventEnvelope], Any]) -> str:
        """
        Subscribe a handler to a topic. Returns a subscription ID for unsubscribe.

        Args:
            topic: Topic string (e.g., "agent.context.ready", "task.completed")
            handler: Callable that receives an EventEnvelope.
                     Can be sync or async.

        Returns:
            subscription_id: Pass to unsubscribe() to remove.
        """
        sub_id = uuid.uuid4().hex[:12]
        handler._sub_id = sub_id  # type: ignore[attr-defined]
        self._subscribers[topic].append(handler)
        logger.debug("Subscribed [%s] to topic '%s'", sub_id, topic)
        return sub_id

    def unsubscribe(self, topic: str, sub_id: str) -> bool:
        """Remove a subscription by ID."""
        handlers = self._subscribers.get(topic, [])
        for i, h in enumerate(handlers):
            if getattr(h, "_sub_id", None) == sub_id:
                handlers.pop(i)
                logger.debug("Unsubscribed [%s] from topic '%s'", sub_id, topic)
                return True
        return False

    def unsubscribe_all(self, topic: str) -> int:
        """Remove all subscribers for a topic. Returns count removed."""
        count = len(self._subscribers.pop(topic, []))
        logger.debug("Unsubscribed %d handlers from topic '%s'", count, topic)
        return count

    # ── Publishing ────────────────────────────────────────────────────────────

    def publish(self, topic: str, envelope: EventEnvelope) -> int:
        """
        Publish an envelope to a topic. Fire-and-forget.

        Args:
            topic: Topic to publish to
            envelope: Validated EventEnvelope

        Returns:
            Number of handlers invoked (0 if no subscribers)
        """
        self._stats["published"] += 1

        # Validate envelope
        if not isinstance(envelope, EventEnvelope):
            try:
                envelope = EventEnvelope(**envelope)
            except Exception as e:
                logger.error("Dropping invalid envelope on topic '%s': %s", topic, e)
                self._stats["dropped"] += 1
                return 0

        # Deliver to subscribers
        delivered = 0
        for pattern, handlers in self._subscribers.items():
            if self._topic_matches(pattern, topic):
                for handler in handlers:
                    try:
                        handler(envelope)
                        self._stats["delivered"] += 1
                        delivered += 1
                    except Exception as exc:
                        logger.error(
                            "Handler failed for topic '%s' (handler=%s): %s",
                            topic, handler.__qualname__, exc, exc_info=True,
                        )
                        self._stats["errors"] += 1

        return delivered

    def broadcast(self, event_type: str, payload: dict[str, Any],
                  sender: str = "system", priority: Priority = Priority.NORMAL) -> int:
        """
        Convenience: build an envelope and publish it.

        Args:
            event_type: Event type string (used as topic)
            payload: Event payload dict
            sender: Sender agent ID
            priority: Message priority

        Returns:
            Number of handlers invoked
        """
        envelope = EventEnvelope(
            id=uuid.uuid4().hex,
            timestamp=self._now_iso(),
            sender=sender,
            recipients=[],
            action="broadcast",
            priority=priority,
            payload=payload,
            context={},
            metadata={},
        )
        return self.publish(event_type, envelope)

    # ── Request-Reply ─────────────────────────────────────────────────────────

    def request(self, envelope: EventEnvelope,
                timeout: float = 30.0) -> Optional[EventResponse]:
        """
        Send a request and wait for a response.

        This is a synchronous wrapper: it publishes the request and waits
        for a single response via `respond()`.

        Args:
            envelope: Request envelope
            timeout: Max seconds to wait

        Returns:
            EventResponse if received, None on timeout
        """
        import threading

        response_holder: list[EventResponse] = []
        event = threading.Event()

        def _capture_response(resp: EventResponse):
            response_holder.append(resp)
            event.set()

        # Temporarily subscribe to the response topic
        response_topic = f"response.{envelope.id}"
        self.subscribe(response_topic, _capture_response)

        try:
            self.publish(envelope.recipients[0] if envelope.recipients else "default", envelope)
            signaled = event.wait(timeout=timeout)
            if signaled and response_holder:
                return response_holder[0]
            logger.warning("Request timed out after %.1fs: msg_id=%s", timeout, envelope.id)
            return None
        finally:
            self.unsubscribe_all(response_topic)

    def respond(self, original_id: str, response: EventResponse):
        """
        Publish a response to a pending request.

        Args:
            original_id: The envelope ID from the original request
            response: The response to deliver
        """
        response_topic = f"response.{original_id}"
        self.publish(response_topic, EventEnvelope(
            id=uuid.uuid4().hex,
            timestamp=self._now_iso(),
            sender=response.original_id or "unknown",
            recipients=[],
            action="response",
            payload=response.model_dump(),
        ))

    # ── Utilities ─────────────────────────────────────────────────────────────

    def _topic_matches(self, pattern: str, topic: str) -> bool:
        """Simple wildcard matching: 'topic.*' matches 'topic.anything'."""
        if pattern.endswith(".*"):
            prefix = pattern[:-2]
            return topic.startswith(prefix + ".") or topic == prefix
        return pattern == topic

    @staticmethod
    def _now_iso() -> str:
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()

    def stats(self) -> dict[str, int]:
        """Return bus statistics."""
        return dict(self._stats, subscriptions=sum(len(h) for h in self._subscribers.values()))

    def reset_stats(self):
        """Reset all counters."""
        for k in self._stats:
            self._stats[k] = 0