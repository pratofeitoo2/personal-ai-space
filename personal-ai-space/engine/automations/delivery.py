"""Multi-channel delivery for automations: WhatsApp, macOS notifications, Reminders."""
import json
import subprocess
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

REMINDRES_BRIDGE = Path.home() / ".claude" / "reminders-bridge"
REMINDRES_LIST = "Sisyphus"

# Rule types that warrant a persistent Reminder (not every interval tick)
_REMINDER_TITLES = {
    "morning_brief": "Sisyphus - Briefing Matinal",
    "midday_checkpoint": "Sisyphus - Briefing Meio-Dia",
    "end_of_day": "Sisyphus - Briefing Fim do Dia",
    "alert_overdue_tasks": "Sisyphus - Tarefas Atrasadas",
    "alert_habits_at_risk": "Sisyphus - Habitos em Risco",
    "alert_calendar_soon": "Sisyphus - Compromisso Proximo",
    "alert_goal_deadlines": "Sisyphus - Metas Proximas",
}


def send_whatsapp(text: str, recipient: str) -> bool:
    """Send message via WhatsApp bridge. Returns True on success."""
    if not recipient:
        logger.error("WhatsApp recipient not configured")
        return False
    # Strip leading '+' — bridge expects digits-only format
    clean_recipient = recipient.lstrip("+")
    try:
        resp = requests.post(
            WHATSAPP_API,
            json={"recipient": clean_recipient, "message": text},
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


# ── macOS Notification Center ────────────────────────────────────────────


def send_macos_notification(title: str, subtitle: str = "", text: str = "") -> bool:
    """Show a notification in macOS Notification Center via osascript."""
    try:
        safe_title = title.replace('"', '\\"')
        safe_subtitle = subtitle.replace('"', '\\"')
        safe_text = text.replace('"', '\\"')

        script = f'display notification "{safe_text}" with title "{safe_title}"'
        if safe_subtitle:
            script += f' subtitle "{safe_subtitle}"'

        subprocess.run(["osascript", "-e", script], timeout=5, capture_output=True)
        logger.info("macOS notification sent: %s", title)
        return True
    except Exception as e:
        logger.warning("macOS notification failed: %s", e)
        return False


# ── Apple Reminders ──────────────────────────────────────────────────────


def _ensure_sisyphus_list() -> bool:
    """Create the Sisyphus reminders list if it doesn't exist."""
    try:
        result = subprocess.run(
            [str(REMINDRES_BRIDGE), "lists"],
            timeout=10, capture_output=True, text=True,
        )
        if REMINDRES_LIST not in (result.stdout or ""):
            subprocess.run(
                [str(REMINDRES_BRIDGE), "create-list", REMINDRES_LIST],
                timeout=10, capture_output=True,
            )
            logger.info("Created '%s' reminders list", REMINDRES_LIST)
        return True
    except Exception as e:
        logger.warning("Failed to ensure reminders list: %s", e)
        return False


def send_reminder(title: str, notes: str = "") -> bool:
    """Create/update a reminder in the Sisyphus list with due date = now.

    Completes any existing reminder with the same title first, then creates
    a new one.  This keeps at most one reminder per title type at any time.
    """
    if not _ensure_sisyphus_list():
        return False

    try:
        # Complete any old reminder with the same title
        subprocess.run(
            [str(REMINDRES_BRIDGE), "complete", REMINDRES_LIST, title],
            timeout=10, capture_output=True,
        )

        # Create new reminder
        add_args = [str(REMINDRES_BRIDGE), "add", REMINDRES_LIST, title]
        if notes:
            add_args.append(notes[:500])
        subprocess.run(add_args, timeout=10, capture_output=True)

        # Set due date = now so it appears in Today view + badge
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        subprocess.run(
            [str(REMINDRES_BRIDGE), "set-due", REMINDRES_LIST, title, now_str],
            timeout=10, capture_output=True,
        )

        logger.info("Reminder created: %s", title)
        return True
    except Exception as e:
        logger.warning("Failed to create reminder: %s", e)
        return False


# ── Unified delivery ─────────────────────────────────────────────────────


def deliver_all(message: str, rule_id: str, rule_name: str, recipient: str = "") -> None:
    """Deliver a message to all configured channels.

    Channels
    --------
    - **WhatsApp**  – only if *recipient* is non-empty; enqueues on failure.
    - **macOS Notification Center** – fire-and-forget osascript banner.
    - **Apple Reminders** – only for rule types listed in ``_REMINDER_TITLES``.
    """
    # 1. WhatsApp
    if recipient:
        ok = send_whatsapp(message, recipient)
        if not ok:
            enqueue_pending(message, recipient)

    # 2. macOS Notification
    first_line = (message.split("\n")[0] or message)[:120]
    send_macos_notification(title="Sisyphus", subtitle=rule_name, text=first_line)

    # 3. Apple Reminder (only for designated rule types)
    rem_title = _REMINDER_TITLES.get(rule_id)
    if rem_title:
        send_reminder(rem_title, message[:500])
