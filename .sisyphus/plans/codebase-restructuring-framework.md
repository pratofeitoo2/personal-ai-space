# Codebase Restructuring Framework

> **Date:** 2026-05-14
> **Context:** User reported friction with too many loose files, scattered configs across multiple directory levels, and config-like data files mixed throughout `personal-ai-space/`.

## Overview

Layered framework for restructuring `personal-ai-space/` incrementally without overloading the system. Each layer tackles a distinct kind of friction. Earlier layers don't break later ones.

---

## Layer 0: Audit & Baseline (prerequisite, 1 session)

**Before any change, map dependencies.**

| Action | Why |
|---|---|
| Map **import graph** across all Python files | Know what breaks if you move a file |
| Record every **config file path** referenced in code | Know what breaks if you move configs |
| Catalog every **hardcoded value** that should be a config | Know the full extraction surface |
| Check `engine/transport/config.py` usage throughout | Understand the one config class you already have |

🟢 **No changes. Just knowledge.** Move forward only after this is captured.

---

## Layer 1: Group Loose Files Into Subdirectories (structural)

**The engine root is where the pain is most visible. Fix this first — it's pure file moves, no logic changes.**

Current `engine/` root — **17 loose Python files**:

```
engine/
├── engine.py            ← orchestrator
├── cli.py               ← CLI (600+ lines, 1/3 of engine's total surface)
├── backup.py
├── comprehensive_extractor.py
├── converters.py
├── db_manager.py
├── frontmatter_apply.py
├── init_engine.py
├── llm_bridge.py
├── log_manager.py
├── propagator.py
├── start_engine.py      ← ~5 lines each
├── stop_engine.py       ← ~5 lines each
├── sync_scanner.py
├── sync_self.py
├── synthesis_loop.py
├── synthesis_run.py
└── 7 subdirectories (agents/, config/, db/, etc.)
```

### Proposed groups:

| New Subdirectory | Files to Move | Rationale |
|---|---|---|
| `engine/sync/` | `sync_scanner.py`, `sync_self.py`, `frontmatter_apply.py` | All deal with syncing .md frontmatter ↔ database |
| `engine/synthesis/` | `synthesis_loop.py`, `synthesis_run.py`, `propagator.py` | All part of the autonomous learning/synthesis cycle |
| `engine/orchestrator/` | `engine.py`, `cli.py` | Both are entry points for running the system |
| `engine/converters/` | `converters.py`, `comprehensive_extractor.py` | Both deal with format conversion/extraction |
| Keep at root | `db_manager.py`, `log_manager.py`, `llm_bridge.py`, `init_engine.py`, `backup.py` | These are cross-cutting infrastructure used by everything — moving them breaks imports everywhere |

**Total flat files reduced from 17 → 5.** Only pure moves + import path updates.

---

## Layer 2: Consolidate Configs Into One Directory (centralization)

**Configs are scattered across 4 directories + 2 Python modules. Bring them together.**

### Scattered config surface:

| Current Location | Type | Should Move To |
|---|---|---|
| `engine/config/engine.config.json` | ✅ Already here | Already centralized |
| `engine/config/system.config.json` | ✅ Already here | Already centralized |
| `engine/config/github_agent.json` | ❌ **Expected by code but doesn't exist** | **Must create it** |
| `engine/agents/agents.config.json` | Config (agent registry) | → `engine/config/agents.config.json` |
| `engine/mcp_tools/registry.json` | Config (MCP server registry) | → `engine/config/mcp_registry.json` |
| `engine/mcp_tools/claude_bridges_config.json` | Config | → `engine/config/claude_bridges.json` |
| `engine/transport/config.py` | Config class (stays as Python) | Keep in `transport/` (it's the transport module's own config class) |

**After consolidation:** ONE directory (`engine/config/`) holds ALL JSON-based config. The only exception is `transport/config.py` which is a Pydantic class tightly coupled to the transport module (and follows a different pattern — env vars, not file-based).

---

## Layer 3: Extract Hardcoded Configs From Code (externalization)

**Several files have configuration baked into Python code. Pull them into config files.**

| File | Hardcoded Configs | Target Config File |
|---|---|---|
| `process_intake.py` (lines 112-181) | Routing rules (19 type→destination mappings, 10+ filename/tag patterns) | `engine/config/intake_routing.json5` |
| `init_engine.py` (lines 74-80, 100-137) | Seed habits, seed needs, seed tasks, seed projects | `engine/config/seeds.json5` |
| `engine.py` (lines 49-58) | Agent class list → `agents.config.json` already exists, but agent class mapping is in code | `engine/config/agents.config.json` (extend it) |
| `synthesis_loop.py` (lines 10-11) | `DB_PATH`, `INBOX_DIR` | Already possible via `transport/config.py` |

---

## Layer 4: Choose & Apply Unified Config Format (format migration)

**Decide on the config format and apply consistently.**

### Recommendation: JSON5

Why JSON5 wins here:

- **Python has a native `json5` library** (`pip install json5`) — low friction
- All existing configs are already JSON — JSON5 is a superset (valid JSON = valid JSON5)
- **Comments** (the main thing missing) — you can add `//` and `/* */` to explain what values mean
- **Trailing commas** — less frustrating to edit
- **Unquoted keys** — less visual noise
- Migration can be **incremental**: convert files one at a time, each is immediately valid

### Considered alternative: YAML

YAML would add:
- Indentation sensitivity (real risk in config files)
- Different quoting rules
- Need to change ALL config readers to use PyYAML instead of `json`
- More friction for incremental migration

---

## Layer 5: Separate Data From Config (semantic cleanup)

**Several JSON files in the codebase are *data*, not *config*. Mixing them feels messy.**

| File | It's Actually... | What To Do |
|---|---|---|
| `command/tasks/active_tasks.json` | Operational data | Already belongs in the database (tasks.db) — this is a data file in the file system |
| `command/activities/disciplined_routines.json` | Operational data | Same — should be DB-backed |
| `command/finances/overview.json` | Snapshot data | Potentially keep as JSON but clearly mark as data, not config |
| `self/profile.json` | User data | Clearly data — keep in `self/` but recognize it's different from config |
| `self/needs/current_needs.json` | User data | Same |
| `self/traits/inferred_personality.json` | AI-generated data | Same |
| `habits/tracking.csv` | Time-series data | Same |

**Action:** Physically separate config files from data files in the directory tree:

- All **configs** → `engine/config/*.json5`
- All **data** stays in their domain directories (`command/`, `self/`, `knowledge/`)

This way, when you open the project, you immediately know: "files in `config/` = knobs I can turn; files in `command/` = state the system operates on."

---

## Recommended Sequence

```
Phase 0: Audit & Baseline ───────────────────────────────→ (knowledge capture, no changes)
         │
         ▼
Phase 1: Group Loose Files ──────────────────────────────→ (engine/ root cleanup, pure moves)
         │
         ▼
Phase 2: Consolidate Configs ────────────────────────────→ (all .json → engine/config/)
         │
         ▼
Phase 3: Extract Hardcoded Configs ─────────────────────→ (intake routing, seed data, etc.)
         │
         ▼
Phase 4: Unify Config Format (JSON5) ───────────────────→ (add comments, trailing commas)
         │
         ▼
Phase 5: Separate Data from Config ─────────────────────→ (semantic clean boundary)
```

This sequence ensures:
- **Phase 1** is pure file moves (no behavior changes, easy to verify)
- **Phase 2** is config file moves (update code references, straightforward)
- **Phase 3** is new files + removing hardcoded values (additive, can be rolled back per-file)
- **Phase 4** is purely additive (JSON5 is valid JSON — convert file by file)
- **Phase 5** is a touch decision per file (data vs config), done last so you have context
