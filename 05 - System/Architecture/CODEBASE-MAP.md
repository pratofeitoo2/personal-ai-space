# Codebase Map — Personal AI Powerhouse

> Generated: 2026-06-12 | Branch: `small-version` | After cleanup: 283MB disk, ~600 tracked files

---

## 1. System Landscape

### Mermaid Diagram
```mermaid
flowchart TB
    subgraph User["👤 User Layer"]
        CLI["cli.py<br/>Click + Rich CLI"]
        WEB["web/<br/>Flask Web API"]
        OBS["Obsidian Vault<br/>Notes + Tasks + Habits"]
    end

    subgraph Engine["🧠 Personal AI Engine"]
        ENGINE["engine.py<br/>Core Orchestrator"]
        SCHEDULER["scheduler.py<br/>Cron-like Scheduler"]

        subgraph Agents["Agent Network"]
            TC["TaskCoordinator"]
            IG["InsightGenerator"]
            RS["ReminderSystem"]
            RG["ReportGenerator"]
            KI["KnowledgeIndexer"]
            BO["BehaviorObserver"]
            PL["PatternLearner"]
            MCP["MCPAgent"]
            GH["GitHubAgent"]
        end

        subgraph Extractors["Data Extractors"]
            CE["ComprehensiveExtractor"]
            SE["SessionExtractor"]
            BV["BehaviorVocab"]
        end

        subgraph Sync["Sync Layer"]
            SR["sync_reminders.py"]
            SH["sync_habits.py"]
            SK["sync_knowledge.py"]
            SJ["sync_jobs.py"]
            SC["sync_calendar.py"]
        end

        subgraph Transport["Transport Layer"]
            EB["EventBus"]
            DH["DataHub"]
            MT["MCPTransport"]
            REG["Registry"]
        end
    end

    subgraph Storage["💾 Storage"]
        DB["SQLite Databases<br/>(tasks, memories, knowledge,<br/>calendar, activities, jobs, git)"]
        MEM["Memory Bridge<br/>(MemPalace + AIVectorMemory)"]
        MCP_SERVER["MCP Servers<br/>(vault-bridge, mempalace,<br/>whatsapp-mcp, tablepro)"]
    end

    subgraph External["🌍 External Services"]
        LLM["LLM APIs<br/>(OpenAI, Anthropic, etc.)"]
        GH_API["GitHub API"]
        WHATSAPP["WhatsApp<br/>(via MCP)"]
        APPLE["Apple Apps<br/>(via bridges)"]
    end

    CLI --> ENGINE
    WEB --> ENGINE
    OBS -->|"obsidian-sync"| SYNC

    ENGINE --> SCHEDULER
    ENGINE --> Agents
    ENGINE --> Extractors
    ENGINE --> Transport

    Agents --> DB
    Agents --> MEM
    Agents --> LLM
    GH --> GH_API
    MCP --> MCP_SERVER

    Transport --> EB
    Transport --> DH
    Transport --> MT

    Sync --> DB
    Sync --> OBS

    MCP_SERVER --> WHATSAPP
    MCP_SERVER --> APPLE
```

### ASCII Fallback
```text
┌─────────────────────────────────────────────────────────────────────┐
│                        USER LAYER                                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐                     │
│  │  cli.py  │  │  web/    │  │  Obsidian    │                     │
│  │ (Click)  │  │ (Flask)  │  │  Vault       │                     │
│  └────┬─────┘  └────┬─────┘  └──────┬───────┘                     │
│       │              │               │                              │
├───────┼──────────────┼───────────────┼──────────────────────────────┤
│       ▼              ▼               ▼                              │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              PERSONAL AI ENGINE                              │   │
│  │  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐   │   │
│  │  │  engine.py  │  │  scheduler   │  │  Extractors      │   │   │
│  │  │ (Core)      │  │  (Cron)      │  │  (Session,       │   │   │
│  │  │             │  │              │  │   Comprehensive)  │   │   │
│  │  └──────┬──────┘  └──────────────┘  └──────────────────┘   │   │
│  │         │                                                   │   │
│  │  ┌──────┴──────────────────────────────────────────────┐    │   │
│  │  │              AGENT NETWORK                           │    │   │
│  │  │  TaskCoord │ Insight  │ Reminder │ Report │ Know    │    │   │
│  │  │  Behavior  │ Pattern  │ MCP      │ GitHub │ ...     │    │   │
│  │  └─────────────────────────────────────────────────────┘    │   │
│  │         │                                                   │   │
│  │  ┌──────┴──────────────────────────────────────────────┐    │   │
│  │  │              TRANSPORT LAYER                         │    │   │
│  │  │  EventBus ←→ DataHub ←→ MCPTransport ←→ Registry   │    │   │
│  │  └─────────────────────────────────────────────────────┘    │   │
│  └─────────────────────────────────────────────────────────────┘   │
│       │              │               │                              │
├───────┼──────────────┼───────────────┼──────────────────────────────┤
│       ▼              ▼               ▼                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ SQLite   │  │ Memory   │  │ MCP Servers  │  │  External    │  │
│  │ DBs      │  │ Bridge   │  │ (vault, mp,  │  │  (LLM, GH,  │  │
│  │ (7 DBs)  │  │          │  │  whatsapp)   │  │   WhatsApp)  │  │
│  └──────────┘  └──────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Engine Architecture

### Mermaid Diagram
```mermaid
flowchart LR
    subgraph Entry["Entry Points"]
        ENGINE["engine.py<br/>Core Orchestrator"]
        CLI["cli.py<br/>Command Line"]
        WEB["web/api/<br/>Flask Routes"]
        INIT["init_engine.py<br/>Bootstrap"]
    end

    subgraph Agents["Agents (brain/agents/)"]
        BASE["base_agent.py"]
        TC["task_coordinator"]
        IG["insight_generator"]
        RS["reminder_system"]
        RG["report_generator"]
        KI["knowledge_indexer"]
        BO["behavior_observer"]
        PL["pattern_learner"]
        MCP_A["mcp_agent"]
        GH_A["github_agent"]
        CTX["context_manager"]
    end

    subgraph Extractors["Extractors (brain/extractors/)"]
        CE["comprehensive_extractor"]
        SE["session_extractor"]
        BV["behavior_vocab"]
        SC["session_storage"]
        CONV["converters"]
    end

    subgraph Sync["Sync (brain/sync/)"]
        SR["sync_reminders"]
        SH["sync_habits"]
        SK["sync_knowledge"]
        SJ["sync_jobs"]
        SCAL["sync_calendar"]
        SSELF["sync_self"]
        SSRC["sync_scanner"]
        ABS["absorb_command_data"]
        WA["whatsapp_jobs_import"]
    end

    subgraph Transport["Transport (brain/transport/)"]
        EB["event_bus"]
        DH["data_hub"]
        MT["mcp_transport"]
        REG["registry"]
        CFG["config"]
        T["types"]
    end

    subgraph Synthesis["Synthesis (brain/synthesis/)"]
        SL["synthesis_loop"]
        SR2["synthesis_run"]
        PROP["propagator"]
    end

    subgraph Analytics["Analytics (brain/analytics/)"]
        BA["behavior_analytics"]
        TI["trait_inference"]
    end

    subgraph Memory["Memory (brain/memory/)"]
        MB["mcp_bridge"]
        FB["fallback_bridge"]
    end

    subgraph Storage["Storage (brain/db/)"]
        DM["db_manager.py"]
        ID["id_helpers.py"]
        DBS["activities/ calendar/ git/ jobs/<br/>knowledge/ memories/ self/ tasks/"]
    end

    Entry --> Agents
    Agents --> Extractors
    Agents --> Transport
    Agents --> Synthesis
    Agents --> Analytics
    Agents --> Memory
    Agents --> Storage

    Extractors --> Storage
    Sync --> Storage
    Sync --> Agents
    Transport --> Agents
    Synthesis --> Transport
```

### ASCII Fallback
```text
ENTRY POINTS                    AGENTS
┌──────────────┐               ┌─────────────────────────────┐
│ engine.py    │──────────────▶│ base_agent.py               │
│ cli.py       │               │ task_coordinator             │
│ web/api/     │               │ insight_generator            │
│ init_engine  │               │ reminder_system              │
└──────────────┘               │ report_generator             │
                               │ knowledge_indexer            │
                               │ behavior_observer            │
                               │ pattern_learner              │
                               │ mcp_agent                    │
                               │ github_agent                 │
                               │ context_manager              │
                               └──────────┬──────────────────┘
                                          │
          ┌───────────────┬───────────────┼───────────────┬──────────────┐
          ▼               ▼               ▼               ▼              ▼
   ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌──────────┐ ┌──────────┐
   │ EXTRACTORS  │ │    SYNC     │ │  TRANSPORT  │ │SYNTHESIS │ │ MEMORY   │
   │ session     │ │ reminders   │ │ event_bus   │ │ loop     │ │ mcp      │
   │ comprehensive│ │ habits     │ │ data_hub    │ │ run      │ │ bridge   │
   │ behavior    │ │ knowledge   │ │ mcp_transp  │ │ propa-   │ │ fallback │
   │ converters  │ │ jobs        │ │ registry    │ │ gator    │ │ bridge   │
   └──────┬──────┘ │ calendar    │ │ config      │ └────┬─────┘ └────┬─────┘
          │        │ self        │ │ types       │      │            │
          │        │ scanner     │ └──────┬──────┘      │            │
          │        │ whatsapp    │        │             │            │
          │        └──────┬──────┘        │             │            │
          │               │               │             │            │
          ▼               ▼               ▼             ▼            ▼
   ┌─────────────────────────────────────────────────────────────────────┐
   │                        STORAGE (SQLite)                             │
   │  db_manager.py │ id_helpers.py                                      │
   │  ┌─────────┬─────────┬─────────┬─────────┬─────────┬─────────┐    │
   │  │activities│calendar │  git    │  jobs   │knowledge│memories │    │
   │  ├─────────┼─────────┼─────────┼─────────┼─────────┼─────────┤    │
   │  │  self   │  tasks  │         │         │         │         │    │
   │  └─────────┴─────────┴─────────┴─────────┴─────────┴─────────┘    │
   └─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Data Flow

### Mermaid Diagram
```mermaid
sequenceDiagram
    autonumber
    participant U as User
    participant CLI as cli.py
    participant E as Engine
    participant EXT as Extractors
    participant SYNC as Sync Layer
    participant DB as SQLite DBs
    participant MEM as Memory Bridge
    participant LLM as LLM APIs
    participant OBS as Obsidian

    U->>CLI: `python cli.py chat "I finished task X"`
    CLI->>E: engine.process(message)
    E->>EXT: ComprehensiveExtractor.extract()
    EXT->>EXT: Parse intent, entities, sentiment
    EXT->>DB: Store extracted data (tasks, memories)
    EXT->>E: Return ExtractionResult

    E->>E: Route to agents
    E->>MEM: Recall relevant context
    MEM->>DB: Query memories/knowledge
    DB-->>MEM: Return context
    MEM-->>E: Context loaded

    E->>LLM: Generate response (with context)
    LLM-->>E: Response generated

    E->>DB: Update tasks, log activity
    E-->>CLI: Return response
    CLI-->>U: Display response

    Note over SYNC,OBS: Background sync cycle
    SYNC->>OBS: Read notes, tasks, habits
    OBS-->>SYNC: Vault data
    SYNC->>DB: Upsert into engine DBs
    SYNC->>E: Emit sync events
```

### ASCII Fallback
```text
 User          CLI          Engine       Extractors      DB        Memory       LLM        Obsidian
  │             │             │             │             │          │           │            │
  │──"chat"────▶│──process───▶│             │             │          │           │            │
  │             │             │──extract───▶│             │          │           │            │
  │             │             │             │──store─────▶│          │           │            │
  │             │             │◀─result─────│             │          │           │            │
  │             │             │             │             │          │           │            │
  │             │             │──recall─────────────────▶│          │           │            │
  │             │             │◀─context─────────────────│          │           │            │
  │             │             │             │             │          │           │            │
  │             │             │──generate──────────────────────────────────────▶│            │
  │             │             │◀─response──────────────────────────────────────│            │
  │             │             │             │             │          │           │            │
  │             │◀─response───│──update────▶│             │          │           │            │
  │◀─display───│             │             │             │          │           │            │
  │             │             │             │             │          │           │            │
  │             │             │             │     BACKGROUND SYNC              │            │
  │             │             │             │             │          │           │            │
  │             │             │             │             │◀──read──────────────────────────│
  │             │             │             │             │──upsert────────────────────────▶│
```

---

## 4. Agent Network

### Mermaid Diagram
```mermaid
flowchart TB
    subgraph Core["Core Agents"]
        TC["TaskCoordinator<br/>Creates/manages tasks"]
        IG["InsightGenerator<br/>Generates insights from data"]
        RS["ReminderSystem<br/>Handles reminders"]
        RG["ReportGenerator<br/>Generates reports"]
    end

    subgraph Intelligence["Intelligence Agents"]
        KI["KnowledgeIndexer<br/>Indexes knowledge base"]
        BO["BehaviorObserver<br/>Observes user behavior"]
        PL["PatternLearner<br/>Learns patterns from data"]
        CTX["ContextManager<br/>Manages context window"]
    end

    subgraph Integration["Integration Agents"]
        MCP_A["MCPAgent<br/>MCP server integration"]
        GH_A["GitHubAgent<br/>GitHub sync & API"]
    end

    subgraph Observers["Observer Agents"]
        RPT["ReportGenerator<br/>Daily/weekly reports"]
        INS["InsightGenerator<br/>Behavioral insights"]
    end

    ENGINE["engine.py<br/>Orchestrator"]

    ENGINE --> Core
    ENGINE --> Intelligence
    ENGINE --> Integration
    ENGINE --> Observers

    TC -->|"creates tasks"| DB[(SQLite)]
    IG -->|"stores insights"| DB
    RS -->|"manages reminders"| DB
    KI -->|"indexes knowledge"| DB
    BO -->|"tracks behavior"| DB
    PL -->|"learns patterns"| DB

    GH_A -->|"syncs repos"| GH[GitHub API]
    MCP_A -->|"routes calls"| MCP[MCP Servers]

    CTX -->|"provides context"| ENGINE
```

---

## 5. Module Dependency Graph

### Mermaid Diagram
```mermaid
flowchart LR
    subgraph Core["Core"]
        ENGINE["engine.py"]
        CLI["cli.py"]
        DB_MGR["db_manager.py"]
        ID["id_helpers.py"]
        LLM["llm_bridge.py"]
    end

    subgraph Agents["Agents"]
        BASE["base_agent.py"]
        TC["task_coordinator"]
        IG["insight_generator"]
        RS["reminder_system"]
        KI["knowledge_indexer"]
        BO["behavior_observer"]
        PL["pattern_learner"]
        GH["github_agent"]
        MCP["mcp_agent"]
    end

    subgraph Transport["Transport"]
        EB["event_bus"]
        DH["data_hub"]
        MT["mcp_transport"]
        REG["registry"]
    end

    subgraph Extractors["Extractors"]
        CE["comprehensive_extractor"]
        SE["session_extractor"]
        BV["behavior_vocab"]
    end

    subgraph Sync["Sync"]
        SR["sync_reminders"]
        SH["sync_habits"]
        SK["sync_knowledge"]
    end

    subgraph Synthesis["Synthesis"]
        SL["synthesis_loop"]
        PROP["propagator"]
    end

    %% Core dependencies
    ENGINE --> TC
    ENGINE --> IG
    ENGINE --> RS
    ENGINE --> KI
    ENGINE --> BO
    ENGINE --> PL
    ENGINE --> GH
    ENGINE --> MCP
    ENGINE --> EB
    ENGINE --> DH

    CLI --> ENGINE

    %% Agent dependencies
    BASE --> DB_MGR
    BASE --> EB
    TC --> DB_MGR
    TC --> ID
    IG --> DB_MGR
    IG --> LLM
    RS --> DB_MGR
    KI --> DB_MGR
    BO --> DB_MGR
    PL --> DB_MGR
    PL --> LLM
    GH --> DB_MGR
    MCP --> MT

    %% Transport dependencies
    EB --> DH
    DH --> REG
    MT --> REG

    %% Extractor dependencies
    CE --> DB_MGR
    CE --> BV
    SE --> DB_MGR

    %% Sync dependencies
    SR --> DB_MGR
    SH --> DB_MGR
    SK --> DB_MGR

    %% Synthesis dependencies
    SL --> EB
    SL --> LLM
    PROP --> EB
```

---

## 6. Database Schema Overview

### Mermaid Diagram
```mermaid
erDiagram
    TASKS {
        string id PK
        string title
        string description
        string project_id FK
        string priority
        string status
        string created_at
        string due_date
        float estimated_hours
        float actual_hours
        string assigned_to
        string tags
        string recurrence
        string category
    }

    MEMORIES {
        string id PK
        string content
        string tags
        string scope
        float importance
        string created_at
    }

    KNOWLEDGE {
        string id PK
        string title
        string content
        string source
        string tags
        string created_at
    }

    ACTIVITIES {
        string id PK
        string type
        string content
        string metadata
        string timestamp
    }

    CALENDAR {
        string id PK
        string title
        string date
        string time
        string type
        string metadata
    }

    JOBS {
        string id PK
        string company
        string position
        string status
        string applied_at
        string metadata
    }

    GIT {
        string id PK
        string repo
        string branch
        string commit
        string message
        string timestamp
    }

    TASKS ||--o{ PROJECTS : "belongs to"
    MEMORIES ||--o{ TAGS : "has"
    KNOWLEDGE ||--o{ TAGS : "has"
    ACTIVITIES ||--o{ USERS : "performed by"
```

---

## 7. File Size Breakdown (Post-Cleanup)

```mermaid
pie title Disk Usage by Directory
    "opencode/node_modules" : 57
    "obsidian/plugins/univer" : 47
    "obsidian/plugins (enabled)" : 5
    "personal-ai-space/engine" : 15
    "personal-ai-space/command" : 1
    "personal-ai-space/web" : 0.2
    "opencode/skills" : 10
    "Other configs" : 2
```

| Directory | Size | Purpose |
|-----------|------|---------|
| `.opencode/node_modules/` | 57 MB | OpenCode plugin dependencies |
| `.obsidian/plugins/univer/` | 47 MB | Spreadsheet editor (disable if unused) |
| `.obsidian/plugins/` (9 enabled) | ~5 MB | Active Obsidian plugins |
| `.obsidian/themes/` | ~200 KB | Alien (active) + Obsidianite |
| `personal-ai-space/engine/` | ~15 MB | Core engine Python code |
| `personal-ai-space/command/` | ~1 MB | 86 command files |
| `personal-ai-space/web/` | ~200 KB | Flask web API |
| `02 - Self/` | ~100 KB | Profile, traits, goals |
| `personal-ai-space/docs/` | ~1 MB | Architecture docs |
| `.opencode/skills/` | ~10 MB | 30 skill directories |
| `.opencode/command/` | ~56 KB | 7 slash commands |
| `.opencode/agent/` | ~20 KB | Agent definitions |
| Root configs | ~50 KB | AGENTS.md, opencode.json, etc. |

**Total: ~283 MB** (down from 1.1 GB)

---

## 8. Quick Reference

### Entry Points
| File | Purpose | Usage |
|------|---------|-------|
| `personal-ai-space/engine/engine.py` | Core orchestrator | `python engine.py` |
| `personal-ai-space/engine/cli.py` | CLI interface | `python cli.py [command]` |
| `personal-ai-space/web/api/` | Flask web API | `python -m flask run` |
| `personal-ai-space/engine/init_engine.py` | Bootstrap | First-time setup |

### Key Config Files
| File | Purpose |
|------|---------|
| `opencode.json` | MCP server configuration |
| `AGENTS.md` | Agent workflow rules |
| `.gitignore` | Git exclusions |
| `.env` | Secrets (gitignored) |
| `.obsidian/community-plugins.json` | Enabled Obsidian plugins |

### Database Locations
| Database | Path | Purpose |
|----------|------|---------|
| tasks.db | `engine/db/tasks/` | Task management |
| memories.db | `engine/db/memories/` | Memory storage |
| knowledge.db | `engine/db/knowledge/` | Knowledge base |
| calendar.db | `engine/db/calendar/` | Calendar events |
| activities.db | `engine/db/activities/` | Activity log |
| jobs.db | `engine/db/jobs/` | Job tracking |
| git.db | `engine/db/git/` | Git integration |
| self.db | `engine/db/self/` | Self/profile data |
