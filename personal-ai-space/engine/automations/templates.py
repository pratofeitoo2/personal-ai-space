"""Message template builders for automation briefs and alerts."""
from datetime import datetime
from typing import Optional

from log_manager import get_logger
from llm_bridge import enrich_digest_opener


logger = get_logger("engine.automations.templates")


def build_brief_message(sections: list[dict]) -> str:
    """Join section results into a single message string."""
    parts = [s["formatted"] for s in sections if s.get("formatted")]
    return "\n\n".join(parts)


def format_section(items: list[str], label: str, empty_msg: str = "") -> Optional[str]:
    """Format items under a header. Returns None to skip section."""
    if not items:
        return empty_msg if empty_msg else None
    lines = [label]
    lines.extend(f"• {item}" for item in items)
    return "\n".join(lines)


def generate_greeting() -> str:
    """Return time-appropriate greeting in Portuguese."""
    hour = datetime.now().hour
    if hour < 12:
        return "🌅 Bom dia!"
    elif hour < 18:
        return "☀️ Boa tarde!"
    else:
        return "🌙 Boa noite!"


def generate_opener(tasks_due: int, overdue: int, habits_at_risk: int, habit_count: int) -> Optional[str]:
    """Generate LLM opener via existing bridge. Returns None if offline."""
    try:
        return enrich_digest_opener(tasks_due, overdue, habits_at_risk, habit_count)
    except Exception:
        logger.warning("LLM opener unavailable (Ollama bridge exception)", exc_info=True)
        return None
