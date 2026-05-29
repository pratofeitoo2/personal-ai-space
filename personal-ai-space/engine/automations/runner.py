"""Automation rule engine — reads YAML rules, checks schedules, executes."""
import json
import logging
from datetime import datetime, time
from pathlib import Path
from typing import Any, Optional

import yaml

from log_manager import get_logger
import db_manager as db
from automations.delivery import deliver_all, retry_pending
from automations.templates import (
    build_brief_message,
    format_section,
    generate_greeting,
    generate_opener,
)


logger = get_logger("engine.automations.runner")

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "automations.yaml"
STATE_DIR = Path.home() / ".local" / "share" / "personal-ai-space"
STATE_FILE = STATE_DIR / "automation_state.json"

# ── Query dispatch — maps query names to db_manager calls ──

QUERIES: dict[str, tuple] = {
    "tasks_due_today": (
        "tasks",
        "SELECT title, due_date, priority FROM tasks WHERE due_date=date('now','localtime') AND status NOT IN ('completed','cancelled')",
        "title",
        (),
    ),
    "overdue_tasks": (
        "tasks",
        "SELECT title, due_date, priority FROM tasks WHERE due_date<date('now','localtime') AND status NOT IN ('completed','cancelled')",
        "title",
        (),
    ),
    "tasks_remaining": (
        "tasks",
        "SELECT title, due_date, priority FROM tasks WHERE due_date<=date('now','localtime') AND status NOT IN ('completed','cancelled')",
        "title",
        (),
    ),
    "tasks_completed_today": (
        "tasks",
        "SELECT title, updated_at FROM tasks WHERE status='completed' AND date(updated_at)=date('now','localtime') ORDER BY updated_at",
        "title",
        (),
    ),
    "habits_at_risk": (
        "self",
        "SELECT habit_name, current_streak, last_completed FROM habits WHERE status='active' AND (last_completed IS NULL OR last_completed < date('now','localtime','-1 day'))",
        "habit_name",
        (),
    ),
    "habits_completed_today": (
        "self",
        "SELECT h.habit_name, hl.completed_at FROM habit_logs hl JOIN habits h ON hl.habit_id=h.id WHERE date(hl.completed_at)=date('now','localtime') ORDER BY hl.completed_at",
        "habit_name",
        (),
    ),
    "habits_today_status": (
        "self",
        "SELECT h.habit_name, CASE WHEN hl.id IS NOT NULL THEN '✅' ELSE '⬜' END as status FROM habits h LEFT JOIN habit_logs hl ON hl.habit_id=h.id AND date(hl.completed_at)=date('now','localtime') WHERE h.status='active'",
        "habit_name",
        (),
    ),
    "goals_active": (
        "self",
        "SELECT title, category FROM needs WHERE status='active' ORDER BY priority",
        "title",
        (),
    ),
    "goals_near_deadline": (
        "self",
        "SELECT title, deadline FROM needs WHERE status='active' AND deadline IS NOT NULL AND deadline <= date('now','localtime','+7 days') ORDER BY deadline",
        "title",
        (),
    ),
    "calendar_today": (
        "calendar",
        "SELECT title, start_time FROM events WHERE date(start_time)=date('now','localtime') ORDER BY start_time",
        "title",
        (),
    ),
    "calendar_upcoming": (
        "calendar",
        "SELECT title, start_time FROM events WHERE start_time >= datetime('now','localtime') AND start_time <= datetime('now','localtime','+30 minutes') ORDER BY start_time",
        "title",
        (),
    ),
}


class AutomationRunner:
    """Reads automations.yaml and executes due rules on each scheduler tick."""

    def __init__(self, engine):
        self._engine = engine
        self._rules: list[dict] = []
        self._settings: dict = {}
        self._state: dict[str, Any] = {}
        self._last_state_write = datetime.min
        self._load_state()
        self._load_rules()

    # ── Public ────────────────────────────────────────────────────────────

    def run(self):
        """Called by scheduler every ~30s. Delivers retries then runs due rules."""
        if not self._rules:
            return

        recipient = str(self._settings.get("whatsapp_recipient") or "")
        retry_pending()

        now = datetime.now()

        for rule in self._rules:
            try:
                self._run_rule(rule, now, recipient)
            except Exception as e:
                logger.error("Rule '%s' failed: %s", rule.get("id", "?"), e)

    # ── Rule execution ────────────────────────────────────────────────────

    def _run_rule(self, rule: dict, now: datetime, recipient: str):
        if not self._is_due(rule, now):
            return

        rule_id = rule.get("id", "unknown")

        # State tracking — skip if no change (for interval alerts)
        if rule.get("state_track"):
            current_fp = self._compute_fingerprint(rule)
            if not self._state_changed(rule_id, current_fp):
                return
            self._state[rule_id] = {"fingerprint": current_fp, "last_alerted": now.isoformat()}
            self._save_state()

        # Execute sections
        sections = []
        for section_def in rule.get("sections", []):
            result = self._execute_section(section_def)
            if result is not None:
                sections.append(result)

        if not sections:
            return

        # Check min_items threshold
        total_items = sum(len(s.get("items", [])) for s in sections)
        if total_items < rule.get("min_items", 0):
            return

        message = build_brief_message(sections)
        if not message:
            return

        deliver_all(message, rule_id, rule.get("name", "Automation"), recipient)

    # ── Schedule check ────────────────────────────────────────────────────

    def _is_due(self, rule: dict, now: datetime) -> bool:
        sched = rule.get("schedule", "")
        if isinstance(sched, str):
            try:
                h, m = sched.strip().split(":")
                return now.hour == int(h) and now.minute == int(m)
            except (ValueError, AttributeError):
                return False
        if isinstance(sched, dict) and sched.get("type") == "interval":
            seconds = int(sched.get("seconds", 300))
            total_secs = now.hour * 3600 + now.minute * 60 + now.second
            return total_secs % seconds < 30
        return False

    # ── State tracking ────────────────────────────────────────────────────

    def _compute_fingerprint(self, rule: dict) -> str:
        """Run rule's queries and produce a deterministic hash of results."""
        items = []
        for sec in rule.get("sections", []):
            if sec.get("type") in ("greeting", "llm_opener"):
                continue
            qname = sec.get("query", "")
            data = self._query_db(qname)
            items.append({qname: [dict(r) for r in data]})
        return json.dumps(items, sort_keys=True, default=str)

    def _state_changed(self, rule_id: str, current_fp: str) -> bool:
        prev = self._state.get(rule_id, {}).get("fingerprint", "")
        return current_fp != prev

    # ── Section execution ─────────────────────────────────────────────────

    def _execute_section(self, sec: dict) -> Optional[dict]:
        stype = sec.get("type", "query")
        if stype == "greeting":
            return {"formatted": generate_greeting(), "items": []}
        if stype == "llm_opener":
            tasks_due = len(self._query_db("tasks_due_today"))
            overdue = len(self._query_db("overdue_tasks"))
            habits_at_risk = len(self._query_db("habits_at_risk"))
            opener = generate_opener(tasks_due, overdue, habits_at_risk, 0)
            if opener:
                return {"formatted": opener, "items": []}
            return None
        if stype == "query":
            qname = sec.get("query", "")
            label = sec.get("label", "")
            empty_msg = sec.get("empty_msg", "")
            data = self._query_db(qname)
            items = [self._format_item(row, qname) for row in data]
            formatted = format_section(items, label, empty_msg)
            if formatted:
                return {"formatted": formatted, "items": items}
            return None
        return None

    # ── DB queries ────────────────────────────────────────────────────────

    def _query_db(self, query_name: str) -> list[dict]:
        spec = QUERIES.get(query_name)
        if not spec:
            logger.warning("Unknown query: %s", query_name)
            return []
        try:
            db_name, sql, _, params = spec
            return db.query(db_name, sql, params)
        except Exception as e:
            logger.warning("Query '%s' failed: %s", query_name, e)
            return []

    def _format_item(self, row: dict, query_name: str) -> str:
        spec = QUERIES.get(query_name)
        if not spec or len(spec) < 3:
            return str(row)
        field = spec[2]
        val = row.get(field, "")
        extras = []
        if query_name in ("overdue_tasks", "tasks_due_today", "tasks_remaining"):
            if row.get("due_date"):
                extras.append(f"({row['due_date']})")
            if row.get("priority") and row["priority"] not in (None, "medium"):
                extras.append(f"[{row['priority']}]")
        if query_name in ("habits_at_risk",):
            if row.get("current_streak") is not None:
                extras.append(f"streak:{row['current_streak']}")
            if row.get("last_completed"):
                extras.append(f"last:{row['last_completed']}")
        if query_name == "goals_near_deadline" and row.get("deadline"):
            extras.append(f"até {row['deadline']}")
        if query_name in ("calendar_today", "calendar_upcoming") and row.get("start_time"):
            extras.append(row["start_time"])
        if query_name == "habits_today_status":
            status = row.get("status", "⬜")
            return f"{status} {val}"
        suffix = f" {', '.join(extras)}" if extras else ""
        return f"{val}{suffix}"

    # ── State persistence ─────────────────────────────────────────────────

    def _load_state(self):
        if STATE_FILE.exists():
            try:
                self._state = json.loads(STATE_FILE.read_text())
            except (json.JSONDecodeError, OSError):
                self._state = {}
        else:
            self._state = {}

    def _save_state(self):
        now = datetime.now()
        if (now - self._last_state_write).total_seconds() < 10:
            return  # rate-limit writes
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(self._state, ensure_ascii=False, indent=2))
        self._last_state_write = now

    # ── Config loading ────────────────────────────────────────────────────

    def _load_rules(self):
        if not CONFIG_PATH.exists():
            logger.warning("automations.yaml not found at %s", CONFIG_PATH)
            return
        try:
            with open(CONFIG_PATH) as f:
                data = yaml.safe_load(f)
            self._settings = data.get("settings", {}) if data else {}
            self._rules = data.get("automations", []) if data else []
            logger.info("Loaded %d automation rules", len(self._rules))
        except Exception as e:
            logger.error("Failed to load automations.yaml: %s", e)
            self._rules = []
