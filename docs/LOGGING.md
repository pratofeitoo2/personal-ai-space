# Logging Architecture

## Log Types and Purposes

### 1. system.log
**What**: Engine operations, agent lifecycle, normal events
**When**: Every operation, startup/shutdown, agent transitions
**Retention**: 90 days

```log
[2026-05-06 08:00:01] INFO: Engine started in development mode
[2026-05-06 08:00:02] INFO: Agent 'context-manager' loaded
[2026-05-06 08:00:05] INFO: Task coordinator processing 12 pending tasks
[2026-05-06 08:00:15] INFO: Daily analysis triggered
```

### 2. errors.log
**What**: Failures, exceptions, recoverable issues
**When**: Any error condition
**Retention**: 90 days

```log
[2026-05-06 09:15:23] ERROR: Database connection failed (attempt 1/3)
[2026-05-06 09:15:24] ERROR: Agent 'insight-generator' timeout after 30s
[2026-05-06 14:30:45] WARNING: Integration sync failed for Todoist
[2026-05-06 14:30:50] ERROR: Context retrieval fallback to defaults
```

### 3. audit.log
**What**: Data modifications, access patterns, security events
**When**: Before/after significant changes
**Retention**: 1 year (sensitive)

```log
[2026-05-06 10:30:11] AUDIT: User created task 'task_001'
[2026-05-06 10:30:12] AUDIT: Task 'task_001' status changed (pending → in_progress)
[2026-05-06 10:31:02] AUDIT: Habit 'meditation' logged completion
[2026-05-06 11:00:00] AUDIT: Database backup completed
```

### 4. performance.log
**What**: Timing, resource usage, optimization opportunities
**When**: Every agent execution, queries > 100ms
**Retention**: 30 days

```log
[2026-05-06 08:15:33] PERF: context-manager execution: 145ms (memory: 12MB)
[2026-05-06 08:15:45] PERF: Database query (tasks.db): 234ms (rows: 127)
[2026-05-06 08:16:00] PERF: Insight generation: 1847ms (CPU: 45%)
```

---

## Log Format

**Standard Format:**
```
[TIMESTAMP] LEVEL: MESSAGE [metadata]
```

**JSON Format (for machine parsing):**
```json
{
  "timestamp": "2026-05-06T08:15:33Z",
  "level": "INFO",
  "component": "agent_name",
  "message": "Operation completed",
  "duration_ms": 145,
  "resource_usage": {
    "memory_mb": 12,
    "cpu_percent": 5
  },
  "context": {
    "session_id": "session_uuid",
    "user_id": "self",
    "operation_id": "op_uuid"
  }
}
```

---

## Log Levels

- **DEBUG**: Detailed diagnostic info (disabled in production)
- **INFO**: General informational messages
- **WARNING**: Warning messages (recoverable issues)
- **ERROR**: Error messages (failures, exceptions)
- **CRITICAL**: System-level failures

---

## Rotation and Retention

**Rotation:**
- Daily rotation at midnight
- Backup count: 30 days of logs
- Compression after 7 days (optional)

**Cleanup:**
- Automatic cleanup at startup
- Purge logs older than retention period
- Alert if disk usage > 80%

---

## Analysis and Querying

### Common Queries

**Daily Summary:**
```bash
# Get today's errors
grep "ERROR" logs/errors.log | tail -20

# Count operations by agent
grep "INFO" logs/system.log | grep -o "agent '[^']*'" | sort | uniq -c

# Performance bottlenecks
grep "PERF" logs/performance.log | grep -oP 'duration_ms.*' | sort -rn | head -10
```

**Performance Analysis:**
```json
{
  "query": "agents_by_duration",
  "results": {
    "insight-generator": 1847,
    "context-manager": 145,
    "task-coordinator": 89,
    "reminder-system": 23
  }
}
```

**Error Rate:**
```json
{
  "errors_today": 3,
  "recovery_rate": 0.67,
  "mean_time_between_failures": 14400,
  "most_common_error": "database_connection"
}
```

---

## Monitoring and Alerts

**Alert Thresholds:**
- Error rate > 5% in 1 hour → Alert
- Agent timeout > 2x → Alert
- Database query > 5 seconds → Log warning
- Disk usage > 80% → Alert
- Memory usage > 1GB → Log warning

**Alert Destinations:**
- Email to user
- Log to errors.log
- Update system status dashboard
- Create incident ticket

---

## Log Archival

**Daily Backup:**
```
logs/
├── 2026-05-06/
│   ├── system.log.gz
│   ├── errors.log.gz
│   ├── audit.log
│   └── performance.log.gz
└── current/
    ├── system.log
    ├── errors.log
    ├── audit.log
    └── performance.log
```

**Retention Policy:**
- system.log: 90 days
- errors.log: 90 days
- audit.log: 1 year
- performance.log: 30 days

