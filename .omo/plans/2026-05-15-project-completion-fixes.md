# Project Completion Fixes — Execution Plan

> **For agentic workers:** Execution uses Sisyphus orchestration with parallel agent spawning per phase. Each phase is self-contained with its own entry/exit criteria. The orchestrator (Sisyphus) spawns specialist agents, verifies their output, and gates progression between phases.

**Goal:** Resolve all high-impact and medium-impact issues identified in the project audit, raising the overall completeness score from B+ to A.

**Architecture:** Fixes are organized into 5 sequential phases + 1 optional phase, ordered by dependency. Phase 0 removes blockers for Phase 1. Each phase produces independently verifiable results. Phases are gated — Phase 2 depends on Phase 1 completing.

**Reference:** Full audit at `project-audit-completeness-report.md`
**Codebase Root:** `/Users/paulorezende/Documents/Personal_AI_powerhouse`
**Engine Root:** `/Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine/`

---

## Phase Dependency Map

```
Phase 0: Quick Wins (no deps)
  └── Phase 1: Fix Test Suite (depends on Phase 0 items that affect DB)
  └── Phase 2: Fix Init-Order (depends on Phase 1 — tests validate the fix)
  └── Phase 3: Code Quality (no deps, can run in parallel with 1+2)
  └── Phase 4: Config & Architecture (no deps, can run in parallel)
  └── Phase 5: Stale Branches (no deps, standalone)
```

---

## Phase 0: Quick Wins

**Objective:** Eliminate startup warnings and broken references that produce noise on every engine boot.

**Success Criteria:**
- Mail-mcp binary resolves correctly (no `[Errno 2]` on startup)
- Schema `schema_git.sql` warning eliminated
- 0 "no such table" errors during engine start (wired, but fixed in Phase 2)
- All verifications checked below pass

---

### Task 0.1: Fix mail-mcp broken symlink

**Files:**
- `~/.local/bin/mail-mcp` (symlink, broken)
- `mcp-servers/mail-mcp/pyproject.toml` (project reference)

**Approach:** The symlink at `~/.local/bin/mail-mcp` points to a deleted uv tool installation. Fix by reinstalling the tool from the local source.

**Spawning instructions:**

Spawn a `quick` agent with:
- `load_skills=[]`
- `run_in_background=false`
- Prompt: "Run `uv tool install --reinstall /Users/paulorezende/Documents/Personal_AI_powerhouse/mcp-servers/mail-mcp` to reinstall the mail-mcp CLI tool. Then verify with `~/.local/bin/mail-mcp --help` that the symlink resolves and the command works. Report the output of both commands."

**Alternative (if uv not available):** Spawn a `quick` agent to remove the broken symlink: `rm /Users/paulorezende/.local/bin/mail-mcp`. Update `mcp_registry.json5` to set `"enabled": false` for the mail server.

**Verification:**
```
file ~/.local/bin/mail-mcp
# Expected: "symbolic link to ..." (NOT "broken symbolic link")
~/.local/bin/mail-mcp --help
# Expected: help text output, exit code 0
```

**Rollback:** `rm ~/.local/bin/mail-mcp` if reinstall causes issues.

---

### Task 0.2: Fix schema filename mismatch

**Files to modify:**
- `personal-ai-space/engine/db_manager.py` (lines 226-238)

**Issue:** `init_all()` at line 229 auto-generates `schema_{db_name}.sql` which for git becomes `schema_git.sql`. But the actual file is `schema_git_repos.sql`. A separate `init_git_db()` handles the correct name, but the generic loop still fires a warning.

**Two approaches (choose one):**

**Option A (rename file):** Rename `personal-ai-space/engine/db/git/schema_git_repos.sql` → `personal-ai-space/engine/db/git/schema_git.sql`, update the reference in `db_manager.py:215` to match.

**Option B (fix path generation):** In `db_manager.py:init_all()`, skip git.db in the generic loop since `init_git_db()` handles it already. Add `if db_name == "git": continue`.

**Spawning instructions:**

Spawn a `quick` agent with:
- `load_skills=[]`
- `run_in_background=false`
- Prompt: "Task: Fix schema filename mismatch in db_manager.py. There are two approaches. Read `personal-ai-space/engine/db_manager.py` lines 210-240 to understand the issue. Then implement **Option B**: In the `init_all()` function, skip git.db in the generic loop by adding `if db_name == 'git': continue` after line 228 (inside the for loop, before the schema_file exists check). The `init_git_db()` function already handles git.db separately. After making the change, run `python3 -c 'from db_manager import init_all; init_all()'` from the engine/ directory to verify it initializes without the schema_git warning. Do NOT touch any other files."

**Verification:**
```bash
cd /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine
python3 -c "from db_manager import init_all; init_all()" 2>&1
# Expected: NO "Schema missing:" warnings for schema_git.sql
# Expected: "Initialized: git.db" appears (from init_git_db)
```

**Rollback:** `git checkout personal-ai-space/engine/db_manager.py`

---

## Phase 1: Fix Test Suite

**Objective:** Make all 72 engine tests pass by fixing the 7 failing tests.

**Success Criteria:**
- `python -m pytest tests/ -v --tb=short` reports 72 passed, 0 failed
- CI workflow would produce green build

---

### Task 1.1: Fix conftest.py to initialize databases before tests

**Files:**
- Modify: `personal-ai-space/engine/tests/conftest.py`
- Modify: `personal-ai-space/engine/tests/test_db_manager.py`

**Root cause analysis:** The 7 failing tests share one root cause: test fixtures create temp databases (or use the `DatabaseManager` with test paths) but never call `init_databases()` before running queries. Tables exist in schema files but aren't created in the temp databases.

**Spawning instructions:**

Spawn an `unspecified-high` agent with:
- `load_skills=[]`
- `run_in_background=false`
- Prompt: "Task: Fix 7 failing pytest tests in the Personal AI Powerhouse project. All failures share one root cause: test fixtures create temp databases but don't run `init_databases()` before querying.

First read these files:
1. `tests/conftest.py` — understanding the current fixture setup
2. `tests/test_db_manager.py` — to see how db_manager tests create their databases  
3. `tests/test_engine.py` — to understand how engine tests set up

Then read the reference implementation in:
4. `db_manager.py` — especially `init_all()`, `init_git_db()`, and the `DB_PATHS` dict
5. `init_engine.py` — to see how production init works

The fix strategy:
- Update conftest.py to add a fixture or autouse mechanism that calls `init_databases()` on the test database paths before any test runs
- OR update test_db_manager.py and test_engine.py individually to ensure DBs are initialized

After fixing, run the tests:
```bash
cd /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine
python3 -m pytest tests/ -v --tb=short 2>&1
```
All 72 tests must pass. Report exactly which tests were failing, what the fix was, and the final test output."

**Verification:**
```bash
cd /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine
python3 -m pytest tests/ -v --tb=short 2>&1 | tail -20
# Expected: "72 passed" (or the correct total), 0 failed
```

**Rollback:** `git checkout personal-ai-space/engine/tests/conftest.py` and/or any modified test files.

---

## Phase 2: Fix Init-Order (Eliminate Runtime Errors)

**Objective:** Eliminate all 5 "no such table" errors that fire on every engine startup by ensuring databases are initialized before agents start querying.

**Success Criteria:**
- Engine starts with 0 `no such table` errors in logs
- `engine logs/errors.log` shows clean startup

---

### Task 2.1: Move database initialization before agent startup

**Files to modify:**
- `personal-ai-space/engine/engine.py` (start method)

**Issue:** In `engine.py:start()`, agents are initialized at lines 48-76 (agent_classes loop). `init_databases()` is NOT called from the engine at all — it's only called from `init_engine.py` (a separate setup script). The engine assumes DBs already exist, but DataHub and agents query tables immediately.

**Spawning instructions:**

Spawn an `ultrabrain` agent with:
- `load_skills=[]`  
- `run_in_background=false`
- Prompt: "Task: Fix database initialization order in the Personal AI Powerhouse engine. The engine starts agents before databases are initialized, causing 5 `no such table` errors on every startup.

First read these files:
1. `engine.py` — the `start()` method, especially lines 35-80
2. `db_manager.py` — especially `init_all()`, `init_git_db()`, and any `health_check()`
3. `transport/data_hub.py` — DataHub queries `profile` table in its init
4. `sync/sync_scanner.py` — queries `tasks` table

The fix: In `engine.py:start()`, call `db.init_all()` (import db_manager as db) BEFORE the agent initialization loop (lines 48-76). Check the existing import at the top of engine.py — `db_manager` may already be imported or may need adding.

After fixing, verify:
```bash
cd /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine
python3 -c "
from engine import Engine
import logging
logging.basicConfig(level=logging.INFO)
eng = Engine()
eng.start()
eng.shutdown()
" 2>&1 | grep -E "ERROR|no such table|WARNING.*schema"
# Expected: No 'no such table' errors. The schema_git warning should already be fixed by Phase 0.
```
If `schema_git.sql` warning still appears, note it but don't fix it (it's a Phase 0 Task 0.2 fix).

Then run the full test suite:
```bash
python3 -m pytest tests/ -v --tb=short 2>&1 | tail -10
```
All tests must pass."

**Verification:**
```bash
cd /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine
python3 -m pytest tests/ -v --tb=short 2>&1 | tail -5
# Expected: "72 passed", 0 failed
grep -c "no such table" logs/errors.log 2>/dev/null || echo "No errors.log yet (fresh start)"
# After running engine once: grep should show 0 matches
```

**Rollback:** `git checkout personal-ai-space/engine/engine.py`

---

## Phase 3: Code Quality

**Objective:** Reduce tech debt markers and fix structural issues across the codebase.

**Success Criteria:**
- 47 empty `except: pass` blocks reduced to <10 (only legitimate cases remain)
- 9 Python directories gain `__init__.py`
- `profile.json` has updated `updated` timestamp
- All existing tests still pass

---

### Task 3.1: Fix empty `except: pass` blocks (priority files)

**Files to modify (priority order):**
1. `personal-ai-space/engine/extractors/comprehensive_extractor.py` — 15 blocks
2. `personal-ai-space/engine/memory/fallback_bridge.py` — 8 blocks
3. `personal-ai-space/engine/extractors/__init__.py` — 4 blocks
4. `personal-ai-space/engine/llm_bridge.py` — 2 blocks
5. `personal-ai-space/engine/db_manager.py` — 2 blocks
6. `personal-ai-space/intake/process_intake.py` — 2 blocks
7. `personal-ai-space/engine/agents/github_config.py` — 2 blocks
8. Remaining files with 1 block each (see audit report Section 13)

**Spawning instructions:**

Spawn a `deep` agent with:
- `load_skills=["simplify"]`
- `run_in_background=false`
- Prompt: "Task: Audit and fix empty `except: pass` blocks across 18 Python files in the Personal AI Powerhouse project. There are 47 total instances.

**CRITICAL RULE:** Do NOT change the behavior of any code. These `except: pass` blocks silently swallow errors. Replace each one with an appropriate logging statement that preserves the non-crashing behavior but surfaces the error for debugging.

The project uses a logger at `log_manager.py` — import pattern:
```python
from log_manager import get_logger
logger = get_logger(__name__)
```

For each file, follow this pattern:
```python
# BEFORE:
except SomeError:
    pass

# AFTER:
except SomeError as e:
    logger.debug("Suppressed error in [context]: %s", e)  # or logger.warning for significant errors
```

**Priority files (do these first):**
1. `engine/extractors/comprehensive_extractor.py` (15 blocks) — use `logger.warning` for extraction failures
2. `engine/memory/fallback_bridge.py` (8 blocks) — use `logger.warning` for fallback failures
3. `engine/extractors/__init__.py` (4 blocks) — use `logger.debug`
4. All remaining files with 1-2 blocks each

**Verification after completion:**
```bash
cd /Users/paulorezende/Documents/Personal_AI_powerhouse
# Check count of remaining empty except: pass blocks
grep -rn "except.*:" --include="*.py" . | grep -v node_modules | grep -v ".git/" | grep -v "__pycache__" | grep -v ".venv/" | grep -v "venv/" | grep -v "site-packages" | grep -v "/lib/python" | grep -v "mcp-servers/claude-apple-bridges" | while IFS=: read f l r; do n=$(sed -n "$((l+1))p" "$f" 2>/dev/null); if echo "$n" | grep -q "^\s*pass\s*\(#.*\)\?$"; then echo "REMAINING: $f:$l"; fi; done | wc -l
# Expected: < 10 remaining

# Run tests
python3 -m pytest personal-ai-space/engine/tests/ -v --tb=short 2>&1 | tail -5
# All tests must pass
```

Report a summary of: files touched, blocks fixed per file, remaining empty except blocks count."

**Verification:**
```bash
cd /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine
python3 -m pytest tests/ -v --tb=short 2>&1 | tail -5
# Expected: All tests pass
grep -rn "except.*:\s*$" --include="*.py" personal-ai-space/engine/ | grep -v __pycache__ | wc -l
# Expected: close to 0 remaining
```

**Rollback:** `git checkout` on any modified files.

---

### Task 3.2: Add `__init__.py` to 9 Python directories

**Files to create:**
1. `personal-ai-space/__init__.py`
2. `personal-ai-space/engine/__init__.py`
3. `personal-ai-space/engine/tests/__init__.py`
4. `personal-ai-space/engine/transport/tests/__init__.py`
5. `personal-ai-space/engine/db/migrations/__init__.py`
6. `personal-ai-space/engine/db/tasks/__init__.py`
7. `personal-ai-space/engine/db/knowledge/__init__.py`
8. `personal-ai-space/engine/db/self/__init__.py`
9. `personal-ai-space/intake/__init__.py`

**Spawning instructions:**

Spawn a `quick` agent with:
- `load_skills=[]`
- `run_in_background=false`
- Prompt: "Create empty `__init__.py` files in the following 9 directories. Each file should contain only a module docstring comment. Do NOT add any code or imports.

Directories:
1. `personal-ai-space/__init__.py` → content: `"""Personal AI Space — root package."""`
2. `personal-ai-space/engine/__init__.py` → content: `"""Personal AI Space engine — orchestrator, agents, databases, transport."""`
3. `personal-ai-space/engine/tests/__init__.py` → content: `"""Engine test suite."""`
4. `personal-ai-space/engine/transport/tests/__init__.py` → content: `"""Transport layer tests."""`
5. `personal-ai-space/engine/db/migrations/__init__.py` → content: `"""Database migrations."""`
6. `personal-ai-space/engine/db/tasks/__init__.py` → content: `"""Tasks database schema and migrations."""`
7. `personal-ai-space/engine/db/knowledge/__init__.py` → content: `"""Knowledge database schema and migrations."""`
8. `personal-ai-space/engine/db/self/__init__.py` → content: `"""Self database schema and migrations."""`
9. `personal-ai-space/intake/__init__.py` → content: `"""File intake pipeline — watcher and processor."""`

After creating all files, verify:
```bash
cd /Users/paulorezende/Documents/Personal_AI_powerhouse
python3 -c "import personal_ai_space; import personal_ai_space.engine; import personal_ai_space.intake; print('All packages import OK')"
# Expected: "All packages import OK"
```

All paths are absolute relative to `/Users/paulorezende/Documents/Personal_AI_powerhouse/`."

**Verification:**
```bash
cd /Users/paulorezende/Documents/Personal_AI_powerhouse
python3 -c "
import personal_ai_space
import personal_ai_space.engine
import personal_ai_space.intake
print('Package imports OK')
" 2>&1
# Expected: "Package imports OK"
```

**Rollback:** `rm` the created `__init__.py` files.

---

### Task 3.3: Update profile.json timestamp

**Files to modify:**
- `personal-ai-space/self/profile.json` — field: `"updated"`

**Spawning instructions:**

Spawn a `quick` agent with:
- `load_skills=[]`
- `run_in_background=false`
- Prompt: "Update the `updated` field in `/Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/self/profile.json` to today's date (2026-05-15). The field is at line 4: `\"updated\": \"2026-05-06\"`. Change it to `\"updated\": \"2026-05-15\"`. Verify the change with `grep updated personal-ai-space/self/profile.json`."

**Verification:**
```bash
grep '"updated"' /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/self/profile.json
# Expected: "updated": "2026-05-15"
```

**Rollback:** Revert to `"updated": "2026-05-06"`.

---

## Phase 4: Config & Architecture

**Objective:** Align agent configuration with actual agent files and improve agent architecture consistency.

**Success Criteria:**
- `agents.json5` lists all 10 agent files that engine.py imports
- `BehaviorObserver` and `PatternLearner` extend `BaseAgent`
- All existing tests still pass
- Architecture diagrams committed

---

### Task 4.1: Register missing agents in agents.json5

**Files to modify:**
- `personal-ai-space/engine/config/agents.json5`

**Issue:** Config lists 7 agents, but engine.py imports 10. Missing: `mcp-agent`, `behavior-observer`, `pattern-learner`.

**Spawning instructions:**

Spawn a `quick` agent with:
- `load_skills=[]`
- `run_in_background=false`
- Prompt: "Add the 3 missing agent entries to `/Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine/config/agents.json5`. Add them after the last existing entry (github-agent):

```json5
  {
    "id": "mcp-agent",
    "name": "MCP Agent",
    "description": "Manages external MCP server connections and tool indexing",
    "priority": "medium",
    "dependencies": ["mcp_registry.json5"],
    "capabilities": [
      "Connect to MCP servers",
      "Discover tools",
      "Route tool calls",
      "Handle server lifecycle"
    ],
    "triggers": ["on_startup", "server_change"],
    "outputs": ["tool_registry", "server_status"],
    "error_handling": "log_and_continue"
  },
  {
    "id": "behavior-observer",
    "name": "Behavior Observer",
    "description": "Observes and logs user actions, task creation/completion, and habit tracking for behavioral analysis",
    "priority": "low",
    "dependencies": ["self.db"],
    "capabilities": [
      "Log user actions",
      "Track task lifecycle",
      "Monitor habit streaks",
      "Record context changes"
    ],
    "triggers": ["on_action", "scheduled_sync"],
    "outputs": ["behavior_log", "action_stream"],
    "error_handling": "log_and_continue"
  },
  {
    "id": "pattern-learner",
    "name": "Pattern Learner",
    "description": "Learns user patterns from observed behavior — time patterns, preferences, workflows",
    "priority": "low",
    "dependencies": ["self.db", "memories.db"],
    "capabilities": [
      "Infer time patterns",
      "Detect preferences",
      "Learn workflows",
      "Predict next actions"
    ],
    "triggers": ["scheduled_learning", "on_new_data"],
    "outputs": ["patterns", "predictions"],
    "error_handling": "degrade_gracefully"
  }
```

Make sure JSON5 syntax is valid — no trailing commas, proper indentation. After editing, verify with:
```bash
cd /Users/paulorezende/Documents/Personal_AI_powerhouse
python3 -c "import json5; data = json5.load(open('personal-ai-space/engine/config/agents.json5')); print(f'{len(data)} agents registered'); [print(f'  - {a[\"id\"]}') for a in data]"
# Expected: "10 agents registered" with all 10 IDs listed"
```

If `json5` is not installed, run `pip install json5` first."

**Verification:**
```bash
python3 -c "import json5; d=json5.load(open('personal-ai-space/engine/config/agents.json5')); print(f'{len(d)} agents')"
# Expected: "10 agents"
python3 -m pytest personal-ai-space/engine/tests/ -v --tb=short 2>&1 | tail -5
# All tests must pass
```

**Rollback:** `git checkout personal-ai-space/engine/config/agents.json5`

---

### Task 4.2: Refactor BehaviorObserver and PatternLearner to extend BaseAgent

**Files to modify:**
- `personal-ai-space/engine/agents/behavior_observer.py`
- `personal-ai-space/engine/agents/pattern_learner.py`
- `personal-ai-space/engine/agents/base_agent.py` (if needed for interface adjustments)

**Issue:** Both classes are plain classes (no inheritance). They don't implement the standard `BaseAgent` lifecycle (`execute()`, `get_capabilities()`, `get_metadata()`).

**Spawning instructions:**

Spawn a `deep` agent with:
- `load_skills=["architecture-patterns"]`
- `run_in_background=false`
- Prompt: "Refactor `BehaviorObserver` and `PatternLearner` to extend `BaseAgent` in the Personal AI Powerhouse project. This is a structural refactor — behavior must NOT change.

First read the reference implementation:
1. `agents/base_agent.py` — understand the BaseAgent interface
2. `agents/behavior_observer.py` — current plain class
3. `agents/pattern_learner.py` — current plain class
4. `engine.py` — lines 55-65 show how they're initialized separately as observers

**Requirements:**
- Both classes must inherit from `BaseAgent`
- Implement `execute()`, `get_capabilities()`, `get_metadata()` methods
- The `id` property must match their existing usage in engine.py
- Preserve ALL existing functionality — `observe()`, `get_behavior_log()` etc must still work
- Do NOT change how engine.py initializes them (they're initialized outside the agent_classes loop — that's intentional)
- `engine.py` currently creates them as `self._observer = BehaviorObserver()` and `self._pattern_learner = PatternLearner()` — these instantiations must still work

After refactoring, verify:
```bash
cd /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine
# Test that the agents can be instantiated and have base agent methods
python3 -c "
from agents.behavior_observer import BehaviorObserver
from agents.pattern_learner import PatternLearner
from agents.base_agent import BaseAgent

assert issubclass(BehaviorObserver, BaseAgent), 'Must extend BaseAgent'
assert issubclass(PatternLearner, BaseAgent), 'Must extend BaseAgent'

bo = BehaviorObserver()
pl = PatternLearner()
assert hasattr(bo, 'execute'), 'Missing execute()'
assert hasattr(pl, 'execute'), 'Missing execute()'
assert hasattr(bo, 'get_capabilities'), 'Missing get_capabilities()'
assert hasattr(pl, 'get_capabilities'), 'Missing get_capabilities()'
print('BehaviorObserver id:', bo.id)
print('PatternLearner id:', pl.id)
print('All checks passed')
"

# Run tests
python3 -m pytest tests/ -v --tb=short 2>&1 | tail -5
# All tests must pass
```

Report: what methods were added, what BaseAgent features each class now uses, any engine.py adjustments needed."

**Verification:**
```bash
cd /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine
python3 -c "
from agents.behavior_observer import BehaviorObserver
from agents.pattern_learner import PatternLearner
from agents.base_agent import BaseAgent
assert issubclass(BehaviorObserver, BaseAgent)
assert issubclass(PatternLearner, BaseAgent)
print('Both extend BaseAgent — OK')
"
# Expected: "Both extend BaseAgent — OK"
python3 -m pytest tests/ -v --tb=short 2>&1 | tail -5
# All tests must pass
```

**Rollback:** `git checkout` on modified agent files.

---

### Task 4.3: Commit untracked architecture diagrams (optional)

**Files:**
- `personal-ai-space/docs/diagrams/` — 8 files (3 D2 + 4 SVG + 1 HTML)

**Spawning instructions:**

Spawn a `quick` agent with `load_skills=["git-master"]` and:
- Prompt: "Stage and commit the 8 untracked files in `personal-ai-space/docs/diagrams/` with commit message: `docs(diagrams): add architecture diagrams — agent communication, container architecture, data flow intake`. Do NOT push. Use a commit, not --amend."

**Verification:**
```bash
git log --oneline -1
# Expected: commit message matches above
git status --short personal-ai-space/docs/diagrams/
# Expected: empty (no untracked/modified files)
```

**Rollback:** `git reset HEAD~1`

---

## Phase 5: Stale Branches Cleanup

**Objective:** Remove noise from branch list by deleting auto-generated snapshot branches.

**Success Criteria:**
- All `entire/*` branches deleted locally
- `memory-layer-refactory` archived if no longer active
- `git branch` shows only `main` and `feature/llm-integration`

---

### Task 5.1: Delete stale entire/* branches

**Branches to delete:**
- All 12 branches matching `entire/*`

**NOT to delete:**
- `main` (production)
- `feature/llm-integration` (current active branch)
- `memory-layer-refactory` (may have valuable work — keep for user to decide)
- Remote branches on origin (user must decide)

**Spawning instructions:**

Spawn a `quick` agent with `load_skills=["git-master"]` and:
- Prompt: "Delete all local branches matching `entire/*` in the repo at `/Users/paulorezende/Documents/Personal_AI_powerhouse`. Use `git branch --list 'entire/*' | xargs git branch -D` to force-delete them. These are auto-generated session snapshot branches with no meaningful code changes. After deletion, run `git branch` and report the remaining branches."

**Verification:**
```bash
git branch --list 'entire/*'
# Expected: empty (no output)
git branch
# Expected: only main, feature/llm-integration, and possibly memory-layer-refactory
```

**Rollback:** `git reflog` to recover deleted branches if needed.

---

## Final Verification Gate

After ALL phases complete, run this comprehensive check:

```bash
# 1. Syntax check
find . -name "*.py" ! -path "*/node_modules/*" ! -path "*/.git/*" ! -path "*/__pycache__/*" ! -path "*/.venv/*" ! -path "*/venv/*" ! -path "*/site-packages/*" -exec python3 -m py_compile {} \; 2>&1 | head -5
echo "Syntax: $?"

# 2. Test suite
cd /Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space/engine
python3 -m pytest tests/ -v --tb=short 2>&1 | tail -10

# 3. Engine startup smoke test
python3 -c "
from engine import Engine
import logging
logging.basicConfig(level=logging.WARNING)
eng = Engine()
eng.start()
eng.shutdown()
print('Engine started and stopped cleanly')
" 2>&1 | grep -c "no such table"

# 4. Branch count
cd /Users/paulorezende/Documents/Personal_AI_powerhouse
echo "Branches: $(git branch | wc -l)"

# 5. Empty except count
echo "Empty excepts:"
grep -rn "except.*:" --include="*.py" . | grep -v node_modules | grep -v ".git/" | grep -v "__pycache__" | grep -v ".venv/" | grep -v "site-packages" | while IFS=: read f l r; do n=$(sed -n "$((l+1))p" "$f" 2>/dev/null); if echo "$n" | grep -q "^\s*pass"; then echo "  $f:$l"; fi; done | wc -l
```

**PASS criteria for project close:**
- [ ] All Python files compile (exit 0)
- [ ] 72 engine tests pass, 0 fail
- [ ] Engine starts with 0 "no such table" errors
- [ ] No `.gitignore`-ignored branches listed in `git branch`
- [ ] Empty except count < 10 (only intentional swallows remain)
- [ ] `__init__.py` present in all Python source directories
- [ ] `agents.json5` lists all 10 agents
- [ ] `BehaviorObserver` and `PatternLearner` extend `BaseAgent`

---

## Rollback Strategy

Each task specifies its own rollback (typically `git checkout` on modified files). For a full project rollback:

```bash
cd /Users/paulorezende/Documents/Personal_AI_powerhouse
git checkout -- .
git branch -D $(git branch --list 'entire/*')
```

This resets all modified files to HEAD and re-deletes entire/* branches (they'll be recreated by the Entire CLI plugin on next session, but that's fine).

---

*Plan generated 2026-05-15. Based on audit at `project-audit-completeness-report.md`.*
