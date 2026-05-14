# personal-ai-space/engine/agents/

## Responsibility
Autonomous agent system — 8 specialized agents that observe, reason, and act on behalf of the user. Each extends `BaseAgent` and runs within the `Engine` lifecycle.

## Architecture
- **BaseAgent** (`base_agent.py`): Abstract base class defining `execute()`, `get_capabilities()`, `get_metadata()` interface
- Agents loaded dynamically by `engine.py` from `agents.config.json`
- Communication via shared `db_manager.py` and `mcp_bridge.py` (no direct agent-to-agent calls)

## Agent Registry

| Agent | File | Responsibility | Key Methods |
|-------|------|---------------|-------------|
| Context Manager | `context_manager.py` | Profile loading, session state, MCP memory bridge | `load_context()`, `get_context_snapshot()` |
| Task Coordinator | `task_coordinator.py` | Task CRUD, priorities, deadlines, dependencies | `create_task()`, `list_tasks()`, `update_priority()` |
| Insight Generator | `insight_generator.py` | Habit analysis, pattern detection, anomaly detection | `analyze_habits()`, `generate_insights()` |
| Reminder System | `reminder_system.py` | Time-based and event-based reminders | `schedule_reminder()`, `check_reminders()` |
| Knowledge Indexer | `knowledge_indexer.py` | Index, search, deduplicate knowledge base | `index_file()`, `search()`, `deduplicate()` |
| Report Generator | `report_generator.py` | Daily digest, weekly review, monthly reports | `generate_daily()`, `generate_weekly()` |
| Behavior Observer | `behavior_observer.py` | Logs user actions (task creation, completion, habits) | `observe()`, `get_behavior_log()` |
| Pattern Learner | `pattern_learner.py` | Infers time patterns, preferences, workflows | `learn_patterns()`, `predict_next()` |

## Flow
1. `engine.py` loads agent configurations from `agents.config.json`
2. On each tick, engine calls `agent.execute()` with current context
3. Agents read/write state through `db_manager.py` and `mcp_bridge.py`
4. Results are logged via `log_manager.py` and persisted to databases

## Integration Points
- **Consumed by**: `engine.py` (orchestrator loads and invokes all agents)
- **Depends on**: `db_manager.py` (SQLite persistence), `mcp_bridge.py` (memory), `log_manager.py` (audit trail)
- **Config**: `agents.config.json` defines enabled agents, schedules, and parameters
