# Orchestration Layer

## Engine Orchestrator

The orchestrator coordinates all agents and manages system state.

```
Orchestrator
    ├─ Agent Lifecycle Manager
    ├─ Request Router
    ├─ State Manager
    ├─ Error Handler
    ├─ Resource Manager
    └─ Scheduler
```

---

## Request Lifecycle

### 1. User Request Arrives

```
User: "What's my priority for today?"
    ↓
Parse request
    ↓
Determine intent: "get_daily_priorities"
    ↓
Route to appropriate agent
```

### 2. Context Loading

```
Orchestrator → Context Manager
  "Load user context"
    ↓
Context Manager queries:
  - self.db: profile, needs, traits
  - memories.db: recent interactions
  - tasks.db: today's tasks
    ↓
Return: User context packet
```

### 3. Processing

```
With context, route to Task Coordinator
  "Get today's priorities"
    ↓
Task Coordinator queries:
  - tasks.db: tasks due today
  - Calculate priority scores
  - Consider user traits/preferences
    ↓
Return: Prioritized task list
```

### 4. Enrichment

```
Optional: Route to Insight Generator
  "Any blockers or anomalies?"
    ↓
Insight Generator:
  - Check for habit blockers
  - Detect anomalies
  - Generate recommendations
    ↓
Return: Enriched response
```

### 5. Response

```
Compile final response
  ├─ Task list
  ├─ Insights
  └─ Recommendations
    ↓
Format for user (markdown/JSON)
    ↓
Log interaction
    ↓
Return to user
```

---

## Scheduled Operations

### Every 5 Minutes
```
Check for immediate reminders
Check for task deadline warnings
Sync cache → long-term
```

### Every 30 Minutes
```
Sync external integrations:
  - Google Calendar
  - Gmail
Pull new items
Detect changes
Update engine
```

### Hourly
```
Agent health checks
Database integrity check
Memory cleanup
Performance metrics collection
```

### Daily (08:00)
```
1. Daily analysis
2. Generate daily digest
3. Extract insights from previous day
4. Prepare daily priorities
5. Report generation
```

### Weekly (Friday 18:00)
```
1. Weekly analysis
2. Review complete week
3. Identify patterns
4. Generate weekly report
5. Plan next week
```

### Monthly (1st Monday 09:00)
```
1. Monthly analysis
2. Trend analysis
3. Goal progress review
4. Generate monthly report
5. Archive old data
```

---

## State Management

### Engine States

```
IDLE
  ↓ [request arrives]
PROCESSING
  ↓ [agents working]
  ├─ Agent A: 40% complete
  ├─ Agent B: 100% complete
  ├─ Agent C: 70% complete
  ↓ [all complete]
READY
  ↓ [user receives response]
IDLE
```

### Agent States

```
RUNNING     - Actively processing
IDLE        - Waiting for work
DEGRADED    - Working with fallbacks
ERROR       - Failed, needs recovery
RESTARTING  - Recovering from error
```

### Recovery from Error

```
ERROR detected
  ↓
Log error details
  ↓
Attempt auto-recovery:
  1. Restart agent (retry 1)
  2. Clear cache, retry (retry 2)
  3. Use fallback handler (retry 3)
  ↓
If recovered: Resume normal
If failed: Report to user, halt
```

---

## Load Balancing

### Agent Priorities

```
Priority: Critical
  - Context Manager
  - Task Coordinator
  - Reminder System

Priority: High
  - Insight Generator
  - Report Generator

Priority: Low
  - Knowledge Indexer
  - Async tasks
```

### Resource Allocation

```
Request arrives
  ↓
Classify by priority
  ↓
Check available resources
  ├─ CPU quota: 80% available
  ├─ Memory quota: 60% available
  ├─ DB connections: 4/10 available
  ↓
Route to appropriate agents
  ↓
Monitor execution
  ↓
Throttle if approaching limits
```

---

## Performance Monitoring

### Real-time Metrics

```json
{
  "timestamp": "2026-05-06T08:15:33Z",
  "system": {
    "cpu_percent": 35,
    "memory_mb": 345,
    "disk_percent": 42
  },
  "agents": {
    "context-manager": {
      "status": "running",
      "tasks": 1,
      "avg_duration_ms": 145,
      "errors": 0
    },
    "task-coordinator": {
      "status": "idle",
      "tasks": 0,
      "avg_duration_ms": 89,
      "errors": 0
    }
  },
  "databases": {
    "query_count": 234,
    "slow_queries": 2,
    "avg_query_ms": 45
  },
  "requests": {
    "pending": 3,
    "processing": 2,
    "completed_today": 847
  }
}
```

### Alerts

```
IF cpu_percent > 80:
  → Log warning
  → Consider deferring non-critical tasks

IF query_time > 1000ms:
  → Log slow query
  → Recommend index

IF error_rate > 5% per hour:
  → Alert user
  → Investigate failure pattern
```

---

## Dashboard & Observability

### System Dashboard

```
╔═══════════════════════════════════════════╗
║          ENGINE STATUS DASHBOARD          ║
╠═══════════════════════════════════════════╣
║ Status: ✓ HEALTHY                         ║
║                                           ║
║ Agents: 6/6 running                       ║
║ Requests: 847 today | 3 pending           ║
║ Errors: 0 critical | 2 warnings           ║
║                                           ║
║ System:                                   ║
║   CPU: 35% | Memory: 345MB | Disk: 42%   ║
║                                           ║
║ Recent Activity:                          ║
║   08:15:33 - Daily analysis complete      ║
║   08:05:12 - 3 tasks prioritized          ║
║   07:30:45 - Calendar synced (47 events)  ║
║                                           ║
║ Next Events:                              ║
║   08:30 - Gmail sync                      ║
║   09:00 - Todoist sync                    ║
║   18:00 - Weekly analysis (in 10h)        ║
╚═══════════════════════════════════════════╝
```

### Query Dashboard

```
User: "Show me my system health"
  ↓
Orchestrator → Dashboard Agent
  ↓
Return JSON:
{
  "status": "healthy",
  "uptime_hours": 720,
  "requests_today": 847,
  "error_rate": 0.2%,
  "response_time_p50": 145ms,
  "response_time_p95": 450ms,
  "storage_used": 85MB,
  "next_maintenance": "2026-05-12"
}
```

