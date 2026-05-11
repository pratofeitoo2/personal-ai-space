> **⚠️ Aspirational Design Document**
> The integrations described below (Google Calendar, Gmail, Todoist, GitHub) are **not yet implemented**.
> This document serves as a specification for future development.
> Currently active integrations: mail-mcp (email). mcp-whatsapp has been moved to STANDBY — see `engine/docs/STANDBY.md`.

# Integration Architecture

## Supported Integrations

### 1. Google Calendar
**Purpose**: Sync events, block time, detect availability  
**Sync**: Bidirectional every 30 minutes  
**Scope**: Read/Write events

```json
{
  "id": "integration_google_calendar",
  "service": "google",
  "type": "calendar",
  "enabled": false,
  "config": {
    "sync_interval_minutes": 30,
    "direction": "bidirectional",
    "calendar_ids": ["primary"],
    "categories": ["work", "personal", "health"]
  },
  "auth": {
    "type": "oauth2",
    "scopes": ["calendar.read", "calendar.write"],
    "credentials_path": "vault/credentials/google_oauth.json"
  },
  "mapping": {
    "event_to_task": true,
    "auto_create_blocks": true,
    "availability_analysis": true
  }
}
```

**Data Flow:**
```
Google Calendar Events
    ↓
Normalize to internal format
    ↓
Check for conflicts
    ↓
Upsert to tasks.db calendar_events table
    ↓
Sync to self profile
    ↓
Trigger availability analysis
```

---

### 2. Gmail
**Purpose**: Monitor inbox, extract action items, track important emails  
**Sync**: One-way pull every 30 minutes  
**Scope**: Read-only

```json
{
  "id": "integration_gmail",
  "service": "google",
  "type": "email",
  "enabled": false,
  "config": {
    "sync_interval_minutes": 30,
    "inbox_monitoring": true,
    "action_extraction": true,
    "vip_contacts": ["manager", "key_partners"]
  },
  "auth": {
    "type": "oauth2",
    "scopes": ["gmail.read"],
    "credentials_path": "vault/credentials/google_oauth.json"
  },
  "rules": {
    "auto_task_creation": {
      "enabled": true,
      "keywords": ["action required", "todo", "please send"]
    },
    "priority_labeling": {
      "enabled": true,
      "vip_labels": ["important", "urgent"]
    }
  }
}
```

**Data Flow:**
```
Gmail Inbox
    ↓
Query for new/unread emails
    ↓
Extract metadata (from, subject, date)
    ↓
Analyze for action items
    ↓
If action detected → Create task in tasks.db
    ↓
Flag VIP senders → Mark as high priority
    ↓
Log in memories.db
```

---

### 3. Todoist (or Similar)
**Purpose**: Sync task management, avoid duplicate tracking  
**Sync**: Bidirectional every 60 minutes  
**Scope**: Read/Write tasks

```json
{
  "id": "integration_todoist",
  "service": "todoist",
  "type": "task_management",
  "enabled": false,
  "config": {
    "sync_interval_minutes": 60,
    "direction": "bidirectional",
    "projects_to_sync": ["inbox", "personal", "work"]
  },
  "auth": {
    "type": "api_token",
    "credentials_path": "vault/credentials/todoist_token.json"
  },
  "conflict_resolution": "engine_wins"
}
```

**Data Flow:**
```
Todoist Tasks
    ↓
Query API for updates since last sync
    ↓
Compare with tasks.db
    ↓
For each task:
  - New in Todoist → Import to engine
  - Changed in Todoist → Update in engine
  - Changed in engine → Push to Todoist
  - Deleted → Sync deletion
    ↓
Update sync timestamp
    ↓
Log sync results
```

---

### 4. GitHub
**Purpose**: Track projects, issues, contributions  
**Sync**: One-way pull every 120 minutes  
**Scope**: Read-only

```json
{
  "id": "integration_github",
  "service": "github",
  "type": "project_tracking",
  "enabled": false,
  "config": {
    "sync_interval_minutes": 120,
    "repositories": ["personal-ai-powerhouse"],
    "track_issues": true,
    "track_prs": true,
    "track_contributions": true
  },
  "auth": {
    "type": "personal_access_token",
    "credentials_path": "vault/credentials/github_token.json"
  }
}
```

**Data Flow:**
```
GitHub Repositories
    ↓
Query for:
  - Open issues
  - Pull requests
  - Recent commits
  - Discussions
    ↓
Map to internal project structure
    ↓
Sync to knowledge.db projects table
    ↓
Extract metrics (velocity, contribution)
    ↓
Update self profile insights
```

---

### 5. Fitness Apps (Fitbit, Strava)
**Purpose**: Track health metrics, identify patterns  
**Sync**: One-way pull daily (1440 min)  
**Scope**: Read-only

```json
{
  "id": "integration_fitness",
  "service": "fitbit",
  "type": "health_tracking",
  "enabled": false,
  "config": {
    "sync_interval_minutes": 1440,
    "metrics": ["steps", "heart_rate", "sleep", "calories", "workout"]
  },
  "auth": {
    "type": "oauth2",
    "credentials_path": "vault/credentials/fitbit_oauth.json"
  },
  "analysis": {
    "correlation_with_productivity": true,
    "sleep_impact_analysis": true,
    "exercise_habit_tracking": true
  }
}
```

**Data Flow:**
```
Fitness Platform
    ↓
Query daily summary
    ↓
Parse metrics
    ↓
Store in self.db health_metrics table
    ↓
Correlate with:
  - Task completion rates
  - Deep work quality
  - Habit maintenance
    ↓
Generate health insights
```

---

## Integration Framework

### Universal Integration Flow

```
Step 1: Authentication
  └─ Load credentials from vault
  └─ Refresh tokens if needed
  └─ Handle auth failures

Step 2: Query External System
  └─ Build request with parameters
  └─ Execute with timeout
  └─ Parse response

Step 3: Normalize Data
  └─ Map external format to internal
  └─ Validate schema
  └─ Handle missing fields

Step 4: Conflict Resolution
  ├─ Bidirectional: Compare timestamps
  ├─ One-way: Simple insert/update
  └─ Custom logic for specific conflicts

Step 5: Persist
  └─ Transaction to database
  └─ Update sync metadata
  └─ Log sync event

Step 6: Analysis
  └─ Extract insights
  └─ Update correlations
  └─ Trigger dependent agents

Step 7: Error Handling
  └─ Retry logic (exponential backoff)
  └─ Graceful degradation
  └─ Alert on persistent failures
```

---

## Integration Management

### Enable Integration

```json
{
  "action": "enable_integration",
  "integration_id": "integration_google_calendar",
  "config_overrides": {}
}
```

### Disable Integration

```json
{
  "action": "disable_integration",
  "integration_id": "integration_google_calendar",
  "cleanup": "purge_unread_data"
}
```

### Check Sync Status

```json
{
  "query": "integration_status",
  "results": {
    "google_calendar": {
      "enabled": true,
      "last_sync": "2026-05-06T07:30:00Z",
      "next_sync": "2026-05-06T08:00:00Z",
      "items_synced": 47,
      "errors": 0,
      "status": "healthy"
    },
    "github": {
      "enabled": true,
      "last_sync": "2026-05-06T03:45:00Z",
      "next_sync": "2026-05-06T07:45:00Z",
      "items_synced": 12,
      "errors": 0,
      "status": "healthy"
    }
  }
}
```

---

## Sync Scheduling

```
08:00 - Google Calendar sync
08:30 - Gmail sync
09:00 - Todoist sync
12:00 - Google Calendar sync
14:00 - Gmail sync
16:00 - Todoist sync
20:00 - Google Calendar sync
20:30 - Gmail sync
22:00 - Todoist sync
00:00 - GitHub sync
```

**Off-peak sync**: 23:00 - 07:00 (staggered to avoid load)

---

## Data Ownership & Conflicts

**Principle**: Engine of truth, bidirectional sync attempts to keep systems in sync

**Conflict Resolution:**
- **Timestamp-based**: Newest wins
- **Engine preference**: Integrations → Engine (one-way systems)
- **User choice**: Manual resolution for complex conflicts

**Example Conflict:**
```
Task in engine: "Complete feature" (updated 14:30)
Task in Todoist: "Complete feature" (updated 14:15)
Resolution: Engine version kept, Todoist updated
```

---

## Testing Integrations

### Sandbox Mode

```json
{
  "integration": "google_calendar",
  "mode": "sandbox",
  "config": {
    "fetch_limit": 5,
    "sync_enabled": false,
    "read_only": true
  }
}
```

### Health Check

```
Google Calendar: ✓ Connected, 47 events
Gmail: ✓ Connected, 2,349 emails
Todoist: ✓ Connected, 34 tasks
GitHub: ✓ Connected, 5 repos
Fitbit: ✗ Auth expired - re-authenticate
```

---

## Adding New Integrations

**Process:**
1. Define integration config (json)
2. Build credentials handler
3. Implement API client
4. Create data normalizer
5. Add conflict resolver
6. Create test suite
7. Schedule sync job
8. Document in this file

