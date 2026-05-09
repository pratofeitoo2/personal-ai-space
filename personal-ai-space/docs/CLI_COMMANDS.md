# CLI Commands Reference

All commands run from `engine/` directory via:
```
python3 cli.py <command> [options]
```

---

## System

| Command | Description |
|---------|-------------|
| `health` | Show engine health, agent status, database tables |
| `digest` | Generate and display today's daily digest |
| `review` | Generate and display weekly review |
| `reminders` | Show overdue tasks, tasks due today, and upcoming |
| `context` | Display current profile, habits, needs, and MCP memory facts |

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
```
