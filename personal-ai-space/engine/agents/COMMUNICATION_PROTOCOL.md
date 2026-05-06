# Agent Communication Protocol

## Message Structure

All agent-to-agent communication follows this protocol:

```json
{
  "id": "msg_uuid",
  "timestamp": "2026-05-06T08:30:15.123Z",
  "sender": "task-coordinator",
  "recipients": ["insight-generator", "reminder-system"],
  "action": "request",
  "priority": "high",
  "payload": {
    "command": "analyze_task_completion",
    "parameters": {
      "task_id": "task_001",
      "time_period": "week"
    }
  },
  "context": {
    "session_id": "session_uuid",
    "user_id": "self",
    "request_chain": ["context-manager", "task-coordinator", "insight-generator"]
  },
  "metadata": {
    "timeout_ms": 5000,
    "retry_policy": "exponential_backoff",
    "require_response": true
  }
}
```

---

## Action Types

### 1. Request
Agent asks another agent to perform an action.

```json
{
  "action": "request",
  "payload": {
    "command": "get_user_profile",
    "parameters": {}
  },
  "metadata": {
    "timeout_ms": 3000,
    "require_response": true
  }
}
```

**Response:**
```json
{
  "action": "response",
  "status": "success",
  "payload": {
    "user_profile": { ... }
  }
}
```

### 2. Broadcast
Agent publishes an event for any interested listeners.

```json
{
  "action": "broadcast",
  "event_type": "habit_completed",
  "payload": {
    "habit_id": "habit_001",
    "completed_at": "2026-05-06T08:30:00Z"
  }
}
```

**Listeners register:**
- insight-generator (for pattern detection)
- reminder-system (for next reminders)
- report-generator (for statistics)

### 3. Async Command
Agent sends command but doesn't need immediate response.

```json
{
  "action": "async_command",
  "payload": {
    "command": "index_article",
    "article_id": "article_123"
  },
  "metadata": {
    "require_response": false
  }
}
```

---

## Communication Patterns

### Pattern 1: Request-Response
```
Agent A → Request
  ↓
Agent B processes
  ↓
Agent B → Response
  ↓
Agent A continues
```

**Example:**
- Task Coordinator requests current habits from Context Manager
- Context Manager responds with user habits
- Task Coordinator uses habits for prioritization

### Pattern 2: Publish-Subscribe
```
Agent A → Broadcast Event
  ↓
Agent B (subscribed) → Process
Agent C (subscribed) → Process
Agent D (subscribed) → Process
```

**Example:**
- Task completed event published
- Reminder system removes related reminders
- Insight generator updates statistics
- Report generator notes completion

### Pattern 3: Request with Parallel Responses
```
Orchestrator → Request to [Agent A, Agent B, Agent C]
  ↓
Agent A → Response (100ms)
Agent B → Response (200ms)
Agent C → Response (150ms)
  ↓
Orchestrator → Aggregate & Continue
```

**Example:**
- Get task status, habits, and calendar events in parallel
- Aggregate into unified report
- Respond to user

---

## Message Routing

```
Message Queue
    ↓
Route by recipient
    ├─ Single recipient → Direct call
    ├─ Multiple recipients → Fan-out
    └─ Broadcast → Publish to subscribers
    ↓
Agent receives message
    ↓
Process
    ↓
Response (if required)
```

---

## Error Handling in Communication

### Timeout
```
Agent A sends request
  ↓
30s timeout (configurable)
  ↓
No response received
  ↓
Agent A retries (if configured)
  ↓
After max retries → Fallback/Error
```

### Malformed Message
```
Message validation fails
  ↓
Log error to errors.log
  ↓
Send error response
  ↓
Discard message
```

### Agent Unavailable
```
Recipient agent not running
  ↓
Queue message (if persistent queue enabled)
  ↓
Retry when agent available
  ↓
Timeout if never available
```

---

## Priority Levels

- **critical**: Process immediately (e.g., reminders)
- **high**: Process soon (e.g., task updates)
- **normal**: Process in order (default)
- **low**: Process when idle (e.g., archival)

**Prioritization:**
- Critical messages bypass queue
- High priority queue processed first
- Normal/Low fill remaining capacity

---

## Example: Daily Analysis Workflow

```
08:00:00
  ↓
Scheduler → Broadcast "daily_analysis_trigger"
  ↓
Agents subscribe and process:
  
  1. Context Manager
     └─ Load user profile, prepare context
     └─ Broadcast "context_ready"
  
  2. Task Coordinator (waiting for context_ready)
     └─ Load pending tasks
     └─ Calculate priorities
     └─ Broadcast "tasks_analyzed"
  
  3. Insight Generator (waiting for context_ready)
     └─ Analyze habits from last 24h
     └─ Detect anomalies
     └─ Broadcast "insights_generated"
  
  4. Report Generator (waiting for tasks_analyzed, insights_generated)
     └─ Request daily digest template
     └─ Compile all data
     └─ Output report
     └─ Broadcast "report_ready"
  
  5. Reminder System (always listening)
     └─ Check upcoming reminders
     └─ Schedule notifications
  
08:05:00
  ↓
All processing complete
  └─ User receives daily digest
```

---

## Debugging Communication

**Trace a message:**
```bash
grep "msg_uuid" logs/*.log
# Shows: creation → routing → processing → response
```

**Monitor agent health:**
```
Agents up: 6/6
Avg response time: 145ms
Error rate: 0.2%
Message queue: 3 pending
```

**Communication metrics:**
```json
{
  "messages_today": 847,
  "avg_latency_ms": 145,
  "timeout_rate": 0.001,
  "error_rate": 0.002,
  "broadcast_events": 134,
  "direct_requests": 713
}
```

