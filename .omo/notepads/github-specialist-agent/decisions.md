## Decisions — GitHub Specialist Agent

### Auto-wiring vs External Wiring
- DECISION: Agent auto-wires helpers on initialize()
- RATIONALE: Reduces engine complexity. Agent lazily imports and wires GitOps, GitHubAPI, Discovery modules on init.
- TRADE-OFF: Slightly slower first init (negligible)

### Guardrail Strategy
- Three-layer: (1) GitOps refuses force push on main/master, (2) Agent process() checks registered repos, (3) SyncEngine refuses main/master commits
- Fresh repos (no commits) bypass guardrail automatically

### gh CLI over direct API
- DECISION: Use gh CLI subprocess rather than directly calling GitHub REST API
- RATIONALE: gh handles auth (OAuth, tokens), supports JSON output, no extra dependencies
- TRADE-OFF: Requires gh to be installed and authenticated

### Sync engine threading
- DECISION: Background daemon thread for periodic sync
- RATIONALE: Non-blocking, auto-cleaned on shutdown, simple implementation
- CAVEAT: Thread-safety — each repo sync is independent

### Config storage
- DECISION: JSON file with env var overrides
- RATIONALE: Simple, no extra dependencies, follows existing patterns
