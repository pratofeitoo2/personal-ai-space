# GitHub Specialist Agent

## TL;DR

> **Quick Summary**: Add a new GitHub Specialist agent to the personal AI engine that handles all git/GitHub operations (repositories, branches, worktrees, commits, syncs) and maintains bidirectional communication with every other agent to track their work via passive observation, active notifications, and peer messaging.

> **Deliverables**:
> - New `git.db` SQLite database with `git_repos` schema
> - `github_agent.py` — Python agent implementing `BaseAgent`
> - Agent registered in `agents.config.json`
> - Engine wiring in `engine.py` (registration + convenience wrappers + notification bridge)
> - Git CLI helper module for local git operations
> - GitHub API wrapper using `gh` CLI
> - Auto-discovery scanner for workspace git repos
> - Periodic sync engine with idle detection
> - Cross-agent communication handlers (subscribe to agent broadcasts + pub/sub)
> - BehaviorObserver integration for passive tracking
> - Guardrails: no force push, only registered repos, no auto-push
> - Unit + integration tests

> **Estimated Effort**: Medium
> **Parallel Execution**: YES — 4 waves
> **Critical Path**: T1 → T3 → T5 → T10 → T14 → F1-F4 → User OK

---

## Context

### Original Request
Add a GitHub Specialist agent to handle repositories, branches, worktrees, commits, syncs. Must have direct connection with every other agent to track their work.

### Interview Summary
**Key Discussions**:
- Connection model: Full bidirectional — passive observer + active notifications + peer messaging
- Git operations: All — Git CLI locally, GitHub API via `gh` CLI, auto-commit, repo management, branch lifecycle
- Storage: New SQLite table `git_repos` in new `git.db`
- Auth: GitHub CLI (`gh`) + SSH keys for git
- Auto-commit: Idle detection (2 min) + configurable fixed interval
- Guardrails: No force push to main, only registered repos, no auto-push
- Test strategy: Tests after implementation
- Repo discovery: Auto-scan workspace paths for `.git`

### Research Findings
- 6 agents in registry: ContextManager, TaskCoordinator, InsightGenerator, ReminderSystem, KnowledgeIndexer, ReportGenerator
- Plus MCPAgent (external tool routing) + BehaviorObserver + PatternLearner
- All agents implement `BaseAgent` with `handle()` → `process()` lifecycle
- Engine routes messages via `send()` with logging to DB + BehaviorObserver
- Communication protocol: JSON messages (request-response, pub/sub, parallel)
- No existing git/GitHub tools in the engine

---

## Work Objectives

### Core Objective
Create a fully functional GitHub Specialist agent that manages git/GitHub operations across all repos in the workspace, tracks agent work via cross-agent communication, and auto-syncs with configurable policies.

### Concrete Deliverables
- `personal-ai-space/engine/agents/github_agent.py` — Agent implementation
- `personal-ai-space/engine/agents/github_git_ops.py` — Git CLI helper
- `personal-ai-space/engine/agents/github_gh_api.py` — GitHub API wrapper
- `personal-ai-space/engine/agents/github_discovery.py` — Repo auto-discovery
- `personal-ai-space/engine/agents/github_sync.py` — Sync/commit engine
- `personal-ai-space/engine/agents/agents.config.json` — Updated with new agent entry
- `personal-ai-space/engine/engine.py` — Updated with agent registration + notification bridge
- `personal-ai-space/engine/db/schema_git_repos.sql` — SQLite schema
- `personal-ai-space/engine/db/git.db` — New database (created at runtime)
- `personal-ai-space/engine/agents/__init__.py` — Updated exports
- Agent tests

### Definition of Done
- [ ] Engine starts with GitHub agent registered and connected
- [ ] Agent can discover git repos in workspace paths
- [ ] Agent executes git CLI commands (status, branch, commit, log)
- [ ] Agent executes GitHub API calls via gh CLI
- [ ] Agent receives broadcasts from other agents
- [ ] Agent performs periodic sync with idle detection
- [ ] Guardrails enforced: no force push, only registered repos, no auto-push
- [ ] All tests pass

### Must Have
- Agent registration in `agents.config.json` with full metadata
- `github_agent.py` implementing `BaseAgent` with `process()`, `initialize()`, `shutdown()`
- Engine wiring: agent loaded in `engine.py` startup, accessible via `send("github-agent", ...)`
- Cross-agent communication: subscribe to `agent_work_completed` broadcasts
- Sync engine with idle detection + configurable interval
- Git CLI operations: clone, init, status, add, commit, branch, checkout, merge, log, worktree
- GitHub API operations via `gh`: repo info, PR list, issue list, status checks
- Auto-discovery of git repos in configured workspace paths
- New `git.db` with `git_repos` table for tracking repos, branches, workstates

### Must NOT Have (Guardrails)
- NO force pushes to main/master branches
- NO operations on unregistered repos (only repos tracked in git.db)
- NO auto-push without explicit confirmation
- NO destructive git operations (reset --hard, push --force) without explicit command
- NO direct filesystem modifications outside git operations
- NO deployment/CI-CD pipeline management (scope boundary)

---

## Verification Strategy (MANDATORY)

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed. No exceptions.

### Test Decision
- **Infrastructure exists**: YES (pytest in personal-ai-space/engine/tests/)
- **Automated tests**: Tests after implementation
- **Framework**: pytest
- **Agent-Executed QA**: ALWAYS — each task has runnable QA scenarios

### QA Policy
Every task MUST include agent-executed QA scenarios:
- **Git operations**: Create temp git repos, run commands, verify output
- **GitHub API**: Use `gh api` in read-only mode (list repos, check status)
- **Agent communication**: Send test messages via engine, verify responses
- **Sync engine**: Create files, trigger sync, verify commits created

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Foundation — all independent):
├── T1: Git.db schema (sql + db init)
├── T2: Agent config + command definitions
├── T3: GitHub agent skeleton (BaseAgent subclass)
└── T4: Engine wiring (registration + send integration)

Wave 2 (Core modules — depends on T3, parallel among themselves):
├── T5: Git CLI helper module (github_git_ops.py)
├── T6: GitHub API wrapper (github_gh_api.py)
├── T7: Repo auto-discovery (github_discovery.py)
├── T8: Cross-agent communication handlers
└── T9: BehaviorObserver integration

Wave 3 (Integration layer — depends on Wave 2):
├── T10: Auto-commit/sync engine (github_sync.py)
├── T11: Engine notification bridge + guardrails
└── T12: Configuration + error handling

Wave 4 (Testing — parallel with Wave 3 + standalone):
├── T13: Unit tests for git ops + gh API
└── T14: Integration tests (cross-agent messaging, sync, discovery)

Wave FINAL (Verification — after ALL tasks):
├── F1: Plan compliance audit (oracle)
├── F2: Code quality review (unspecified-high)
├── F3: Real manual QA (unspecified-high)
└── F4: Scope fidelity check (deep)
```

### Dependency Matrix
- **T1-T4**: independent, start immediately
- **T5**: T3 — T10
- **T6**: T3 — T10
- **T7**: T3 — T10
- **T8**: T3 — T10, T11
- **T9**: T3 — T11
- **T10**: T5, T6, T7 — T13, T14
- **T11**: T8, T9 — T13, T14
- **T12**: T3 — T13, T14
- **T13**: T10, T11, T12 — F1-F4
- **T14**: T10, T11, T12 — F1-F4

---

## TODOs

- [x] 1. Create git.db schema and initialization

  **What to do**:
  - Create `personal-ai-space/engine/db/schema_git_repos.sql` with:
    - `repos` table: id, name, path, remote_url, default_branch, last_synced_at, is_registered, created_at, updated_at
    - `branches` table: id, repo_id (FK), name, is_active_worktree, last_committed_at, created_at
    - `sync_log` table: id, repo_id (FK), action, status, commit_hash, details, started_at, completed_at
    - `worktrees` table: id, repo_id (FK), name, path, branch, created_at
    - Appropriate indexes on repo_id, status, last_synced_at
  - Add `git.db` initialization to `db_manager.py` (follow existing pattern for self.db, tasks.db, memories.db)
  - Add `init_git_db()`, `health_check_git()`, and query helpers in `db_manager.py`
  - Follow the existing schema pattern in `schema_agent_memory.sql`

  **Must NOT do**:
  - Don't modify existing DB schemas
  - Don't use ORM — follow raw SQLite pattern

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []
  - **Category reason**: Straightforward SQL + Python DB wiring, well-defined patterns to follow

  **Parallelization**:
  - **Can Run In Parallel**: YES — Wave 1
  - **Parallel Group**: Wave 1 (with T2, T3, T4)
  - **Blocks**: T10 (sync engine needs git.db)
  - **Blocked By**: None (can start immediately)

  **References**:
  - `personal-ai-space/engine/db/schema_agent_memory.sql` — Schema pattern (CREATE TABLE, indexes, IF NOT EXISTS)
  - `personal-ai-space/engine/db_manager.py` — DB initialization and query helper patterns (init_all, health_check)
  - `personal-ai-space/engine/db/migrate_tasks.py` — Migration pattern for new database
  - `personal-ai-space/engine/agents/insight_generator.py:initialize()` — Example of agent wiring to a database

  **Acceptance Criteria**:
  - [ ] `schema_git_repos.sql` exists with repos, branches, sync_log, worktrees tables
  - [ ] `db_manager.py` has `init_git_db()` that creates git.db
  - [ ] `python -c "from db_manager import init_git_db; init_git_db(); print('OK')"` → OK

  **QA Scenarios**:
  ```
  Scenario: DB schema creation
    Tool: Bash
    Preconditions: schema_git_repos.sql exists, db_manager.py has init_git_db()
    Steps:
      1. Run: python -c "import db_manager; db_manager.init_git_db(); print('OK')"
      2. Run: sqlite3 engine/db/git.db ".tables"  (verify repos, branches, sync_log, worktables exist)
      3. Run: sqlite3 engine/db/git.db ".schema repos"
    Expected Result: All 4 tables created with correct columns
    Failure Indicators: Missing tables, wrong column types, sqlite3 error
    Evidence: .sisyphus/evidence/task-1-db-schema.txt

  Scenario: DB health check
    Tool: Bash
    Preconditions: git.db initialized
    Steps:
      1. Run: python -c "import db_manager; print(db_manager.health_check().get('git'))"
    Expected Result: {'ok': True, 'tables': 4}
    Evidence: .sisyphus/evidence/task-1-db-health.txt
  ```

  **Commit**: YES
  - Message: `feat(db): add git.db schema for GitHub agent repo tracking`
  - Files: `schema_git_repos.sql`, `db_manager.py`

- [x] 2. Register GitHub agent in agents.config.json

  **What to do**:
  - Add new entry to `personal-ai-space/engine/agents/agents.config.json`:
    - `id`: "github-agent"
    - `name`: "GitHub Specialist"
    - `description`: "Manages git repositories, branches, worktrees, commits, and syncs. Tracks agent work across the system via cross-agent communication."
    - `priority`: "high"
    - `dependencies`: ["git.db", "gh CLI", "git CLI"]
    - `capabilities`: git operations (clone, branch, commit, merge, log, worktree), GitHub API (repo info, PRs, issues), repo auto-discovery, auto-commit/sync, agent work tracking
    - `triggers`: ["scheduled_sync", "agent_work_completed", "on_startup", "on_command"]
    - `outputs`: ["git_status", "sync_report", "commit_log", "repo_discovery"]
    - `error_handling`: "retry_with_backoff"
  - Define the command schema for the agent in a comment block at the top of `github_agent.py` (to be implemented in T3):
    - Commands: status, branch_list, branch_create, branch_delete, commit, log, pull, push, clone, init, worktree_add, worktree_list, repo_discover, repo_register, repo_list, sync_now, gh_repo_info, gh_pr_list, gh_ci_status

  **Must NOT do**:
  - Don't modify existing agent entries
  - Don't remove any existing config fields

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []
  - **Category reason**: Simple JSON config entry + documentation comments

  **Parallelization**:
  - **Can Run In Parallel**: YES — Wave 1
  - **Group**: Wave 1 (with T1, T3, T4)
  - **Blocks**: T8 (cross-agent handlers reference commands)
  - **Blocked By**: None

  **References**:
  - `personal-ai-space/engine/agents/agents.config.json` — Full existing config with all agent entries
  - `personal-ai-space/engine/agents/task_coordinator.py:1-30` — Command doc comment pattern

  **Acceptance Criteria**:
  - [ ] `agents.config.json` has valid JSON with github-agent entry
  - [ ] All required fields present: id, name, description, priority, dependencies, capabilities, triggers, outputs, error_handling

  **QA Scenarios**:
  ```
  Scenario: Config entry validation
    Tool: Bash
    Preconditions: agents.config.json updated
    Steps:
      1. Run: python -c "import json; c=json.load(open('engine/agents/agents.config.json')); a=[x for x in c if x['id']=='github-agent']; print(a[0]['name'])"
    Expected Result: "GitHub Specialist"
    Evidence: .sisyphus/evidence/task-2-config.json

  Scenario: JSON validity
    Tool: Bash
    Preconditions: agents.config.json
    Steps:
      1. Run: python -c "import json; json.load(open('engine/agents/agents.config.json')); print('VALID')"
    Expected Result: VALID
    Evidence: .sisyphus/evidence/task-2-valid-json.txt
  ```

  **Commit**: YES (with T3 or standalone)
  - Message: `feat(agents): register GitHub Specialist agent in config`
  - Files: `agents.config.json`

- [x] 3. Implement GitHub Agent base class

  **What to do**:
  - Create `personal-ai-space/engine/agents/github_agent.py`:
    - Class `GitHubAgent(BaseAgent)` with agent_id="github-agent"
    - `initialize()`: Create git.db tables if needed, discover registered repos from DB, setup sync timer, return True
    - `process(message)`: Route incoming messages by `payload.command` to handler methods
    - `shutdown()`: Flush any pending sync, save state, close DB connections
    - Implement base command handlers (delegate actual work to helper modules T5-T7):
      - `cmd_status()`: return current git status of all registered repos
      - `cmd_branch_list()`: list branches for a repo
      - `cmd_commit()`: commit staged changes with message
      - `cmd_log()`: recent commit log
      - `cmd_repo_list()`: list registered repos with metadata
      - `cmd_sync_now()`: trigger immediate sync
      - Default handler returning `_unknown(command)` for unimplemented commands
    - Use `self.logger`, `_ok()`, `_error()` from BaseAgent
    - Wire `self.discovery` (GitHubDiscovery from T7), `self.git_ops` (GitOps from T5), `self.gh_api` (GitHubAPI from T6) — initialize as None for now with TODOs to wire once helper modules exist
    - Set `self.state = "ready"` on successful init
    - Add `set_observer()` passthrough to super

  **Must NOT do**:
  - No external API calls during initialize() (lazy connect)
  - No blocking startup — init should be fast
  - Keep it clean — one command per handler method

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: []
  - **Category reason**: Core agent implementation with message routing, needs care

  **Parallelization**:
  - **Can Run In Parallel**: YES — Wave 1
  - **Group**: Wave 1 (with T1, T2, T4)
  - **Blocks**: T5, T6, T7, T8, T9, T12 (all depend on the agent class existing)
  - **Blocked By**: None

  **References**:
  - `personal-ai-space/engine/agents/base_agent.py` — Full BaseAgent implementation (handle, process, shutdown, _ok, _error)
  - `personal-ai-space/engine/agents/task_coordinator.py:24-31` — Initialization pattern
  - `personal-ai-space/engine/agents/mcp_agent.py:32-62` — More complex agent init pattern
  - `personal-ai-space/engine/agents/context_manager.py` — Agent with DB dependency pattern

  **Acceptance Criteria**:
  - [ ] `github_agent.py` exists with `GitHubAgent(BaseAgent)` class
  - [ ] `initialize()` returns True and sets state to "ready"
  - [ ] `python -c "from agents.github_agent import GitHubAgent; a=GitHubAgent(); print(a.initialize())"` → True
  - [ ] `python -c "from agents.github_agent import GitHubAgent; a=GitHubAgent(); a.initialize(); r=a.handle({'payload':{'command':'status'}}); print(r['status'])"` → success

  **QA Scenarios**:
  ```
  Scenario: Agent initialization
    Tool: Bash
    Preconditions: github_agent.py created
    Steps:
      1. cd personal-ai-space/engine
      2. python -c "from agents.github_agent import GitHubAgent; a=GitHubAgent(); result=a.initialize(); print(f'init={result} state={a.state}')"
    Expected Result: "init=True state=ready"
    Evidence: .sisyphus/evidence/task-3-agent-init.txt

  Scenario: Basic command routing
    Tool: Bash
    Preconditions: Agent initialized
    Steps:
      1. python -c "
from agents.github_agent import GitHubAgent
a = GitHubAgent()
a.initialize()
msg = {'payload': {'command': 'status', 'parameters': {}}}
print(a.handle(msg)['status'])
"
    Expected Result: "success" (even if body is empty/placeholder)
    Evidence: .sisyphus/evidence/task-3-command-routing.txt

  Scenario: Unknown command returns error
    Tool: Bash
    Preconditions: Agent initialized
    Steps:
      1. python -c "
from agents.github_agent import GitHubAgent
a = GitHubAgent()
a.initialize()
msg = {'payload': {'command': 'nonexistent'}}
print(a.handle(msg)['status'], a.handle(msg)['error'][:30])
"
    Expected Result: "error Unknown command: nonexistent"
    Evidence: .sisyphus/evidence/task-3-unknown-cmd.txt
  ```

  **Commit**: YES
  - Message: `feat(agents): implement GitHubAgent base class with command routing`
  - Files: `github_agent.py`

- [x] 4. Wire GitHub Agent into engine

  **What to do**:
  - Add import in `personal-ai-space/engine/engine.py`: `from agents.github_agent import GitHubAgent`
  - Add `GitHubAgent` to the `agent_classes` list in `Engine.start()`
  - Add convenience wrapper methods to `Engine`:
    - `git_status(repo_id=None)` → `send("github-agent", "status", {"repo_id": repo_id})`
    - `git_sync_now(repo_id=None)` → `send("github-agent", "sync_now", {"repo_id": repo_id})`
    - `git_repo_list()` → `send("github-agent", "repo_list")`
  - Wire notification hook: In `Engine.send()`, after successful agent interaction, check if the result has work-related changes and optionally notify GitHub agent (stub for T11)
  - Update `personal-ai-space/engine/agents/__init__.py` to export `GitHubAgent`

  **Must NOT do**:
  - Don't modify existing agent initialization flow
  - Don't change existing engine.send() behavior — only add observation hook

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []
  - **Category reason**: Well-defined pattern additions to existing engine code

  **Parallelization**:
  - **Can Run In Parallel**: YES — Wave 1
  - **Group**: Wave 1 (with T1, T2, T3)
  - **Blocks**: T11 (notification bridge), T14 (integration tests)
  - **Blocked By**: T3 (github_agent.py must exist)

  **References**:
  - `personal-ai-space/engine/engine.py:19-27` — Agent import pattern
  - `personal-ai-space/engine/engine.py:55-63` — Agent class list
  - `personal-ai-space/engine/engine.py:187-206` — Convenience wrapper method pattern (daily_digest, todays_tasks, etc.)
  - `personal-ai-space/engine/engine.py:120-184` — send() method with observer wiring
  - `personal-ai-space/engine/agents/__init__.py` — Module exports

  **Acceptance Criteria**:
  - [ ] `engine.py` imports GitHubAgent
  - [ ] `engine.py` has `GitHubAgent` in agent_classes
  - [ ] Engine starts with GitHub agent active (log shows "✓ Agent: github-agent")
  - [ ] Engine convenience methods: `git_status`, `git_sync_now`, `git_repo_list`

  **QA Scenarios**:
  ```
  Scenario: Engine starts with GitHub agent
    Tool: Bash
    Preconditions: engine.py updated
    Steps:
      1. cd personal-ai-space/engine
      2. python -c "
from engine import Engine
e = Engine(log_level='ERROR')
ok = e.start()
agents = [a for a in e._agents.keys()]
print(f'started={ok} github_agent={\"github-agent\" in agents}')
e.stop()
"
    Expected Result: "started=True github_agent=True"
    Failure Indicators: Engine fails to start, agent not registered
    Evidence: .sisyphus/evidence/task-4-engine-start.txt

  Scenario: Git repo_list convenience wrapper
    Tool: Bash
    Preconditions: Engine running
    Steps:
      1. python -c "
from engine import Engine
e = Engine(log_level='ERROR')
e.start()
result = e.git_repo_list()
e.stop()
print(f'status={result.get(\"status\")} payload={result.get(\"payload\")}')
"
    Expected Result: "status=success" (with empty list or valid payload)
    Evidence: .sisyphus/evidence/task-4-convenience.txt
  ```

  **Commit**: YES (group with T3)
  - Message: `feat(engine): wire GitHubAgent into engine with convenience wrappers`
  - Files: `engine.py`, `__init__.py`

- [x] 5. Implement Git CLI helper module

  **What to do**:
  - Create `personal-ai-space/engine/agents/github_git_ops.py` with class `GitOps`:
    - `__init__(repo_path: str)` — path to a git repository
    - `status()` — returns dict with branch, modified/staged/untracked files, ahead/behind counts
    - `branch_list()` — returns list of branches with current marker
    - `branch_create(name: str, base: str = None)` — create branch from base or HEAD
    - `branch_delete(name: str, force: bool = False)` — delete branch (safe: refuses if unmerged)
    - `branch_current()` — returns current branch name
    - `add(paths: list[str] = [])` — stage files (default: all)
    - `commit(message: str, author: str = None)` — create commit, returns commit hash
    - `log(n: int = 10)` — recent commits with hash, message, author, date
    - `pull(remote: str = "origin", branch: str = None)` — git pull with merge handling
    - `push(remote: str = "origin", branch: str = None, force: bool = False)` — git push. If force=True, check guardrail and refuse (only allow with explicit `allow_force=True` parameter)
    - `clone(url: str, path: str, branch: str = None)` — clone a repository
    - `init(path: str)` — init new repository
    - `worktree_add(path: str, branch: str)` — add worktree
    - `worktree_list()` — list worktrees
    - `diff()` — return unstaged diff
    - `has_uncommitted()` — bool, check for uncommitted changes
    - `last_commit_time()` — datetime of last commit
    - All methods use `subprocess.run()` with shell=False, capture_output=True
    - Raise `GitOperationError` on non-zero exit codes
    - Log all operations via `get_logger("github-agent.git_ops")`
    - Guardrail: `_check_force_push()` — raises if force push to main/master

  **Must NOT do**:
  - No interactive git commands (no -i flags)
  - No destructive defaults (force=False everywhere)
  - Do NOT modify any actual repos during testing — create temp repos

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: []
  - **Category reason**: Multiple git subprocess commands with error handling

  **Parallelization**:
  - **Can Run In Parallel**: YES — Wave 2
  - **Group**: Wave 2 (with T6, T7, T8, T9)
  - **Blocks**: T10 (sync engine needs GitOps)
  - **Blocked By**: T3 (base agent exists, for import pattern reference)

  **References**:
  - Python `subprocess` docs — `subprocess.run()` pattern (use with `capture_output=True`, `text=True`, `shell=False`)
  - `personal-ai-space/engine/agents/mcp_agent.py` — subprocess usage pattern for running external commands
  - Real git CLI commands: `git status --porcelain`, `git branch`, `git log --oneline --format="..."`, `git worktree list`

  **Acceptance Criteria**:
  - [ ] `github_git_ops.py` exists with `GitOps` class
  - [ ] `python -c "from agents.github_git_ops import GitOps; print('OK')"` → OK
  - [ ] All methods documented with docstrings

  **QA Scenarios**:
  ```
  Scenario: GitOps on a temp repo
    Tool: Bash
    Preconditions: github_git_ops.py exists
    Steps:
      1. mkdir -p /tmp/test_gitops && cd /tmp/test_gitops && git init && git config user.email "test@test.com" && git config user.name "Test"
      2. echo "hello" > test.txt && git add test.txt && git commit -m "initial"
      3. python -c "
import sys; sys.path.insert(0, 'personal-ai-space/engine')
from agents.github_git_ops import GitOps
g = GitOps('/tmp/test_gitops')
s = g.status()
b = g.branch_current()
l = g.log(1)
print(f'branch={b} files={s[\"staged\"]} log={len(l[\"commits\"])}')
"
    Expected Result: "branch=master files=['test.txt'] log=1"
    Failure Indicators: GitOps fails to parse git output, wrong counts
    Evidence: .sisyphus/evidence/task-5-gitops-basic.txt

  Scenario: GitOps commit flow
    Tool: Bash
    Preconditions: Temp repo from previous scenario
    Steps:
      1. cd /tmp/test_gitops && echo "world" >> test.txt
      2. python -c "
import sys; sys.path.insert(0, 'personal-ai-space/engine')
from agents.github_git_ops import GitOps
g = GitOps('/tmp/test_gitops')
g.add(['test.txt'])
r = g.commit('test commit')
print(f'commit={r[\"hash\"][:8]} files={r[\"files_changed\"]}')
"
    Expected Result: "commit=<hash> files=1"
    Evidence: .sisyphus/evidence/task-5-gitops-commit.txt

  Scenario: Force push guardrail
    Tool: Bash
    Preconditions: Temp repo
    Steps:
      1. python -c "
import sys; sys.path.insert(0, 'personal-ai-space/engine')
from agents.github_git_ops import GitOps
from agents.github_git_ops import GitOperationError
g = GitOps('/tmp/test_gitops')
try:
    g.push(force=True)
    print('NO GUARDRAIL')
except GitOperationError as e:
    print(f'GUARDRAIL: {str(e)[:60]}')
"
    Expected Result: "GUARDRAIL: ..." (error raised about force push on main)
    Evidence: .sisyphus/evidence/task-5-gitops-guardrail.txt
  ```

  **Commit**: YES
  - Message: `feat(agents): implement Git CLI helper (git-ops)`
  - Files: `github_git_ops.py`

- [x] 6. Implement GitHub API wrapper

  **What to do**:
  - Create `personal-ai-space/engine/agents/github_gh_api.py` with class `GitHubAPI`:
    - `__init__()` — check `gh` CLI availability, verify auth status via `gh auth status`
    - `repo_info(owner: str, repo: str)` — returns dict: description, stars, forks, default_branch, last_updated, open_issues, open_prs
    - `pr_list(owner: str, repo: str, state: str = "open")` — list PRs with title, number, author, status
    - `issue_list(owner: str, repo: str, state: str = "open")` — list issues
    - `ci_status(owner: str, repo: str, branch: str = None)` — latest CI run status
    - `repo_list_for_user()` — list user's repos via `gh repo list`
    - `check_rate_limit()` — return API rate limit info
    - `is_authenticated()` — bool
    - All methods use `subprocess.run([gh,...])` with JSON output parsing
    - Raise `GitHubAPIError` on gh CLI failures
    - Log all calls via `get_logger("github-agent.gh_api")`

  **Must NOT do**:
  - No destructive API calls (no create/delete PRs, no merge, no push)
  - Read-only API access only — all mutating operations go through T5 (GitOps)
  - Don't require gh interactive mode — use `--json` flags for non-interactive output

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: []
  - **Category reason**: CLI wrapper with JSON parsing, needs error handling patterns

  **Parallelization**:
  - **Can Run In Parallel**: YES — Wave 2
  - **Group**: Wave 2 (with T5, T7, T8, T9)
  - **Blocks**: T10 (sync engine can use gh info)
  - **Blocked By**: T3 (base agent reference)

  **References**:
  - `gh repo list --json name,description,owner,isPrivate` — JSON output format
  - `gh api repos/{owner}/{repo} --jq '.description,.stargazers_count,.open_issues_count'` — API query pattern
  - `gh pr list --json number,title,state,headRefName,author --repo {owner}/{repo}` — PR list JSON
  - `personal-ai-space/engine/agents/github_git_ops.py` — Similar subprocess pattern (reference after T5)

  **Acceptance Criteria**:
  - [ ] `github_gh_api.py` exists with `GitHubAPI` class
  - [ ] `python -c "from agents.github_gh_api import GitHubAPI; print('OK')"` → OK
  - [ ] `is_authenticated()` works (may return False if gh not configured)

  **QA Scenarios**:
  ```
  Scenario: GitHub API init checks gh availability
    Tool: Bash
    Preconditions: github_gh_api.py exists
    Steps:
      1. cd personal-ai-space/engine
      2. python -c "
import sys
from agents.github_gh_api import GitHubAPI
api = GitHubAPI()
print(f'auth={api.is_authenticated()}')
"
    Expected Result: "auth=True" or "auth=False" (depends on gh auth status)
    Evidence: .sisyphus/evidence/task-6-gh-auth.txt

  Scenario: GitHub API repo list (read-only)
    Tool: Bash
    Preconditions: gh authenticated
    Steps:
      1. python -c "
import sys; sys.path.insert(0, 'personal-ai-space/engine')
from agents.github_gh_api import GitHubAPI
api = GitHubAPI()
if api.is_authenticated():
    repos = api.repo_list_for_user()[:3]
    print(f'repos={len(repos)} names={[r[\"name\"] for r in repos]}')
else:
    print('SKIP: not authenticated')
"
    Expected Result: "repos=N names=[...]" or "SKIP: not authenticated"
    Evidence: .sisyphus/evidence/task-6-gh-repos.txt
  ```

  **Commit**: YES
  - Message: `feat(agents): implement GitHub API wrapper (gh)`
  - Files: `github_gh_api.py`

- [x] 7. Implement repo auto-discovery

  **What to do**:
  - Create `personal-ai-space/engine/agents/github_discovery.py` with class `GitHubDiscovery`:
    - `__init__(db_manager, config_paths: list[str] = None)` — takes db_manager ref and list of paths to scan
    - `discover(paths: list[str] = None)` — scan directories for `.git` subdirectories:
      - Walk each path (max depth 5)
      - For each `.git` found, determine: remote origin URL, current branch, last commit time, tracked branch count
      - Return list of discovered repos as dicts
    - `register(repo_path: str, auto_register: bool = True)` — upsert repo into git.db `repos` table
    - `is_registered(repo_path: str)` — check if repo is in git.db
    - `get_registered_repos()` — return all registered repos from DB
    - `discover_and_register(paths: list[str])` — discover + auto-register new repos
    - `unregister(repo_path: str)` — remove repo from git.db (but don't delete it)
    - Config: default paths include the project root and user-configured paths
    - Log all via `get_logger("github-agent.discovery")`

  **Must NOT do**:
  - Don't discover outside configured paths (respect boundaries)
  - Don't delete repos from disk on unregister
  - Don't scan hidden directories (except .git itself)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: []
  - **Category reason**: Filesystem walking with .git detection, DB integration

  **Parallelization**:
  - **Can Run In Parallel**: YES — Wave 2
  - **Group**: Wave 2 (with T5, T6, T8, T9)
  - **Blocks**: T10 (sync engine needs discovered repos)
  - **Blocked By**: T3 (base agent pattern), T1 (git.db)

  **References**:
  - `personal-ai-space/engine/db_manager.py` — DB query patterns (query, execute)
  - `personal-ai-space/engine/sync_scanner.py` — Example of filesystem scanning pattern in the codebase
  - `personal-ai-space/engine/agents/github_git_ops.py` — GitOps for reading repo metadata (reference after T5)

  **Acceptance Criteria**:
  - [ ] `github_discovery.py` exists with `GitHubDiscovery` class
  - [ ] `discover()` returns repos found in test paths
  - [ ] `register()` inserts into git.db
  - [ ] `get_registered_repos()` returns registered repos

  **QA Scenarios**:
  ```
  Scenario: Discovery finds .git repos
    Tool: Bash
    Preconditions: github_discovery.py, git.db initialized
    Steps:
      1. cd personal-ai-space/engine
      2. python -c "
import sys, tempfile, os, subprocess
tmp = tempfile.mkdtemp()
subprocess.run(['git','init'], cwd=tmp, capture_output=True)
import db_manager; db_manager.init_git_db()
from agents.github_discovery import GitHubDiscovery
d = GitHubDiscovery()
repos = d.discover([tmp])
print(f'found={len(repos)} paths={[r[\"path\"] for r in repos]}')
"
    Expected Result: "found=1 paths=[...]"
    Failure Indicators: No repos found, scanning fails
    Evidence: .sisyphus/evidence/task-7-discovery.txt

  Scenario: Register and retrieve repo
    Tool: Bash
    Preconditions: Discovery works
    Steps:
      1. python -c "
import sys; sys.path.insert(0, 'personal-ai-space/engine')
import db_manager; db_manager.init_git_db()
from agents.github_discovery import GitHubDiscovery
d = GitHubDiscovery()
d.register('/tmp/test_repo')
repos = d.get_registered_repos()
print(f'registered={len(repos)}')
d.unregister('/tmp/test_repo')
repos2 = d.get_registered_repos()
print(f'after_unreg={len(repos2)}')
"
    Expected Result: "registered=1 after_unreg=0"
    Evidence: .sisyphus/evidence/task-7-register.txt
  ```

  **Commit**: YES
  - Message: `feat(agents): implement repo auto-discovery and registration`
  - Files: `github_discovery.py`

- [x] 8. Implement cross-agent communication handlers

  **What to do**:
  - In `personal-ai-space/engine/agents/github_agent.py`, add message handlers:
    - Add `subscribed_events` dict: maps event types to handler methods
    - `subscribe_to_event(event_type: str, handler)` — register interest in an event
    - `on_agent_work_completed(data: dict)` — triggered when any agent finishes work:
      - Check if the work involved file changes in any registered repo
      - If yes, log the event to sync_log table
      - If auto-sync is enabled, trigger a sync check
    - `on_task_created(data: dict)` — triggered when task-coordinator creates a task:
      - Check if task involves a registered repo
      - If yes, create a tracking branch suggestion (stub)
    - `on_habit_completed(data: dict)` — triggered by insight-generator/reminder-system
    - Register default subscriptions in `initialize()`
    - All handlers follow the communication protocol from `COMMUNICATION_PROTOCOL.md`
    - Log all cross-agent events via `get_logger("github-agent.bridge")`

  - In `personal-ai-space/engine/agents/github_agent.py`, handle incoming broadcast messages:
    - Add `cmd_subscribe(event_type)` — allow engine to subscribe agent to broadcasts
    - Add `cmd_handle_event(data)` — process a broadcast event from another agent
    - Parse `payload.command == "event"` to route to correct handler

  **Must NOT do**:
  - Don't create circular dependencies — the GitHub agent observes, doesn't control other agents
  - Don't block on cross-agent messages — handle asynchronously
  - Don't modify other agents' code to fit the GitHub agent

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: []
  - **Category reason**: Event-driven architecture, cross-agent integration

  **Parallelization**:
  - **Can Run In Parallel**: YES — Wave 2
  - **Group**: Wave 2 (with T5, T6, T7, T9)
  - **Blocks**: T11 (notification bridge)
  - **Blocked By**: T2 (command definitions), T3 (agent class)

  **References**:
  - `personal-ai-space/engine/agents/COMMUNICATION_PROTOCOL.md` — Message format, pub/sub patterns
  - `personal-ai-space/engine/engine.py:120-184` — How send() routes messages
  - `personal-ai-space/engine/agents/behavior_observer.py` — Observer pattern for agent activity tracking
  - `personal-ai-space/engine/agents/pattern_learner.py` — Another agent that listens to cross-agent events

  **Acceptance Criteria**:
  - [ ] GitHub agent has `subscribe_to_event()` method
  - [ ] `on_agent_work_completed()` handler exists and logs to sync_log
  - [ ] Agent can process incoming "event" command messages
  - [ ] Subscriptions registered on `initialize()`

  **QA Scenarios**:
  ```
  Scenario: Agent subscribes to events
    Tool: Bash
    Preconditions: github_agent.py updated with handlers
    Steps:
      1. cd personal-ai-space/engine
      2. python -c "
from agents.github_agent import GitHubAgent
a = GitHubAgent()
a.initialize()
# Simulate an agent_work_completed broadcast
msg = {
    'payload': {
        'command': 'event',
        'parameters': {
            'event_type': 'agent_work_completed',
            'data': {
                'agent_id': 'task-coordinator',
                'task_id': 'task_001',
                'action': 'task_completed',
                'repo_path': '/tmp/test_repo'
            }
        }
    }
}
result = a.handle(msg)
print(f'status={result[\"status\"]}')
"
    Expected Result: "status=success"
    Evidence: .sisyphus/evidence/task-8-cross-agent-event.txt

  Scenario: Unknown event type handled gracefully
    Tool: Bash
    Preconditions: Agent initialized
    Steps:
      1. python -c "
from agents.github_agent import GitHubAgent
a = GitHubAgent()
a.initialize()
msg = {'payload': {'command': 'event', 'parameters': {'event_type': 'unknown_event', 'data': {}}}}
result = a.handle(msg)
print(f'status={result[\"status\"]} msg={str(result.get(\"payload\",\"\"))[:50]}')
"
    Expected Result: "status=success" (graceful no-op, not error)
    Evidence: .sisyphus/evidence/task-8-unknown-event.txt
  ```

  **Commit**: YES
  - Message: `feat(agents): add cross-agent communication handlers for event routing`
  - Files: `github_agent.py`

- [x] 9. Integrate with BehaviorObserver

  **What to do**:
  - In `personal-ai-space/engine/agents/github_agent.py`:
    - Override `set_observer()` to store observer reference AND subscribe to observer notifications
    - Implement `_register_with_observer()`:
      - Register interest in observation types: `task_created`, `task_completed`, `command_executed`
      - When observer logs an observation that involves file changes/repo paths, forward to GitHub agent's event handlers
    - When `_observer.observe_task_completed()` fires for a task that has `repo_path` in its metadata:
      - Automatically trigger a sync check for that repo
      - Log to sync_log with source="observer"
    - When `_observer.observe_command_executed()` fires for git-related commands:
      - Record command in sync_log for tracking
    - All observer interactions are non-blocking — observer runs transparently
    - Log via `get_logger("github-agent.observer")`

  - In `personal-ai-space/engine/engine.py` (if needed):
    - The existing observer wiring already calls `agent.set_observer()` for all agents
    - Verify GitHub agent gets observer via super() call

  **Must NOT do**:
  - Don't modify BehaviorObserver base class (it's shared infra)
  - Don't make any part of the agent dependent on observer being present (observer may be None)
  - Passive integration only — observer informs, doesn't control

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: []
  - **Category reason**: Integration with existing observer infrastructure

  **Parallelization**:
  - **Can Run In Parallel**: YES — Wave 2
  - **Group**: Wave 2 (with T5, T6, T7, T8)
  - **Blocks**: T11 (notification bridge)
  - **Blocked By**: T3 (base agent class must exist)

  **References**:
  - `personal-ai-space/engine/agents/behavior_observer.py` — Full BehaviorObserver class with observation types
  - `personal-ai-space/engine/agents/base_agent.py:68-70` — `set_observer()` base implementation
  - `personal-ai-space/engine/engine.py:76-80` — How observer is wired to agents (`agent.set_observer(self._observer)`)
  - `personal-ai-space/engine/agents/pattern_learner.py` — Example of an agent using observer data

  **Acceptance Criteria**:
  - [ ] `GitHubAgent.set_observer()` stores observer and calls super
  - [ ] Observer notifications trigger sync checks for known repos
  - [ ] Agent works correctly when observer is None
  - [ ] No crashes when observer fires events

  **QA Scenarios**:
  ```
  Scenario: Observer is wired to GitHub agent
    Tool: Bash
    Preconditions: github_agent.py with observer integration
    Steps:
      1. cd personal-ai-space/engine
      2. python -c "
from agents.github_agent import GitHubAgent
a = GitHubAgent()
a.initialize()
# Simulate observer wiring (mock observer)
class MockObserver:
    def observe_task_created(self, task):
        pass
a.set_observer(MockObserver())
print(f'observer_set={a.observer is not None}')
"
    Expected Result: "observer_set=True"
    Evidence: .sisyphus/evidence/task-9-observer-wired.txt

  Scenario: Agent works without observer
    Tool: Bash
    Preconditions: github_agent.py
    Steps:
      1. python -c "
from agents.github_agent import GitHubAgent
a = GitHubAgent()
a.initialize()
a.set_observer(None)
result = a.handle({'payload': {'command': 'status'}})
print(f'status={result[\"status\"]}')
"
    Expected Result: "status=success" (no crash despite no observer)
    Evidence: .sisyphus/evidence/task-9-no-observer.txt
  ```

  **Commit**: YES (group with T8 or standalone)
  - Message: `feat(agents): integrate GitHub agent with BehaviorObserver`
  - Files: `github_agent.py`

- [x] 10. Implement auto-commit and sync engine

  **What to do**:
  - Create `personal-ai-space/engine/agents/github_sync.py` with class `SyncEngine`:
    - `__init__(git_ops: GitOps, discovery: GitHubDiscovery, db_manager, config: dict)`:
      - `config`: `idle_timeout` (default 120s), `sync_interval` (default 900s), `enabled` (default True)
    - `start()` — begin sync timer thread
    - `stop()` — stop timer, flush pending syncs
    - `sync_repo(repo_path: str, message: str = None)` — sync a single repo:
      - Check `has_uncommitted()`
      - If yes: stage all changes, create commit with auto-generated message
      - Message format: `"chore(sync): auto-sync [timestamp]"` with details of what changed
      - Record in sync_log with status, commit_hash, timing
      - Guardrail: if branch is main/master and `allow_main_commit` is False, create a feature branch instead
    - `sync_all_registered()` — iterate all registered repos and sync each
    - `check_idle()` — called periodically, checks if there's been activity since last sync:
      - Compare `last_activity_time` vs `last_sync_time`
      - If idle for > `idle_timeout` and has uncommitted changes → trigger sync
    - `_sync_timer_loop()` — runs in background thread:
      - Every `sync_interval` seconds, call `sync_all_registered()`
      - Between intervals, check idle detection
    - `report()` — return dict with last sync times, counts per repo, pending changes
    - All operations non-blocking (use threading)

  **Must NOT do**:
  - Never push without explicit confirmation (guardrail: `auto_push=False` by default)
  - Never commit to main/master without `allow_main_commit=True`
  - Never block agent initialization on sync
  - No force push ever (delegates to GitOps guardrail)

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: []
  - **Category reason**: Threading + git operations + state management, needs careful design

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on T5, T6, T7)
  - **Group**: Wave 3 (with T11, T12)
  - **Blocks**: T13 (unit tests need sync engine)
  - **Blocked By**: T5 (GitOps), T6 (gh API), T7 (discovery)

  **References**:
  - `personal-ai-space/engine/agents/github_git_ops.py` — GitOps for all git operations
  - `personal-ai-space/engine/agents/github_discovery.py` — Discovery for registered repos
  - `personal-ai-space/engine/agents/task_coordinator.py` — Example of timer-based operations pattern
  - Python `threading.Timer` or `threading.Thread` for non-blocking background sync

  **Acceptance Criteria**:
  - [ ] `github_sync.py` exists with `SyncEngine` class
  - [ ] `sync_repo()` creates commit for uncommitted changes in a temp repo
  - [ ] `sync_all_registered()` iterates all repos
  - [ ] `start()` and `stop()` manage background thread cleanly
  - [ ] Guardrails prevent committing to main/master by default

  **QA Scenarios**:
  ```
  Scenario: Sync commits uncommitted changes
    Tool: Bash
    Preconditions: github_sync.py, git.db, temp repo with changes
    Steps:
      1. mkdir -p /tmp/test_sync && cd /tmp/test_sync && git init && git config user.email "t@t.com" && git config user.name "T" && echo "init" > f.txt && git add f.txt && git commit -m "init"
      2. echo "new content" >> /tmp/test_sync/f.txt
      3. python -c "
import sys; sys.path.insert(0, 'personal-ai-space/engine')
from agents.github_git_ops import GitOps
from agents.github_sync import SyncEngine
import db_manager; db_manager.init_git_db()
g = GitOps('/tmp/test_sync')
s = SyncEngine(g, None, db_manager, {})
result = s.sync_repo('/tmp/test_sync', 'test auto-sync')
print(f'committed={result[\"committed\"]} hash={result.get(\"hash\",\"\")[:8]}')
"
    Expected Result: "committed=True hash=<hash>"
    Failure Indicators: No commit created, sync fails
    Evidence: .sisyphus/evidence/task-10-sync-commit.txt

  Scenario: Sync idle detection
    Tool: Bash
    Preconditions: SyncEngine
    Steps:
      1. python -c "
import sys; sys.path.insert(0, 'personal-ai-space/engine')
from agents.github_sync import SyncEngine
# Just verify config parsing and idle check work
s = SyncEngine(None, None, None, {'idle_timeout': 5, 'sync_interval': 3600})
print(f'timeout={s.idle_timeout}s interval={s.sync_interval}s')
"
    Expected Result: "timeout=5s interval=3600s"
    Evidence: .sisyphus/evidence/task-10-sync-config.txt
  ```

  **Commit**: YES
  - Message: `feat(agents): implement auto-commit and sync engine with idle detection`
  - Files: `github_sync.py`

- [x] 11. Implement engine notification bridge and guardrails

  **What to do**:
  - In `personal-ai-space/engine/engine.py`:
    - Create `_notify_github_agent(agent_id: str, action: str, data: dict)`:
      - Called after every successful `send()` to any agent
      - If the action involves task changes, file modifications, or new content:
        - Forward to github-agent as a `event` message with `event_type: "agent_work_completed"`
        - Include: agent_id, action, timestamp, and any repo-related info
    - Wire this into the `send()` method after logging (around line 148):
      - After `db.log_interaction(...)` and observer wiring, check if GitHub agent exists
      - If yes, fire notification (non-blocking, don't wait for response)
    - Add convenience: `notify_git_repo_change(repo_path: str, action: str)`
      - Direct method to tell GitHub agent a repo changed

  - Guardrails implementation in `github_agent.py`:
    - `_check_guardrail(operation: str, params: dict)`:
      - OPERATION_REGISTERED_REPO: verify repo is in git.db before operating
      - OPERATION_FORCE_PUSH: refuse force push on main/master
      - OPERATION_AUTO_PUSH: refuse if `auto_push` config is False
    - Add `guardrail_violation` event logging to sync_log with details

  **Must NOT do**:
  - Don't make engine.send() synchronous with GitHub agent — fire-and-forget
  - Don't block engine operations on guardrail checks (fail fast, log, return error)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: []
  - **Category reason**: Engine integration with non-blocking notification pattern

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on T8, T9)
  - **Group**: Wave 3 (with T10, T12)
  - **Blocks**: T14 (integration tests)
  - **Blocked By**: T8 (cross-agent handlers), T9 (observer integration)

  **References**:
  - `personal-ai-space/engine/engine.py:120-184` — send() method where notification hook goes
  - `personal-ai-space/engine/engine.py:76-80` — Observer wiring pattern (analogous to notification wiring)
  - `personal-ai-space/engine/agents/github_agent.py` — Guardrail methods go here
  - `personal-ai-space/engine/db/schema_git_repos.sql` — sync_log table for guardrail events

  **Acceptance Criteria**:
  - [ ] `engine.py` has notification bridge that fires after agent interactions
  - [ ] Guardrail check prevents operations on unregistered repos
  - [ ] Guardrail check prevents force push to main
  - [ ] Guardrail violations logged to sync_log

  **QA Scenarios**:
  ```
  Scenario: Engine notifies GitHub agent after task creation
    Tool: Bash
    Preconditions: engine.py with notification bridge
    Steps:
      1. cd personal-ai-space/engine
      2. python -c "
from engine import Engine
e = Engine(log_level='ERROR')
e.start()
# Create a task via task-coordinator
result = e.send('task-coordinator', 'create_task', {'title': 'Test task for notification'})
print(f'task_created={result[\"status\"]}')
# Check if github agent was notified
gh = e._agents.get('github-agent')
print(f'github_agent_active={gh is not None and gh.state == \"ready\"}')
e.stop()
"
    Expected Result: "task_created=success github_agent_active=True"
    Evidence: .sisyphus/evidence/task-11-notification-bridge.txt

  Scenario: Guardrail blocks unregistered repo operation
    Tool: Bash
    Preconditions: github_agent.py with guardrails
    Steps:
      1. python -c "
import sys; sys.path.insert(0, 'personal-ai-space/engine')
from agents.github_agent import GitHubAgent
a = GitHubAgent()
a.initialize()
# Try to operate on an unregistered repo
msg = {'payload': {'command': 'status', 'repo_path': '/nonexistent/unregistered'}}
result = a.handle(msg)
print(f'status={result[\"status\"]}')
"
    Expected Result: "status=error" (guardrail blocks unregistered repo)
    Evidence: .sisyphus/evidence/task-11-guardrail-unregistered.txt
  ```

  **Commit**: YES
  - Message: `feat(engine): add notification bridge for GitHub agent + guardrails`
  - Files: `engine.py`, `github_agent.py`

- [x] 12. Implement configuration management and error handling

  **What to do**:
  - Create `personal-ai-space/engine/agents/github_config.py` with class `GitHubConfig`:
    - Default config values:
      - `sync_interval`: 900 (15 min)
      - `idle_timeout`: 120 (2 min)
      - `auto_sync`: True
      - `auto_push`: False
      - `allow_main_commit`: False
      - `discovery_paths`: [project_root]
      - `max_discovery_depth`: 5
      - `log_level`: "INFO"
    - Load config from: env vars > config file > defaults
    - `config_file`: `personal-ai-space/engine/config/github_agent.yaml` (create if missing)
    - `get(key)` / `set(key, value)` — get/set config values
    - `save()` — persist config
    - `validate()` — check config for invalid values
    - Config can be updated at runtime via agent command `update_config`

  - Error handling in `github_agent.py`:
    - Create comprehensive error handling in `process()`:
      - Catch `GitOperationError` → return error with details
      - Catch `GitHubAPIError` → return error with details
      - Catch `GuardrailViolation` → log violation and return error
      - Catch unexpected exceptions → log, return generic error
    - Add `error_handling` strategy: retry_with_backoff for transient failures
    - Implement retry decorator for git/gh operations that fail transiently

  **Must NOT do**:
  - Don't store secrets in config file (gh handles auth)
  - Don't make config changes require engine restart — support runtime updates

  **Recommended Agent Profile**:
  - **Category**: `unspecified-low`
  - **Skills**: []
  - **Category reason**: Configuration management with YAML + error handling patterns

  **Parallelization**:
  - **Can Run In Parallel**: YES — Wave 3
  - **Group**: Wave 3 (with T10, T11)
  - **Blocks**: T13 (tests need config)
  - **Blocked By**: T3 (base agent)

  **References**:
  - `personal-ai-space/engine/config/` — Existing config files for pattern reference
  - Python `yaml` module for YAML config
  - `personal-ai-space/engine/agents/mcp_agent.py:error_handling` — Retry pattern
  - `tenacity` or custom retry decorator for transient failures

  **Acceptance Criteria**:
  - [ ] `github_config.py` exists with `GitHubConfig` class
  - [ ] Defaults applied when no config file exists
  - [ ] Config can be read and written at runtime
  - [ ] Retry decorator works for transient failures
  - [ ] All git operations have error handling

  **QA Scenarios**:
  ```
  Scenario: Config defaults loaded correctly
    Tool: Bash
    Preconditions: github_config.py
    Steps:
      1. cd personal-ai-space/engine
      2. python -c "
from agents.github_config import GitHubConfig
cfg = GitHubConfig()
print(f'sync_interval={cfg.get(\"sync_interval\")} idle_timeout={cfg.get(\"idle_timeout\")} auto_push={cfg.get(\"auto_push\")}')
"
    Expected Result: "sync_interval=900 idle_timeout=120 auto_push=False"
    Evidence: .sisyphus/evidence/task-12-config-defaults.txt

  Scenario: Config runtime update
    Tool: Bash
    Preconditions: github_config.py
    Steps:
      1. python -c "
from agents.github_config import GitHubConfig
cfg = GitHubConfig()
cfg.set('idle_timeout', 300)
print(f'updated={cfg.get(\"idle_timeout\")}')
cfg.set('idle_timeout', 120)  # reset
"
    Expected Result: "updated=300"
    Evidence: .sisyphus/evidence/task-12-config-update.txt
  ```

  **Commit**: YES
  - Message: `feat(agents): add configuration management and error handling`
  - Files: `github_config.py`, `github_agent.py`

- [x] 13. Write unit tests for git ops and gh API

  **What to do**:
  - Create `personal-ai-space/engine/tests/test_github_git_ops.py`:
    - Test GitOps on temporary git repos (created/destroyed per test)
    - Test: `status()` on clean/modified/staged repos
    - Test: `branch_create()`, `branch_delete()`, `branch_list()`, `branch_current()`
    - Test: `add()`, `commit()`, `log()` on various states
    - Test: `has_uncommitted()` true/false
    - Test: `worktree_add()`, `worktree_list()`
    - Test: `diff()` on modified files
    - Test: Force push guardrail raises `GitOperationError`
    - Test: Error on non-existent repo path
    - Use `pytest` fixtures for temp repo setup/teardown

  - Create `personal-ai-space/engine/tests/test_github_gh_api.py`:
    - Test: `is_authenticated()` returns bool (non-crashing)
    - Test: `check_rate_limit()` returns dict with expected keys
    - Test: `repo_list_for_user()` returns list (if authenticated)
    - Mock gh CLI if needed for offline testing

  - Create `personal-ai-space/engine/tests/test_github_discovery.py`:
    - Test: `discover()` on paths with and without .git
    - Test: `register()` and `get_registered_repos()` round-trip
    - Test: `unregister()` removes from DB
    - Test: `is_registered()` true/false

  - Create `personal-ai-space/engine/tests/test_github_config.py`:
    - Test: defaults when no config file
    - Test: `get()` and `set()` round-trip
    - Test: `validate()` catches invalid values

  **Must NOT do**:
  - Don't test against real GitHub repos without authentication
  - Don't test sync engine in unit tests (covered in integration T14)
  - Don't modify actual workspace repos during testing

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []
  - **Category reason**: Standard pytest unit tests, clear patterns to follow

  **Parallelization**:
  - **Can Run In Parallel**: YES — Wave 4
  - **Group**: Wave 4 (with T14)
  - **Blocks**: F1-F4 (final verification)
  - **Blocked By**: T10 (sync), T11 (engine bridge), T12 (config)

  **References**:
  - `personal-ai-space/engine/tests/test_base_agent.py` — Test pattern and fixture style
  - `personal-ai-space/engine/agents/github_git_ops.py` — Module under test
  - `personal-ai-space/engine/agents/github_gh_api.py` — Module under test
  - `personal-ai-space/engine/agents/github_discovery.py` — Module under test
  - `personal-ai-space/engine/agents/github_config.py` — Module under test

  **Acceptance Criteria**:
  - [ ] All 4 test files exist
  - [ ] `pytest tests/test_github_git_ops.py -v` → all pass
  - [ ] `pytest tests/test_github_config.py -v` → all pass
  - [ ] `pytest tests/test_github_discovery.py -v` → all pass

  **QA Scenarios**:
  ```
  Scenario: Unit tests pass
    Tool: Bash
    Preconditions: All test files exist
    Steps:
      1. cd personal-ai-space/engine
      2. python -m pytest tests/test_github_git_ops.py tests/test_github_config.py tests/test_github_discovery.py -v --tb=short 2>&1
    Expected Result: All tests pass (or relevant skips if gh not auth'd)
    Failure Indicators: Any test failures
    Evidence: .sisyphus/evidence/task-13-unit-tests.txt
  ```

  **Commit**: YES
  - Message: `test(agents): add unit tests for git ops, gh API, discovery, and config`
  - Files: `tests/test_github_git_ops.py`, `tests/test_github_gh_api.py`, `tests/test_github_discovery.py`, `tests/test_github_config.py`

- [x] 14. Write integration tests

  **What to do**:
  - Create `personal-ai-space/engine/tests/test_github_integration.py`:
    - Test: End-to-end agent initialization via engine
      - Start Engine, verify github-agent is registered and ready
      - Send commands to github-agent via engine.send()
      - Verify response structure follows protocol
    - Test: Cross-agent notification flow
      - Create task via task-coordinator
      - Verify github-agent receives event notification
      - Check sync_log for event record
    - Test: Repo discovery + registration + status flow
      - Create temp git repo
      - Run discovery on temp directory
      - Register found repo
      - Send status command, verify response
    - Test: Sync engine with temp repos
      - Create temp repo with uncommitted changes
      - Register it
      - Trigger sync, verify commit created
    - Test: Guardrails in action
      - Try operations on unregistered repo → error
      - Try force push on main → guardrail error
    - Test: Observer integration
      - Verify agent.set_observer() doesn't crash
      - Verify observer receives observations from agent operations
    - Test: Config runtime updates
      - Change config via agent command
      - Verify new config value returned

  **Must NOT do**:
  - Don't use real GitHub credentials in tests (test with local repos)
  - Don't depend on network access
  - Don't write tests that modify actual workspace files

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: []
  - **Category reason**: Complex setup/teardown, multiple components interacting

  **Parallelization**:
  - **Can Run In Parallel**: YES — Wave 4
  - **Group**: Wave 4 (with T13)
  - **Blocks**: F1-F4 (final verification)
  - **Blocked By**: T10 (sync), T11 (notification bridge), T12 (config)

  **References**:
  - `personal-ai-space/engine/engine.py` — Full engine integration test pattern
  - `personal-ai-space/engine/agents/github_agent.py` — Agent under test
  - `personal-ai-space/engine/agents/github_sync.py` — Sync engine under test
  - `personal-ai-space/engine/agents/github_discovery.py` — Discovery under test

  **Acceptance Criteria**:
  - [ ] Integration test file exists
  - [ ] `pytest tests/test_github_integration.py -v` → all pass

  **QA Scenarios**:
  ```
  Scenario: Integration tests pass
    Tool: Bash
    Preconditions: All modules implemented
    Steps:
      1. cd personal-ai-space/engine
      2. python -m pytest tests/test_github_integration.py -v --tb=short 2>&1
    Expected Result: All integration tests pass
    Failure Indicators: Any test failures — may need to check if gh CLI is authenticated
    Evidence: .sisyphus/evidence/task-14-integration-tests.txt
  ```

  **Commit**: YES
  - Message: `test(agents): add integration tests for GitHub agent end-to-end`
  - Files: `tests/test_github_integration.py`

---

## Final Verification Wave (MANDATORY)

> 4 review agents run in PARALLEL. ALL must APPROVE. Present consolidated results to user and get explicit "okay" before completing.
>
> Do NOT auto-proceed after verification. Wait for user's explicit approval before marking work complete.

- [x] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, run command). For each "Must NOT Have": search codebase for forbidden patterns — reject with file:line if found. Check evidence files exist in `.sisyphus/evidence/`. Compare deliverables against plan.
  Key checks:
  - `agents.config.json` has github-agent entry with all fields
  - `engine.py` imports and registers GitHubAgent
  - `github_agent.py` exists and implements BaseAgent
  - `github_git_ops.py`, `github_gh_api.py`, `github_discovery.py`, `github_sync.py`, `github_config.py` exist
  - `git.db` schema has repos, branches, sync_log, worktrees tables
  - No force push code without guardrail
  - No auto-push without explicit config
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [x] F2. **Code Quality Review** — `unspecified-high`
  Run `cd personal-ai-space/engine && python -m pytest tests/test_github_*.py -v`. Review all changed files: `as any`/`# type: ignore`, empty except blocks, hardcoded paths, print statements in prod code, unused imports. Check AI slop: excessive comments, over-abstraction, generic names.
  Output: `Build [PASS/FAIL] | Tests [N pass/N fail] | Files [N clean/N issues] | VERDICT`

- [x] F3. **Real Manual QA** — `unspecified-high`
  Start from clean state. Execute EVERY QA scenario from EVERY task — follow exact steps, capture evidence. Test cross-task integration (discovery → register → status → sync). Test edge cases: empty repos, invalid paths, missing gh CLI, no network.
  Save to `.sisyphus/evidence/task-*-*.txt`.
  Output: `Scenarios [N/N pass] | Integration [N/N] | Edge Cases [N tested] | VERDICT`

- [x] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual diff (git log/diff). Verify 1:1 — everything in spec was built (no missing), nothing beyond spec was built (no creep). Check "Must NOT do" compliance. Detect cross-task contamination.
  Output: `Tasks [N/N compliant] | Contamination [CLEAN/N issues] | Unaccounted [CLEAN/N files] | VERDICT`

---

## Commit Strategy

- **T1**: `feat(db): add git.db schema for GitHub agent repo tracking` — `schema_git_repos.sql`, `db_manager.py`
- **T2**: `feat(agents): register GitHub Specialist agent in config` — `agents.config.json`
- **T3+T4**: `feat(agents): implement GitHubAgent base and wire into engine` — `github_agent.py`, `engine.py`, `__init__.py`
- **T5**: `feat(agents): implement Git CLI helper (git-ops)` — `github_git_ops.py`
- **T6**: `feat(agents): implement GitHub API wrapper (gh)` — `github_gh_api.py`
- **T7**: `feat(agents): implement repo auto-discovery` — `github_discovery.py`
- **T8**: `feat(agents): add cross-agent communication handlers` — `github_agent.py`
- **T9**: `feat(agents): integrate with BehaviorObserver` — `github_agent.py`
- **T10**: `feat(agents): implement auto-commit sync engine` — `github_sync.py`
- **T11**: `feat(engine): add notification bridge + guardrails` — `engine.py`, `github_agent.py`
- **T12**: `feat(agents): add config management and error handling` — `github_config.py`, `github_agent.py`
- **T13**: `test(agents): unit tests for git ops, gh API, discovery, config` — test files
- **T14**: `test(agents): integration tests` — `test_github_integration.py`
- **F1-F4**: Verification commits (if fixes needed)

---

## Success Criteria

### Verification Commands
```bash
cd personal-ai-space/engine

# 1. DB schema exists
sqlite3 db/git.db ".tables"  # Expected: repos, branches, sync_log, worktrees

# 2. Config entry valid
python -c "import json; c=json.load(open('agents/agents.config.json')); print([x['id'] for x in c])"  # Expected: includes 'github-agent'

# 3. Agent imports and initializes
python -c "from agents.github_agent import GitHubAgent; a=GitHubAgent(); assert a.initialize(); print('OK')"  # Expected: OK

# 4. Engine starts with GitHub agent
python -c "from engine import Engine; e=Engine(log_level='INFO'); e.start(); e.stop(); print('OK')"  # Expected: ✓ Agent: github-agent

# 5. Git operations work
python -c "
from agents.github_git_ops import GitOps
import tempfile, os, subprocess
tmp = tempfile.mkdtemp()
subprocess.run(['git','init'], cwd=tmp, capture_output=True)
g = GitOps(tmp)
print(f'branch={g.branch_current()} status={g.status()[\"branch\"]}')
"

# 6. Discovery works
python -c "
from agents.github_discovery import GitHubDiscovery
import db_manager; db_manager.init_git_db()
d = GitHubDiscovery()
repos = d.discover(['.'])
print(f'discovered={len(repos)}')
"

# 7. Tests pass
python -m pytest tests/test_github_*.py -v --tb=short
```

### Final Checklist
- [ ] `agents.config.json` has github-agent entry
- [ ] `engine.py` imports and registers `GitHubAgent`
- [ ] `github_agent.py` implements BaseAgent with all command handlers
- [ ] `github_git_ops.py` — Git CLI operations
- [ ] `github_gh_api.py` — GitHub API via gh CLI
- [ ] `github_discovery.py` — Repo auto-discovery
- [ ] `github_sync.py` — Sync engine with idle detection
- [ ] `github_config.py` — Configuration management
- [ ] `git.db` schema created on engine start
- [ ] Cross-agent communication: GitHub agent receives events
- [ ] BehaviorObserver integration: agent tracks work
- [ ] Guardrails enforced: no force push, only registered repos, no auto-push
- [ ] All unit and integration tests pass
- [ ] Evidence files in `.sisyphus/evidence/` for all QA scenarios
