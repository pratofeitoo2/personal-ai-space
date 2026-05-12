# Fix MCP Memory Server Instability

## TL;DR
> **Summary**: Two MCP memory servers exist — `opencode-mem-mcp` (project-scoped, broken) and `opencode-mempalace` (globally-scoped plugin, unstable). Fix both: reinstall the Python package, fix the config, remove the broken duplicate plugin.

> **Deliverables**:
> - `opencode-mem-mcp` MCP server running and responding to tools/list
> - `opencode.jsonc` updated with direct venv path (no `uv run` overhead)
> - Broken `opencode_mem` plugin entry removed from global `opencode.json`
>
> **Estimated Effort**: Quick
> **Parallel Execution**: NO — sequential fix + verify

---

## Context

### Root Causes Found
1. **opencode-mem-mcp (project-scoped)**: Python package wasn't properly installed in `.venv` → `ModuleNotFoundError` on every startup. Editable install via `.pth` file didn't work with `uv run`. Package is now built as a wheel and properly installed.
2. **opencode-mempalace (globally-scoped)**: Plugin logs show "Plugin loading" every 3-5 seconds → OpenCode restarting repeatedly. The `python3 -m mempalace.mcp_server` MCP command works when tested directly (v3.3.5 responds correctly).
3. **opencode_mem (broken global plugin)**: `~/.cache/opencode/packages/opencode_mem@latest/` is an empty directory. Listed in global `opencode.json` plugins. Already removed from plugin list.
4. **opencode.jsonc uses `uv run`**: This adds startup delay and dependency check overhead per session. Direct `.venv/bin/opencode-mem-mcp` path is faster and more reliable.

### Key Files
- `opencode.jsonc` — Project-level MCP config (MUST edit)
- `opencode.json` — Global plugin + MCP config (EDITED: removed `opencode_mem`)
- `opencode-mem.jsonc` — Global memory plugin config (already correct)

---

## TODOs

- [ ] 1. Update `opencode.jsonc` to use direct venv path

  **What to do**:
  Change the `opencode-mem-mcp` MCP server command from:
  ```
  ["uv", "run", "--directory", "/Users/paulorezende/Documents/Personal_AI_powerhouse/mcp-servers/opencode-mem-mcp", "opencode-mem-mcp"]
  ```
  to:
  ```
  ["/Users/paulorezende/Documents/Personal_AI_powerhouse/mcp-servers/opencode-mem-mcp/.venv/bin/opencode-mem-mcp"]
  ```
  This avoids uv's dependency check overhead and startup delay.

  **File to edit**: `/Users/paulorezende/Documents/Personal_AI_powerhouse/opencode.jsonc`

  **QA Scenarios**:
  ```
  Scenario: Verify config syntax
    Tool: Bash
    Steps:
      1. Read opencode.jsonc — confirm valid JSONC format
      2. Confirm direct venv path exists: ls .venv/bin/opencode-mem-mcp
    Expected: Path exists, config is valid JSON
  ```

- [ ] 2. Verify opencode-mem-mcp MCP server works end-to-end

  **What to do**:
  Test MCP initialization and tools/list with the direct venv path.

  **QA Scenarios**:
  ```
  Scenario: MCP server initialize
    Tool: Bash
    Steps:
      1. cd /Users/paulorezende/Documents/Personal_AI_powerhouse/mcp-servers/opencode-mem-mcp
      2. echo '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}},"id":1}' | timeout 10 .venv/bin/opencode-mem-mcp 2>/dev/null
    Expected: Response includes "result" with serverInfo and capabilities.tools
  ```

- [ ] 3. Verify opencode-mempalace plugin MCP works

  **What to do**:
  Test the mempalace MCP server separately.

  **QA Scenarios**:
  ```
  Scenario: mempalace MCP server initialize
    Tool: Bash
    Steps:
      1. echo '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}},"id":1}' | timeout 10 python3 -m mempalace.mcp_server 2>/dev/null
    Expected: Response includes "result" with serverInfo.name "mempalace" and version "3.3.5"
  ```

- [ ] 4. Confirm `opencode_json` global plugin fix

  **What to do**:
  Verify the broken `opencode_mem` entry was removed from global plugins.

  **QA Scenarios**:
  ```
  Scenario: Check global opencode.json
    Tool: Bash
    Steps:
      1. cat ~/.config/opencode/opencode.json | grep -i "opencode_mem\|opencode-mempalace"
    Expected: opencode_mem NOT present, opencode-mempalace IS present
  ```

