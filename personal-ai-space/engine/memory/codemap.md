# personal-ai-space/engine/memory/

## Responsibility
Memory bridge layer — provides Python-to-Node.js communication for the MCP memory server. Translates agent memory operations (add_fact, get_fact, list_facts, add_lesson) into subprocess calls to the Node.js headless memory server.

## Files

| File | Responsibility |
|------|---------------|
| `__init__.py` | Package marker |
| `mcp_bridge.py` | Python bridge — spawns `headless.js` as subprocess for each MCP memory operation. Methods: `add_fact()`, `get_fact()`, `list_facts()`, `add_lesson()`, `sync_profile_facts()`, `get_context_snapshot()`, `get_memory_stats()` |

## Flow
1. Agent calls `mcp_bridge.add_fact(key, value, tags)`
2. Bridge serializes request as JSON, pipes to `headless.js` subprocess via stdin
3. Node.js `store.ts` processes the request against SQLite (`memory.db`)
4. Result returned via stdout as JSON
5. Bridge deserializes and returns to agent

## Integration Points
- **Consumed by**: All agents (especially Context Manager, Behavior Observer, Pattern Learner)
- **Depends on**: Node.js MCP memory server (located at `mcp-server/` — TypeScript source, `store.ts`, `consolidator.ts`, `injector.ts`)
- **Storage**: SQLite database at `mcp-server/data/memory.db`
