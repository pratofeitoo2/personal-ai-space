# Quality Assurance & Data Integrity

## Data Validation Framework

### 1. Input Validation

All data entering the system must pass validation:

```python
# Schema validation
{
  "id": "task_001",
  "title": "Complete engine setup",
  "priority": "critical",  # Must be: critical, high, normal, low
  "due_date": "2026-05-20",  # ISO 8601 format
  "estimated_hours": 4.5  # Positive number
}
```

**Validation Rules:**
- Required fields present
- Data types match schema
- Values within allowed range
- Formats match patterns (dates, emails, etc.)
- No SQL injection attempts

### 2. Duplicate Detection

**Before Insert:**
```sql
-- Check for exact duplicates
SELECT * FROM tasks 
WHERE title = ? AND project_id = ? 
AND created_at > now() - interval '7 days'

-- If exists: Log duplicate, merge if needed, skip insert
```

**Fuzzy Matching** (for similar items):
```
Article 1: "Building Personal AI Systems"
Article 2: "Personal AI System Construction"
→ Similarity score: 0.87 → Flag as potential duplicate
```

### 3. Referential Integrity

```sql
-- Foreign key constraints
CREATE TABLE task_dependencies (
  task_id TEXT REFERENCES tasks(id),
  depends_on TEXT REFERENCES tasks(id)
);

-- Cascade delete on task removal
-- Constraint checked on every insert
```

### 4. Consistency Checks

**Cross-database consistency:**
```
Query 1: Task status in tasks.db = "completed"
Query 2: Task completion logged in memories.db?
Result: ✓ Consistent OR ✗ Inconsistent

If inconsistent:
  → Log to errors.log
  → Alert user
  → Trigger manual review
```

---

## Data Quality Metrics

### Collection & Measurement

```json
{
  "timestamp": "2026-05-06T08:00:00Z",
  "data_quality": {
    "completeness": 0.98,        // % of expected fields populated
    "accuracy": 0.96,             // % of validated records
    "consistency": 0.99,           // Cross-table consistency
    "timeliness": 0.94,            // % data within expected recency
    "uniqueness": 0.97             // % records non-duplicate
  },
  "issues": {
    "missing_values": 2,
    "validation_failures": 1,
    "inconsistencies": 0,
    "duplicates_detected": 3,
    "stale_data": 5
  }
}
```

### Quality Scoring

```
Overall Score = (
  Completeness × 0.25 +
  Accuracy × 0.25 +
  Consistency × 0.25 +
  Timeliness × 0.15 +
  Uniqueness × 0.10
)

Score interpretation:
> 0.95: Excellent
0.90-0.95: Good
0.85-0.90: Fair (review needed)
< 0.85: Poor (intervention required)
```

---

## Anomaly Detection

### Statistical Methods

```
Normal Range Detection:
  1. Collect baseline (30 days)
  2. Calculate mean, std dev
  3. Detect values > 3σ from mean
  4. Flag for review

Example: Task completion
  Baseline: 18 ± 3 tasks/week
  Week value: 8 tasks
  Deviation: -3.3σ
  → Anomaly! Flag for investigation
```

### Trigger-Based Anomalies

```
IF habit_streak = 0 AND previous_streak > 5
  → Anomaly: Habit broken
  → Action: Alert user, investigate

IF estimate_error > 100%
  → Anomaly: Bad estimate
  → Action: Log for learning

IF task_completed_in < 10% of estimate
  → Possible: Underestimate or task misclassification
  → Action: Review for pattern
```

---

## Error Recovery

### Transaction Rollback

```
Operation:
  1. Begin transaction
  2. Insert task A
  3. Update task B dependency
  4. Create reminder

If step 3 fails:
  → Rollback entire transaction
  → No partial state
  → User notified
  → Log error
```

### Data Repair

**Duplicate Merging:**
```
Duplicates detected: Task_001 and Task_002
  ↓
Keep: Task_001 (created first)
  ↓
Merge data:
  - Keep older ID
  - Combine notes
  - Use latest timestamp
  - Update dependencies
  ↓
Delete: Task_002
  ↓
Log merge in audit.log
```

**Orphan Resolution:**
```
Found: Task with non-existent project_id
  ↓
Move to: Default/Unassigned project
  ↓
Log: Orphan repair event
  ↓
Alert: User to categorize
```

---

## Backup & Recovery

### Backup Schedule

```
Hourly:
  - Transaction log backup
  - Size: ~1 MB

Daily:
  - Full database backup at 02:00
  - Compressed (gzip)
  - Stored locally + cloud
  - Retention: 30 days

Weekly:
  - Full system backup (Sunday 03:00)
  - All databases + attachments
  - Encrypted before cloud upload
  - Retention: 1 year

Monthly:
  - Full system backup (1st of month)
  - Long-term archive
  - Retention: Indefinite
```

### Recovery Procedure

**Point-in-time Recovery:**
```
Scenario: Accidentally deleted important task
  ↓
Request: Recover to timestamp T (6 hours ago)
  ↓
Process:
  1. Stop all agents
  2. Load backup from T
  3. Verify integrity
  4. Replay transaction log
  5. Resume agents
  
Time: ~5 minutes
Data loss: ~0 (transaction-logged)
```

---

## Audit Trail

### Tracked Events

```sql
CREATE TABLE audit_log (
  id TEXT PRIMARY KEY,
  timestamp DATETIME,
  action TEXT,              -- create, update, delete
  table_name TEXT,
  record_id TEXT,
  old_value JSON,
  new_value JSON,
  user_id TEXT,
  reason TEXT,
  ip_address TEXT
);
```

### Example Audit Trail

```
2026-05-06 10:30:11 | UPDATE | tasks | task_001
  Field: status
  Old: pending → New: in_progress
  User: self | Reason: User clicked start

2026-05-06 10:31:02 | CREATE | habit_logs | log_001
  Habit: meditation
  Completed: 15 minutes
  Confidence: high
  User: self | Reason: Daily logging

2026-05-06 11:00:00 | DELETE | articles | article_123
  Title: "Old reference"
  User: self | Reason: Duplicate cleanup
```

### Audit Query Examples

```
-- What changed in task_001 today?
SELECT * FROM audit_log 
WHERE table_name = 'tasks' 
AND record_id = 'task_001'
AND timestamp > '2026-05-06 00:00:00'

-- Who deleted what this week?
SELECT * FROM audit_log 
WHERE action = 'DELETE'
AND timestamp > '2026-04-30'

-- Track all modifications to profile
SELECT * FROM audit_log 
WHERE table_name = 'profile'
ORDER BY timestamp DESC
```

---

## Testing & Validation

### Automated Tests

**Daily Run (02:00):**
```
✓ Schema validation: All tables match schema.sql
✓ Foreign key integrity: All references valid
✓ Duplicate detection: No exact duplicates found
✓ Data type validation: All values correct type
✓ Range validation: All numeric values in range
✓ Consistency checks: Cross-table consistency verified
✓ Performance test: Queries within SLA
```

**Results:**
```
Tests passed: 24/24
Data quality score: 0.97
Last run: 2026-05-06 02:15:23
Issues found: 0
```

### Manual Validation

**Weekly (Monday 09:00):**
```
1. Sample 50 random records from each table
2. Verify against source truth
3. Check for data drift
4. Review recent errors
5. Update quality baseline
```

---

## Data Governance

### Retention Policy

```
Active data:
  Tasks: Keep until 1 year after completion
  Habits: Keep forever (history)
  Articles: Keep forever (knowledge)
  Interactions: Keep 2 years for analysis
  
Archived data:
  Move to archive/ folder
  Compress (gzip)
  Index for searching
  Retain indefinitely

Sensitive data (vault/):
  Purge credentials after 1 year unused
  Rotate API keys quarterly
  Audit access monthly
```

### Data Access Control

```
Internal (self):
  Read: All agents
  Write: Authorized agents only
  Delete: Manual approval only

External (integrations):
  Read: Via API with tokens
  Write: Rate-limited, logged
  Delete: Requires confirmation

User-facing:
  View: All own data
  Edit: Data she created
  Delete: With confirmation
```

