# Agent Harness Implementation Plan for Personal AI Powerhouse

## Current State Analysis
- **Strengths**: Robust memory system, 8-agent architecture, MCP integration
- **Gaps**: Limited external agent access, no Obsidian bridge, no capability registry

## Phase 1: Critical MCP Endpoints (Token-Efficient)

### 1. TASK_MANAGEMENT_ENDPOINT
**Purpose**: External agent access to task system
**Methods**:
- `list_tasks(due_date=None, status=None)` → Returns task list
- `create_task(title, description, due_date=None)` → Returns task_id
- `update_task_status(task_id, new_status)` → Returns success

### 2. APPOINTMENT_ENDPOINT  
**Purpose**: Calendar integration for agents
**Methods**:
- `get_appointments(date_range)` → Returns appointment list
- `create_appointment(title, start_time, end_time)` → Returns appointment_id

### 3. PROJECT_CONTEXT_ENDPOINT
**Purpose**: Share project context with external agents
**Methods**:
- `get_project_context(project_id)` → Returns context dict
- `update_project_context(project_id, new_data)` → Returns success

## Phase 2: Obsidian Integration (Manual Implementation)

### Bridge Strategy:
1. **File Watcher**: Monitor `~/Obsidian/Vault/**/*.md`
2. **Intake Pipeline**: Route to appropriate system (tasks → tasks.db, notes → knowledge.db)
3. **Sync Protocol**: 
   - Push: Obsidian → Intake (immediate)
   - Pull: Agents query databases → Format for Obsidian

### Implementation Files:
- `obsidian_bridge.py`: Main sync logic
- `obsidian_watcher.py`: File system monitor (launchd service)
- `obsidian_formatter.py`: Markdown ↔ Database format conversion

## Phase 3: Agent Capability Registry

### Registry Structure (`agent_capabilities.json`):
```json
{
  "endpoints": {
    "TASK_MANAGEMENT": {
      "description": "Manage tasks",
      "methods": ["list_tasks", "create_task", "update_task_status"],
      "access": "read_write"
    },
    "APPOINTMENT": {
      "description": "Calendar access",
      "methods": ["get_appointments", "create_appointment"],
      "access": "read_write"
    }
  },
  "agents": {
    "hermes": {
      "capabilities": ["TASK_MANAGEMENT", "APPOINTMENT"],
      "access_level": "full"
    }
  }
}
```

## Token-Saving Implementation Strategy

1. **Use Existing Components**:
   - Leverage current MCP server structure (`opencode-mem-mcp`)
   - Extend `memory.py` with new endpoints
   - Reuse database layer (`db_manager.py`)

2. **Minimal New Code**:
   - Add 3 new Python files (< 200 lines each)
   - Modify 2 existing files (add endpoint registrations)
   - No model training required

3. **Free Model Usage**:
   - Use `mistralai/mistral-small-latest` for documentation
   - Use `openrouter/mistralai/devstral-small` for testing
   - Avoid large context windows

## Next Steps (Your Approval Required)

1. [ ] Create MCP endpoint files (3 new endpoints)
2. [ ] Implement Obsidian bridge (file watcher + formatter)
3. [ ] Build capability registry (JSON + documentation)
4. [ ] Test with Hermes agent (verify access patterns)

**Token Estimate**: < 5,000 tokens total (mostly for testing)
**Time Estimate**: 2-3 hours implementation, 1 hour testing

Would you like me to proceed with implementation?