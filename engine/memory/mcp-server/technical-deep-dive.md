# pi-memory: Complete Technical Summary

## One-Page Overview

**What**: A persistent memory system for AI agents that learns from sessions and injects learned knowledge into future conversations.

**Why**: Agents forget everything between sessions. pi-memory fixes this by automatically extracting preferences, corrections, and patterns from conversations and making them available next session.

**How**: 
1. At session start: Load memory from SQLite, inject as context
2. During session: Collect conversation messages
3. At session end: Use LLM to extract structured knowledge (facts + lessons)
4. Store with high confidence (≥0.8) to avoid noise
5. Repeat: Next session reads the enriched memory

**Tech Stack**: 
- SQLite (WAL mode) for persistence
- FTS5 for semantic search (fallback to LIKE)
- LLM for extraction (via pi SDK)
- Jaccard similarity for deduplication

---

## Database Tables Explained

### `semantic` — Learned Preferences & Patterns
```sql
key              TEXT PRIMARY KEY
value            TEXT
confidence       REAL (0.0-1.0)
source           TEXT (user | consolidation | correction)
created_at       TEXT
updated_at       TEXT
last_accessed    TEXT (for staleness tracking)
```

**Examples**:
- `pref.commit_style` → `"conventional commits"`
- `project.rosie.language` → `"Go"`
- `tool.editor` → `"vim with plugins"`

**Key Naming Convention**:
```
pref.*          — User preferences
project.<name>.*  — Project-specific patterns
tool.*          — Tool usage preferences
user.*          — User identity
```

### `lessons` — Learned Corrections & Validations
```sql
id               TEXT PRIMARY KEY (uuid/hash)
rule             TEXT
category         TEXT
source           TEXT (consolidation | user)
negative         INTEGER (0=validated, 1=avoid)
is_deleted       INTEGER (soft delete flag)
created_at       TEXT
```

**Examples**:
- `rule: "Use sed for vault inserts, not echo >>"`, `negative: 1` (correction)
- `rule: "Deploy via git push+webhook, not ssh exec"`, `negative: 0` (validated)

**Why `negative` field?** Distinguishes:
- `negative=1` → "DON'T do X" (learned from mistakes)
- `negative=0` → "DO X" (confirmed to work)

### `events` — Audit Log
```sql
id          INTEGER PRIMARY KEY AUTOINCREMENT
event_type  TEXT (store, update, delete, search)
memory_type TEXT (semantic | lesson)
memory_key  TEXT
details     TEXT
created_at  TEXT
```

Tracks provenance: which session added/updated/deleted what fact.

---

## Core Classes & Methods

### MemoryStore (store.ts)
```typescript
class MemoryStore {
  // SQLite connection
  private db: DatabaseSync
  private hasFTS5: boolean
  
  // Semantic facts
  setSemantic(key, value, confidence, source)
  getSemantic(key): SemanticEntry | undefined
  deleteSemantic(key): boolean
  listSemantic(prefix?, limit)
  searchSemantic(query, limit): SemanticEntry[]
  touchAccessed(keys)  // Update last_accessed timestamps
  
  // Lessons
  setLesson(rule, category, negative, source)
  listLessons(category?, limit)
  deleteLesson(id)
  
  // Utilities
  stats(): { semantic, lessons, events }
  close()
}
```

**Search Strategy**:
1. If FTS5 available: Use `bm25(fts5)` for ranking
2. If not: Fall back to substring matching (scored by term coverage)

### Injector (injector.ts)
```typescript
function buildContextBlock(
  store: MemoryStore,
  cwd?: string,
  prompt?: string,
  config?: InjectorConfig
): ContextBlock

// Returns:
// {
//   text: "<memory>\n• fact1\n• fact2\n... </memory>",
//   stats: { semantic: N, lessons: M }
// }
```

**Two Modes**:
- **Selective** (prompt provided): Search for relevant facts + filter lessons
- **Fallback** (no prompt): Dump top entries by prefix (backward compatibility)

**Context Cap**: 8KB max (prevents bloat in system prompt)

### Consolidator (consolidator.ts)
```typescript
function buildConsolidationPrompt(
  input: ConsolidationInput,
  currentFacts?,
  currentLessons?
): string

function parseConsolidationResponse(jsonText: string): ExtractedMemory

function applyExtracted(
  store: MemoryStore,
  extracted: ExtractedMemory,
  source: string
): { semantic: N, lessons: M }
```

**Consolidation Input**:
- `userMessages`: strings from user (one per message)
- `assistantMessages`: strings from assistant
- `cwd`: working directory (for project context)
- `sessionId`: session identifier (for audit)

**Consolidation Output**:
```json
{
  "semantic": [
    { "key": "pref.X", "value": "...", "confidence": 0.9 }
  ],
  "lessons": [
    { "rule": "...", "category": "X", "negative": true }
  ]
}
```

---

## Lifecycle Hooks (index.ts)

### Hook 1: `session_start`
```typescript
pi.on("session_start", async (event, ctx) => {
  sessionCwd = ctx.cwd
  resolvedDbPath = resolveDbPath(sessionCwd)
  store = new MemoryStore(resolvedDbPath)
  
  // Show stats in status bar
  const stats = store.stats()
  ctx.ui.setStatus("pi-memory", `Memory: ${stats.semantic} facts, ${stats.lessons} lessons`)
})
```

### Hook 2: `before_agent_start`
```typescript
pi.on("before_agent_start", async (event, ctx) => {
  const { prompt, cwd } = event
  
  // Build context block
  const block = buildContextBlock(store, cwd, prompt, injectorConfig)
  
  // Inject as <memory> section in system prompt
  return { systemPrompt: `${block.text}\n\n${originalSystemPrompt}` }
})
```

### Hook 3: `agent_end`
```typescript
pi.on("agent_end", async (event, ctx) => {
  // Collect messages for consolidation
  for (const msg of event.messages) {
    if (msg.role === "user") pendingUserMessages.push(extractText(msg.content))
    if (msg.role === "assistant") pendingAssistantMessages.push(extractText(msg.content))
  }
})
```

### Hook 4: `session_shutdown`
```typescript
pi.on("session_shutdown", async (event, ctx) => {
  // Only consolidate if enough messages
  if (pendingUserMessages.length < 3) return
  
  // Extract knowledge from session
  const extracted = await runConsolidation({
    userMessages: pendingUserMessages,
    assistantMessages: pendingAssistantMessages,
    cwd: sessionCwd,
    sessionId
  })
  
  // Apply to store (dedup + confidence check)
  applyExtracted(store, extracted, `consolidation:${sessionId}`)
  
  // Close connection
  store.close()
})
```

---

## Tools Exposed (MCP)

### 1. `memory_search(query: string)`
```
Search semantic memory by keyword.
Returns: top 10 facts + confidence scores
```

### 2. `memory_remember(key: string, value: string, confidence?: number)`
```
Manually add/update a fact.
Useful for explicit corrections or user-provided preferences.
```

### 3. `memory_forget(key: string)`
```
Delete a fact.
Triggers audit log entry.
```

### 4. `memory_lessons(category?: string)`
```
List learned corrections.
If category: filter to "vault", "security", "git", etc.
```

### 5. `memory_stats()`
```
Show { semantic: N, lessons: M, events: K }
Useful for debugging memory state.
```

---

## Deduplication Strategy

### Exact Deduplication (Lessons)
```typescript
// If same rule already exists, skip
if (existing.rule === newLesson.rule) {
  skip(newLesson)
}
```

### Similarity Deduplication (Jaccard)
```typescript
function jaccardSimilarity(a: string, b: string): number {
  const tokensA = new Set(a.toLowerCase().split(/\s+/))
  const tokensB = new Set(b.toLowerCase().split(/\s+/))
  
  const intersection = [...tokensA].filter(t => tokensB.has(t)).length
  const union = tokensA.size + tokensB.size - intersection
  
  return intersection / union
}

// If similar (≥0.7 threshold), skip
if (jaccardSimilarity(newLesson.rule, existing.rule) >= 0.7) {
  skip(newLesson)
}
```

**Why?** Captures variations like:
- "Use sed to insert, don't use echo >>"
- "Never use echo >> for vault notes, use sed instead"
→ Same lesson, different phrasing → deduplicate

---

## Path Resolution (Multi-Project Support)

### Priority Order (Highest to Lowest)
```
1. project/.pi/settings.json::pi-memory.localPath
   → {localPath}/memory.db

2. project/.pi/settings.json::pi-total-recall.localPath (cascade)
   → {localPath}/memory/memory.db

3. Global default
   → ~/.pi/memory/memory.db
```

### Example Config
```json
{
  "cwd": "/users/me/projects/myapp",
  ".pi/settings.json": {
    "pi-memory": {
      "localPath": ".pi/memory"
    }
  }
}

// Resolves to: /users/me/projects/myapp/.pi/memory/memory.db
```

---

## Consolidation Prompt (Key Insight)

The LLM is given explicit instructions on what to extract & what NOT to extract:

### ✅ DO Extract
- Preferences (commit style, testing approach, documentation habits)
- Project patterns (languages, frameworks, DI tools)
- Tool preferences (sed vs echo, vim vs nano)
- Corrections (things user corrected you on)
- Validated approaches (things user confirmed work)

### ❌ DON'T Extract
- Code patterns, file paths, project structure (grep/git are authoritative)
- Git history, blame info
- Exact commands that worked once (unless they encode a pattern)
- File contents or code snippets
- Ephemeral task details or in-progress work
- Activity summaries ("we worked on X today")
- Anything already documented in config files (AGENTS.md, etc.)

**Why?** Avoids polluting memory with derivable or ephemeral information.

---

## Injection Modes

### Mode 1: "all" (Default)
```
Every session gets all lessons injected.
Pro: Simple, backward compatible
Con: Can waste context if you have 50+ lessons
```

### Mode 2: "selective" (Opt-in)
```
Filter lessons by relevance:
1. FTS search on user's first message
2. Category inference (keywords trigger categories)
3. Always include "general" lessons

Result: ~5-10 most relevant lessons instead of all 50
Pro: Preserves context for reasoning
Con: May miss edge-case lessons
```

**Config**:
```json
{
  "memory": {
    "lessonInjection": "selective"
  }
}
```

---

## SQLite Pragmas (Why They Matter)

```sql
PRAGMA journal_mode = WAL
  → Write-Ahead Logging
  → Allows concurrent reads while writing
  → Faster commits

PRAGMA busy_timeout = 5000
  → Wait up to 5 seconds if database is locked
  → Prevents spurious failures under contention

PRAGMA foreign_keys = ON
  → Enforce referential integrity
  → Prevent orphaned lesson records if semantic facts deleted

PRAGMA cache_size = -64000
  → 64MB in-memory cache
  → Speeds up searches
```

---

## Bootstrap (One-Time Migration)

If user has session-search index, bootstrap historical sessions:

```bash
npx tsx bootstrap.ts --limit 100 --batch-size 20
```

**What it does**:
1. Read `~/.pi/session-search/index/session-index.json`
2. Take 100 most recent sessions
3. Batch them (20 per batch)
4. For each batch: consolidate summaries via LLM
5. Apply extracted facts, deduplicating across batches
6. Result: memory seeded with historical patterns

**Timing**: 2-5 hours for 100+ sessions (depends on LLM latency)

---

## Performance Characteristics

### Storage
- **Database size**: ~1MB per 1000 facts + 100 lessons (with events log)
- **Growth**: ~100 facts + 20 lessons per 50 sessions (rough estimate)

### Lookup Speed
- **FTS5 search**: <50ms (typical)
- **LIKE fallback**: <200ms (typical)
- **Memory injection**: <5ms

### LLM Cost
- **Per session**: ~1000-2000 tokens (depends on message volume)
- **Cost**: $0.01-0.05 per session (with gpt-4o-mini)
- **Frequency**: Only if ≥3 user messages in session

---

## What Makes It Special

### vs. Session History Search
- Session-search: *What did I do?* (imperative history)
- pi-memory: *What did I learn?* (declarative knowledge)

### vs. Document Search
- Document search: *What exists?* (current state)
- pi-memory: *What's my preference?* (user patterns)

### vs. RAG/Knowledge Base
- RAG: External knowledge (wikis, docs)
- pi-memory: Internal knowledge (user patterns, corrections)

**Combination**: session-search + pi-knowledge-search + pi-memory = complete context stack (pi-total-recall)

---

## Potential Pitfalls & Mitigations

### Pitfall 1: Memory Pollution (Too Much Noise)
**Solution**: High confidence threshold (≥0.8), smart deduplication

### Pitfall 2: Stale Memory (Old Preferences)
**Solution**: Track `last_accessed` timestamps, allow staleness decay (future)

### Pitfall 3: Context Waste (Too Many Lessons)
**Solution**: Selective injection mode (filter by relevance)

### Pitfall 4: Multi-Project Confusion
**Solution**: Path resolution cascade (isolate project memory)

### Pitfall 5: Consolidation Failures (LLM unavailable)
**Solution**: Graceful fallback, audit log shows what failed

---

## Extensibility Points

### Custom Extraction
Replace consolidation prompt with domain-specific instructions:
```typescript
const CUSTOM_PROMPT = `
Extract from conversation:
1. Machine learning architectures used
2. Hyperparameter choices
3. Dataset characteristics
...
`;
```

### Custom Injection
Filter lessons beyond FTS:
```typescript
const customFiltered = lessons.filter(
  l => l.category === getUserSpecialty(user)
);
```

### Custom Storage
Replace SQLite with PostgreSQL for team shared memory:
```typescript
class PgMemoryStore extends MemoryStore {
  // Override connection & queries
}
```

### Analytics & Insights
Query `events` table to understand learning patterns:
```sql
SELECT 
  event_type,
  memory_type,
  COUNT(*) as count,
  DATE(created_at) as date
FROM events
GROUP BY event_type, memory_type, DATE(created_at);
```

---

## Key Takeaway

**pi-memory is "simple yet powerful" because it**:
1. Uses only SQLite (no external services)
2. Automates the entire learning cycle (no manual intervention)
3. Handles deduplication intelligently (Jaccard similarity)
4. Injects selectively (doesn't waste context)
5. Is debuggable & extensible (audit log + tools)
6. Composes with other knowledge sources (session-search, knowledge-search)

**The secret**: LLM-based extraction (not brittle rules) + high confidence threshold (not noise) + path resolution (not single-project thinking).

