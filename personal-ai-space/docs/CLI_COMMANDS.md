---
created: 2026-05-09T08:13
updated: 2026-05-10T14:00
---
# CLI Commands Reference

All commands run from `engine/` directory via:
```
python3 cli.py <command> [options]
```

---

## System

| Command     | Description                                                  |
|-------------|--------------------------------------------------------------|
| `health`    | Show engine health, agent status, database tables            |
| `digest`    | Generate and display today's daily digest                    |
| `review`    | Generate and display weekly review                           |
| `sync`      | Manually sync .md frontmatter with database                  |
| `reminders` | Show overdue tasks, tasks due today, and upcoming            |
| `context`   | Display current profile, habits, needs, and MCP memory facts |
| `serve`     | Run engine as persistent HTTP server (foreground)            |

---

## Tasks

| Command | Description |
|---------|-------------|
| `task list` | List today's tasks. Use `--all` to show all open tasks |
| `task add <title>` | Add a new task. Options: `--priority`, `--due`, `--hours`, `--desc` |
| `task done <task_id>` | Mark a task as completed |
| `task summary` | Show task completion summary (JSON) |

### task add options

| Flag | Description |
|------|-------------|
| `-p, --priority` | critical, high, normal (default), low |
| `-d, --due` | Due date in YYYY-MM-DD format |
| `-h, --hours` | Estimated hours (float) |
| `-D, --desc` | Task description |

---

## Habits

| Command | Description |
|---------|-------------|
| `habit log <name>` | Log a habit completion. Options: `--duration`, `--notes` |
| `habit insights` | Show habit patterns, streaks, and recommendations. Option: `--days` (default 7) |

---

## Knowledge Base (Notes)

| Command | Description |
|---------|-------------|
| `note add <title>` | Add a note. Options: `--content`, `--tags`, `--category` |
| `note search <query>` | Search the knowledge base |
| `note stats` | Show knowledge base statistics (JSON) |

---

## MCP Memory (Persistent Agent Memory)

| Command | Description |
|---------|-------------|
| `memory stats` | Show MCP memory statistics (semantic facts, lessons, events) |
| `memory facts` | List semantic facts. Option: `--prefix` to filter by key prefix |
| `memory add-fact <key> <value>` | Store a semantic fact. Options: `--confidence`, `--category` |
| `memory add-lesson <text>` | Store a lesson learned. Options: `--negative` (mark as "avoid"), `--category` |
| `memory lessons` | List stored lessons. Options: `--category`, `--negative` |
| `memory sync-profile` | Re-sync user profile into MCP memory |

---

## Learning (Observation & Pattern Inference)

| Command | Description |
|---------|-------------|
| `learning buffer` | Show current observation buffer stats |
| `learning observations` | Show recent observations. Option: `--limit` |
| `learning infer` | Run pattern inference on accumulated observations |
| `learning workflow` | Show inferred workflow recommendation |

---

## MCP Tools (External Service Integration)

| Command | Description |
|---------|-------------|
| `mcp status` | Show configured MCP servers and connection status |
| `mcp tools` | List all available tools from connected servers |
| `mcp call <server> <tool>` | Call a tool on an MCP server. Option: `--args` (JSON) |
| `mcp discover` | Re-discover tools from all enabled servers |

### LLM-powered tool routing

`nl` now auto-routes to MCP tools when it detects you want to use an external service. The LLM (with `model_hint="tool_routing"`, preferring the 3B tier) selects the right tool and extracts parameters from natural language:

```
nl "send an email to Maria saying I'm running late"
  → IntentClassifier → mcp-agent.mcp_route
  → TextGenerator(model_hint="tool_routing") selects tool + params
  → MCPAgent routes to the mail-mcp server via JSON-RPC
  → Result returned to you
```

```
nl "check my Gmail inbox"
  → IntentClassifier → mcp-agent.mcp_route
  → TextGenerator picks tools/list_inbox or similar
```

### Model-per-task routing

The `TextGenerator` now automatically selects the best model for each task type:

| Task                         | Model hint     | Preferred model | When                       |
|------------------------------|----------------|-----------------|----------------------------|
| Phrasing (habit insights)    | `phrasing`     | smollm2:1.7b    | 1.7B tier, 8K context      |
| Tool routing (MCP selection) | `tool_routing` | smollm2:1.7b    | 1.7B tier (see note below) |
| Writing (digest opener)      | `writing`      | smollm2:1.7b    | 1.7B tier (see note below) |

> **M1 8GB memory note:** `llama3.2:3b` has a default 128K context window, which
> creates a 13GB+ KV cache on Apple Silicon. All Ollama calls are capped at
> `num_ctx=8192` (set via `OLLAMA_NUM_CTX` in `llm_bridge.py`). Smaller 1.7B
> models like `smollm2:1.7b` have 8K context by default and use ~1GB loaded.

Defined in `MODEL_HINTS` in `llm_bridge.py`. Falls back gracefully if the preferred model isn't installed.

### Supported transports

- **stdio** — spawns subprocess, communicates via JSON-RPC 2.0 with Content-Length framing
- **http** — POST JSON-RPC to a remote endpoint (e.g. whatsapp-mcp daemon)

Server configurations live in `engine/mcp_tools/registry.json`. Enable a server by setting `"enabled": true`.

```bash
python3 cli.py mcp status
python3 cli.py mcp tools
python3 cli.py mcp discover
python3 cli.py mcp call mail send_email --args '{"to": "maria@...", "subject": "Hi"}'
```

---

## Natural Language (LLM Bridge)

| Command               | Description                                                  |
|-----------------------|--------------------------------------------------------------|
| `nl <text>`           | Free-text query — routes to the right agent automatically    |
| `nl <text> --enhance` | Same, with LLM-generated narrative on top of structured data |
| `llm status`          | Check Ollama availability and list pulled models             |
| `llm classify <text>` | Test intent classification accuracy without executing        |

### How `nl` works

1. **IntentClassifier** embeds your text via `nomic-embed-text` (Ollama) and finds the best-matching agent command by cosine similarity
2. The matched agent command executes normally (rule-based, ~50ms)
3. With `--enhance`, a `TextGenerator` (e.g. `llama3.2:3b`) rephrases the structured response into natural language

**Zero persistent RAM** — both the embedding and text models stay in Ollama's process, not in Python. The text model loads on first `--enhance` call and stays warm for the session.

**Graceful degradation** — if Ollama is not running, the classifier falls back to fuzzy keyword matching. All existing CLI commands continue to work as before.

```bash
# Natural language queries
python3 cli.py nl "what should I do today"
python3 cli.py nl "how are my habits" --enhance
python3 cli.py nl "add a task to review the budget"
python3 cli.py nl "what's overdue"

# LLM diagnostics
python3 cli.py llm status
python3 cli.py llm classify "find something about sexology"
```

---

## Daemon (Background Engine)

| Command | Description |
|---------|-------------|
| `daemon status` | Show whether the engine daemon is running and health |
| `daemon start` | Start the engine daemon in background |
| `daemon stop` | Stop the engine daemon |

```bash
python3 cli.py daemon status
python3 cli.py daemon start
python3 cli.py daemon stop
```

---

## Quick Reference

```bash
# System overview
python3 cli.py health
python3 cli.py context

# Daily operations
python3 cli.py reminders
python3 cli.py task list
python3 cli.py task add "Learn TypeScript" -p high -d 2026-05-15 -h 3
python3 cli.py habit log "Exercise" -d 30
python3 cli.py note add "React patterns" -c "Notes about hooks" -t react,frontend

# Reports
python3 cli.py digest
python3 cli.py review
python3 cli.py habit insights
python3 cli.py habit insights --days 30

# Memory & Learning
python3 cli.py memory add-fact user.language Portuguese --confidence 0.95
python3 cli.py memory add-lesson "Always back up before updates" --negative
python3 cli.py learning observations --limit 20
python3 cli.py learning infer

# Natural language (LLM bridge)
python3 cli.py nl "what's on my plate today" --enhance
python3 cli.py nl "how are my habits this week"

# MCP tools
python3 cli.py mcp status
python3 cli.py mcp tools
python3 cli.py mcp discover

# Sync & serve
python3 cli.py sync
python3 cli.py serve

# LLM-powered MCP tool routing
python3 cli.py nl "send an email to Maria saying I'm running late"
python3 cli.py nl "check my Gmail inbox"
python3 cli.py nl "look up John's contact"
```
