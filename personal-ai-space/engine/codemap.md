# personal-ai-space/engine/

## Responsibility
Core AI engine — orchestrates 8 agents, exposes 20+ CLI commands, manages 5 SQLite databases, provides MCP memory bridge, and runs synthesis/learning loops. The central nervous system of the Personal AI Powerhouse.

## Core Files

| File | Responsibility | Key Exports |
|------|---------------|-------------|
| `engine.py` | Main orchestrator — loads agents, routes messages, runs scheduled jobs | `Engine` class |
| `cli.py` | CLI entry point — 20+ commands via Click + Rich | `cli` group (health, context, task, habit, note, memory, learning, system) |
| `db_manager.py` | SQLite connection management and query layer | `DatabaseManager` |
| `log_manager.py` | Structured logging — audit, performance, error, system logs | `LogManager` |
| `init_engine.py` | Database initialization and schema creation | `init_databases()` |
| `comprehensive_extractor.py` | Data extraction from various sources | `ComprehensiveExtractor` |
| `converters.py` | File format conversion — .txt/.pdf/.docx to .md | `convert_to_md()` |
| `llm_bridge.py` | LLM integration for inference and text generation | `LlmBridge` |
| `synthesis_loop.py` | Continuous synthesis and learning loop | `SynthesisLoop` |
| `synthesis_run.py` | One-shot synthesis execution | `run_synthesis()` |
| `propagator.py` | Data propagation across subsystems | `Propagator` |
| `sync_scanner.py` | File system sync and change detection | `SyncScanner` |
| `backup.py` | Backup and restore system | `backup_all()` |
| `start_engine.py` | Engine startup script | — |
| `stop_engine.py` | Engine graceful shutdown | — |

## CLI Architecture
```
cli.py
├── health         — System health check
├── context        — View current session context
├── task list      — List active tasks
├── habit log      — Log a habit entry
├── note add       — Add a note
├── note search    — Search knowledge base
├── memory stats   — View memory statistics
├── memory add-fact — Add memory fact
├── learning infer — Run inference
└── system *       — System commands
```

## Subdirectory Map

| Directory | Responsibility | Map |
|-----------|---------------|-----|
| `agents/` | 8 autonomous agents extending BaseAgent | [View Map](agents/codemap.md) |
| `db/` | 5 SQLite databases, schema files, migration scripts | [View Map](db/codemap.md) |
| `extractors/` | Data extraction extension point | [View Map](extractors/codemap.md) |
| `mcp_tools/` | MCP tool client abstraction layer | [View Map](mcp_tools/codemap.md) |
| `memory/` | Python-to-Node.js MCP bridge | [View Map](memory/codemap.md) |
| `tests/` | Pytest suite for engine components | [View Map](tests/codemap.md) |
| `config/` | Engine and system configuration JSON files | — |
| `logs/` | Rotating system, error, audit, and performance logs | — |
