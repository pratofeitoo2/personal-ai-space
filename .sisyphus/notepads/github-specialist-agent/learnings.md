## Learnings — GitHub Specialist Agent

### Architecture Decisions
- Agent auto-wires helpers on initialize() via _auto_wire_helpers() — no need for external wiring
- GitOps uses subprocess.run() with shell=False for all git operations
- gh CLI wrapper (_gh) parses JSON output from `gh --json` commands
- GitHubDiscovery uses recursive directory walk (max_depth=5) for repo discovery
- SyncEngine runs a background thread with periodic + idle-detection sync
- Guardrails enforced at multiple layers: GitOps (force push), agent process() (registered repo check), SyncEngine (main/master commit)

### Edge Cases Handled
- Fresh repos with no commits: branch_current() falls back to symbolic-ref, log() returns empty gracefully
- Empty repos: status() returns clean, commit() works on first commit
- New/untracked files: diff() only shows modified tracked files
- Symlinked paths (/var → /private/var): Path.resolve() handles consistently
- Force push guardrail: raises GitOperationError on main/master unless allow_force=True

### File Structure
```
engine/agents/
  github_agent.py        — Main agent class (command routing + auto-wiring)
  github_git_ops.py      — Git CLI operations (GitOps class)
  github_gh_api.py       — GitHub API via gh CLI (GitHubAPI class)
  github_discovery.py    — Repo discovery + registration (GitHubDiscovery)
  github_sync.py         — Background sync engine (SyncEngine)
  github_config.py       — Configuration management (GitHubConfig)
engine/db/
  schema_git_repos.sql   — git.db schema (repos, branches, sync_log, worktrees)
engine/tests/
  test_github_git_ops.py     — 15 tests
  test_github_gh_api.py      — (tested via agent commands)
  test_github_discovery.py   — 7 tests
  test_github_config.py      — 7 tests
```
