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


# ── Per-section reminder titles ───────────────────────────────────────────

_SECTION_TITLES = {
    "tasks_due_today": "📋 Tarefas do Dia",
    "tasks_remaining": "📋 Restam do Dia",
    "overdue_tasks": "⚠️ Tarefas Atrasadas",
    "calendar_today": "📅 Agenda de Hoje",
    "calendar_upcoming": "🔔 Em Breve na Agenda",
    "habits_at_risk": "🎯 Hábitos em Risco",
    "habits_completed_today": "💪 Hábitos Concluídos Hoje",
    "habits_today_status": "🎯 Status dos Hábitos",
    "goals_active": "🎯 Metas Ativas",
    "goals_near_deadline": "🎯 Metas Próximas do Prazo",
    "tasks_completed_today": "✅ Concluído Hoje",
}

# Time-scheduled rules get per-section Reminder tiles; interval alerts get one
# grouped reminder to avoid thrash from frequent re-creation.
_SECTION_REMINDER_RULES = {"morning_brief", "midday_checkpoint", "end_of_day"}


# ── Message builders per channel ──────────────────────────────────────────


def _build_whatsapp_message(message: str, sections: list[dict], rule_name: str) -> str:
    """Enhance WhatsApp message with compact summary header and footer."""
    greeting = ""
    summary_bits = []
    has_data = False

    for sec in sections:
        it = sec.get("item_type", "")
        items = sec.get("items", [])
        if it == "greeting":
            greeting = sec.get("formatted", "")
        elif items:
            has_data = True
            title = _SECTION_TITLES.get(it, "")
            if title:
                summary_bits.append(f"{title}: {len(items)}")

    footer = "\n\n[Sisyphus — assistente pessoal]"

    if not has_data:
        return message + footer

    # Build header: greeting + compact per-section counts
    if greeting and summary_bits:
        header = f"{greeting}  {' · '.join(summary_bits)}"
    elif summary_bits:
        header = " · ".join(summary_bits)
    else:
        header = ""

    # Remove greeting from message body (it's in the header now)
    body = message
    if greeting and body.startswith(greeting):
        body = body[len(greeting):].strip("\n")

    result = body + footer if not header else f"{header}\n\n{body}{footer}"
    return result.strip()


def _build_notification_text(rule_id: str, sections: list[dict], rule_name: str, message: str = "") -> str:
    """Build rule-specific macOS notification text from section data."""
    counts = {}
    first_items = {}
    for sec in sections:
        it = sec.get("item_type", "")
        items = sec.get("items", [])
        if items:
            counts[it] = len(items)
            if it not in first_items:
                first_items[it] = items[0].lstrip("• ")

    if rule_id == "morning_brief":
        parts = []
        if c := counts.get("tasks_due_today"):
            parts.append(f"{c} tasks")
        if c := counts.get("calendar_today"):
            parts.append(f"{c} eventos")
        if c := counts.get("habits_at_risk"):
            parts.append(f"{c} hábitos em risco")
        if c := counts.get("goals_active"):
            parts.append(f"{c} metas")
        if parts:
            return " · ".join(parts)

    elif rule_id == "midday_checkpoint":
        parts = []
        if c := counts.get("tasks_remaining"):
            parts.append(f"{c} tasks restam")
        if c := counts.get("habits_today_status"):
            parts.append(f"{c} hábitos")
        if c := counts.get("habits_at_risk"):
            parts.append(f"{c} em risco")
        if parts:
            return " · ".join(parts)

    elif rule_id == "end_of_day":
        parts = []
        if c := counts.get("tasks_completed_today"):
            parts.append(f"{c} tasks concluídas")
        if c := counts.get("habits_completed_today"):
            parts.append(f"{c} hábitos hoje")
        if parts:
            return " · ".join(parts)

    elif rule_id == "alert_overdue_tasks":
        c = counts.get("overdue_tasks", 0)
        return f"⚠️ {c} tarefas atrasadas"

    elif rule_id == "alert_habits_at_risk":
        c = counts.get("habits_at_risk", 0)
        return f"🎯 {c} hábitos em risco"

    elif rule_id == "alert_calendar_soon":
        first = first_items.get("calendar_upcoming", "")
        return f"🔔 {first}"[:120]

    elif rule_id == "alert_goal_deadlines":
        first = first_items.get("goals_near_deadline", "")
        return f"🎯 {first}"[:120]

    # Fallback: first line of the formatted message
    first_line = (message.split("\n")[0] if message else "")[:120]
    return first_line


# ── Unified delivery ─────────────────────────────────────────────────────


def deliver_all(message: str, sections: list[dict], rule_id: str, rule_name: str, recipient: str = "") -> None:
    """Deliver a message to all configured channels.

    Channels
    --------
    - **WhatsApp** – overview with summary header and footer.
    - **macOS Notification Center** – rule-specific summary text.
    - **Apple Reminders** – per-section tiles for briefings, grouped for alerts.
    """
    # 1. WhatsApp – enhanced with summary header and footer
    if recipient:
        whatsapp_msg = _build_whatsapp_message(message, sections, rule_name)
        ok = send_whatsapp(whatsapp_msg, recipient)
        if not ok:
            enqueue_pending(whatsapp_msg, recipient)

    # 2. macOS Notification – rule-specific preview
    notif_text = _build_notification_text(rule_id, sections, rule_name, message)
    send_macos_notification(title="Sisyphus", subtitle=rule_name, text=notif_text)

    # 3. Apple Reminders
    list_title = _REMINDER_TITLES.get(rule_id)
    if list_title:
        if rule_id in _SECTION_REMINDER_RULES:
            # Per-section tiles for time-scheduled briefings
            send_section_reminders(sections, list_title)
        else:
            # Grouped single reminder for interval alerts
            send_reminder(list_title, message[:500])


def send_section_reminders(sections: list[dict], list_title: str) -> None:
    """Create one grouped reminder per data section.

    Skips greeting and llm_opener sections.  Query sections with no items
    are also skipped (they returned *None* from the runner and won't appear
    in the list).
    """
    created = 0
    for sec in sections:
        item_type = sec.get("item_type", "")
        items = sec.get("items", [])
        if not items or item_type in ("greeting", "llm_opener"):
            continue
        section_title = _SECTION_TITLES.get(item_type)
        if not section_title:
            continue
        rem_title = f"{section_title} ({list_title})"
        notes = "\n".join(items)[:500]
        if send_reminder(rem_title, notes):
            created += 1
    if created:
        logger.info("Created %d section reminders for %s", created, list_title)


# ── Habit reminders ──────────────────────────────────────────────────────


_HABIT_REMINDER_LIST = REMINDRES_LIST  # reuse Sisyphus list


def create_habit_reminders(habits: list[dict]) -> None:
    """Create one daily reminder per active habit.

    Each reminder has:
    - Title: "🔲 {habit_name}"
    - Notes: JSON with habit_id and type=habit (for completion detection)
    - Due: today (appears in Today view + badge)

    Completes any existing reminder with the same title first to avoid duplicates.
    """
    if not _ensure_sisyphus_list():
        return

    for habit in habits:
        habit_id = habit.get("id", "")
        habit_name = habit.get("habit_name", habit_id)
        title = f"🔲 {habit_name}"
        notes = json.dumps({"habit_id": habit_id, "type": "habit"})

        try:
            # Complete old reminder with same title
            subprocess.run(
                [str(REMINDRES_BRIDGE), "complete", _HABIT_REMINDER_LIST, title],
                timeout=10, capture_output=True,
            )

            # Create new reminder
            add_args = [str(REMINDRES_BRIDGE), "add", _HABIT_REMINDER_LIST, title, notes]
            subprocess.run(add_args, timeout=10, capture_output=True)

            # Set due = now so it appears in Today view
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            subprocess.run(
                [str(REMINDRES_BRIDGE), "set-due", _HABIT_REMINDER_LIST, title, now_str],
                timeout=10, capture_output=True,
            )
        except Exception as e:
            logger.warning("Failed to create habit reminder '%s': %s", title, e)

    logger.info("Created %d habit reminders", len(habits))


def deliver_all_with_habits(message: str, sections: list[dict], rule_id: str,
                            rule_name: str, recipient: str = "",
                            habits: list[dict] = None) -> None:
    """Deliver message + create individual habit reminders.

    Same as deliver_all but also creates one reminder per active habit.
    """
    deliver_all(message, sections, rule_id, rule_name, recipient)

    if habits:
        create_habit_reminders(habits)
