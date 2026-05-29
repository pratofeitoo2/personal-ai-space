# Personal Automations — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers-optimized:subagent-driven-development (recommended) or superpowers-optimized:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add YAML-driven personal automations (morning brief, checkpoints, real-time alerts) delivered via WhatsApp.
**Architecture:** A new `engine/automations/` module with three internal units (runner, delivery, templates) plus a YAML config file. The scheduler gets one new job that calls `AutomationRunner.run()` every 30s. Reuses existing DataHub, LLM bridge, and WhatsApp bridge.
**Tech Stack:** Python 3.11+, PyYAML, requests, existing db_manager + DataHub
**Assumptions:** WhatsApp bridge runs at `localhost:8080` — if the port changes, `delivery.py` needs a config update. Recipient number is configured in `automations.yaml` — automations are silently skipped if missing.

---

## File Structure

```
engine/
  automations/
    __init__.py          # package marker
    delivery.py          # WhatsApp send + pending retry queue
    templates.py         # message section builders (format_section, build_brief_message, greeting, LLM opener)
    runner.py            # AutomationRunner — reads YAML, checks schedules, tracks state, executes rules
  config/
    automations.yaml     # declarative automation rules
  orchestrator/
    scheduler.py         # +1 job entry (MODIFY)
```

---

### Task 1: delivery.py — WhatsApp send + retry queue

**Files:**
- Create: `engine/automations/__init__.py`
- Create: `engine/automations/delivery.py`
- Create: `engine/tests/test_automations_delivery.py`

**Security flag:** `none`

**Does NOT cover:** Authentication with WhatsApp bridge (bridge handles auth at its layer). Message length > 4096 chars (bridge truncates, not our concern).

- [ ] **Step 1: Write failing tests**

```python
"""Tests for automations/delivery.py"""
from pathlib import Path
import json, tempfile, pytest
from unittest.mock import patch, Mock

from automations.delivery import send_whatsapp, enqueue_pending, retry_pending


class TestSendWhatsApp:
    def test_sends_post_to_bridge(self):
        with patch("automations.delivery.requests.post") as mock_post:
            mock_post.return_value.ok = True
            result = send_whatsapp("hello", "+5511999999999")
            assert result is True
            mock_post.assert_called_once()
            args, kwargs = mock_post.call_args
            assert "http://localhost:8080/api/send" in args[0]
            assert kwargs["json"]["recipient"] == "+5511999999999"
            assert kwargs["json"]["message"] == "hello"

    def test_returns_false_on_connection_error(self):
        with patch("automations.delivery.requests.post") as mock_post:
            from requests import ConnectionError
            mock_post.side_effect = ConnectionError()
            result = send_whatsapp("hello", "+5511999999999")
            assert result is False

    def test_returns_false_on_http_error(self):
        with patch("automations.delivery.requests.post") as mock_post:
            mock_post.return_value.ok = False
            mock_post.return_value.status_code = 500
            result = send_whatsapp("hello", "+5511999999999")
            assert result is False

    def test_returns_false_on_empty_recipient(self):
        result = send_whatsapp("hello", "")
        assert result is False


class TestEnqueuePending:
    def test_writes_to_pending_file(self, tmp_path):
        with patch("automations.delivery.PENDING_FILE", tmp_path / "pending.json"):
            enqueue_pending("test msg", "+5511999999999")
            data = json.loads((tmp_path / "pending.json").read_text())
            assert len(data) == 1
            assert data[0]["text"] == "test msg"
            assert data[0]["retry_count"] == 0

    def test_appends_to_existing_pending(self, tmp_path):
        pf = tmp_path / "pending.json"
        pf.write_text(json.dumps([{"text": "old", "recipient": "+55", "failed_at": "x", "retry_count": 0}]))
        with patch("automations.delivery.PENDING_FILE", pf):
            enqueue_pending("new msg", "+5511999999999")
            data = json.loads(pf.read_text())
            assert len(data) == 2

    def test_keeps_only_last_50(self, tmp_path):
        pf = tmp_path / "pending.json"
        old = [{"text": str(i), "recipient": "+55", "failed_at": "x", "retry_count": 0} for i in range(55)]
        pf.write_text(json.dumps(old))
        with patch("automations.delivery.PENDING_FILE", pf):
            enqueue_pending("newest", "+5511999999999")
            data = json.loads(pf.read_text())
            assert len(data) == 50
            assert data[-1]["text"] == "newest"


class TestRetryPending:
    def test_delivers_pending_and_removes(self, tmp_path):
        pf = tmp_path / "pending.json"
        pf.write_text(json.dumps([{"text": "m1", "recipient": "+55", "failed_at": "x", "retry_count": 0}]))
        with patch("automations.delivery.PENDING_FILE", pf), \
             patch("automations.delivery.send_whatsapp", return_value=True):
            count = retry_pending()
            assert count == 1
            assert json.loads(pf.read_text()) == []

    def test_increments_retry_count_on_failure(self, tmp_path):
        pf = tmp_path / "pending.json"
        pf.write_text(json.dumps([{"text": "m1", "recipient": "+55", "failed_at": "x", "retry_count": 0}]))
        with patch("automations.delivery.PENDING_FILE", pf), \
             patch("automations.delivery.send_whatsapp", return_value=False):
            count = retry_pending()
            assert count == 0
            data = json.loads(pf.read_text())
            assert data[0]["retry_count"] == 1

    def test_discards_after_3_retries(self, tmp_path):
        pf = tmp_path / "pending.json"
        pf.write_text(json.dumps([{"text": "m1", "recipient": "+55", "failed_at": "x", "retry_count": 3}]))
        with patch("automations.delivery.PENDING_FILE", pf), \
             patch("automations.delivery.send_whatsapp") as mock_send:
            count = retry_pending()
            assert count == 0
            mock_send.assert_not_called()
            assert json.loads(pf.read_text()) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd personal-ai-space/engine && python -m pytest tests/test_automations_delivery.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'automations'`

- [ ] **Step 3: Implement delivery.py**

```python
# engine/automations/__init__.py
"""Automation engine — briefings, checkpoints, and real-time alerts."""
```

```python
# engine/automations/delivery.py
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
    if PENDING_FILE.exists():
        try:
            return json.loads(PENDING_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            return []
    return []
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd personal-ai-space/engine && python -m pytest tests/test_automations_delivery.py -v`
Expected: PASS (all tests)

- [ ] **Step 5: Commit**

```bash
git add engine/automations/__init__.py engine/automations/delivery.py engine/tests/test_automations_delivery.py
git commit -m "feat(automations): delivery module — WhatsApp send + pending retry queue"
```

---

### Task 2: templates.py — Message section builders

**Files:**
- Create: `engine/automations/templates.py`
- Create: `engine/tests/test_automations_templates.py`

**Security flag:** `none`

**Does NOT cover:** HTML/markdown rendering in WhatsApp (plain text only). LLM opener — templates.py delegates to llm_bridge; that module's offline behavior is already handled there.

- [ ] **Step 1: Write failing tests**

```python
"""Tests for automations/templates.py"""
from datetime import datetime
from unittest.mock import patch
import pytest

from automations.templates import (
    format_section, build_brief_message, generate_greeting,
)


class TestFormatSection:
    def test_returns_formatted_with_items(self):
        result = format_section(["item 1", "item 2"], "📋 Lista")
        assert result is not None
        assert "📋 Lista" in result
        assert "• item 1" in result
        assert "• item 2" in result

    def test_returns_empty_msg_when_no_items(self):
        result = format_section([], "📋 Lista", empty_msg="Nada aqui")
        assert result == "Nada aqui"

    def test_returns_none_when_no_items_and_no_empty_msg(self):
        result = format_section([], "📋 Lista")
        assert result is None

    def test_formats_single_item(self):
        result = format_section(["only one"], "📋 Lista")
        assert "• only one" in result


class TestBuildBriefMessage:
    def test_joins_sections_with_double_newline(self):
        sections = [
            {"formatted": "Section 1", "items": []},
            {"formatted": "Section 2", "items": ["a"]},
        ]
        result = build_brief_message(sections)
        assert result == "Section 1\n\nSection 2"

    def test_skips_empty_formatted(self):
        sections = [
            {"formatted": "", "items": []},
            {"formatted": "Only this", "items": ["x"]},
        ]
        result = build_brief_message(sections)
        assert result == "Only this"

    def test_returns_empty_string_for_no_sections(self):
        assert build_brief_message([]) == ""

    def test_returns_empty_string_if_all_empty(self):
        sections = [{"formatted": "", "items": []}, {"formatted": "", "items": []}]
        assert build_brief_message(sections) == ""


class TestGenerateGreeting:
    def test_morning_before_12(self):
        with patch("automations.templates.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 5, 29, 7, 0, 0)
            assert "Bom dia" in generate_greeting()

    def test_afternoon_12_to_18(self):
        with patch("automations.templates.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 5, 29, 14, 0, 0)
            assert "Boa tarde" in generate_greeting()

    def test_night_after_18(self):
        with patch("automations.templates.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 5, 29, 20, 0, 0)
            assert "Boa noite" in generate_greeting()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd personal-ai-space/engine && python -m pytest tests/test_automations_templates.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'automations.templates'`

- [ ] **Step 3: Implement templates.py**

```python
# engine/automations/templates.py
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
    return enrich_digest_opener(tasks_due, overdue, habits_at_risk, habit_count)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd personal-ai-space/engine && python -m pytest tests/test_automations_templates.py -v`
Expected: PASS (all tests)

- [ ] **Step 5: Commit**

```bash
git add engine/automations/templates.py engine/tests/test_automations_templates.py
git commit -m "feat(automations): templates module — message formatting + LLM opener"
```

---

### Task 3: automations.yaml config file

**Files:**
- Create: `engine/config/automations.yaml`

**Security flag:** `none`

- [ ] **Step 1: Write automations.yaml**

```yaml
# Personal AI Automations — declarative rules
# Schedule types: "HH:MM" (daily at time), {type: interval, seconds: N}
# state_track: true → only alerts on state change (for interval rules)

settings:
  whatsapp_recipient: ""                     # ← SET YOUR NUMBER
  timezone: "America/Sao_Paulo"

automations:

  - id: morning_brief
    name: "Briefing Matinal"
    schedule: "07:00"
    sections:
      - {type: greeting}
      - {type: llm_opener}
      - {query: tasks_due_today,      label: "📋 Tarefas do dia",     empty_msg: "Nenhuma tarefa para hoje"}
      - {query: calendar_today,       label: "📅 Agenda de hoje",     empty_msg: "Sem compromissos hoje"}
      - {query: habits_at_risk,       label: "🎯 Hábitos em risco",   empty_msg: "Todos os hábitos em dia"}
      - {query: goals_active,         label: "🎯 Metas ativas",       empty_msg: "Nenhuma meta ativa no momento"}

  - id: midday_checkpoint
    name: "Checkpoint Meio-dia"
    schedule: "12:00"
    sections:
      - {type: greeting}
      - {query: tasks_remaining,      label: "📋 Restam do dia",      empty_msg: "Tarefas todas concluídas!"}
      - {query: habits_today_status,  label: "🎯 Hábitos hoje",       empty_msg: "Nenhum hábito registrado ainda hoje"}
      - {query: habits_at_risk,       label: "⚠️ Hábitos em risco",   empty_msg: ""}

  - id: end_of_day
    name: "Fechamento do Dia"
    schedule: "18:00"
    sections:
      - {query: tasks_completed_today, label: "✅ Concluído hoje",    empty_msg: "Nenhuma tarefa concluída hoje"}
      - {query: habits_completed_today,label: "💪 Hábitos do dia",    empty_msg: "Nenhum hábito hoje"}

  - id: alert_overdue_tasks
    name: "Tarefas Atrasadas"
    schedule: {type: interval, seconds: 60}
    state_track: true
    min_items: 1
    sections:
      - {query: overdue_tasks,        label: "⚠️ Tarefas atrasadas",  empty_msg: ""}

  - id: alert_habits_at_risk
    name: "Hábitos em Risco"
    schedule: {type: interval, seconds: 300}
    state_track: true
    min_items: 1
    sections:
      - {query: habits_at_risk,       label: "⚠️ Hábitos precisando de atenção", empty_msg: ""}

  - id: alert_calendar_soon
    name: "Agenda Iminente"
    schedule: {type: interval, seconds: 120}
    state_track: true
    min_items: 1
    sections:
      - {query: calendar_upcoming,    label: "🔔 Em breve na agenda", empty_msg: ""}

  - id: alert_goal_deadlines
    name: "Metas Próximas do Prazo"
    schedule: {type: interval, seconds: 3600}
    state_track: true
    min_items: 1
    sections:
      - {query: goals_near_deadline,  label: "🎯 Metas perto do prazo", empty_msg: ""}
```

- [ ] **Step 2: Validate YAML parses correctly**

Run: `cd personal-ai-space/engine && python -c "import yaml; yaml.safe_load(open('config/automations.yaml')); print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add engine/config/automations.yaml
git commit -m "feat(automations): rule definitions — brief, checkpoints, alerts"
```

---

### Task 4: runner.py — Automation rule engine

**Files:**
- Create: `engine/automations/runner.py`
- Create: `engine/tests/test_automations_runner.py`

**Security flag:** `none`

**Does NOT cover:** Graceful handling of missing tables in db queries (db_manager.query already returns empty list on error). Multi-instance engine (state file locking — not needed for single-thread scheduler).

- [ ] **Step 1: Write failing tests**

```python
"""Tests for automations/runner.py"""
import json
from datetime import datetime
from unittest.mock import Mock, patch, PropertyMock
import pytest
import yaml

from automations.runner import AutomationRunner


SAMPLE_RULES = """
settings:
  whatsapp_recipient: "+5511999999999"
  timezone: "America/Sao_Paulo"

automations:
  - id: test_brief
    name: "Test"
    schedule: "07:00"
    sections:
      - {type: greeting}
      - {query: tasks_due_today, label: "📋 Test", empty_msg: ""}

  - id: test_alert
    name: "Test Alert"
    schedule: {type: interval, seconds: 60}
    state_track: true
    min_items: 1
    sections:
      - {query: overdue_tasks, label: "⚠️ Overdue", empty_msg: ""}
"""


@pytest.fixture
def runner(tmp_path):
    eng = Mock()
    eng._hub = Mock()
    # Point runner to a temp config
    cfg = tmp_path / "automations.yaml"
    cfg.write_text(SAMPLE_RULES)
    r = AutomationRunner.__new__(AutomationRunner)
    r._engine = eng
    r._rules = []
    r._state = {}
    r._settings = {}
    r._last_state_write = datetime.min
    r.STATE_FILE = tmp_path / "state.json"
    r._load_rules = lambda: None  # skip file loading in test
    return r


class TestIsDue:
    def test_daily_time_exact_match(self, runner):
        runner._rules = [{"schedule": "07:00"}]
        dt = datetime(2026, 5, 29, 7, 0, 0)
        assert runner._is_due(runner._rules[0], dt)

    def test_daily_time_wrong_hour(self, runner):
        runner._rules = [{"schedule": "07:00"}]
        dt = datetime(2026, 5, 29, 8, 0, 0)
        assert not runner._is_due(runner._rules[0], dt)

    def test_interval_within_window(self, runner):
        runner._rules = [{"schedule": {"type": "interval", "seconds": 60}}]
        dt = datetime(2026, 5, 29, 10, 0, 15)
        assert runner._is_due(runner._rules[0], dt)

    def test_interval_outside_window(self, runner):
        runner._rules = [{"schedule": {"type": "interval", "seconds": 60}}]
        dt = datetime(2026, 5, 29, 10, 0, 45)
        assert not runner._is_due(runner._rules[0], dt)


class TestStateChange:
    def test_detects_change(self, runner):
        runner._state["alert"] = {"fingerprint": json.dumps(["a"], sort_keys=True)}
        changed = runner._state_changed("alert", json.dumps(["b"], sort_keys=True))
        assert changed is True

    def test_no_change(self, runner):
        runner._state["alert"] = {"fingerprint": json.dumps(["a"], sort_keys=True)}
        changed = runner._state_changed("alert", json.dumps(["a"], sort_keys=True))
        assert changed is False

    def test_first_run_detects_change(self, runner):
        changed = runner._state_changed("new_alert", json.dumps(["a"], sort_keys=True))
        assert changed is True


class TestLoadRules:
    def test_parses_valid_yaml(self, tmp_path):
        cfg = tmp_path / "automations.yaml"
        cfg.write_text(SAMPLE_RULES)
        eng = Mock()
        r = AutomationRunner(eng)
        with patch("automations.runner.CONFIG_PATH", cfg), \
             patch("automations.runner.STATE_FILE", tmp_path / "state.json"):
            r._load_rules()
            assert len(r._rules) == 2
            assert r._settings["whatsapp_recipient"] == "+5511999999999"

    def test_no_file_doesnt_crash(self, tmp_path):
        eng = Mock()
        r = AutomationRunner(eng)
        with patch("automations.runner.CONFIG_PATH", tmp_path / "nonexistent.yaml"), \
             patch("automations.runner.STATE_FILE", tmp_path / "state.json"):
            r._load_rules()
            assert r._rules == []


class TestStatePersistence:
    def test_saves_and_loads_state(self, tmp_path):
        sf = tmp_path / "state.json"
        eng = Mock()
        r = AutomationRunner(eng)
        with patch("automations.runner.CONFIG_PATH", tmp_path / "nonexistent.yaml"), \
             patch("automations.runner.STATE_FILE", sf):
            r._state = {"alert": {"fingerprint": "abc", "last_alerted": "2026-01-01"}}
            r._save_state()
            r2 = AutomationRunner(eng)
            with patch("automations.runner.CONFIG_PATH", tmp_path / "nonexistent.yaml"), \
                 patch("automations.runner.STATE_FILE", sf):
                assert r2._state.get("alert", {}).get("fingerprint") == "abc"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd personal-ai-space/engine && python -m pytest tests/test_automations_runner.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'automations.runner'`

- [ ] **Step 3: Implement runner.py**

```python
# engine/automations/runner.py
"""Automation rule engine — reads YAML rules, checks schedules, executes."""
import json
import logging
from datetime import datetime, time
from pathlib import Path
from typing import Any, Optional

import yaml

# Import project modules
from log_manager import get_logger
import db_manager as db
from automations.delivery import send_whatsapp, enqueue_pending, retry_pending
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

QUERIES: dict[str, tuple[str, str, str, tuple]] = {
    # (db_name, sql, format_field, params)
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
        if not recipient:
            return

        # Retry any previously failed deliveries
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

        ok = send_whatsapp(message, recipient)
        if not ok:
            enqueue_pending(message, recipient)

    # ── Schedule check ────────────────────────────────────────────────────

    def _is_due(self, rule: dict, now: datetime) -> bool:
        sched = rule.get("schedule", "")
        if isinstance(sched, str):
            # Daily at "HH:MM"
            try:
                h, m = sched.strip().split(":")
                return now.hour == int(h) and now.minute == int(m)
            except (ValueError, AttributeError):
                return False
        if isinstance(sched, dict) and sched.get("type") == "interval":
            seconds = int(sched.get("seconds", 300))
            total_secs = now.hour * 3600 + now.minute * 60 + now.second
            return total_secs % seconds < 30  # within scheduler tick window
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
        # Add extra context when available
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd personal-ai-space/engine && python -m pytest tests/test_automations_runner.py -v`
Expected: PASS (all tests)

- [ ] **Step 5: Commit**

```bash
git add engine/automations/runner.py engine/tests/test_automations_runner.py
git commit -m "feat(automations): runner module — schedule check, state tracking, query dispatch"
```

---

### Task 5: Scheduler integration

**Files:**
- Modify: `engine/orchestrator/scheduler.py`

**Security flag:** `none`

- [ ] **Step 1: Add automation_runner job to scheduler.py**

Insert after the `archive_tasks` job entry (around line 101):

```python
        self._jobs.append({
            "name": "automation_runner",
            "handler": self._run_automations,
            "type": "interval",
            "interval_minutes": 0.5,
        })
```

Add the handler method anywhere in the handler section (after `_run_task_archiver`):

```python
    def _run_automations(self):
        """Run automation rules — briefings, checkpoints, real-time alerts."""
        try:
            from automations.runner import AutomationRunner
            if hasattr(self, '_automation_runner'):
                self._automation_runner.run()
            else:
                self._automation_runner = AutomationRunner(self._engine)
                self._automation_runner.run()
        except ImportError as e:
            logger.debug("automations module not available: %s", e)
        except Exception as e:
            logger.error("automation_runner failed: %s", e)
```

- [ ] **Step 2: Verify scheduler starts without error**

Run: `cd personal-ai-space/engine && python -c "from unittest.mock import Mock; from orchestrator.scheduler import Scheduler; s = Scheduler(Mock()); s.start(); print('OK')"`
Expected: `OK` (scheduler loads, including automation_runner job)

- [ ] **Step 3: Commit**

```bash
git add engine/orchestrator/scheduler.py
git commit -m "feat(scheduler): add automation_runner job (30s interval)"
```

---

### Task 6: Integration verification

**Security flag:** `none`

- [ ] **Step 1: Run all automation tests**

Run: `cd personal-ai-space/engine && python -m pytest tests/test_automations_delivery.py tests/test_automations_templates.py tests/test_automations_runner.py -v`
Expected: PASS (all tests)

- [ ] **Step 2: Validate YAML schema**

Run: `cd personal-ai-space/engine && python -c "import yaml; d=yaml.safe_load(open('config/automations.yaml')); rules=d.get('automations',[]); print(f'{len(rules)} rules'); assert all(r.get('id') and r.get('schedule') and r.get('sections') for r in rules); print('validation OK')"`
Expected: `7 rules\nvalidation OK`

- [ ] **Step 3: Verify state file persistence**

Run: `cd personal-ai-space/engine && python -c "
from automations.runner import AutomationRunner
from unittest.mock import Mock
r = AutomationRunner(Mock())
r._state = {'test': {'fingerprint': 'abc', 'last_alerted': 'x'}}
r._save_state()
r2 = AutomationRunner(Mock())
print('state preserved:', r2._state.get('test', {}).get('fingerprint') == 'abc')
"`
Expected: `state preserved: True`

- [ ] **Step 4: Run full test suite for regression**

Run: `cd personal-ai-space/engine && python -m pytest tests/ -v --tb=short 2>&1 | tail -20`
Expected: All pre-existing tests still pass

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "test(automations): integration verification — all tests pass"
```
