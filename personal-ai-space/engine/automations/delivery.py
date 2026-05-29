"""WhatsApp delivery for automations with retry queue."""
import json
from pathlib import Path
from datetime import datetime, timezone

import requests

from log_manager import get_logger

logger = get_logger("engine.automations.delivery")

WHATSAPP_API = "http://localhost:8080/api/send"
STATE_DIR = Path.home() / ".local" / "share" / "personal-ai-space"
PENDING_FILE = STATE_DIR / "pending_deliveries.json"
MAX_PENDING = 50
MAX_RETRIES = 3


def send_whatsapp(text: str, recipient: str) -> bool:
    """Send message via WhatsApp bridge. Returns True on success."""
    if not recipient:
        logger.error("WhatsApp recipient not configured")
        return False
    try:
        resp = requests.post(
            WHATSAPP_API,
            json={"recipient": recipient, "message": text},
            timeout=10,
        )
        if resp.ok:
            logger.info("WhatsApp delivered to %s (%d chars)", recipient, len(text))
            return True
        logger.warning("WhatsApp API returned %d: %s", resp.status_code, resp.text[:200])
        return False
    except requests.ConnectionError:
        logger.warning("WhatsApp bridge unreachable")
        return False
    except requests.Timeout:
        logger.warning("WhatsApp bridge timed out after 10s")
        return False


def enqueue_pending(text: str, recipient: str) -> None:
    """Save message for retry later."""
    PENDING_FILE.parent.mkdir(parents=True, exist_ok=True)
    pending = _read_pending()
    pending.append({
        "text": text,
        "recipient": recipient,
        "failed_at": datetime.now(timezone.utc).isoformat(),
        "retry_count": 0,
    })
    PENDING_FILE.write_text(json.dumps(pending[-MAX_PENDING:], ensure_ascii=False))


def retry_pending() -> int:
    """Retry undelivered messages. Returns count delivered."""
    pending = _read_pending()
    if not pending:
        return 0

    delivered = 0
    remaining = []
    for item in pending:
        if item.get("retry_count", 0) >= MAX_RETRIES:
            logger.warning("Discarding after %d retries: %.60s", MAX_RETRIES, item.get("text", ""))
            continue
        ok = send_whatsapp(item.get("text", ""), item.get("recipient", ""))
        if ok:
            delivered += 1
        else:
            item["retry_count"] = item.get("retry_count", 0) + 1
            remaining.append(item)

    PENDING_FILE.write_text(json.dumps(remaining, ensure_ascii=False))
    return delivered


def _read_pending() -> list[dict]:
    """Read pending deliveries file, return parsed list."""
    if PENDING_FILE.exists():
        try:
            return json.loads(PENDING_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            return []
    return []
