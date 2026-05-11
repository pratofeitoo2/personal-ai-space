> **⚠️ Aspirational Design Document**
> The 3-tier memory model with TTL-based caching described below is **not yet fully implemented**.
> The current implementation is simpler: SQLite-persisted facts and lessons with MCP bridge.
> This document serves as a specification for future development.

# Memory Systems Architecture

## Three-Tier Memory Model

```
┌─────────────────────────────────────────┐
│ SHORT-TERM (Session)                    │
│ In-memory: 3600s TTL, 512MB max         │
│ Speed: <1ms access                      │
│ Use: Current conversation context       │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ MEDIUM-TERM (Recent)                    │
│ Cache layer: 7 days TTL                 │
│ Speed: <10ms access                     │
│ Use: Weekly patterns, recent history    │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ LONG-TERM (Persistent)                  │
│ SQLite: Full retention                  │
│ Speed: 50-500ms access                  │
│ Use: Historical data, archival          │
└─────────────────────────────────────────┘
```

---

## 1. Short-Term Memory (Session)

**Storage**: In-memory dictionary (Python dict)  
**TTL**: 3600 seconds (1 hour)  
**Max Size**: 512 MB  
**Retention**: Current session only

### What Gets Stored
- Current user context (profile loaded)
- Active task being discussed
- Recent message history (last 10)
- Temporary calculations
- In-flight requests

### Example Session Memory

```json
{
  "session_id": "sess_abc123",
  "user_context": {
    "name": "Paulo",
    "timezone": "America/Sao_Paulo",
    "current_focus": "engine_build",
    "mood": "productive"
  },
  "active_task": {
    "id": "task_001",
    "title": "Complete engine setup",
    "priority": "critical"
  },
  "message_history": [
    {
      "timestamp": "2026-05-06T08:00:00Z",
      "agent": "context-manager",
      "content": "Good morning"
    }
  ],
  "in_flight": {
    "analysis_request_id": "req_xyz789",
    "status": "processing"
  }
}
```

### Access Pattern
```
Query short-term → Hit (95%+ success)
  ↓
Cache result for future queries
  ↓
Invalidate on update
  ↓
Fall back to cache if expired
```

---

## 2. Medium-Term Memory (Cache)

**Storage**: SQLite (cache.db)  
**TTL**: 604800 seconds (7 days)  
**Retention**: Last 7 days of activity  
**Use**: Pattern detection, recent history

### What Gets Stored

```sql
-- Cache Schema
CREATE TABLE cache_interactions (
  key TEXT PRIMARY KEY,
  data TEXT,
  timestamp DATETIME,
  ttl_seconds INTEGER,
  access_count INTEGER
);

-- Examples:
key: "week_task_completion_rate"
data: "{ rate: 0.94, completed: 23, total: 25 }"
ttl: 604800

key: "recent_habits_week_4"
data: "{ completed: 22, target: 24, streak: 5 }"
ttl: 604800

key: "daily_analytics_2026-05-06"
data: "{ insights: [...], anomalies: [...] }"
ttl: 86400
```

### Cache Eviction Policy
- LRU (Least Recently Used) when full
- TTL-based automatic purge
- Manual clear on sync boundaries

### Access Pattern
```
Query cache → Miss
  ↓
Compute from long-term
  ↓
Store in cache (set TTL)
  ↓
Return result
  ↓
Next query → Hit (fast response)
```

---

## 3. Long-Term Memory (Persistent)

**Storage**: SQLite databases  
**Retention**: Full history  
**Databases**:
- `memories.db`: Interactions, context logs
- `self.db`: Profile, habits, traits
- `tasks.db`: Tasks, projects, calendar
- `knowledge.db`: Articles, notes, references

### memories.db Structure

```sql
-- Interactions log (audit trail)
interactions (
  id, timestamp, agent_id, action,
  input_data, output_data, duration_ms, status
)
-- Access: ~234ms per query (1000 rows/week)

-- Context snapshots (for later replay)
context_window (
  id, session_id, timestamp, content,
  embedding, relevance_score, expires_at
)
-- Access: ~145ms per query

-- Agent memory (persistent state)
agent_memory (
  id, agent_id, key, value, ttl_seconds
)
-- Access: <50ms per query (indexed by agent_id)
```

### Indexing Strategy

**Primary Indexes:**
```sql
CREATE INDEX idx_interactions_agent ON interactions(agent_id);
CREATE INDEX idx_interactions_timestamp ON interactions(timestamp DESC);
CREATE INDEX idx_context_session ON context_window(session_id);
```

**Access Pattern:**
```
Recent queries (< 7 days):
  ↓
Check cache first (hit rate ~70%)
  ↓
If miss, query long-term (add to cache)

Historical queries (> 7 days):
  ↓
Query long-term directly
  ↓
Stream results (don't cache)
```

---

## 4. Vector Memory (Semantic Search)

**Storage**: FAISS (or Pinecone)  
**Embedding Model**: all-MiniLM-L6-v2 (384 dim)  
**Index Size**: ~50MB per 10k documents

### What Gets Indexed

```
Articles → Embeddings
Notes → Embeddings
Task descriptions → Embeddings
Email subjects → Embeddings
```

### Example Vector Query

```
User asks: "What article covered context windows?"
  ↓
Embed query: "context windows" → [0.23, -0.15, ...]
  ↓
Search vector DB (FAISS)
  ↓
Return top 3 similar articles:
  1. "Context Length in LLMs" (0.89 similarity)
  2. "Token Optimization" (0.76 similarity)
  3. "Memory Architecture" (0.71 similarity)
```

### Sync with Long-Term

```
New article added to knowledge.db
  ↓
Extract text
  ↓
Generate embedding
  ↓
Add to FAISS index
  ↓
Log to vector_index table
```

---

## Memory Coherence

### Write Consistency
```
Write to short-term
  ↓
Queue to cache (medium-term)
  ↓
Batch write to long-term (every 5 min)
  ↓
Invalidate cache entries
  ↓
Update vector index (async)
```

### Read Priority
```
Query → Short-term (1ms)
     → Cache (10ms)
     → Long-term (100ms)
     → Vector search (100ms)
```

### Conflicts
```
Same key updated in short-term & long-term
  ↓
Use timestamp to determine winner
  ↓
Merge if non-overlapping changes
  ↓
Log conflict to audit.log
```

---

## Garbage Collection

### Short-Term (Every 5 minutes)
```
For each entry in memory:
  if created_time < now - 3600s:
    remove from memory
  if size_bytes > 512MB:
    evict oldest 10% (LRU)
```

### Medium-Term (Daily at 02:00)
```
For each entry in cache:
  if created_time < now - ttl_seconds:
    delete from cache.db
```

### Long-Term (Monthly on 1st at 03:00)
```
For each database:
  VACUUM (reclaim space)
  Reindex tables
  Analyze query plans
  Backup to archive/
```

---

## Memory Monitoring

### Metrics

```json
{
  "timestamp": "2026-05-06T08:15:00Z",
  "memory_usage": {
    "short_term_mb": 234,
    "cache_mb": 156,
    "total_mb": 390
  },
  "hit_rates": {
    "short_term": 0.95,
    "cache": 0.72,
    "long_term": 0.28
  },
  "database_sizes": {
    "memories_mb": 12.4,
    "self_mb": 2.1,
    "tasks_mb": 3.8,
    "knowledge_mb": 45.2
  },
  "query_performance": {
    "avg_short_term_ms": 0.3,
    "avg_cache_ms": 8.2,
    "avg_long_term_ms": 145,
    "p95_long_term_ms": 523
  }
}
```

### Alerts
- Short-term > 400MB → Evict aggressively
- Cache hit rate < 50% → Adjust TTL
- Query > 1s → Investigate indexes
- Database > 500MB → Archive older data

---

## Memory Lifecycle Example

```
08:00:00 - User asks "What's my task for today?"
  ↓
Short-term: Check session memory (miss)
Cache: Check weekly cache (miss)
Long-term: Query tasks.db (hit: task_001)
  ↓
Store in short-term (user context)
Store in cache (today's tasks)
  ↓
08:15:00 - Same question
  ↓
Short-term: Hit! Return immediately
  ↓
08:30:00 - New task created
  ↓
Update short-term (user sees immediately)
Queue update to cache/long-term
  ↓
09:00:00 - Batch sync completes
  ↓
Long-term written
Cache updated
Vector index refreshed
```

