# Task Management MCP Server

This MCP server provides external agent access to the Personal AI Powerhouse task management system.

## Endpoints

### list_tasks(due_date=None, status=None, limit=20)
List tasks with optional filtering.

### create_task(title, description="", due_date=None, project_id=None)
Create a new task.

### update_task_status(task_id, new_status)
Update task status.

### get_task_details(task_id)
Get detailed task information.

## Usage

```bash
# Start the server
task-management-mcp

# Test with OpenCode
opencode run 'List my tasks for today' --mcp task-management-mcp
```

## Integration

Add to `opencode.jsonc`:
```json
{
  "mcp": {
    "task-management-mcp": {
      "type": "local",
      "command": ["task-management-mcp"],
      "enabled": true
    }
  }
}
```