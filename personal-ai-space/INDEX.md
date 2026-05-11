---
created: 2026-05-06T02:55
updated: 2026-05-09T09:01
---
# Personal AI Space — Complete Directory Index

**Generated:** 2026-05-09  
**Location:** `/Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space`  
**Purpose:** Comprehensive mapping of all folders, subfolders, and files in the personal AI system

---

## 📊 Directory Structure

```
personal-ai-space/
├── command/                          # Control center
│   ├── activities/disciplined_routines.json
│   ├── calendar/upcoming.csv
│   ├── finances/                     # 18 files (CVs, cover letters, profiles)
│   ├── inbox/                        # 30+ timestamped daily notes
│   └── tasks/active_tasks.json
│
├── db/                               # Operational databases
│   └── agent_memory.db               # MCP memory store (SQLite)
│
├── docs/                             # Documentation
│   ├── reports/                      # System reports (3 files)
│   ├── setup/                        # Automation setup guide + script
│   ├── workflows/                    # Intake workflow docs
│   ├── ARCHITECTURE.md
│   ├── CLI_COMMANDS.md               # ← NEW: CLI command reference
│   ├── COMPLETE_OVERVIEW.md
│   ├── DATA_FLOWS.md
│   ├── INTEGRATIONS.md
│   ├── LEARNING_LAYER.md
│   ├── LOGGING.md
│   ├── MEMORY_SYSTEMS.md
│   ├── OPERATIONAL_HANDBOOK.md
│   ├── ORCHESTRATION.md
│   ├── QUALITY_ASSURANCE.md
│   ├── README.md
│   ├── REPORTING.md
│   ├── SETUP_GUIDE.md
│   ├── architecture-map.canvas      # ← NEW: Obsidian canvas diagram
│   └── architecture-map.md          # ← NEW: Mermaid architecture diagram
│
├── engine/                           # AI brain
│   ├── agents/                       # 8 Python agents + config
│   │   ├── base_agent.py
│   │   ├── behavior_observer.py
│   │   ├── context_manager.py
│   │   ├── insight_generator.py
│   │   ├── knowledge_indexer.py
│   │   ├── pattern_learner.py
│   │   ├── reminder_system.py
│   │   ├── report_generator.py
│   │   ├── task_coordinator.py
│   │   ├── AGENT_TEMPLATES.md
│   │   ├── COMMUNICATION_PROTOCOL.md
│   │   └── agents.config.json
│   ├── config/
│   │   ├── engine.config.json
│   │   └── system.config.json
│   ├── db/                           # Engine SQLite databases
│   │   ├── knowledge.db
│   │   ├── memories.db
│   │   ├── self.db
│   │   ├── tasks.db
│   │   └── schema_*.sql             # 4 schema definition files
│   ├── extractors/__init__.py
│   ├── logs/                         # 4 log files (rotated)
│   ├── memory/
│   │   ├── __init__.py
│   │   ├── mcp_bridge.py            # Python → Node subprocess bridge
│   │   └── mcp-server/              # Node.js MCP memory server
│   │       ├── src/                  # 9 TypeScript source files
│   │       │   ├── bootstrap.ts
│   │       │   ├── cli.ts
│   │       │   ├── consolidator.ts
│   │       │   ├── demo-cli.ts
│   │       │   ├── index.ts
│   │       │   ├── injector.ts
│   │       │   ├── nlp-interface.ts
│   │       │   ├── playground.ts
│   │       │   └── store.ts
│   │       ├── tests/                # 5 test files
│   │       ├── examples/
│   │       ├── headless.js           # Headless JSON CLI
│   │       ├── package.json
│   │       ├── tsconfig.json
│   │       ├── jest.config.js
│   │       └── data/memory.db
│   ├── cli.py                        # CLI entry point (20+ commands)
│   ├── comprehensive_extractor.py
│   ├── db_manager.py
│   ├── engine.py                     # Main orchestrator
│   ├── init_engine.py
│   ├── log_manager.py
│   └── requirements.txt
│
├── intake/                           # Auto-processing pipeline
│   ├── watcher.py                    # macOS launchd file watcher
│   ├── process_intake.py             # File router + extractor
│   ├── processed/                    # Archive of processed files
│   ├── intake.log                    # Import audit trail
│   ├── watcher.log                   # Watcher daemon log
│   └── README.md
│
├── knowledge/                        # Library
│   ├── articles/
│   ├── notes/
│   ├── projects/
│   ├── references/
│   └── INDEX.md
│
├── self/                             # Digital twin
│   ├── profile.json                  # Master personal profile
│   ├── goals/                        # 90+ career, study, and life planning files
│   ├── habits/tracking.csv
│   ├── needs/current_needs.json
│   ├── traits/inferred_personality.json
│   ├── behaviors/
│   ├── insights/
│   └── relationships/               # People network (6 files)
│
├── vault/                            # 🔒 Secrets (git-ignored)
│
├── .gitignore
└── INDEX.md                          # This file
```

---

## 📂 Directory Descriptions

### 🎯 `command/` — Central Management Hub
**Purpose:** Daily operations — tasks, calendar, finances, and inbox captures  
**Git Status:** Tracked  
**Contents:**
- **activities/** — Disciplined routines and habit tracking
- **calendar/** — Upcoming events and schedule
- **finances/** — 18 professional files (CVs in EN/PT, cover letters, profiles)
- **inbox/** — 30+ timestamped daily notes and quick captures
- **tasks/** — Active task list (`active_tasks.json`)

**Key Files:**
| File | Purpose |
|------|---------|
| `tasks/active_tasks.json` | Current task list managed by task-coordinator agent |
| `activities/disciplined_routines.json` | Habit definitions tracked by insight-generator |
| `calendar/upcoming.csv` | Events and schedule data |
| `finances/overview.json` | Financial/profile overview |

---

### 💾 `db/` — Primary Database
**Purpose:** MCP agent memory store  
**Git Status:** Tracked  
**Contents:**
- `agent_memory.db` — MCP persistent memory (semantic facts, lessons, events)
- Written to by `mcp_bridge.py` → `store.ts` via subprocess calls

---

### 📖 `docs/` — System Documentation
**Purpose:** Complete system documentation, guides, and operational handbooks  
**Git Status:** Tracked

**Architecture & Reference:**
| File | Description |
|------|-------------|
| `README.md` | Quick start overview |
| `ARCHITECTURE.md` | Engine layers, agents, data flows, system states |
| `COMPLETE_OVERVIEW.md` | Full 600-line system blueprint |
| `CLI_COMMANDS.md` | All 20+ CLI commands with options |
| `architecture-map.canvas` | Interactive Obsidian canvas architecture map |
| `architecture-map.md` | Mermaid diagram architecture map |

**Guides & Handbooks:**
| File | Description |
|------|-------------|
| `SETUP_GUIDE.md` | Installation and first run |
| `OPERATIONAL_HANDBOOK.md` | Daily operations, backup, troubleshooting |
| `MEMORY_SYSTEMS.md` | 3-tier memory architecture |
| `DATA_FLOWS.md` | How data moves through the system |

**Specialized Reference:**
| File | Description |
|------|-------------|
| `INTEGRATIONS.md` | External service connections (Google, Todoist, GitHub) |
| `REPORTING.md` | Report templates and schedules |
| `LOGGING.md` | Log structure and retention |
| `QUALITY_ASSURANCE.md` | Data integrity and validation |
| `ORCHESTRATION.md` | Agent coordination patterns |
| `LEARNING_LAYER.md` | Observation and pattern inference |

**Subdirectories:**
- **reports/** — System reports: extraction, import, build summary
- **setup/** — Automation setup guide + shell script
- **workflows/** — Intake workflow documentation

---

### 🤖 `engine/` — AI Engine Core
**Purpose:** Orchestrator, agents, memory systems, databases, and CLI  
**Git Status:** Tracked

#### **agents/** — Autonomous Agents
8 Python agents extending `BaseAgent`:

| Agent | File | Responsibility |
|-------|------|----------------|
| **Context Manager** | `context_manager.py` | Profile loading, session state, MCP memory bridge |
| **Task Coordinator** | `task_coordinator.py` | Task CRUD, priorities, deadlines, dependencies |
| **Insight Generator** | `insight_generator.py` | Habit analysis, patterns, anomaly detection |
| **Reminder System** | `reminder_system.py` | Time-based and event-based reminders |
| **Knowledge Indexer** | `knowledge_indexer.py` | Index, search, deduplicate knowledge base |
| **Report Generator** | `report_generator.py` | Daily digest, weekly review, monthly analysis |
| **Behavior Observer** | `behavior_observer.py` | Logs user actions (task creation, completion, habits) |
| **Pattern Learner** | `pattern_learner.py` | Infers time patterns, preferences, workflows |

Supporting files: `agents.config.json`, `AGENT_TEMPLATES.md`, `COMMUNICATION_PROTOCOL.md`

#### **config/** — Configuration
| File | Purpose |
|------|---------|
| `system.config.json` | Full engine config (agents, memory tiers, logging, integrations) |
| `engine.config.json` | Engine version, mode, update cycles |

#### **db/** — Engine Databases
5 SQLite databases initialized on startup:
- `memories.db` — Agent interactions and context (3 tables)
- `self.db` — Profile, habits, traits, needs (9 tables)
- `tasks.db` — Tasks, projects, calendar (5 tables)
- `knowledge.db` — Articles, notes, references (6 tables)
- Schema SQL files for each database

#### **memory/** — Memory Systems
**Bridge Layer:**
- `mcp_bridge.py` — Python ↔ Node.js bridge; spawns `headless.js` subprocess for each MCP operation. Provides `add_fact`, `get_fact`, `list_facts`, `add_lesson`, `sync_profile_facts`, `get_context_snapshot`

**MCP Server** (`mcp-server/`) — Node.js/TypeScript persistent memory:
| Source File | Purpose |
|-------------|---------|
| `store.ts` | SQLite CRUD — semantic facts, lessons, audit events (WAL mode) |
| `consolidator.ts` | LLM-based knowledge extraction + Jaccard dedup |
| `injector.ts` | Context injection into agent prompts |
| `nlp-interface.ts` | Intent-based routing and tool call extraction |
| `cli.ts` | Interactive REPL for memory operations |
| `bootstrap.ts` | MCP server lifecycle and session management |
| `index.ts` | Entry point with lifecycle hooks |
| `demo-cli.ts` | Demonstration CLI with sample data |
| `playground.ts` | Testing and demonstration harness |

Supporting: `headless.js` (non-interactive JSON interface), `package.json`, `tsconfig.json`, `jest.config.js`, 5 test files, examples directory

#### **Core Files:**
| File | Purpose |
|------|---------|
| `engine.py` | Main orchestrator — loads 6+ agents, routes messages, runs scheduled jobs |
| `cli.py` | CLI entry point — 20+ commands via click + rich |
| `db_manager.py` | SQLite connection management and query layer |
| `log_manager.py` | Structured logging with audit and performance tracking |
| `init_engine.py` | Database initialization and schema creation |
| `comprehensive_extractor.py` | Data extraction system |
| `requirements.txt` | Python dependencies |

#### **logs/** — System Logging
| File | Retention |
|------|-----------|
| `system.log` | Engine operations, agent calls (rotated) |
| `errors.log` | Failures, exceptions |
| `audit.log` | Data modifications, access patterns |
| `performance.log` | Timing, resource usage |

---

### 📥 `intake/` — Data Staging & Auto-Processing
**Purpose:** Zero-touch file import pipeline  
**Git Status:** Tracked  
**Automation:** macOS `launchd` service (`com.personalai.intake-watcher`) — runs 24/7

**Components:**
| File | Role |
|------|------|
| `watcher.py` | Monitors staging/ every 10s, 60s debounce, triggers processor |
| `process_intake.py` | Routes files by filename/frontmatter to correct destinations |
| `intake.log` | Import audit trail |
| `watcher.log` | Watcher daemon log |
| `processed/` | Archive of imported files by category |

**Routing rules:** Filename keywords ("Daily Notes" → inbox, "PF"/"financial" → finances, etc.) and frontmatter tags (article, project)

---

### 📚 `knowledge/` — Knowledge Base
**Purpose:** Personal library and research repository  
**Git Status:** Tracked  
**Contents:**
- `articles/` — Saved research articles
- `notes/` — Personal notes and ideas
- `projects/` — Active research projects
- `references/` — Important links and references
- `INDEX.md` — Knowledge curation index

---

### 👤 `self/` — Digital Twin
**Purpose:** Your evolving digital profile — what the system knows about you  
**Git Status:** Tracked

| Path | Contents |
|------|----------|
| `profile.json` | Master profile (name, timezone, work style, goals, constraints) |
| `goals/` | 90+ career, study, and life planning files (markdown, PDFs) |
| `habits/tracking.csv` | Habit tracking data |
| `needs/current_needs.json` | Active needs and priorities |
| `traits/inferred_personality.json` | Inferred personality patterns |
| `behaviors/` | Behavior analysis data |
| `insights/` | AI-generated learning and insights |
| `relationships/` | People network (6 relationship files + People.base) |

---

### 🔐 `vault/` — Data Vault (Sensitive)
**Purpose:** Secure storage for credentials and personal documents  
**Git Status:** Git-ignored (`.gitignore`)

---

## 📊 Statistics

| Category | Count | Status |
|----------|-------|--------|
| Python scripts | 15+ | Functional |
| TypeScript source files | 10+ | Compiled |
| Agent implementations | 8 | Active |
| SQLite databases | 6 | Operational |
| Documentation files | 18+ | Current |
| CLI commands | 20+ | Functional |
| Log files | 4 | Rotating |
| MCP server tests | 5 | Passing |

---

## 🔄 Data Flow

```
User → CLI (cli.py) → Engine (engine.py) → Agents
                                              │
                    ┌─────────────────────────┤
                    │           │             │
                    ▼           ▼              ▼
              context      task-coord      insight-gen
              manager     knowledge-index  reminder-sys
              report-gen  behavior-obs   pattern-learner
                    │           │             │
                    └───────────┼─────────────┘
                                ▼
                          Memory Layer
                    ┌──────────┼──────────┐
                    ▼          ▼          ▼
              mcp_bridge.py  SQLite DBs  Logs
                    │
                    ▼
              mcp-server (Node.js)
              store.ts → consolidator.ts → injector.ts
```

---

## 🔗 Quick Navigation

| Action | Command / Path |
|--------|----------------|
| Start engine | `python3 cli.py <command>` |
| Check health | `python3 cli.py health` |
| View context | `python3 cli.py context` |
| List tasks | `python3 cli.py task list` |
| Log habit | `python3 cli.py habit log "Exercise"` |
| Add note | `python3 cli.py note add "Title"` |
| Search knowledge | `python3 cli.py note search <query>` |
| View memory stats | `python3 cli.py memory stats` |
| Add memory fact | `python3 cli.py memory add-fact key value` |
| Run inference | `python3 cli.py learning infer` |
| Import files | Copy to `intake/staging/` (auto-processed) |
| Architecture map | Open `docs/architecture-map.canvas` in Obsidian |

---

**Last Updated:** 2026-05-09  
**System Status:** ✅ Operational  
**Python:** 3.x | **Node.js:** 22+ | **OS:** macOS
