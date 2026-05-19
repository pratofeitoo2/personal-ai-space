# personal-ai-space/

## Responsibility
Root of the Personal AI Space system — holds all AI augmentation subsystems: engine, agents, memory, data intake, self-modeling, documentation, and personal data vault. Acts as the single source of truth for the user's digital twin and knowledge base.

## Directory Structure

| Directory | Responsibility | Map |
|-----------|---------------|-----|
| `command/` | Control center — tasks (`active_tasks.json`), activities (`engine/db/activities/activities.db`), calendar (`engine/db/calendar/calendar.db`), finances (CVs, cover letters), inbox (30+ daily notes) | — |
| `engine/` | AI engine core — orchestrator, CLI, agents, databases, memory bridge | [View Map](engine/codemap.md) |
| `intake/` | Auto-processing file import pipeline — watcher + processor + routing | [View Map](intake/codemap.md) |
| `knowledge/` | Personal library — articles (research), notes, projects, references | — |
| `self/` | Digital twin — profile.json, goals, habits, traits, relationships | [View Map](self/codemap.md) |
| `docs/` | System documentation — architecture, data flows, integrations, operations | — |
| `vault/` | Secrets and personal documents (git-ignored) | — |

## Data Flow
1. **Intake**: Files dropped in `intake/staging/` → `watcher.py` triggers `process_intake.py` → routes to `command/`, `knowledge/`, or `self/`
2. **Engine**: `cli.py` → `engine.py` → 8 agents (context, tasks, insights, reminders, knowledge, reports, behavior, patterns) → memory layer
3. **Memory**: Agents write facts via `mcp_bridge.py` → Node.js MCP server (`store.ts`) → SQLite persistence
4. **Self**: Profile and behavioral data flow from agents → `self/` JSON files ←→ `db/self.db` schema

## Integration Points
- **OpenCode**: MCP servers configured in `opencode.jsonc` — `opencode-mem-mcp` for persistent memory
- **macOS launchd**: Intake watcher runs as a system service (`com.personalai.intake-watcher`)
- **GitHub Actions**: CI via `.github/workflows/engine-ci.yml`
