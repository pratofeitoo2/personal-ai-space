---
created: 2026-05-06T00:48
updated: 2026-05-09T08:42
---
# Engine Architecture

## System Overview

The engine is the AI nervous system. It orchestrates agents, manages memory, coordinates flows, and learns about you.

```
┌─────────────────────────────────────────────────────────────┐
│                      COMMAND LAYER                          │
│  (User interactions: tasks, calendar, activities)           │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────────┐
│                   ORCHESTRATION LAYER                       │
│  (Agent coordination, request routing, state management)    │
└─────────────────┬───────────────────────────────────────────┘
                  │
        ┌─────────┴──────────┬──────────────┬──────────────┐
        │                    │              │              │
┌───────▼────┐  ┌───────────▼───┐  ┌──────▼──────┐  ┌────▼────────┐
│   AGENTS   │  │    MEMORY     │  │   DATA      │  │ REPORTING   │
│            │  │    SYSTEMS    │  │   FLOWS     │  │             │
└────────────┘  └───────────────┘  └─────────────┘  └─────────────┘
        │              │                  │               │
        └──────────────┼──────────────────┼───────────────┘
                       │
        ┌──────────────▼───────────────┐
        │   STORAGE LAYER              │
        │  (SQLite, File, Vector DB)   │
        └──────────────────────────────┘
```

## Core Components

### 1. Agent Layer
- **Context Manager**: Maintains conversation state, pulls self data
- **Task Coordinator**: Manages tasks, priorities, deadlines
- **Insight Generator**: Analyzes habits, generates recommendations
- **Reminder System**: Time-based and event-based triggers
- **Knowledge Indexer**: Maintains knowledge base index
- **Report Generator**: Creates summaries and analysis

### 2. Memory Systems
- **Short-term**: Current session context (in-memory)
- **Medium-term**: Weekly/monthly patterns (cache layer)
- **Long-term**: Persistent data (SQLite)
- **Vector**: Semantic search (embedding store)

### 3. Data Flows
- **Ingestion**: Convert → Capture → Normalize → Index
- **Processing**: Extract features → Analyze → Generate insights
- **Reporting**: Query → Aggregate → Visualize
- **Integration**: External systems ↔ Engine ↔ User

### 4. Storage
- **memories.db**: All indexed interactions
- **self.db**: Your profile, habits, traits, needs
- **tasks.db**: Task tracking, completions, patterns
- **knowledge.db**: Articles, notes, cross-references

### 5. Logging
- **system.log**: Engine operations, agent calls
- **errors.log**: Failures, exceptions, issues
- **audit.log**: Data modifications, access patterns
- **performance.log**: Timing, resource usage

## Data Flow Architecture

### Capture Flow
```
User Input → Inbox → Normalize → Classify → Route → Relevant System
```

### Processing Flow
```
Raw Data → Extract Features → Aggregate → Analyze → Generate Insights
```

### Reporting Flow
```
Query System → Fetch Data → Transform → Visualize → Output
```

### Integration Flow
```
External System → Transform → Upsert to DB → Sync to Self
```

## Agent Communication Protocol

**Message Format:**
```json
{
  "id": "uuid",
  "timestamp": "2026-05-06T00:30:00Z",
  "sender": "agent_name",
  "recipient": ["agent1", "agent2"],
  "action": "request|response|broadcast",
  "payload": {},
  "context": {
    "user_id": "self",
    "session_id": "session_uuid",
    "priority": "high|normal|low"
  }
}
```

## System States

```
IDLE → ACTIVE → PROCESSING → REPORTING → IDLE
  ↑       ↓           ↓           ↓
  └───────ERROR ← ────────────────┘
```

## Integration Points

- **Google Calendar**: Two-way sync
- **Gmail**: Inbox monitoring
- **Todoist/Notion**: Task sync
- **GitHub**: Project tracking
- **Fitness Apps**: Health data
- **Financial Systems**: Spending tracking

