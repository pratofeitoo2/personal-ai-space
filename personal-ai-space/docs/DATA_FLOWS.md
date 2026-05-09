> **⚠️ Aspirational Design Document**
> The ingestion, processing, and routing pipelines described below are **not yet fully implemented**.
> Current capabilities: file intake via watcher → process_intake.py, basic agent routing via engine.
> This document serves as a specification for future development.

# Data Flow Architecture

## 1. Ingestion Flow

```
User Input
    ↓
Capture (inbox, import, API)
    ↓
Normalize (standardize format, clean data)
    ↓
Classify (categorize, assign type)
    ↓
Validate (schema check, constraint check)
    ↓
Route (determine destination)
    ↓
Store (task.db, self.db, knowledge.db)
    ↓
Index (memories.db, vector DB)
```

**Handlers by Type:**
- Task input → tasks.db + task_coordinator
- Habit log → self.db + habit_tracker
- Article → knowledge.db + knowledge_indexer
- Event → tasks.db + calendar, reminder_system
- Note → knowledge.db + notes_indexer

---

## 2. Processing Flow

```
Raw Data (stored in DB)
    ↓
Trigger (scheduled, event-based, manual)
    ↓
Extract Features
    ├─ Habit patterns (frequency, streaks, correlations)
    ├─ Task metrics (velocity, completion rate, estimate accuracy)
    ├─ Time allocation (calendar analysis)
    └─ Knowledge usage (relevance, citations)
    ↓
Aggregate (combine across time periods)
    ├─ Weekly patterns
    ├─ Monthly trends
    └─ Yearly analysis
    ↓
Analyze (detect patterns, anomalies)
    ├─ Clustering (group similar behaviors)
    ├─ Regression (predict trends)
    ├─ Anomaly detection (flag unusual)
    └─ Correlation (find relationships)
    ↓
Generate Insights
    ├─ Recommendations
    ├─ Alerts
    ├─ Summaries
    └─ Visualizations
    ↓
Store Results → insights table in self.db
```

**Processing Triggers:**
- `daily_analysis` → 08:00 each morning
- `weekly_review` → Friday 18:00
- `monthly_analysis` → First Monday 09:00
- `on_habit_change` → Immediate
- `anomaly_detected` → Immediate alert

---

## 3. Reporting Flow

```
Report Request (scheduled or manual)
    ↓
Determine Scope (daily, weekly, monthly, custom)
    ↓
Query Databases
    ├─ tasks.db: Task metrics, completions
    ├─ self.db: Habits, traits, needs
    ├─ memories.db: Interactions, patterns
    └─ knowledge.db: Content stats
    ↓
Transform Data
    ├─ Aggregate metrics
    ├─ Calculate KPIs
    ├─ Format for display
    └─ Generate visualizations
    ↓
Apply Templates
    ├─ Daily digest template
    ├─ Weekly review template
    ├─ Monthly analysis template
    └─ Custom templates
    ↓
Output
    ├─ JSON (programmatic)
    ├─ Markdown (readable)
    ├─ HTML (web view)
    └─ PDF (shareable)
```

**Report Types:**
- **Daily Digest**: Tasks today, habits, key metrics (2 min read)
- **Weekly Review**: Week summary, blockers, wins, next week preview
- **Monthly Analysis**: Trends, growth, patterns, goals progress
- **Custom Reports**: On-demand analysis for any metric

---

## 4. Integration Flow

```
External System
    ↓
Query / Fetch Data
    ├─ Google Calendar: Fetch events
    ├─ Todoist: Sync tasks
    ├─ GitHub: Fetch projects/issues
    └─ Fitness Apps: Get health data
    ↓
Transform
    └─ Map to internal schema
    ↓
Upsert to DB
    ├─ Check for duplicates
    ├─ Update existing
    └─ Insert new
    ↓
Sync to Self Profile
    └─ Aggregate into insights
    ↓
Log Integration Event
    └─ Track sync status, issues
```

**Integration Schedule:**
- Google Calendar: Every 30 minutes
- Email: Every 30 minutes
- Todoist: Every 60 minutes
- GitHub: Every 120 minutes
- Fitness: Every 1440 minutes (daily)

---

## 5. Memory Management Flow

```
Data arrives
    ↓
Short-term (Current session)
    └─ Stored in-memory (3600s TTL)
    └─ Fast access, limited size (512 MB)
    ↓
Medium-term (Last 7 days)
    └─ Cache layer (604800s TTL)
    └─ SQLite cache.db
    ↓
Long-term (Persistent)
    └─ SQLite databases
    └─ Full retention
    ↓
Vector (Semantic search)
    └─ Embeddings indexed
    └─ FAISS or similar
    └─ For similarity search
```

---

## Error Handling Flows

### Retry with Backoff (Reminders, Integrations)
```
Operation fails
    ↓
Log error
    ↓
Wait (1s base * 2^attempt)
    ↓
Retry (up to 3 times)
    ↓
If still failing → Alert user
```

### Fallback to Defaults (Context Manager)
```
Cannot load profile
    ↓
Use cached version
    ↓
Log warning
    ↓
Continue with degraded function
```

### Graceful Degradation (Insights)
```
Analysis incomplete
    ↓
Return partial results
    ↓
Mark as incomplete in report
    ↓
Continue to next analysis
```

---

## Data Consistency

**Write Consistency:**
- Transactions across related tables
- Duplicate detection before insert
- Schema validation on every write

**Read Consistency:**
- Time-based snapshots
- Versioning of critical data
- Audit trail for modifications

