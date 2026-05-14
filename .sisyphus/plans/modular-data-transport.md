# Modular Data Transport Layer for Personal AI Powerhouse

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

## TL;DR

**Goal:** Create a safe, modular data transport layer that decouples the 8 engine agents, 2 MCP memory backends, 5 SQLite databases, and 3 external MCP server integrations — eliminating the current ad-hoc coupling where any module can directly import and mutate any other module's state.

**Architecture:** Introduce a typed `EventBus` with validated message envelopes (matching the existing `COMMUNICATION_PROTOCOL.md` spec), a `DataHub` facade for all persistent reads/writes, and a `SafeMCPTransport` wrapper that isolates MCP server communication behind retry/fallback logic.

**Tech Stack:** Python 3.12+, Pydantic v2 (type validation), existing `log_manager`, existing `db_manager`, existing `mcp_tools.base_client`.

---

## Context

### Current State (Problems)

1. **No unified message transport** — `engine.py` directly imports and calls each agent. Agents sometimes import other agents' internals directly (e.g., `context_manager.py` imports `db_manager` and `mcp_bridge` directly).
2. **Scattered database access** — `db_manager.py` is a shared module, but any agent can call `db.query()` / `db.execute()` with raw SQL, risking data corruption and making it impossible to enforce access control.
3. **Two independent MCP memory systems** — Node.js pi-memory (`mcp_bridge.py`) and Python `opencode-mem-mcp` serve similar purposes but are completely disconnected.
4. **No error isolation** — A crash in `opencode-mem-mcp` (503 error) can cascade through the entire agent system because there's no circuit breaker or fallback.
5. **Hardcoded paths** — `context_manager.py` has `PROFILE_PATH` hardcoded; `embedder.py` has Ollama URL hardcoded; `mcp_bridge.py` has `headless.js` path relative to `__file__`.
6. **Zombie MCP processes** — Multiple `opencode-mem-mcp` processes are running simultaneously (4+ PIDs visible), indicating previous crashes left orphan processes.

### Target State

- **Typed message envelopes** for all inter-agent communication (validated by Pydantic)
- **DataHub** — single facade for all database operations with schema-level access control
- **SafeMCPTransport** — MCP server communication with circuit breaker, retry, and graceful fallback
- **EventBus** — publish/subscribe pattern replacing direct agent-to-agent calls
- **Configuration from environment** — no hardcoded paths or URLs

---

## Work Objectives

### Must Have
- [x] Typed `EventEnvelope` schema matching `COMMUNICATION_PROTOCOL.md` spec
- [x] `EventBus` class supporting `publish()`, `subscribe()`, `request()` with Pydantic validation
- [x] `DataHub` facade wrapping all `db_manager` operations with typed query methods
- [x] `SafeMCPTransport` wrapper with circuit breaker, retry, and fallback for external MCP servers
- [x] Refactored `context_manager.py` to use `DataHub` + `EventBus` instead of direct imports
- [x] Config loader replacing all hardcoded paths (from env vars or config file)
- [x] Graceful degradation: system works with MCP memory unavailable

### Must NOT Have
- [x] No new database schema changes
- [x] No changes to external MCP server protocols (mail-mcp, WhatsApp, etc.)
- [x] No changes to agent business logic (only transport layer changes)
- [x] No circular imports

---

## Verification Strategy

### Test Infrastructure
- **Infrastructure exists**: YES — `pytest` configured in engine directory, existing test suite in `personal-ai-space/engine/tests/`
- **Automated tests**: YES (tests after) — Add tests for new transport layer, then verify existing agent tests still pass
- **Framework**: pytest (already in use)
- **Agent-Executed QA**: ALL tasks include QA scenarios

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Foundation — types, config, core bus):
├── T1: Typed EventEnvelope + EventBus core
├── T2: Config loader (env vars + file)
├── T3: DataHub facade (typed wrappers around db_manager)
└── T4: SafeMCPTransport with circuit breaker

Wave 2 (Integration — wire agents through new layer):
├── T5: Refactor context_manager.py → use DataHub + EventBus
├── T6: Refactor mcp_agent.py → use SafeMCPTransport
├── T7: Refactor behavior_observer.py → use DataHub
├── T8: Refactor engine.py → use EventBus for agent dispatch
└── T9: Add MCP memory graceful fallback

Wave 3 (Hardening — tests, cleanup, verification):
├── T10: Type-safe registry.json loader
├── T11: Comprehensive test suite for transport layer
├── T12: Integration tests (all agents through new layer)
└── T13: Remove dead code and direct DB access paths

Wave FINAL (Verification):
├── F1: Plan compliance audit (oracle)
├── F2: Code quality review
├── F3: Full test suite pass
└── F4: Scope fidelity check
```

### Dependency Matrix

- T1, T2, T3, T4: Independent (Wave 1 — all parallel)
- T5: depends on T1, T2, T3
- T6: depends on T1, T4
- T7: depends on T3
- T8: depends on T1, T2
- T9: depends on T4
- T10: depends on T3
- T11: depends on T1-T4
- T12: depends on T5-T9
- T13: depends on T12
- All F-tasks: depend on all Wave 2 and Wave 3 tasks

---

## TODOs

### Wave 1: Foundation (4 tasks)

- [x] 1. [Typed EventEnvelope + EventBus core]
  **What to do**:
  - Create `personal-ai-space/engine/transport/types.py` with Pydantic models:
    - `EventEnvelope` (matches `COMMUNICATION_PROTOCOL.md` schema): `id`, `timestamp`, `sender`, `recipients`, `action`, `priority`, `payload`, `context`, `metadata`
    - `EventResponse`: `status`, `payload`, `error`, `elapsed_ms`
    - `ActionType` enum: `REQUEST`, `BROADCAST`, `ASYNC_COMMAND`
    - `Priority` enum: `CRITICAL`, `HIGH`, `NORMAL`, `LOW`
  - Create `personal-ai-space/engine/transport/event_bus.py`:
    - `EventBus` class with `__init__`, `subscribe(topic, callback)`, `unsubscribe(topic, callback)`, `publish(envelope)`, `request(envelope, timeout=30)` (wait-for-response variant)
    - Internal subscriber registry dict
    - Validation: Pydantic `validate_python=True` on all envelopes
    - Error handling: malformed envelopes logged and discarded (never crash bus)
  - Delete `personal-ai-space/engine/agents/COMMUNICATION_PROTOCOL.md` (spec now enforced in code)

  **Must NOT do**: Touch any agent business logic, modify database schemas, change external MCP protocols

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: [`writing-plans`]
  - Reason: Pure type definitions and simple pub/sub mechanics, no external dependencies beyond Pydantic

  **Parallelization**:
  - Can Run In Parallel: NO (foundation for everything else)
  - Blocks: T5, T6, T7, T8, T11, F4

  **References**:
  - `COMMUNICATION_PROTOCOL.md:1-34` — exact message structure spec to encode in Pydantic
  - `agents/config.json:1-119` — agent IDs, priorities, triggers to validate against
  - `base_agent.py:56-62` — `_ok()` and `_error()` helpers to match response format

  **Acceptance Criteria**:
  - [ ] `EventEnvelope(**valid_dict)` creates instance without errors
  - [ ] `EventEnvelope(**invalid_dict)` raises `ValidationError`
  - [ ] `bus.publish(envelope)` delivers to all subscribers within 30s
  - [ ] `bus.request(envelope, timeout=5)` returns `EventResponse` or raises timeout
  - [ ] `ActionType` enum matches all action types from `COMMUNICATION_PROTOCOL.md`
  - [ ] All types pass `mypy --strict`

  **QA Scenarios**:
  ```
  Scenario: Valid envelope passes Pydantic validation
    Tool: Bash (python -c)
    Preconditions: types.py exists with EventEnvelope model
    Steps:
      1. Run: python -c "
      from transport.types import EventEnvelope, ActionType, Priority
      e = EventEnvelope(
          id='test-1', timestamp='2026-05-14T05:00:00Z',
          sender='test-agent', recipients=['recipient'],
          action=ActionType.REQUEST, priority=Priority.NORMAL,
          payload={'command': 'test'}, context={}, metadata={})
      print(e.model_dump_json())
      "
    Expected Result: Valid JSON output with all fields present
    Evidence: .sisyphus/evidence/task-1-valid-envelope.txt

  Scenario: Invalid envelope raises ValidationError
    Tool: Bash (python -c)
    Preconditions: types.py exists
    Steps:
      1. Run: python -c "
      from transport.types import EventEnvelope
      from pydantic import ValidationError
      try:
          EventEnvelope(id='', timestamp='2026-05-14', sender='', recipients=[], action='invalid', priority='x', payload=None, context={}, metadata={})
          print('ERROR: Should have raised')
      except ValidationError as ve:
          print(f'Caught {len(ve.errors())} validation errors')
      "
    Expected Result: ValidationError caught with 3+ errors
    Evidence: .sisyphus/evidence/task-1-invalid-envelope.txt

  Scenario: EventBus delivers published event to subscribers
    Tool: Bash (python -c)
    Preconditions: event_bus.py exists
    Steps:
      1. Run: python -c "
      from transport.event_bus import EventBus
      from transport.types import EventEnvelope, ActionType, Priority
      bus = EventBus()
      received = []
      bus.subscribe('test.topic', lambda e: received.append(e))
      envelope = EventEnvelope(id='1', timestamp='2026-05-14T05:00:00Z', sender='a', recipients=['b'], action=ActionType.REQUEST, priority=Priority.NORMAL, payload={'cmd': 'x'}, context={}, metadata={})
      bus.publish('test.topic', envelope)
      assert len(received) == 1, f'Expected 1, got {len(received)}'
      print('PASS: subscriber received envelope')
      "
    Expected Result: 'PASS: subscriber received envelope'
    Evidence: .sisyphus/evidence/task-1-publish-subscribe.txt
  ```

- [x] 2. [Config loader]
  **What to do**:
  - Create `personal-ai-space/engine/transport/config.py`:
    - `AppConfig` Pydantic model with fields: `ollama_url`, `ollama_model`, `memory_db_dir`, `data_dir`, `mcp_registry_path`, `log_level`, `context_ttl_seconds`
    - Load from environment variables (with sensible defaults)
    - Load from optional `personal-ai-space/config.toml` if present
    - Singleton pattern: `AppConfig.instance()` returns shared config
    - Validation: paths exist, URLs are valid, positive integers for timeouts/retries
  - Replace all hardcoded values:
    - `embedder.py`: `OLLAMA_URL` and `EMBED_MODEL` → read from config
    - `context_manager.py`: `PROFILE_PATH` → from config
    - `mcp_bridge.py`: `MCP_SERVER_DIR` → from config
    - `base_client.py`: timeout/retry defaults → from config
    - `registry.json`: path → from config

  **Must NOT do**: Change what config values exist, only how they're loaded

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: [`writing-plans`]

  **Parallelization**:
  - Can Run In Parallel: NO (needed by T5-T9)
  - Blocks: T5, T6, T7, T8, T9

  **References**:
  - `core/embedder.py:9-10` — hardcoded Ollama URL to externalize
  - `context_manager.py:25` — hardcoded profile path
  - `mcp_bridge.py:27-28` — hardcoded MCP server path

  **Acceptance Criteria**:
  - [ ] `AppConfig.instance()` returns same instance on repeated calls
  - [ ] All current hardcoded values configurable via env vars
  - [ ] Missing env vars use documented defaults (not crashes)
  - [ ] Invalid URL or path raises clear `ConfigError` at startup

  **QA Scenarios**:
  ```
  Scenario: Config loads with defaults when no env vars set
    Tool: Bash
    Steps: unset OLLAMA_URL OLLAMA_MODEL; python -c "from transport.config import AppConfig; c = AppConfig.instance(); print(c.ollama_url)"
    Expected: http://localhost:11434/api/embed

  Scenario: Config overrides via env vars
    Tool: Bash
    Steps: OLLAMA_URL=http://custom:11434 python -c "from transport.config import AppConfig; c = AppConfig.instance(); print(c.ollama_url)"
    Expected: http://custom:11434
  ```

- [x] 3. [DataHub facade]
  **What to do**:
  - Create `personal-ai-space/engine/transport/data_hub.py`:
    - `DataHub` class wrapping `db_manager` functions
    - Typed methods: `get_user_profile() -> UserProfile`, `get_habits() -> list[Habit]`, `get_needs() -> list[Need]`, `get_recent_interactions(limit=10) -> list[Interaction]`, `store_context_snapshot() -> str`, `log_interaction() -> str`, `store_agent_memory() -> bool`, `get_agent_memory() -> list[dict]`, `query(db_name, sql, params) -> list[dict]` (escape hatch for complex queries)
    - Each method logs via `log_manager.audit()` for traceability
    - Connection pooling via `db_manager.get_conn()` context manager
    - Schema version checking on init
  - Add type aliases/enums for common query patterns

  **Must NOT do**: Add new tables or modify existing schema

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: [`writing-plans`]

  **Parallelization**:
  - Can Run In Parallel: NO (needed by T5, T7)
  - Blocks: T5, T7

  **References**:
  - `db_manager.py:18-176` — full database interface to wrap
  - `context_manager.py:61-109` — example of multi-DB query pattern to type
  - `agents/config.json` — agent dependencies on specific databases

  **Acceptance Criteria**:
  - [ ] All existing `db.query()` / `db.execute()` calls in agents produce same results through DataHub
  - [ ] Each DataHub method has type hints for inputs and return values
  - [ ] Audit log entry created for every DataHub call
  - [ ] `DataHub.query()` escape hatch works for arbitrary SQL

  **QA Scenarios**:
  ```
  Scenario: DataHub.get_user_profile returns same data as direct db.query
    Tool: Bash
    Steps: python -c "
    from transport.data_hub import DataHub
    from db_manager import query
    hub = DataHub()
    direct = query('self', 'SELECT * FROM profile LIMIT 1')
    via_hub = hub.get_user_profile()
    assert via_hub == direct[0] if direct else via_hub is None
    print('PASS: profile data matches')
    "
    Expected: 'PASS: profile data matches'
  ```

- [x] 4. [SafeMCPTransport with circuit breaker]
  **What to do**:
  - Create `personal-ai-space/engine/transport/mcp_transport.py`:
    - `MCPServerConfig` Pydantic model: `id`, `name`, `transport`, `command`/`url`, `args`, `env`, `enabled`, `timeout_seconds`, `max_retries`, `health_check_interval`
    - `CircuitBreaker` class: tracks failures (threshold: 3), state machine (`CLOSED` → `OPEN` → `HALF_OPEN` → `CLOSED`), cooldown timer
    - `SafeMCPTransport` class: wraps `mcp_tools.base_client.MCPClient`, adds:
      - Circuit breaker per server
      - Automatic retry with exponential backoff
      - Graceful fallback (return cached empty result or error dict instead of raising)
      - Health check on connect
      - Connection pooling (reuse clients)
    - `MCPTransportManager` class: loads `registry.json`, manages multiple `SafeMCPTransport` instances, `discover_tools()`, `call_tool(server_id, tool, args)`

  **Must NOT do**: Change external MCP server protocols, modify `registry.json` format

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: [`writing-plans`]

  **Parallelization**:
  - Can Run In Parallel: NO (needed by T6, T9)
  - Blocks: T6, T9

  **References**:
  - `mcp_tools/base_client.py:127-339` — existing StdioMCPClient and HTTPMCPClient to wrap
  - `mcp_tools/registry.json:1-34` — server config format to extend with circuit breaker thresholds
  - `agents/mcp_agent.py:111-128` — existing `call_tool` to replace with safe version

  **Acceptance Criteria**:
  - [ ] 3 consecutive failures → circuit breaker opens
  - [ ] Open circuit returns fallback response (not exception)
  - [ ] After cooldown (30s), circuit enters half-open, tests with 1 request
  - [ ] Successful request closes circuit
  - [ ] Automatic retry with exponential backoff (1s, 2s, 4s)
  - [ ] Graceful shutdown closes all client connections

  **QA Scenarios**:
  ```
  Scenario: Circuit breaker opens after 3 failures
    Tool: Bash (python -c with mock)
    Steps: Create SafeMCPTransport pointing at nonexistent server, call 3 times, verify state=OPEN
    Expected: Circuit breaker state is OPEN after 3rd call

  Scenario: Fallback response returned when circuit is open
    Tool: Bash (python -c with mock)
    Steps: With OPEN circuit, call call_tool(), verify no exception and error status in response
    Expected: {'status': 'error', 'error': 'circuit_open'}
  ```

### Wave 2: Integration (5 tasks)

- [x] 5. [Refactor context_manager.py]
  **What to do**:
  - Replace `import db_manager as db` → `from transport.data_hub import DataHub`
  - Replace `from memory.mcp_bridge import MCPMemoryBridge` → `from transport.mcp_transport import MCPTransportManager`
  - Replace `sys.path.insert()` hacks with proper `transport` package imports
  - All data access goes through `DataHub` instance
  - MCP memory operations go through `MCPTransportManager` (with graceful fallback)
  - Use `EventBus` for any outbound events (cache invalidation notifications, etc.)
  - Remove direct `MCPMemoryBridge` instantiation (was duplicated in both `context_manager.py` and `engine.py`)

  **Must NOT do**: Change what data the context manager returns or how it processes commands

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: [`writing-plans`]

  **Parallelization**:
  - Can Run In Parallel: NO (depends on T1, T2, T3)
  - Blocks: T12

  **References**:
  - `context_manager.py:1-175` — full file to refactor
  - `engine.py:19-67` — where ContextManager is instantiated and where MCPMemoryBridge was also created

  **Acceptance Criteria**:
  - [ ] ContextManager passes all existing tests
  - [ ] No `import db_manager` or `from memory.mcp_bridge` remaining in context_manager.py
  - [ ] MCP unavailable → graceful degradation (no crash, returns default context)

  **QA Scenarios**:
  ```
  Scenario: ContextManager.get_context works through DataHub
    Tool: Bash
    Steps: Start engine, send get_context command via EventBus, verify response has profile/habits/needs/mcp_facts keys
    Expected: Response dict contains all expected keys

  Scenario: ContextManager handles missing MCP gracefully
    Tool: Bash
    Steps: Stop mcp-server/headless.js, get_context, verify 'mcp_facts' key is empty dict (not crash)
    Expected: mcp_facts = {}
  ```

- [x] 6. [Refactor mcp_agent.py to use SafeMCPTransport]
  **What to do**:
  - Replace `import mcp_tools.base_client as mcp` → `from transport.mcp_transport import MCPTransportManager`
  - `MCPAgent.initialize()` uses `MCPTransportManager` for connection and tool discovery
  - `MCPAgent.call_tool()` goes through circuit breaker
  - Add fallback behavior when server disconnected (return helpful error, not exception)

  **Must NOT do**: Change the MCP agent's exposed commands or response format

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Parallelization**:
  - Can Run In Parallel: YES (depends only on T1, T4)
  - Blocks: T12

  **References**:
  - `mcp_agent.py:1-183` — full file to refactor
  - `mcp_tools/base_client.py:318-361` — existing `discover_tools` and `load_registry`

  **Acceptance Criteria**:
  - [ ] MCP agent reconnects automatically after server restart
  - [ ] Circuit breaker prevents cascade failures
  - [ ] Existing tests pass

- [x] 7. [Refactor behavior_observer.py]
  **What to do**:
  - Replace `import db_manager as db` → `from transport.data_hub import DataHub`
  - Replace direct `self.mcp.add_fact()` calls with `MCPTransportManager` calls
  - Move observation buffer persistence to `DataHub.store_agent_memory()`

  **Must NOT do**: Change observation types or learning logic

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Parallelization**:
  - Can Run In Parallel: YES (depends on T3)
  - Blocks: T12

- [x] 8. [Refactor engine.py dispatch through EventBus]
  **What to do**:
  - Add EventBus as an `Engine` attribute
  - `Engine.send()` publishes to EventBus instead of direct `agent.handle()` call
  - Agents register their handlers via EventBus subscriptions
  - Keep backward compatibility: `Engine.send()` still returns response synchronously for request-response pattern
  - Fire-and-forget broadcasts (e.g., GitHub agent notifications) use `EventBus.publish()` without waiting

  **Must NOT do**: Remove direct agent instantiation (agents still created in `start()`), change return format

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Parallelization**:
  - Can Run In Parallel: NO (depends on T1)
  - Blocks: T12

  **References**:
  - `engine.py:122-190` — `send()` method to refactor
  - `base_agent.py:27-41` — `handle()` method signature

- [x] 9. [MCP memory graceful fallback layer]
  **What to do**:
  - Create `personal-ai-space/engine/memory/fallback_bridge.py`:
    - `FallbackMemoryBridge` class that tries MCP first, falls back to SQLite direct if MCP unavailable
    - Same API as `MCPMemoryBridge`: `add_fact`, `get_fact`, `list_facts`, `delete_fact`, `add_lesson`, `list_lessons`, `delete_lesson`, `get_stats`, `sync_profile_facts`, `get_context_snapshot`
    - SQLite fallback stores facts in `agent_memory.db` table `fallback_memory`
    - Automatic failover detection (health check on init, periodic check)
    - On MCP recovery: sync fallback data to MCP (catch-up)

  **Must NOT do**: Remove existing MCP bridge or change its interface

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Parallelization**:
  - Can Run In Parallel: YES (depends on T4)
  - Blocks: T5, T12

  **References**:
  - `mcp_bridge.py:60-184` — MCPMemoryBridge API to match
  - `context_manager.py:37-48` — where MCP unavailability is currently handled

### Wave 3: Hardening (4 tasks)

- [x] 10. [Type-safe registry.json loader]
- [x] 11. [Comprehensive test suite for transport layer]
- [x] 12. [Integration tests — all agents through new layer]
- [x] 13. [Remove dead code and direct DB access paths]
  - Scan all agents for direct `db_manager` imports → replace with DataHub
  - Remove `sys.path.insert()` hacks in all agents
  - Identify and remove duplicate code (MCP bridge created in 2 places)
  - Verify no functionality loss

### Wave FINAL: Verification

- [x] F1. **Plan compliance audit** (`oracle`) — verify all Must Have items done, all Must NOT items absent
- [x] F2. **Code quality review** (`unspecified-high`) — `mypy --strict`, `ruff`, `pytest --cov`
- [x] F3. **Full test suite pass** (`unspecified-high`) — All existing + new tests green
- [x] F4. **Scope fidelity check** (`deep`) — No feature creep, no business logic changes

---

## Key Design Decisions (with rationale)

1. **Pydantic for all message types** — The codebase already uses Pydantic in `mcp_tools/base_client.py` and `mail-mcp`. Consistent with existing patterns. Provides both validation and serialization.

2. **EventBus as in-memory pub/sub** — No external message queue needed. The engine is single-process. EventBus provides the decoupling without infrastructure overhead. Future scaling can swap to Redis/pubsub without changing agent code.

3. **DataHub as facade, not ORM** — Wraps existing `db_manager` rather than replacing it. Minimizes risk, avoids migration. Typed methods provide guardrails without requiring schema changes.

4. **Circuit breaker on MCP transport** — Directly addresses the 503 error. The current code propagates MCP failures as unhandled exceptions through the entire agent chain. Circuit breaker isolates failures.

5. **FallbackMemoryBridge for resilience** — The current system treats MCP memory loss as catastrophic (context_manager goes into degraded mode, behavior_observer skips learning). Fallback ensures zero data loss even when MCP is down.

6. **Config from env vars** — macOS app ecosystem standard. No config server needed. `.env` file optional for local dev.

---

## Critical Path

```
T1 (types) → T5 (context_manager) → T12 (integration tests)
T2 (config) → T5, T7, T8
T3 (data_hub) → T5, T7 → T12
T4 (mcp_transport) → T6, T9 → T12
T5 + T6 + T7 + T8 + T9 → T12 → F1-F4
```

**Estimated parallel speedup**: ~60% faster than sequential (Wave 1 has 4 parallel tasks vs 1 sequential).

## Success Criteria

```bash
# All type checks pass
mypy --strict personal-ai-space/engine/transport/

# All existing tests pass
cd personal-ai-space/engine && pytest tests/ -x -q

# All new transport tests pass
pytest transport/tests/ -x -q

# Integration test: engine starts and processes a command
python -c "
from engine.engine import Engine
e = Engine()
e.start()
result = e.send('context-manager', 'get_context')
assert result['status'] == 'success'
print('SUCCESS: engine processes commands through new transport layer')
e.stop()
"

# 503 error no longer reproducible
# (opencode-mem-mcp crash should not cascade)
```

---

## Commit Strategy

| Wave | Commit message | Files |
|------|---------------|-------|
| W1 | `feat(transport): add typed EventBus, DataHub, SafeMCPTransport` | `transport/types.py`, `transport/event_bus.py`, `transport/data_hub.py`, `transport/mcp_transport.py`, `transport/config.py` |
| W2 | `refactor: route agents through EventBus and DataHub` | `agents/context_manager.py`, `agents/mcp_agent.py`, `agents/behavior_observer.py`, `engine/engine.py`, `memory/fallback_bridge.py` |
| W3 | `test: add transport layer test suite + integration tests` | `transport/tests/`, `transport/registry.py` |
| W4 | `cleanup: remove dead code, enforce types` | various agent files (sys.path removals, import changes) |

---

## Scope Boundaries

### INCLUDE
- Typed message schemas (EventEnvelope, EventResponse)
- EventBus (in-memory pub/sub)
- DataHub (typed DB facade)
- SafeMCPTransport (circuit breaker + retry)
- AppConfig (centralized configuration)
- FallbackMemoryBridge (resilience layer)
- All refactoring of existing agents to use new layer
- Comprehensive test suite

### EXCLUDE
- External MCP server implementations (mail-mcp, WhatsApp MCP)
- Agent business logic changes
- Database schema changes
- Claude Apple Bridges (Swift, separate concern)
- UI/frontend changes (none exist)
- Performance optimization (beyond scope of this plan)