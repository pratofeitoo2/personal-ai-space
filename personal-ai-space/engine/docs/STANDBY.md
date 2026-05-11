# Standby — Deferred Features

Features that were designed or documented but consciously deferred from active development. They are detached from the main project — no active code path, no automation, no blockers. They exist as reference only.

## How to Reactivate

1. Read the relevant documentation files linked below
2. Unblock any preconditions listed in the "Unblock Condition" column
3. Build and wire into the engine following the documented design
4. Remove this standby entry and update MAIN.md

---

## Standby Items

| # | Item | Status | Documentation | Unblock Condition | Data State |
|---|------|--------|---------------|-------------------|------------|
| 1 | **Seed goals** | User action deferred | `engine/docs/GOALS_SEEDING.md` | User runs SQL INSERT when ready | `self.db.goals` — 12 columns, 0 rows, schema ready |
| 2 | **Goal Reviewer Agent** | Not built | `engine/docs/GOALS_SEEDING.md` (AI Integration Plan section) | Goals must be seeded first, then build agent | No code exists |
| 3 | **Empty tables (calendar_events, references, projects_knowledge, cross_references)** | No pipeline | `engine/db/DATABASE_ARCHITECTURE.md` | Build data ingestion pipelines for each table | Tables exist in schema, 0 rows each |
| 4 | **FAISS vector DB** | No code populates it | `docs/MEMORY_SYSTEMS.md` (Vector Memory section); `engine/system.config.json` | Build embedding pipeline + indexer | Config exists, zero code, no index on disk |
| 5 | **Test coverage** | Not improved | — | Write tests for 19 untested files | 43 tests pass across 3 test files |
| 6 | **WhatsApp MCP** | Not wired | `knowledge/notes/MCP Server Guides/whatsapp-mcp.md`; `docs/INTEGRATIONS.md` | User copies plist to `~/Library/LaunchAgents/` and sets `$WHATSAPP_MCP_TOKEN` | Docker image built, plist ready, not deployed |

---

## Per-Item Details

### 1. Seed Goals
- **What**: Populate `self.db.goals` table with life/career goals via SQL INSERT
- **Design**: `engine/docs/GOALS_SEEDING.md` — Method A (SQL)
- **Why deferred**: User wants to decide on project direction first

### 2. Goal Reviewer Agent
- **What**: LLM agent that reads unreviewed goals and suggests links to projects/tasks
- **Design**: `engine/docs/GOALS_SEEDING.md` — AI Integration Plan section (pipeline, matching, confirmation flow fully specified)
- **Files to create**: `engine/agents/goal_reviewer.py`, `engine/agents/goal_reviewer_integration_plan.md`
- **Why deferred**: Depends on goals being seeded first; broader project direction unclear

### 3. Empty Tables
- **Tables affected**:
  - `tasks.db.calendar_events` — time-bound task slots
  - `knowledge.db."references"` — reference links
  - `knowledge.db.projects_knowledge` — project-specific knowledge
  - `knowledge.db.cross_references` — entity cross-links
- **Why deferred**: Each needs a pipeline built from scratch (calendar ingestion, reference parsing, entity linking)

### 4. FAISS Vector DB
- **What**: FAISS index for semantic search over articles, notes, task descriptions
- **Design**: `docs/MEMORY_SYSTEMS.md` section 4 (Vector Memory)
- **Config**: `engine/system.config.json` references vector store
- **Why deferred**: No immediate need; requires embedding pipeline, index management, query integration

### 5. Test Coverage
- **What**: 19 Python files have zero tests
- **Files without tests**: `propagator.py`, `sync_scanner.py`, `engine.py`, `task_coordinator.py`, `comprehensive_extractor.py`, `synthesis_loop.py`, `synthesis_run.py`, `init_engine.py`, `mcp_bridge.py`, `intent_classifier.py`, `goal_reviewer.py` (not yet created), and others
- **Why deferred**: Coverage is adequate for core stability (43 tests pass); expanding coverage is large effort

### 6. WhatsApp MCP
- **What**: WhatsApp messaging daemon (Docker image built, plist ready)
- **Design**: `knowledge/notes/MCP Server Guides/whatsapp-mcp.md`
- **Files**: plist at `~/Library/LaunchAgents/` (not yet copied)
- **Why deferred**: Requires user action + project direction decision

---

## Git History

When reactivating an item, reference this commit as the point it was formally deferred:
```
git log --all --oneline | grep -i "standby\|defer"
```
