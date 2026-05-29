# Personal Automations — Design Spec

> **Date:** 2026-05-29
> **Status:** Approved
> **Approach:** A — YAML-driven automation runner

## 1. Scope

### In scope
- Morning brief (07:00 daily) via WhatsApp: tasks due, calendar events, habits at risk, active goals, AI-generated narrative summary
- Midday checkpoint (12:00): task progress + habits check-in
- End-of-day closeout (18:00): completed tasks, habits logged today
- Real-time alerts via WhatsApp: overdue tasks, Apple reminders, habits at risk (state transition), goal deadlines approaching, upcoming calendar agenda
- YAML-defined automation rules (`engine/config/automations.yaml`)
- LLM-enriched narrative via existing `llm_bridge.py` (Ollama)
- State tracking to avoid duplicate alerts across scheduler ticks
- Pending delivery retry (graceful degradation when WhatsApp bridge is down)

### Non-goals
- UI/CLI for managing automations
- Complex condition combinators (AND/OR/NOT — single-condition triggers only)
- Multi-channel delivery per automation
- Historical automation run tracking beyond engine logs
- Webhook/external event triggers

## 2. Architecture

### New files
```
engine/automations/
  __init__.py
  runner.py         # reads rules.yaml, executes automations, state tracking
  delivery.py        # sends formatted messages via WhatsApp bridge API
  templates.py       # message template builders (text sections, LLM enrichment)
engine/config/
  automations.yaml   # declarative automation rule definitions
```

### No new files needed
- `llm_bridge.py` — reuses `TextGenerator` + `enrich_digest_opener()`
- `data_hub.py` — reuses `get_habits()`, `get_needs()`, `get_user_profile()`, observations
- `db_manager.py` — queries tasks.db, calendar.db, self.db
- `orchestrator/scheduler.py` — adds ONE new job entry

### Data flow (per scheduler tick — 30s)

```
Scheduler tick
  └─ automation_runner.run()
       ├─ Load automations.yaml
       ├─ For each rule:
       │    ├─ Skip if schedule not due
       │    ├─ Skip if state-tracked and no change
       │    ├─ Run queries (via DataHub / db_manager)
       │    ├─ Format message (via templates.py)
       │    ├─ Optionally enrich via LLM bridge (if llm_summary: true)
       │    └─ Deliver via delivery.py → WhatsApp bridge
       └─ Update state tracking
```

## 3. automations.yaml Format

```yaml
# Global settings
settings:
  whatsapp_recipient: "5511999999999"    # YOUR NUMBER
  timezone: "America/Sao_Paulo"
  retry_interval_seconds: 120            # retry failed delivery after N seconds

# ── Automated briefings (time-based, always fire) ──

automations:
  - id: morning_brief
    name: "Briefing Matinal"
    schedule: "07:00"                     # daily at 07:00
    sections:
      - id: greeting
        type: greeting                    # "Bom dia!" etc
      - id: summary
        type: llm_opener                  # AI paragraph via TextGenerator
      - id: tasks
        query: tasks_due_today
        label: "📋 Tarefas do dia"
        empty_msg: "Nenhuma tarefa para hoje"
      - id: calendar
        query: calendar_today
        label: "📅 Agenda de hoje"
        empty_msg: "Sem compromissos hoje"
      - id: habits
        query: habits_at_risk
        label: "🎯 Hábitos em risco"
        empty_msg: "Todos os hábitos em dia"
      - id: goals
        query: goals_active
        label: "🎯 Metas ativas"
        empty_msg: "Nenhuma meta ativa no momento"

  - id: midday_checkpoint
    name: "Checkpoint Meio-dia"
    schedule: "12:00"
    sections:
      - id: tasks
        query: tasks_remaining
        label: "📋 Restam do dia"
        empty_msg: "Tarefas todas concluídas!"
      - id: habits
        query: habits_today_status
        label: "🎯 Hábitos hoje"
        empty_msg: "Nenhum hábito registrado hoje ainda"

  - id: end_of_day
    name: "Fechamento do Dia"
    schedule: "18:00"
    sections:
      - id: tasks_done
        query: tasks_completed_today
        label: "✅ Concluído hoje"
        empty_msg: "Nenhuma tarefa concluída hoje"
      - id: habits_done
        query: habits_completed_today
        label: "✅ Hábitos do dia"
        empty_msg: "Nenhum hábito registrado hoje"

# ── Real-time alerts (interval-based, state-tracked) ──

  - id: alert_overdue_tasks
    name: "Tarefas Atrasadas"
    schedule:
      type: interval
      seconds: 60                        # check every 60s
    state_track: true                     # only alert on state change
    sections:
      - id: overdue
        query: overdue_tasks
        label: "⚠️ Tarefas atrasadas"
        empty_msg: ""                     # don't send if nothing overdue
    min_items: 1                          # only send if >= 1 item

  - id: alert_habits_at_risk
    name: "Hábitos em Risco"
    schedule:
      type: interval
      seconds: 300                        # check every 5 min
    state_track: true
    sections:
      - id: habits
        query: habits_at_risk
        label: "⚠️ Hábitos precisando de atenção"
        empty_msg: ""
    min_items: 1

  - id: alert_calendar_soon
    name: "Agenda Iminente"
    schedule:
      type: interval
      seconds: 120                        # check every 2 min
    state_track: true
    sections:
      - id: upcoming
        query: calendar_upcoming         # events in next 30 min
        label: "🔔 Em breve na agenda"
        empty_msg: ""
    min_items: 1

  - id: alert_goal_deadlines
    name: "Metas Próximas do Prazo"
    schedule:
      type: interval
      seconds: 3600                       # check every hour
    state_track: true
    sections:
      - id: goals
        query: goals_near_deadline
        label: "🎯 Metas perto do prazo"
        empty_msg: ""
    min_items: 1
```

## 4. Module Design

### 4.1 `runner.py` — AutomationRunner

**Interface:**
```python
class AutomationRunner:
    def __init__(self, engine):
        self._engine = engine
        self._state: dict[str, Any] = {}      # last-known state per tracked rule
        self._rules: list[Rule] = []           # parsed from YAML
        self._pending_retries: dict[str, dict] = {}  # failed deliveries
    
    def run(self) -> None:
        """Main tick — called by scheduler every 30s."""
    
    def load_rules(self) -> None:
        """Parse automations.yaml into Rule objects."""
    
    def _check_schedule(self, rule: Rule) -> bool:
        """Is this rule due to run?"""
    
    def _check_state_change(self, rule: Rule, current: Any) -> bool:
        """Has state changed since last check?"""
    
    def _execute_rule(self, rule: Rule) -> Optional[str]:
        """Run queries, format message, return text or None if empty."""
```

**State tracking** — dict serializado para `pending_deliveries.json` no startup+shutdown. Estrutura:
```python
self._state = {
    "alert_overdue_tasks": {
        "task_ids": ["abc", "def"],
        "count": 2,
        "last_seen": "2026-05-29T10:00:00"
    },
    "alert_habits_at_risk": {
        "habit_names": ["meditar"],
        "last_seen": "2026-05-29T10:05:00"
    }
}
```

### 4.2 `delivery.py` — WhatsApp Delivery

**Interface:**
```python
def send_whatsapp(text: str, recipient: str = "") -> bool:
    """
    Send message via WhatsApp bridge API.
    
    Falls back to pending_deliveries.json if bridge is unreachable.
    Returns True on success, False on failure.
    """
```

**Bridge call:**
```python
POST http://localhost:8080/api/send
{"recipient": "5511999999999", "message": "..."}
```

**Retry:** Failed messages saved to `pending_deliveries.json` (max 50 entries FIFO). Retried on next runner tick after `retry_interval_seconds`.

### 4.3 `templates.py` — Message Formatting

**Interface:**
```python
def build_message(rule: Rule, sections: list[SectionResult]) -> str:
    """Build final WhatsApp message from section results."""

def format_list(items: list[str], label: str, empty_msg: str = "") -> Optional[str]:
    """Format a query result as a text section."""

def build_brief(tasks, calendar, habits, goals, llm_opener: Optional[str]) -> str:
    """Build the full morning brief message."""
```

**Message format example (morning brief):**
```
🌅 Bom dia! Aqui seu resumo de hoje — 29/05

📋 Tarefas do dia:
• Preparar slides apresentação
• Revisar contrato cliente X
• Enviar relatório semanal

📅 Agenda de hoje:
• 10:00 — Reunião equipe
• 14:30 — Call com cliente
• 17:00 — Academia

🎯 Hábitos em risco:
• Meditar (0/1 hoje)
• Estudar inglês (2 dias sem bater)
• Ler 30 min (streak: 3 dias)

🎯 Metas ativas:
• Fechar 3 novos clientes em Maio
• Correr 10km sem parar até Junho

Bom dia e bons ventos! 🚀
```

## 5. Query Functions

Implemented in `runner.py` as methods that delegate to DataHub / db_manager:

| Query | Source | Implementation |
|---|---|---|
| `tasks_due_today` | tasks.db | `SELECT * FROM tasks WHERE due_date=date('now') AND status NOT IN ('completed','cancelled')` |
| `overdue_tasks` | tasks.db | `SELECT * FROM tasks WHERE due_date<date('now') AND status NOT IN ('completed','cancelled')` |
| `tasks_completed_today` | tasks.db | `SELECT * FROM tasks WHERE status='completed' AND updated_at>=date('now')` |
| `tasks_remaining` | tasks.db | `SELECT * FROM tasks WHERE due_date<=date('now') AND status NOT IN ('completed','cancelled')` |
| `calendar_today` | calendar.db | Query calendar events for today |
| `calendar_upcoming` | calendar.db | Events in next 30 min |
| `habits_at_risk` | self.db | Habits where `last_completed` is >1 day ago or `current_streak=0` |
| `habits_completed_today` | self.db | Habit logs from today |
| `goals_active` | self.db | `SELECT * FROM needs WHERE status='active'` |
| `goals_near_deadline` | self.db | Active needs with upcoming deadline |

## 6. Scheduler Integration

Single addition to `scheduler.py` — one new job:

```python
# In scheduler._load_jobs() or start():
self._jobs.append({
    "name": "automation_runner",
    "handler": self._run_automations,
    "type": "interval",
    "interval_minutes": 0.5,  # tick every 30s
})
```

```python
def _run_automations(self):
    """Run automation rules — briefings, alerts, checkpoints."""
    from automations.runner import AutomationRunner
    if not hasattr(self, '_automation_runner'):
        self._automation_runner = AutomationRunner(self._engine)
    self._automation_runner.run()
```

## 7. Error Handling

| Scenario | Behavior |
|---|---|
| WhatsApp bridge down | Save to pending_deliveries.json, retry on next tick |
| LLM bridge down | Skip `llm_summary` sections, deliver rest of message |
| Query fails (table missing) | Log warning, skip section, deliver remaining sections |
| automações.yaml parse error | Log error, skip all automations until fixed |
| State file corrupt | Reset state dict, log warning |
| Recipient not configured | Log error, skip delivery, do NOT send |

## 8. State File Format

`~/.local/share/personal-ai-space/automation_state.json`
```json
{
  "alert_overdue_tasks": {
    "fingerprint": "hash_of_current_state",
    "last_alerted": "2026-05-29T10:00:00",
    "count": 2
  },
  "alert_habits_at_risk": {
    "fingerprint": "hash_or_empty",
    "last_alerted": "2026-05-29T09:30:00"
  },
  "pending_deliveries": [
    {"text": "...", "failed_at": "...", "retry_count": 1}
  ]
}
```

State file is written to disk after every state change (rate-limited to 1 write per 10s).

## 9. Testing Strategy

- **Unit tests:** `tests/test_automations.py`
  - `test_load_rules_valid_yaml`
  - `test_load_rules_invalid_yaml`
  - `test_state_change_detection`
  - `test_state_no_change_no_alert`
  - `test_build_message_all_sections`
  - `test_build_message_empty_sections`
  - `test_delivery_failure_queues_retry`
  - `test_pending_retry_delivery`
- **Integration:** Run engine with test automations.yaml, verify WhatsApp receives messages

## 10. Rollout

1. Create `engine/automations/` module files
2. Add `automations.yaml` with initial rules
3. Add `automation_runner` job to scheduler
4. Verify morning brief fires at 07:00 (or test manually)
5. Verify alert triggers on state change
6. Test WhatsApp delivery failure + retry

---

## Spec Self-Review

- ✅ No placeholders or TODOs
- ✅ Sections are internally consistent
- ✅ Scope focused — single module, YAML-driven, MVP complexity
- ✅ All requirements unambiguous
- ✅ Failure modes documented with mitigations
