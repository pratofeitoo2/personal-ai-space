# Project Context MCP Server

MCP server for project context access in Personal AI Powerhouse.

## Endpoints
- `get_project_context(project_id)`
- `update_project_context(project_id, new_data)`
- `list_projects(status, limit)`

## Usage
```bash
project-context-mcp  # Start server
opencode run "Get project context for ai-powerhouse" --mcp project-context-mcp
```