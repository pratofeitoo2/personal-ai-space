# personal-ai-space/engine/mcp_tools/

## Responsibility
MCP (Model Context Protocol) tool abstraction layer — provides client base classes, tool registry, and bridge configuration for connecting Python engine to MCP-compatible servers and tools.

## Files

| File | Responsibility |
|------|---------------|
| `__init__.py` | Package marker |
| `base_client.py` | Base client class for MCP tool connections — handles transport, request/response lifecycle, error handling |
| `registry.json` | Tool registry — maps tool names to server endpoints and parameter schemas |
| `claude_bridges_config.json` | Claude-specific bridge configuration — tool enablement, model routing, capability declarations |

## Design
- `BaseClient` provides transport abstraction (stdio/SSE) for MCP communication
- Registry pattern: tools are declared in `registry.json` with their schemas and routed to appropriate backends
- Claude bridge config defines which tools are exposed to Claude models in the OpenCode context

## Integration Points
- **Consumed by**: Agents that need MCP tool access (e.g., GitHub agent, MCP agent)
- **Depends on**: MCP protocol servers (stdio-based subprocess or network)
