# Repository Atlas: Personal AI Powerhouse

## Project Responsibility
Personal AI augmentation system — a persistent cognitive layer that observes, remembers, and assists across OpenCode sessions. Comprises a Python engine (agent orchestration, memory pipelines, CLI), MCP servers (OpenCode plugin memory, entire lifecycle hooks), auto-intake pipeline, and self-modeling digital twin. Runs on macOS.

## System Entry Points

| Path                              | Role                                                                                                      |
|-----------------------------------|-----------------------------------------------------------------------------------------------------------|
| `opencode.jsonc`                  | OpenCode MCP config — registers `opencode-mem-mcp` and `aivectormemory` servers                           |
| `.opencode/plugins/entire.ts`     | Entire CLI lifecycle plugin — fires `turn-start`/`turn-end`/`session-end` hooks into the entire toolchain |
| `.opencode/opencode.json`         | OpenCode MCP config (workspace-local copy of opencode.jsonc MCP entries)                                  |
| `.github/workflows/engine-ci.yml` | CI pipeline — Python 3.13, ruff lint, pytest, trufflehog secrets scan                                     |
| `BMO/Profiles/BMO.md`             | Obsidian BMO chat plugin profile (styling, model params)                                                  |
| `mempalace_dashboard.py`          | MemPalace knowledge graph dashboard script                                                                |
| `mempalace.yaml`                  | MemPalace configuration file                                                                              |
| `.sisyphus/`                      | Sisyphus workflow runtime state directory (transient)                                                     |

## Directory Map

| Directory                              | Responsibility                                                                              | Detailed Map                                               |
|----------------------------------------|---------------------------------------------------------------------------------------------|------------------------------------------------------------|
| `personal-ai-space/`                   | AI augmentation system root — engine, agents, memory, self-model, intake pipeline           | [View Map](personal-ai-space/codemap.md)                   |
| `personal-ai-space/engine/`            | Core orchestrator, CLI, agent system, databases, memory bridge, and modular transport layer | [View Map](personal-ai-space/engine/codemap.md)            |
| `personal-ai-space/engine/agents/`     | 8 autonomous agents (BaseAgent pattern)                                                     | [View Map](personal-ai-space/engine/agents/codemap.md)     |
| `personal-ai-space/engine/db/`         | 5 SQLite databases with schema definitions and migration scripts                            | [View Map](personal-ai-space/engine/db/codemap.md)         |
| `personal-ai-space/engine/extractors/` | Data extraction extension point                                                             | [View Map](personal-ai-space/engine/extractors/codemap.md) |
| `personal-ai-space/engine/mcp_tools/`  | MCP tool abstraction and client base                                                        | [View Map](personal-ai-space/engine/mcp_tools/codemap.md)  |
| `personal-ai-space/engine/memory/`     | Python-to-Node.js MCP memory bridge                                                         | [View Map](personal-ai-space/engine/memory/codemap.md)     |
| `personal-ai-space/engine/tests/`      | Pytest suite for engine components                                                          | [View Map](personal-ai-space/engine/tests/codemap.md)      |
| `personal-ai-space/intake/`            | Zero-touch file import pipeline (macOS launchd)                                             | [View Map](personal-ai-space/intake/codemap.md)            |
| `personal-ai-space/self/`              | Digital twin — profile, goals, habits, relationships, traits                                | [View Map](personal-ai-space/self/codemap.md)              |
| `TaskNotes/`                           | Task note view templates                                                                    | [View Map](TaskNotes/codemap.md)                           |
