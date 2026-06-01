# Personal AI Powerhouse — Project Fit Analysis

> **Date:** 2026-06-01  
> **Purpose:** Deep review of project structure to evaluate whether the system fits into (1) an Obsidian vault wrapper or (2) a local web app/web interface  
> **Author:** Sisyphus (AI Agent)

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Current Architecture](#2-current-architecture)
3. [Component Inventory](#3-component-inventory)
4. [Data Flow Map](#4-data-flow-map)
5. [Alternative A: Obsidian Vault Wrapper](#5-alternative-a-obsidian-vault-wrapper)
6. [Alternative B: Local Web App / Web Interface](#6-alternative-b-local-web-app--web-interface)
7. [Comparative Analysis](#7-comparative-analysis)
8. [Recommendation](#8-recommendation)
9. [Implementation Roadmap](#9-implementation-roadmap)

---

## 1. Project Overview

**Personal AI Powerhouse** is a comprehensive, self-hosted personal AI system built on macOS. It serves as a "digital twin" — a system that knows your habits, tasks, goals, relationships, calendar, job applications, and knowledge base, and proactively surfaces relevant information through automated briefings delivered via WhatsApp, macOS notifications, and Apple Reminders.

### Core Purpose
- **Automated briefings** 3x daily (morning, midday, end-of-day)
- **Task management** with priorities, dependencies, and Apple Reminders sync
- **Habit tracking** with streak analysis and at-risk alerts
- **Job application tracking** with pipeline status
- **Knowledge management** with semantic search
- **Personal profiling** with behavior observation and pattern learning
- **Multi-channel delivery** (WhatsApp, macOS notifications, Apple Reminders)

### Current State
- **78% feature complete** (11/14 planned tasks done)
- **4 SQLite databases** operational
- **8 Python agents** active
- **20+ CLI commands** functional
- **3x daily automations** running
- **4 MCP integrations** active

---

## 2. Current Architecture

### 2.1 Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Engine** | Python 3.x | Core logic, agents, databases |
| **CLI** | Click + Rich | Command-line interface (20+ commands) |
| **Databases** | SQLite (4 instances) | Persistent storage |
| **LLM** | Ollama (local) | Intent classification, text generation |
| **Memory** | MCP servers (Node.js) | Semantic search, project memory |
| **Messaging** | WhatsApp MCP | Automated briefings delivery |
| **Apple** | reminders-bridge CLI | Reminders + Calendar sync |
| **Orchestration** | OpenCode | AI coding assistant |
| **Vault** | Obsidian | Note-taking, knowledge base |
| **Automations** | YAML rules + Python | Scheduled briefings |

### 2.2 Directory Structure

```
Personal_AI_powerhouse updated/
├── personal-ai-space/          # Main application
│   ├── engine/                 # Python AI engine
│   │   ├── agents/             # 8 Python agents
│   │   ├── automations/        # Briefing system
│   │   ├── db/                 # 4 SQLite databases
│   │   │   ├── tasks/tasks.db
│   │   │   ├── self/self.db
│   │   │   ├── calendar/calendar.db
│   │   │   └── jobs/jobs.db
│   │   ├── sync/               # 11 sync scripts
│   │   ├── llm_bridge.py       # Ollama integration
│   │   ├── cli.py              # CLI entry point
│   │   └── engine.py           # Core orchestrator
│   ├── dashboard.html          # Web dashboard (existing)
│   ├── server.js               # Node.js server (existing)
│   └── dashboard_server.py     # Python server (existing)
├── obsidian/                   # Obsidian integration
│   ├── jobs/                   # Job application notes
│   └── templates/              # Note templates
├── .obsidian/                  # Obsidian config
├── .opencode/                  # OpenCode config + 32 skills
├── .mempalace/                 # MemPalace memory
├── docs/                       # Documentation
├── AGENTS.md                   # AI agent workflow rules
├── opencode.json               # MCP server config
└── mempalace.yaml              # MemPalace config
```

---

## 3. Component Inventory

### 3.1 Core Engine Components

| Component | Type | Location | Dependencies |
|-----------|------|----------|--------------|
| Engine | Python | `engine/engine.py` | All agents, db_manager |
| CLI | Python | `engine/cli.py` | Click, Rich, Engine |
| 8 Agents | Python | `engine/agents/` | BaseAgent, db_manager |
| LLM Bridge | Python | `engine/llm_bridge.py` | Ollama, requests |
| DB Manager | Python | `engine/db_manager.py` | sqlite3 (stdlib) |
| 11 Sync Scripts | Python | `engine/sync/` | Obsidian files, SQLite |
| Automation Runner | Python | `engine/automations/runner.py` | YAML rules, delivery |
| Delivery | Python | `engine/automations/delivery.py` | WhatsApp, osascript, reminders-bridge |
| Daemon | Python | `engine/orchestrator/` | Flask/HTTP |
| Dashboard | HTML+JS | `dashboard.html` | None (static) |
| Node Server | Node.js | `server.js` | Express |
| Python Server | Python | `dashboard_server.py` | Flask |

### 3.2 Databases

| Database | Tables | Size | Purpose |
|----------|--------|------|---------|
| tasks.db | 8 | ~1MB | Tasks, projects, archive, sync_state |
| self.db | 12 | ~2.9MB | Profile, habits, goals, needs, behaviors, relationships, documents, observations |
| calendar.db | 1 | ~100KB | Upcoming events |
| jobs.db | 4 | ~500KB | Companies, applications, interviews, contacts |

### 3.3 External Integrations

| Integration | Protocol | Direction | Purpose |
|-------------|----------|-----------|---------|
| Apple Reminders | CLI (`reminders-bridge`) | Bidirectional | Task sync |
| Apple Calendar | CLI (`reminders-bridge`) | Read | Event sync |
| WhatsApp | MCP server | Outbound | Briefing delivery |
| Ollama | HTTP API | Bidirectional | LLM inference |
| AIVectorMemory | MCP server | Bidirectional | Semantic search |
| MemPalace | MCP server | Bidirectional | Project memory |
| ONG Vault | MCP server | Read | Obsidian vault access |
| OpenCode | Config | Integration | AI coding assistant |

### 3.4 Automations

| Rule | Schedule | Delivery Channels |
|------|----------|-------------------|
| morning_brief | 07:00 | WhatsApp + macOS Notification + Apple Reminder |
| midday_checkpoint | 12:00 | WhatsApp + macOS Notification + Apple Reminder |
| end_of_day | 18:00 | WhatsApp + macOS Notification + Apple Reminder |
| alert_overdue_tasks | Event-driven | WhatsApp + macOS Notification + Apple Reminder |
| alert_habits_at_risk | Event-driven | WhatsApp + macOS Notification + Apple Reminder |
| alert_calendar_soon | Event-driven | WhatsApp + macOS Notification + Apple Reminder |
| alert_goal_deadlines | Event-driven | WhatsApp + macOS Notification + Apple Reminder |

---

## 4. Data Flow Map

### 4.1 Primary Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                        INPUT SOURCES                            │
├─────────────────────────────────────────────────────────────────┤
│ Obsidian .md files ──→ sync scripts ──→ SQLite databases       │
│ Apple Reminders ─────→ sync_reminders.py ──→ tasks.db          │
│ Apple Calendar ──────→ sync_calendar.py ──→ calendar.db        │
│ WhatsApp imports ────→ whatsapp_jobs_import.py ──→ jobs.db     │
│ Manual CLI ──────────→ engine.py ──→ SQLite databases          │
│ Intake pipeline ─────→ process_intake.py ──→ knowledge/        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        PROCESSING                               │
├─────────────────────────────────────────────────────────────────┤
│ Engine (engine.py)                                              │
│   ├── 8 Agents (task-coord, behavior-obs, insight-gen, etc.)  │
│   ├── LLM Bridge (Ollama) ──→ intent classification            │
│   ├── DB Manager ──→ SQLite queries                            │
│   └── Automation Runner ──→ YAML rules + schedules             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        OUTPUT / DELIVERY                        │
├─────────────────────────────────────────────────────────────────┤
│ WhatsApp messages (via MCP)                                     │
│ macOS Notifications (via osascript)                             │
│ Apple Reminders (via reminders-bridge)                          │
│ CLI output (Rich/Markdown)                                      │
│ Web dashboard (dashboard.html + server.js)                      │
│ MemPalace memory (via MCP)                                      │
│ AIVectorMemory (via MCP)                                        │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Sync Architecture (Obsidian ↔ SQLite)

```
Obsidian .md Files (source of truth for some data)
    │
    ├── sync_self.py ──────→ self.db (habits, goals, needs, profile)
    ├── sync_reminders.py ─→ tasks.db (tasks, sync_state)
    ├── sync_calendar.py ──→ calendar.db (events)
    ├── sync_jobs.py ──────→ jobs.db (applications, companies)
    ├── sync_knowledge.py ─→ knowledge.db (articles, notes)
    └── sync_scanner.py ───→ doc_links, sync_state
```

**Key Insight:** The sync is **one-way** for most data (Obsidian → SQLite). The system reads Obsidian files and writes to SQLite for fast querying. Some data (Apple Reminders) syncs **bidirectionally**.

---

## 5. Alternative A: Obsidian Vault Wrapper

### 5.1 Concept

Wrap the entire Personal AI Powerhouse into a single Obsidian vault, using Obsidian as the primary interface for all interactions — viewing data, triggering actions, and managing the system.

### 5.2 What Already Fits

| Component | Current State | Fit Level |
|-----------|--------------|-----------|
| `.obsidian/` config | Already exists at project root | ✅ Perfect |
| `obsidian/jobs/` | Job application notes with YAML frontmatter | ✅ Perfect |
| `obsidian/templates/` | Note templates for various domains | ✅ Perfect |
| `personal-ai-space/self/` | 90+ .md files (goals, habits, needs) | ✅ Perfect |
| `docs/AI Engine Command Center.md` | Obsidian note with `runsh` buttons | ✅ Perfect |
| Knowledge base (`knowledge/`) | Articles, notes, references as .md | ✅ Perfect |
| MemPalace memory | Stored in `.mempalace/` | ✅ Compatible |

### 5.3 What Partially Fits

| Component | Challenge | Workaround |
|-----------|-----------|------------|
| **SQLite databases** | 4 databases (5+ MB total) can't be stored as .md notes | Read-only dashboards via Dataview plugin, or API bridge |
| **Sync scripts** | Python scripts need to run periodically | Obsidian CustomJS plugin or periodic manual sync |
| **Automation queries** | SQL queries against SQLite | Need API wrapper or plugin to execute queries |
| **WhatsApp delivery** | Requires WhatsApp MCP server running | Not feasible within Obsidian alone |

### 5.4 What Does NOT Fit

| Component | Why It Doesn't Fit | Severity |
|-----------|-------------------|----------|
| **Background services** (daemon, launchd watcher) | Obsidian is a note-taking app, not a process manager | 🔴 Critical |
| **Python engine** (8 agents, LLM bridge) | Can't run Python processes from within Obsidian | 🔴 Critical |
| **Ollama LLM integration** | Requires local HTTP server, not Obsidian's responsibility | 🔴 Critical |
| **MCP servers** (AIVectorMemory, MemPalace, WhatsApp) | Require separate Node.js/Python processes | 🔴 Critical |
| **SQLite write operations** | Obsidian is read-only for databases; sync writes need external process | 🟡 Medium |
| **Real-time notifications** | Obsidian doesn't natively push macOS notifications | 🟡 Medium |
| **Bidirectional Reminders sync** | Requires CLI tool execution, not Obsidian's domain | 🟡 Medium |

### 5.5 Obsidian Plugins That Could Help

| Plugin | Capability | Limitation |
|--------|-----------|------------|
| **Dataview** | Query SQLite databases (read-only) | Can't write, can't run Python |
| **CustomJS** | Execute custom JavaScript | Limited to Obsidian's JS sandbox |
| **Templater** | Template-driven note creation | Can't trigger external processes |
| **QuickAdd** | Capture data into notes | Can't sync to SQLite |
| **Commander** | Add buttons to UI | Can only trigger Obsidian commands |
| **Shell Commands** | Execute shell commands | Can run sync scripts, but limited |
| **Executor** | Run arbitrary scripts | Limited security, not designed for this |

### 5.6 Verdict for Alternative A

**❌ NOT RECOMMENDED as primary interface**

The Obsidian vault wrapper approach fails because:

1. **The engine is a Python application**, not a collection of notes. The 8 agents, LLM bridge, automation runner, and daemon are runtime processes that Obsidian cannot host.

2. **SQLite databases are the source of truth**, not Obsidian files. The sync scripts write FROM Obsidian TO SQLite. Making Obsidian the primary interface would require reversing this flow or maintaining dual sources of truth.

3. **Background services are essential.** The 3x daily automations, file watchers, and daemon are core to the system's value. Obsidian is not a process manager.

4. **Plugin ecosystem is insufficient.** Even with all relevant plugins combined, you can't replicate the engine's capabilities within Obsidian's sandbox.

**However:** Obsidian remains excellent as a **data input layer** (notes, goals, habits as .md files) and as a **knowledge viewer** (via Dataview queries against the databases). The existing setup already does this well.

---

## 6. Alternative B: Local Web App / Web Interface

### 6.1 Concept

Build a local web application accessible from any device on the local network, providing a unified interface for viewing data, triggering actions, and managing the system.

### 6.2 What Already Exists

| Component | Location | Status |
|-----------|----------|--------|
| `dashboard.html` | `personal-ai-space/dashboard.html` | ✅ Exists (needs enhancement) |
| `server.js` | `personal-ai-space/server.js` | ✅ Node.js server |
| `dashboard_server.py` | `personal-ai-space/dashboard_server.py` | ✅ Python Flask server |
| `mempalace_dashboard.py` | `personal-ai-space/tools/mempalace_dashboard.py` | ✅ MemPalace dashboard |
| Daemon HTTP API | `engine/orchestrator/start_engine.py` | ✅ Already runs on port 19876 |
| CLI as API proxy | `engine/cli.py` (DaemonProxy class) | ✅ Already proxies to daemon |

### 6.3 What Fits Perfectly

| Component | How It Fits | Benefit |
|-----------|------------|---------|
| **CLI commands → REST API** | `DaemonProxy` already exists; wrap CLI commands as HTTP endpoints | 20+ commands instantly available |
| **SQLite queries → Dashboard panels** | `db_manager.py` already provides query layer | Real-time data visualization |
| **Automation status → Dashboard** | Runner already tracks state in JSON | Live automation monitoring |
| **WhatsApp delivery → Web chat** | Add WebSocket for real-time messaging | Alternative delivery channel |
| **LLM bridge → Chat interface** | Ollama already exposes HTTP API | Natural language queries from browser |
| **Sync status → Dashboard** | Sync scripts can report status | Data freshness indicators |

### 6.4 Architecture for Local Web App

```
┌─────────────────────────────────────────────────────────────────┐
│                    LOCAL WEB APP ARCHITECTURE                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│  │   Browser    │    │   Mobile    │    │   Tablet    │        │
│  │  (Desktop)   │    │   (Phone)   │    │  (iPad)     │        │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘        │
│         │                  │                  │                 │
│         └──────────────────┼──────────────────┘                │
│                            │                                    │
│                    ┌───────▼───────┐                           │
│                    │   HTTP/WS     │                           │
│                    │   (Flask/     │                           │
│                    │   FastAPI)    │                           │
│                    └───────┬───────┘                           │
│                            │                                    │
│         ┌──────────────────┼──────────────────┐                │
│         │                  │                  │                 │
│  ┌──────▼──────┐    ┌──────▼──────┐    ┌──────▼──────┐       │
│  │  Dashboard   │    │  Chat UI    │    │  Admin      │       │
│  │  (Tasks,     │    │  (NL        │    │  (Automations│       │
│  │   Habits,    │    │   queries,  │    │   Sync,     │       │
│  │   Calendar,  │    │   actions)  │    │   Health)   │       │
│  │   Jobs)      │    │             │    │             │       │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘       │
│         │                  │                  │                 │
│         └──────────────────┼──────────────────┘                │
│                            │                                    │
│                    ┌───────▼───────┐                           │
│                    │   Engine      │                           │
│                    │   (Python)    │                           │
│                    │   - Agents    │                           │
│                    │   - LLM       │                           │
│                    │   - Automations│                          │
│                    │   - Sync      │                           │
│                    └───────┬───────┘                           │
│                            │                                    │
│                    ┌───────▼───────┐                           │
│                    │   SQLite DBs  │                           │
│                    │   (4 instances)│                          │
│                    └───────────────┘                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 6.5 Key Advantages

| Advantage | Description |
|-----------|-------------|
| **Universal access** | Any device with a browser on the local network can access the system |
| **No app installation** | No need to install Obsidian, Python, or any client software |
| **Real-time updates** | WebSocket support for live dashboard updates |
| **Cross-platform** | Works on macOS, iOS, Android, Windows, Linux |
| **Existing foundation** | `dashboard.html`, `server.js`, and daemon HTTP API already exist |
| **API-first design** | `DaemonProxy` already demonstrates API proxy pattern |
| **Security** | Local network only; no external exposure needed |
| **Mobile-friendly** | Responsive design works on phones and tablets |

### 6.6 What Needs Building

| Component | Effort | Priority |
|-----------|--------|----------|
| **Enhanced dashboard** (tasks, habits, calendar, jobs panels) | Medium | High |
| **Chat interface** (NL queries via Ollama) | Medium | High |
| **Automation control panel** (start/stop, view logs) | Low | Medium |
| **Sync status panel** (last sync, data freshness) | Low | Medium |
| **Authentication** (simple local auth) | Low | Medium |
| **PWA support** (offline, home screen) | Low | Low |

### 6.7 Verdict for Alternative B

**✅ RECOMMENDED as primary interface**

The local web app approach works because:

1. **Infrastructure already exists.** The daemon HTTP API, `DaemonProxy` class, and dashboard files provide a solid foundation.

2. **Solves the core problem.** The user's stated need is "different interactions using different tools, resources and devices." A web app is the only approach that works from any device.

3. **Minimal disruption.** The engine, databases, and automations continue unchanged. Only the interface layer is added/enhanced.

4. **Composable.** Can coexist with Obsidian (data input) and CLI (power user operations).

---

## 7. Comparative Analysis

### 7.1 Feature Comparison

| Feature | Obsidian Vault | Local Web App | Winner |
|---------|---------------|---------------|--------|
| **Multi-device access** | ❌ Desktop only | ✅ Any browser | Web App |
| **Mobile access** | ❌ Limited (Obsidian mobile) | ✅ Full (responsive) | Web App |
| **Real-time data** | ⚠️ Plugin-dependent | ✅ Native WebSocket | Web App |
| **Background services** | ❌ Not possible | ✅ Native | Web App |
| **LLM integration** | ❌ Not possible | ✅ Via API | Web App |
| **Natural language queries** | ❌ Not possible | ✅ Via chat UI | Web App |
| **Automation control** | ⚠️ Shell Commands plugin | ✅ Full control | Web App |
| **Note-taking/input** | ✅ Native strength | ⚠️ Needs rich editor | Obsidian |
| **Knowledge visualization** | ✅ Dataview plugin | ✅ Custom charts | Tie |
| **Data input (goals, habits)** | ✅ .md files | ⚠️ Forms needed | Obsidian |
| **Offline access** | ✅ Full offline | ⚠️ Service worker | Obsidian |
| **Local network access** | ❌ Desktop only | ✅ Any device | Web App |

### 7.2 Effort Comparison

| Task | Obsidian Approach | Web App Approach |
|------|-------------------|------------------|
| **View tasks** | Dataview query (hours) | Dashboard panel (days) |
| **Complete a task** | CustomJS + sync script (days) | API endpoint (hours) |
| **View habits** | Dataview query (hours) | Dashboard panel (days) |
| **Log a habit** | Templater + sync (days) | API endpoint (hours) |
| **Trigger automation** | Shell Commands plugin (hours) | Dashboard button (hours) |
| **View calendar** | Dataview query (hours) | Dashboard panel (days) |
| **Natural language query** | Not feasible | Chat UI (days) |
| **Mobile access** | Obsidian mobile (limited) | Responsive web (native) |

### 7.3 Risk Comparison

| Risk | Obsidian Approach | Web App Approach |
|------|-------------------|------------------|
| **Data consistency** | 🔴 High (dual source of truth) | 🟢 Low (single SQLite source) |
| **Maintenance burden** | 🔴 High (plugin updates, compatibility) | 🟢 Low (standard web stack) |
| **Security** | 🟡 Medium (Obsidian ecosystem) | 🟢 Low (local network only) |
| **Performance** | 🟢 Low (local app) | 🟢 Low (local server) |
| **Scalability** | 🔴 High (Obsidian limitations) | 🟢 Low (standard architecture) |
| **Complexity** | 🔴 High (workarounds needed) | 🟢 Low (natural fit) |

---

## 8. Recommendation

### 8.1 Primary Recommendation: Local Web App

**Build the Personal AI Powerhouse as a local web application.**

This is the clear winner because:

1. **It solves the stated problem.** The user wants access from "different tools, resources and devices." A web app is the only approach that works universally.

2. **The foundation already exists.** The daemon HTTP API, `DaemonProxy`, and dashboard files provide 40-50% of the work already done.

3. **Minimal disruption.** The engine, databases, and automations continue unchanged. Only the interface layer is enhanced.

4. **Future-proof.** A web app can grow with the system — adding features like real-time chat, visualizations, and integrations without architectural changes.

### 8.2 Secondary Recommendation: Keep Obsidian as Data Input

**Maintain Obsidian as the primary data input layer.**

Obsidian excels at:
- Writing goals, habits, needs as .md files with YAML frontmatter
- Knowledge management and note-taking
- Quick capture and organization

The existing sync scripts already handle the Obsidian → SQLite flow. This should continue.

### 8.3 The Hybrid Approach

```
┌─────────────────────────────────────────────────────────────────┐
│                    HYBRID ARCHITECTURE                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  DATA INPUT (Obsidian)          DATA VIEW/ACTION (Web App)     │
│  ─────────────────────          ─────────────────────────────   │
│  • Goals (.md files)            • Dashboard (tasks, habits,     │
│  • Habits (.md files)             calendar, jobs)               │
│  • Needs (.md files)            • Chat UI (NL queries)          │
│  • Knowledge (articles, notes)  • Automation control            │
│  • Job applications (.md)       • Sync status                   │
│  • Templates                    • Real-time notifications       │
│                                  • Mobile access                 │
│                                                                 │
│         │                                    ▲                   │
│         │  sync_self.py                     │                   │
│         │  sync_jobs.py                     │ API               │
│         ▼                                    │                   │
│  ┌─────────────┐                    ┌─────────────┐            │
│  │   SQLite    │◄───────────────────│   Engine    │            │
│  │   Databases │                   │   (Python)  │            │
│  └─────────────┘                    └─────────────┘            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Workflow:**
1. **Input:** Write goals, habits, and notes in Obsidian
2. **Sync:** Obsidian → SQLite (automatic via sync scripts)
3. **Process:** Engine runs agents, automations, LLM queries
4. **View/Act:** Access dashboard from any device on local network
5. **Deliver:** WhatsApp, macOS notifications, Apple Reminders (unchanged)

---

## 9. Implementation Roadmap

### Phase 1: Foundation (Week 1-2)
- [ ] Enhance `server.js` or `dashboard_server.py` with REST API endpoints
- [ ] Map existing CLI commands to API endpoints (using `DaemonProxy` pattern)
- [ ] Create responsive HTML dashboard with task, habit, calendar, and job panels
- [ ] Add SQLite query endpoints for real-time data

### Phase 2: Chat Interface (Week 3)
- [ ] Build chat UI component
- [ ] Connect to Ollama via existing `llm_bridge.py`
- [ ] Add WebSocket for real-time responses
- [ ] Support natural language queries (tasks, habits, calendar, jobs)

### Phase 3: Automation Control (Week 4)
- [ ] Dashboard panel for automation status
- [ ] Start/stop controls for daemon
- [ ] View automation logs
- [ ] Manual trigger for briefings

### Phase 4: Polish (Week 5)
- [ ] Authentication (simple local auth)
- [ ] PWA support (offline, home screen icon)
- [ ] Mobile optimization
- [ ] Error handling and loading states

### Phase 5: Advanced Features (Optional)
- [ ] Real-time WhatsApp chat from browser
- [ ] Data visualization (charts for habits, job pipeline)
- [ ] Voice input (Web Speech API)
- [ ] Calendar integration (FullCalView)

---

## Appendix A: Key Files Reference

| File | Purpose | Relevance |
|------|---------|-----------|
| `engine/cli.py` | CLI with 20+ commands | API endpoint source |
| `engine/engine.py` | Core orchestrator | API wrapper target |
| `engine/db_manager.py` | SQLite query layer | Dashboard data source |
| `engine/automations/runner.py` | Automation engine | Control panel target |
| `engine/automations/delivery.py` | Multi-channel delivery | Status monitoring |
| `engine/llm_bridge.py` | Ollama integration | Chat interface backend |
| `engine/orchestrator/start_engine.py` | Daemon HTTP server | API foundation |
| `dashboard.html` | Existing web dashboard | Enhancement target |
| `server.js` | Node.js server | Enhancement target |
| `dashboard_server.py` | Python server | Alternative enhancement target |

## Appendix B: Existing Daemon API

The daemon already exposes an HTTP API on port 19876:

```
POST /engine — Execute engine method
GET  /health — Health check
```

The `DaemonProxy` class in `cli.py` demonstrates how to proxy CLI commands to the daemon. This pattern can be extended to create a full REST API.

## Appendix C: Database Query Examples

```sql
-- Tasks due today
SELECT t.title, t.due_date, t.priority, p.name AS project 
FROM tasks t LEFT JOIN projects p ON t.project_id=p.id 
WHERE t.status NOT IN ('completed','cancelled') 
ORDER BY t.due_date ASC NULLS LAST

-- Habits at risk
SELECT habit_name, current_streak, last_completed 
FROM habits WHERE status='active' 
AND (last_completed IS NULL OR last_completed < date('now','localtime','-1 day'))

-- Job application pipeline
SELECT status, COUNT(*) as count 
FROM applications GROUP BY status

-- Calendar today
SELECT event_name, event_time, duration_hours 
FROM upcoming WHERE event_date = date('now','localtime')
```

---

*This report provides a complete reference for future sessions working on the Personal AI Powerhouse project. The recommendation is clear: build a local web app as the primary interface, keep Obsidian as the data input layer, and maintain the existing engine/automations infrastructure unchanged.*
