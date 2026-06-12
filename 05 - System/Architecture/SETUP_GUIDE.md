# System Initialization & Setup Guide

Complete walkthrough for setting up the personal AI engine.

---

## Pre-Setup Requirements

### Software Requirements
- Python 3.10+
- SQLite 3.x
- 2GB disk space (minimum)
- 512MB RAM (minimum)

### Knowledge Requirements
- Understanding of tasks/projects (yours)
- API keys for integrations you want (optional)
- Comfortable with JSON config files

---

## Step 1: Directory Structure Verification

Verify all folders exist:

```bash
cd personal-ai-space

# Should see:
ls -la

command/        # Your active management
docs/           # All documentation
engine/         # The AI system
knowledge/      # Your library
self/           # Digital you
vault/          # Secrets (git-ignored)
.gitignore
```

---

## Step 2: Initialize Databases

Create SQLite databases from schema files:

```bash
cd engine/db

# Create memories database
sqlite3 memories.db < schema_memories.sql
sqlite3 memories.db ".tables"
# Output: agent_memory context_window interactions

# Create self database
sqlite3 self.db < schema_self.sql
sqlite3 self.db ".tables"
# Output: behaviors habits needs profile traits

# Create tasks database
sqlite3 tasks.db < schema_tasks.sql
sqlite3 tasks.db ".tables"
# Output: calendar_events projects task_history tasks

# Create knowledge database
sqlite3 knowledge.db < schema_knowledge.sql
sqlite3 knowledge.db ".tables"
# Output: articles cross_references knowledge_index notes...

# Verify all databases created
ls -lh *.db
# Expected: 4 files, each ~30-50KB initially
```

---

## Step 3: Populate User Profile

Update your profile with real data:

```bash
# Edit self/profile.json
nano self/profile.json

# Key fields to update:
{
  "name": "Your Name",           # Your name
  "age": 28,                     # Your age
  "timezone": "America/Sao_Paulo", # Your timezone
  "work_style": "deep_work_preferred",  # How you work
  "energy_peak_hours": ["09:00-12:00", "14:00-17:00"],  # When you're sharp
  "preferences": {
    "communication": "written_async",
    "decision_making": "data_driven",
    "feedback": "direct_constructive"
  },
  "goals_current_year": [
    "Your goal 1",
    "Your goal 2"
  ]
}

# Save and verify
cat self/profile.json | jq .
```

---

## Step 4: Setup Vault (Credentials)

Create credential placeholders (fill in later):

```bash
cd vault

# Create credentials structure
touch credentials/sample.json
touch accounts/sample.json
touch auth/sample.json

# Example credentials/sample.json:
cat > credentials/google_oauth.json << 'EOF'
{
  "type": "oauth2",
  "client_id": "YOUR_CLIENT_ID",
  "client_secret": "YOUR_CLIENT_SECRET",
  "refresh_token": "YOUR_REFRESH_TOKEN",
  "token_uri": "https://oauth2.googleapis.com/token"
}
EOF

# Note: Fill in actual credentials later when setting up integrations
# Vault is git-ignored, so safe to store secrets here
```

---

## Step 5: Configure Engine

Review and customize engine configuration:

```bash
# Review system config
cat engine/config/system.config.json | jq .

# Key sections to customize:

# 1. Engine mode (development vs production)
"mode": "development"  # Or "production"

# 2. Memory settings (adjust for your system)
"memory": {
  "short_term": {
    "max_size_mb": 512    # Increase if you have more RAM
  }
}

# 3. Logging level
"logging": {
  "level": "info"       # Or "debug" for more verbose
}

# 4. Integration status (enable as you set them up)
"integrations": {
  "google": { "enabled": false },   # Enable when ready
  "todoist": { "enabled": false },  # Enable when ready
  "github": { "enabled": false }    # Enable when ready
}

# Make changes if needed
nano engine/config/system.config.json
```

---

## Step 6: Load Sample Data (Optional)

Populate databases with sample data for testing:

```bash
# Create sample tasks
cat > /tmp/sample_tasks.sql << 'EOF'
INSERT INTO tasks (id, title, project_id, priority, status, created_at, due_date, estimated_hours)
VALUES
  ('task_001', 'Review engine architecture', 'personal-ai', 'critical', 'pending', datetime('now'), datetime('now', '+3 days'), 2),
  ('task_002', 'Set up integrations', 'personal-ai', 'high', 'pending', datetime('now'), datetime('now', '+7 days'), 4),
  ('task_003', 'Test reporting system', 'personal-ai', 'high', 'pending', datetime('now'), datetime('now', '+5 days'), 3);
EOF

sqlite3 engine/db/tasks.db < /tmp/sample_tasks.sql

# Verify
sqlite3 engine/db/tasks.db "SELECT id, title, status FROM tasks;"
```

---

## Step 7: Verify Engine Can Start

Do a test start:

```bash
# Navigate to engine
cd engine

# Test import Python dependencies
python3 -c "
import sqlite3
import json
from datetime import datetime
print('✓ Python imports successful')
"

# Test database connections
python3 -c "
import sqlite3
for db in ['db/memories.db', 'db/self.db', 'db/tasks.db', 'db/knowledge.db']:
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute('SELECT count(*) FROM sqlite_master WHERE type=\"table\"')
    tables = cursor.fetchone()[0]
    print(f'✓ {db}: {tables} tables')
    conn.close()
"

# If all checks pass, you're ready!
echo "✓ Engine ready for startup"
```

---

## Step 8: First Startup

Start the engine and verify it runs:

```bash
# Create logs directory
mkdir -p logs

# Start engine (with output)
python3 start_engine.py

# Expected output:
# [2026-05-06 08:00:01] INFO: Engine started in development mode
# [2026-05-06 08:00:02] INFO: Agent 'context-manager' loaded
# [2026-05-06 08:00:03] INFO: Agent 'task-coordinator' loaded
# [2026-05-06 08:00:04] INFO: Databases connected: 4/4
# [2026-05-06 08:00:05] INFO: Memory systems initialized
# [2026-05-06 08:00:06] INFO: Engine ready for requests

# Let it run for 10 seconds, then Ctrl+C to stop
# This initializes all systems

# Check logs were created
ls -la logs/
# Should see: system.log, errors.log, audit.log, performance.log
```

---

## Step 9: Configure Integrations (Optional)

Set up integrations as desired:

### Google Calendar + Gmail

```bash
# 1. Get credentials from Google Cloud Console
# https://console.cloud.google.com/

# 2. Create OAuth2 credentials (Desktop app)

# 3. Save to vault/credentials/google_oauth.json

# 4. Enable in config
nano engine/config/system.config.json
# Set "google": { "enabled": true }

# 5. Test connection
python3 -c "from engine.integrations import GoogleCalendarSync; gc = GoogleCalendarSync(); print(gc.test_connection())"
```

### Todoist

```bash
# 1. Get API token from Todoist Settings
# https://todoist.com/app/settings/integrations/developer

# 2. Save to vault/credentials/todoist_token.json
echo '{"token": "YOUR_TOKEN"}' > vault/credentials/todoist_token.json

# 3. Enable in config
nano engine/config/system.config.json
# Set "todoist": { "enabled": true }

# 4. Test connection
python3 -c "from engine.integrations import TodoistSync; ts = TodoistSync(); print(ts.test_connection())"
```

### GitHub

```bash
# 1. Create Personal Access Token
# https://github.com/settings/tokens

# 2. Save to vault/credentials/github_token.json
echo '{"token": "YOUR_TOKEN"}' > vault/credentials/github_token.json

# 3. Enable in config
nano engine/config/system.config.json
# Set "github": { "enabled": true }

# 4. Test connection
python3 -c "from engine.integrations import GitHubSync; gs = GitHubSync(); print(gs.test_connection())"
```

---

## Step 10: Verify Full System

Run comprehensive system check:

```bash
# Run diagnostics
python3 diagnose.py

# Output should show:
# ✓ Databases: All responsive
# ✓ Agents: 6/6 loaded
# ✓ Memory systems: Ready
# ✓ Integrations: X configured
# ✓ Logs: Created and writable
# ✓ Storage: Healthy

# If all green, you're done!
```

---

## Initial Operations

### Day 1: Capture Some Data

```bash
# Add a few tasks to get started
python3 cli.py add-task --title "Learn engine" --priority high --due 2026-05-10

# Log a habit completion
python3 cli.py log-habit --habit meditation --duration 10

# This populates your data, making reports more useful
```

### Day 2: Review Auto-Generated Report

```bash
# The engine runs daily analysis at 08:00
# Check the daily digest

cat reports/daily_digest_2026-05-07.md

# This shows what the engine can do with real data
```

### Day 3+: Integrate Habits

```bash
# Start adding real data:
# - Add your actual tasks
# - Log your habits
# - Connect integrations
# - Watch insights emerge

# Engine learns about you as data grows
```

---

## Troubleshooting Setup

### Issue: "Database file is corrupted"

```bash
# Remove corrupted database
rm engine/db/self.db

# Recreate from schema
cd engine/db
sqlite3 self.db < schema_self.sql

# Re-populate with data
```

### Issue: "Module not found"

```bash
# Install required Python packages
pip3 install -r requirements.txt

# Required packages:
# - sqlite3 (built-in)
# - json (built-in)
# - datetime (built-in)
# - apscheduler (for scheduling)
# - faiss-cpu (for vector search, optional)
# - requests (for integrations)
```

### Issue: "Engine won't start"

```bash
# Check Python version
python3 --version
# Should be 3.10+

# Check database files exist
ls -la engine/db/*.db

# Check permissions
chmod 644 engine/db/*.db
chmod 755 engine/logs/

# Try starting with verbose logging
DEBUG=1 python3 start_engine.py
```

---

## Next Steps

After setup completes:

1. **Read the docs**
   - `docs/ARCHITECTURE.md` - How it all fits together
   - `docs/DATA_FLOWS.md` - How data moves
   - `docs/OPERATIONAL_HANDBOOK.md` - How to use it

2. **Populate your data**
   - Add your current tasks (command/tasks/)
   - Add your current events (command/calendar/)
   - Add your habits (02 - Self/Habits/)

3. **Connect integrations** (optional)
   - Google Calendar for scheduling
   - Todoist for task sync
   - GitHub for projects

4. **Let it run**
   - Engine learns from your data
   - Generates insights daily
   - Reports improve over time

---

## Quick Reference

### Check status
```bash
curl http://localhost:8000/health
```

### View latest logs
```bash
tail -20 logs/system.log
```

### Generate report
```bash
python3 cli.py generate --report daily
```

### View database
```bash
sqlite3 engine/db/tasks.db "SELECT * FROM tasks LIMIT 5;"
```

### Stop engine
```bash
python3 stop_engine.py
```

