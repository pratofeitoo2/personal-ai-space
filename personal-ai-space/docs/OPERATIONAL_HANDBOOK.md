# Operational Handbook

Quick reference for operating the engine.

---

## Starting the Engine

### First Time Setup

```bash
# 1. Initialize databases
python engine/init_engine.py

# 2. Load vault credentials
# Manually add to vault/ folder:
# - vault/credentials/google_oauth.json
# - vault/credentials/todoist_token.json
# - vault/credentials/github_token.json

# 3. Configure integrations
# Edit engine/config/system.config.json
# Set enabled: true for desired integrations

# 4. Start engine daemon
python engine/start_engine.py

# Expected output:
# [2026-05-09 19:23:52] INFO: Engine v0.1.0 starting…
# [2026-05-09 19:23:52] INFO: ✓ self.db (9 tables)
# [2026-05-09 19:23:53] INFO: Engine ready — 6/7 agents active
```

### Daily Startup

```bash
# Start engine daemon (background)
python engine/start_engine.py

# Or manually:
python engine/cli.py daemon start

# Check status
python engine/cli.py daemon status

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
   ls -la personal-ai-space/engine/db/

2. If missing, reinitialize:
   python engine/init_engine.py

3. Verify permissions:
   chmod 644 personal-ai-space/engine/db/*.db

4. Check logs:
   tail -20 personal-ai-space/engine/logs/errors.log
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
   
  2. Check engine health
     python engine/cli.py daemon status
   
  3. Review logs
     grep "ERROR" logs/errors.log | wc -l
   
  4. Run diagnostic
     python engine/diagnose.py
```

### Monthly (Manual)

```
1st of month 02:00 - Monthly maintenance:
  1. Full system backup
     python engine/backup.py --full
   
  2. Run diagnostic
     python engine/diagnose.py > diagnostic_report.txt
   
  3. Review and approve archival
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
python engine/cli.py daemon stop

# Extract backup to engine/db/
tar -xzf engine/backups/backup_2026-05-06_full.tar.gz -C engine/

# Verify
python engine/diagnose.py

# Restart engine
python engine/start_engine.py
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
# Quick status
python engine/cli.py daemon status

# Run full diagnostic
python engine/diagnose.py

# Output:
# 🔍 Engine Diagnostic Report
# ✓ Engine: Running (v0.1.0 up 2h 34m)
# ✓ Agent: task-coordinator (ready)
# ✓ Agent: knowledge-indexer (ready)
# ...
# ✓ DB: self.db (9 tables)
# ✓ DB: tasks.db (5 tables)
```

### Weekly Health Report

```bash
# Run diagnostic with output to file
python engine/diagnose.py > diagnostic_report.txt

# Check error log
tail -20 engine/logs/errors.log
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
# Stop engine daemon
python engine/stop_engine.py

# Or manually:
python engine/cli.py daemon stop

# Waits for in-flight requests to complete
# Logs shutdown event

# Verify stopped
python engine/cli.py daemon status
# Should show: Engine daemon is not running
```

### Emergency Shutdown

```bash
# Force stop immediately
python engine/cli.py daemon stop
# or
pkill -f "python cli.py serve"

# Check if processes remain
ps aux | grep cli.py

# Only use if normal shutdown hangs
```

---

## Getting Help

### Check Status
```
python engine/cli.py daemon status
```

### Read Recent Errors
```
tail -20 engine/logs/errors.log
```

### Generate Diagnostic Report
```
python engine/diagnose.py > diagnostic_report.txt
```

### Contact/Documentation
- Main docs: `docs/ARCHITECTURE.md`
- Data flows: `docs/DATA_FLOWS.md`
- Troubleshooting: This file
- All logs: `engine/logs/` directory

