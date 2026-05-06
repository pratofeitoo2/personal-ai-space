# Operational Handbook

Quick reference for operating the engine.

---

## Starting the Engine

### First Time Setup

```bash
# 1. Initialize databases
python engine/init_databases.py

# 2. Load vault credentials
# Manually add to vault/ folder:
# - vault/credentials/google_oauth.json
# - vault/credentials/todoist_token.json
# - vault/credentials/github_token.json

# 3. Configure integrations
# Edit engine/config/system.config.json
# Set enabled: true for desired integrations

# 4. Start engine
python engine/start_engine.py

# Expected output:
# [2026-05-06 08:00:01] INFO: Engine started
# [2026-05-06 08:00:02] INFO: 6/6 agents loaded
# [2026-05-06 08:00:03] INFO: Connections verified
# [2026-05-06 08:00:04] INFO: Ready for requests
```

### Daily Startup

```bash
# Start engine (runs in background)
python engine/start_engine.py &

# Verify running
curl http://localhost:8000/health
# Expected: { "status": "healthy", "agents": 6 }

# Check yesterday's report
tail -50 logs/system.log

# Start your day
# Engine automatically runs 08:00 daily digest
```

---

## Common Operations

### Add a New Task

```bash
# Via CLI
python engine/cli.py add-task \
  --title "Complete feature" \
  --priority critical \
  --due 2026-05-20 \
  --estimate 4

# Via Python
from engine import api
api.create_task(
  title="Complete feature",
  priority="critical",
  due_date="2026-05-20",
  estimated_hours=4
)

# Task appears in:
# - command/tasks/active_tasks.json
# - tasks.db
# - Today's digest (if due soon)
```

### Log a Habit Completion

```bash
# Via CLI
python engine/cli.py log-habit \
  --habit meditation \
  --duration 15 \
  --confidence high

# Via direct file edit
# Edit self/habits/tracking.csv
# Add: habit,meditation,date,duration,notes
# Or append to database via API

# Automatically updates:
# - Habit streak
# - Total completions
# - Insights (patterns)
```

### Query Your Data

```bash
# "What were my top tasks last week?"
python engine/cli.py query \
  --question "top_tasks_week"

# "Show me my exercise progress"
python engine/cli.py query \
  --question "habit_progress" \
  --habit exercise

# "Generate weekly report"
python engine/cli.py generate \
  --report weekly

# "Analyze my productivity"
python engine/cli.py analyze \
  --metric productivity \
  --period month
```

---

## Troubleshooting

### Engine Not Starting

```
Error: "Database connection failed"
  ↓
1. Check database files exist:
   ls -la engine/db/

2. If missing, reinitialize:
   python engine/init_databases.py

3. Verify permissions:
   chmod 644 engine/db/*.db

4. Check logs:
   tail -20 logs/errors.log
```

### Slow Queries

```
Error: "Database query took 1.2s"
  ↓
1. Check slow query log:
   grep "PERF.*duration" logs/performance.log | tail -10

2. Identify slow query:
   python engine/analyze_performance.py

3. Reindex if needed:
   python engine/reindex_databases.py

4. Monitor next query:
   Should return to <100ms
```

### Missing Integration Sync

```
Error: "Todoist sync failed"
  ↓
1. Check credentials:
   ls -la vault/credentials/todoist_token.json

2. Verify token valid:
   curl -H "Authorization: Bearer <token>" \
        https://api.todoist.com/rest/v2/tasks \
        | head -5

3. Check logs:
   grep "todoist" logs/errors.log

4. If token expired, update:
   python engine/refresh_integration.py --service todoist

5. Retry sync:
   python engine/sync_integrations.py --service todoist
```

### Data Corruption

```
Error: "Duplicate entry detected"
  ↓
1. Run data integrity check:
   python engine/check_integrity.py

2. Generate report:
   - Lists all issues found
   - Suggests fixes

3. Repair (with backup first):
   python engine/repair_database.py --auto-fix

4. Verify repair:
   python engine/check_integrity.py
```

---

## Maintenance

### Daily (Automatic)

```
✓ 08:00 - Daily analysis runs
✓ 08:30 - Integrations sync
✓ Hourly - Health checks
✓ Every 5 min - Memory cleanup
```

### Weekly (Manual)

```
Friday 17:00 - Before weekly review:
  1. Back up databases
     python engine/backup.py
  
  2. Check integrity
     python engine/check_integrity.py
  
  3. Review logs
     grep "ERROR" logs/errors.log | wc -l
  
  4. Monitor performance
     python engine/performance_report.py
```

### Monthly (Manual)

```
1st of month 02:00 - Monthly maintenance:
  1. Full system backup
     python engine/backup.py --full
  
  2. Archive old data
     python engine/archive_old_data.py
  
  3. Optimize databases
     python engine/optimize_databases.py
  
  4. Generate health report
     python engine/system_health_report.py
  
  5. Review and approve archival
     Review command/archive/ folder
```

---

## Backup & Recovery

### Create Backup

```bash
# Quick backup (current day)
python engine/backup.py --quick
# Output: backup_2026-05-06_quick.tar.gz

# Full backup
python engine/backup.py --full
# Output: backup_2026-05-06_full.tar.gz

# Backup with encryption
python engine/backup.py --full --encrypt
# Output: backup_2026-05-06_full.tar.gz.gpg
# Requires passphrase
```

### Restore Backup

```bash
# Stop engine first
pkill -f "python engine/start_engine.py"

# Restore from backup
python engine/restore_backup.py backup_2026-05-06_full.tar.gz

# Verify integrity
python engine/check_integrity.py

# Restart engine
python engine/start_engine.py &
```

---

## Performance Tuning

### Check Performance

```bash
# Generate performance report
python engine/performance_report.py

# Output:
# Query Performance:
#   Avg: 145ms
#   P50: 89ms
#   P95: 450ms
#   P99: 2100ms
#
# Slow Queries (>1s):
#   - SELECT habits + logs (1.2s) - needs index
#   - SELECT tasks + dependencies (1.8s) - needs join optimization
#
# Recommendations:
#   1. Add index on habit_id in habit_logs
#   2. Add covering index on tasks(project_id, status)
```

### Apply Optimizations

```bash
# Reindex all databases
python engine/reindex_databases.py

# Analyze and optimize query plans
python engine/analyze_queries.py

# Rebuild database (removes bloat)
python engine/vacuum_databases.py

# Verify improvements
python engine/performance_report.py
```

---

## Monitoring Health

### Daily Health Check

```bash
# Run diagnostic
python engine/diagnose.py

# Output:
# ✓ Engine: Running (2h 34m uptime)
# ✓ Agents: 6/6 healthy
# ✓ Databases: All responsive
# ✓ Integrations: 3/3 synced
# ✓ Memory: 345MB / 512MB (67%)
# ✓ Disk: 127MB / 1000MB (12%)
# ✓ Last request: 2m ago
# ✓ Error rate: 0.2% (acceptable)
# ✗ Warning: Meditation habit at risk (0 days)
```

### Weekly Health Report

```bash
# Generate weekly report
python engine/health_report.py --period week

# Saved to: reports/health_2026-05-06.json
# Contains:
#   - System uptime
#   - Agent performance
#   - Error analysis
#   - Resource usage
#   - Recommendations
```

---

## Logs & Diagnostics

### Viewing Logs

```bash
# Last 20 lines of system log
tail -20 logs/system.log

# Follow errors in real-time
tail -f logs/errors.log

# Search for specific error
grep "integration" logs/errors.log

# Count errors by agent
grep "agent" logs/system.log | grep -o "agent '[^']*'" | sort | uniq -c

# Export logs for analysis
tar -czf logs_backup_2026-05-06.tar.gz logs/
```

### Log Analysis

```bash
# Generate log summary
python engine/analyze_logs.py

# Output:
# Daily Activity Report
# =====================
# Total log lines: 2,847
# Info messages: 2,634 (93%)
# Warnings: 189 (7%)
# Errors: 24 (0.8%)
#
# Top errors:
#   1. Integration timeout (8)
#   2. Database connection (6)
#   3. Agent timeout (4)
#   4. Duplicate data (3)
#   5. Invalid input (3)
```

---

## Shutting Down

### Normal Shutdown

```bash
# Stop engine gracefully
python engine/stop_engine.py

# Waits for in-flight requests to complete
# Logs shutdown event
# Expected: < 30 seconds

# Verify stopped
curl http://localhost:8000/health 2>/dev/null
# Should fail: Connection refused
```

### Emergency Shutdown

```bash
# Force stop immediately
pkill -9 -f "python engine"

# Check if processes remain
ps aux | grep engine

# Only use if normal shutdown hangs
```

---

## Getting Help

### Check Status
```
curl http://localhost:8000/status | jq .
```

### Read Recent Errors
```
tail -20 logs/errors.log
```

### Generate Diagnostic Report
```
python engine/diagnose.py > diagnostic_report.txt
```

### Contact/Documentation
- Main docs: `docs/ARCHITECTURE.md`
- Data flows: `docs/DATA_FLOWS.md`
- Troubleshooting: This file
- All logs: `logs/` directory

