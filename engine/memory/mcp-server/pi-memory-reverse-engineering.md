# pi-memory Reverse Engineering Report

## Executive Summary

**Package**: `@samfp/pi-memory` v1.0.4 (by Sam Foy)
**Repository**: https://github.com/samfoy/pi-memory
**Purpose**: Persistent memory extension for the pi coding agent that learns corrections, preferences, and patterns from sessions and automatically injects relevant memory into future conversations.

**Why it's useful**: It turns ephemeral session conversations into permanent, reusable knowledge that makes the agent smarter with every session.

---

## Architecture Overview

### Core Concept: Three-Phase Lifecycle

```
Session Start
    ↓
[1. INJECT] Load memory → inject into system prompt
    ↓
Session Running
    ↓
[2. COLLECT] Queue messages for consolidation
    ↓
Session End
    ↓
[3. CONSOLIDATE] Extract structured knowledge (via LLM) → store
    ↓
[REUSE] Memory injected in next session
```

### Key Innovation: **Semantic Memory + Lessons**

Unlike simple keystroke recording or session replay, pi-memory:
- **Extracts high-confidence facts** ("pref.commit_style" → "conventional commits")
- **Learns from corrections** ("don't use echo >>, use sed instead")
- **Deduplicates with Jaccard similarity** (≥0.7 threshold)
- **Injects selectively** by relevance (can filter lessons to reduce context waste)

---

## Database Schema (SQLite)

### Table 1: `semantic` — Key-Value Facts
```sql
CREATE TABLE semantic (
  key TEXT PRIMARY KEY,                        -- e.g., "pref.commit_style"
  value TEXT NOT NULL,                         -- e.g., "conventional commits"
  confidence REAL NOT NULL DEFAULT 0.8,        -- 0.0–1.0 score from LLM extraction
  source TEXT NOT NULL DEFAULT 'consolidation', -- 'user' | 'consolidation' | 'correction'
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now')),
  last_accessed TEXT                           -- tracks recency
);
```

**Key Prefixes** (convention):
- `pref.*` — User preferences (coding style, workflow habits, tool choices)
- `project.<name>.*` — Project-specific patterns (languages, frameworks, architecture)
- `tool.*` — Tool usage preferences
- `user.*` — User identity (timezone, location, role)

---

### Table 2: `lessons` — Learned Corrections
```sql
CREATE TABLE lessons (
  id TEXT PRIMARY KEY,                        -- UUID or hash of rule
  rule TEXT NOT NULL,                         -- e.g., "Use sed to insert, not echo >>"
  category TEXT NOT NULL DEFAULT 'general',   -- e.g., "vault", "git", "devops"
  source TEXT NOT NULL DEFAULT 'consolidation', -- where it came from
  negative INTEGER NOT NULL DEFAULT 0,        -- 1 = "avoid this", 0 = "validated approach"
  is_deleted INTEGER NOT NULL DEFAULT 0,      -- soft delete flag
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

**Why negative flag?** Distinguishes:
- `negative=1`: "DON'T use echo >>..." (correction from mistake)
- `negative=0`: "Validated approach: use sed for..." (confirmed to work)

---

### Table 3: `events` — Audit Log
```sql
CREATE TABLE events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_type TEXT NOT NULL,                   -- 'store', 'update', 'delete', 'search'
  memory_type TEXT NOT NULL,                  -- 'semantic' | 'lesson'
  memory_key TEXT NOT NULL,                   -- the key or lesson ID
  details TEXT NOT NULL DEFAULT '',           -- context (e.g., source session)
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

---

### Optional: FTS5 Virtual Tables (for fast search)
```sql
-- Full-text search on facts (if FTS5 available)
CREATE VIRTUAL TABLE fact_search USING fts5(key, value);

-- Full-text search on lessons
CREATE VIRTUAL TABLE lesson_search USING fts5(rule, category);
```

**Fallback**: If FTS5 unavailable, uses simple LIKE queries.

---

## File Structure

```
src/
├── index.ts              # Main extension entry point (lifecycle hooks, tools)
├── store.ts              # SQLite wrapper (CRUD operations)
├── injector.ts           # Builds context block for injection
├── consolidator.ts       # LLM consolidation prompt & parsing
├── bootstrap.ts          # One-time migration from session-search index
└── *.test.ts             # Tests (coverage for store, injector, localpath resolution)
```

---

## Core Components

### 1. **MemoryStore** (`store.ts`)
The SQLite backend. Exposes CRUD + search operations.

**Key Methods**:
```typescript
class MemoryStore {
  constructor(dbPath: string)         // Opens DB, runs migrations
  
  // CRUD for semantic facts
  setSemantic(key, value, confidence) // Upsert with confidence score
  getSemantic(key)                    // Retrieve single fact
  searchSemantic(query, limit)        // FTS or LIKE search
  deleteSemantic(key)                 // Remove fact
  listSemantic(prefix?)               // List by key prefix
  
  // CRUD for lessons
  setLesson(rule, category, negative) // Store learned correction
  listLessons(category?, limit)       // List all or by category
  deleteLesson(id)                    // Soft-delete
  
  // Utilities
  stats()                             // { semantic: N, lessons: N, events: N }
  close()                             // Graceful shutdown
  touchAccessed(keys)                 // Update last_accessed timestamps
  
  // FTS search (if available)
  searchFTS(query, table)             // Fast semantic/lesson search
}
```

**SQLite Pragmas**:
- `PRAGMA journal_mode = WAL` — Write-Ahead Logging (allows concurrent reads)
- `PRAGMA busy_timeout = 5000` — Wait up to 5s for locks
- `PRAGMA foreign_keys = ON` — Enforce referential integrity

---

### 2. **Injector** (`injector.ts`)
Builds a context block for system prompt injection.

**Two Modes**:

#### Mode A: Selective Injection (Recommended)
```typescript
buildContextBlock(store, cwd, prompt, config)
```
When `prompt` (user's first message) is provided:
1. **Search semantic facts** relevant to prompt (top 15)
2. **Search project context** if cwd provided (slug-based)
3. **Filter lessons** by relevance (FTS search on rule text, category inference)
4. **Result**: Only inject facts & lessons likely to be useful

**Category Inference**:
- "pentest" in prompt → pull `bug-bounty` lessons
- "blog post" → pull `writing` lessons
- "deploy" → pull `devops` lessons

**Cap**: Max 8KB context (prevent bloat in system prompt)

#### Mode B: Fallback (No Prompt)
```typescript
buildFallbackBlock(store, cwd)
```
- Dump top N facts by key prefix
- List all lessons (old behavior)
- Used when prompt unavailable or FTS disabled

---

### 3. **Consolidator** (`consolidator.ts`)
Extracts structured knowledge from session conversations via LLM.

**Workflow**:
1. **Collect** user + assistant messages during session
2. **Build prompt** with consolidation instructions
3. **Call LLM** (via pi SDK: `pi -p <prompt> --print`)
4. **Parse response** (extract JSON with facts & lessons)
5. **Deduplicate** lessons using:
   - Exact string match
   - Jaccard similarity (≥0.7 threshold)
6. **Store** with source provenance (e.g., "consolidation:session-123")

**Consolidation Prompt Includes**:
- What to extract (preferences, patterns, corrections)
- What NOT to extract (code patterns, file paths, git history, ephemeral tasks)
- Confidence threshold (≥0.8)
- Key naming conventions (lowercase, dots, no spaces)
- JSON schema

**Extraction Categories**:
- **Preferences** → `pref.*` (confidence 0.8+)
- **Project patterns** → `project.<name>.*` (confidence 0.9+)
- **Tool preferences** → `tool.*` (confidence 0.8+)
- **Corrections** → lessons table with `negative=1`
- **Validated approaches** → lessons table with `negative=0`

---

### 4. **Bootstrap** (`bootstrap.ts`)
One-time migration tool to seed memory from historical sessions.

**Purpose**: If user already has session-search index, extract facts from past sessions in bulk.

**Workflow**:
1. Read session-search index (`~/.pi/session-search/index/session-index.json`)
2. Batch sessions (default: 15 per batch)
3. For each batch: run consolidation on combined summaries
4. Apply extracted facts to memory store
5. Deduplicate across batches

**CLI**:
```bash
npx tsx bootstrap.ts [--dry-run] [--limit N] [--batch-size N]
```

**Example**:
```bash
npx tsx bootstrap.ts --limit 100 --batch-size 20
# Processes 100 most recent sessions, 20 per LLM call
```

---

### 5. **Extension Entry Point** (`index.ts`)
Implements pi SDK lifecycle hooks and tool definitions.

**Lifecycle Hooks**:

#### `session_start()`
- Open SQLite store at resolved DB path
- Show memory stats in status bar
- Example: "📚 Memory: 42 facts, 8 lessons"

#### `before_agent_start(prompt, cwd)`
- Build context block from memory
- **Inject** as `<memory>` block in system prompt
- Prepended before agent runs (high priority)

#### `agent_end(messages)`
- Queue conversation messages for consolidation
- Store in memory for later processing

#### `session_shutdown()`
- If ≥3 user messages: trigger consolidation
  - Collect queued messages
  - Call LLM to extract facts & lessons
  - Store results
- Close SQLite connection

**Tools Exposed** (via MCP protocol):
```typescript
1. memory_search(query: string)
   → Search semantic memory by keyword
   → Returns top 10 facts

2. memory_remember(key: string, value: string, confidence?: number)
   → Manually add/update a fact
   → For user corrections or explicit saves

3. memory_forget(key: string)
   → Delete a fact

4. memory_lessons(category?: string)
   → List learned corrections
   → Filter by category if provided

5. memory_stats()
   → Show { semantic: N, lessons: N, events: N }
```

**Commands**:
```
/memory-consolidate
→ Manually trigger consolidation mid-session
→ Useful for immediate feedback
```

---

## Path Resolution Strategy

### Why It Matters
Projects may want isolated memory (local `.pi/memory/`) separate from global user memory (`~/.pi/memory/`).

### Resolution Order (Highest Priority First)
```
1. pi-memory.localPath in {cwd}/.pi/settings.json
   → {localPath}/memory.db

2. pi-total-recall.localPath cascade
   → {localPath}/memory/memory.db

3. Global default
   → ~/.pi/memory/memory.db
```

### Example Config
```json
{
  "cwd": "/path/to/project",
  ".pi/settings.json": {
    "pi-memory": {
      "localPath": ".pi/memory"
    }
  }
}

// Resolves to: /path/to/project/.pi/memory/memory.db
```

**Benefit**: Team projects can have shared memory without polluting global user memory.

---

## Data Flow Diagrams

### Data Flow 1: Injection (On Session Start)
```
┌─────────────────────────────────────────────┐
│ Session Start (with user's first message)   │
└────────────────┬────────────────────────────┘
                 ↓
          ┌──────────────┐
          │ Resolve DB   │
          │ path         │
          └──────┬───────┘
                 ↓
        ┌────────────────────┐
        │ Open SQLite store  │
        │ (WAL mode)         │
        └────────┬───────────┘
                 ↓
      ┌──────────────────────────┐
      │ Extract user's prompt    │
      │ and working directory    │
      └────────┬─────────────────┘
               ↓
    ┌──────────────────────────────┐
    │ buildContextBlock(            │
    │   store, cwd, prompt, config) │
    │                              │
    │ 1. Search semantic facts     │
    │ 2. Search project context   │
    │ 3. Filter lessons           │
    │ 4. Format text block        │
    └────────┬─────────────────────┘
             ↓
  ┌────────────────────────────────┐
  │ Prepend <memory> block to      │
  │ system prompt                  │
  └────────┬───────────────────────┘
           ↓
   ┌──────────────────────┐
   │ Agent starts with    │
   │ enhanced context     │
   └──────────────────────┘
```

### Data Flow 2: Consolidation (On Session End)
```
┌───────────────────────────────────────────┐
│ Session End (collected N user messages)   │
└─────────────────┬───────────────────────┬─┘
                  │                       │
        N < 3?    │                       │    N ≥ 3?
                  ↓                       ↓
             [Skip]                ┌──────────────┐
                                   │ Consolidate  │
                                   └──────┬───────┘
                                          ↓
                        ┌─────────────────────────────┐
                        │ Build consolidation prompt: │
                        │ - Current memory state      │
                        │ - User messages             │
                        │ - Assistant messages        │
                        │ - Extraction instructions   │
                        └────────┬────────────────────┘
                                 ↓
                    ┌────────────────────────────┐
                    │ Execute: pi -p <prompt>    │
                    │ --print                    │
                    │                            │
                    │ (Calls LLM to extract)     │
                    └────────┬───────────────────┘
                             ↓
                  ┌────────────────────────┐
                  │ Parse JSON response    │
                  │ - semantic facts       │
                  │ - lessons              │
                  └────────┬───────────────┘
                           ↓
         ┌─────────────────────────────────┐
         │ Deduplicate lessons:            │
         │ 1. Exact match                  │
         │ 2. Jaccard similarity ≥ 0.7     │
         └────────┬────────────────────────┘
                  ↓
        ┌──────────────────────────────┐
        │ Store to semantic table:      │
        │ - key, value, confidence      │
        │ - source: 'consolidation'     │
        │ - created_at, updated_at      │
        └────────┬─────────────────────┘
                 ↓
        ┌──────────────────────────────┐
        │ Store to lessons table:       │
        │ - rule, category, negative    │
        │ - source: 'consolidation'     │
        │ - created_at                  │
        └────────┬─────────────────────┘
                 ↓
        ┌──────────────────────────────┐
        │ Log audit events              │
        │ (for provenance tracking)     │
        └────────┬─────────────────────┘
                 ↓
        ┌──────────────────────────────┐
        │ Close SQLite connection       │
        └──────────────────────────────┘
```

---

## Key Design Decisions & Trade-offs

### 1. **LLM-Based Extraction vs. Rule-Based**
- **Choice**: LLM-based (consolidator.ts)
- **Why**: Can understand context, nuance, and confidence. Rules are brittle.
- **Trade-off**: Slower, costs money (if using paid API), but higher quality.

### 2. **Semantic Facts + Lessons vs. Flat Memory**
- **Choice**: Separate tables for different memory types
- **Why**: Lessons are narrative (corrections), facts are key-value (preferences). Different search/injection logic.
- **Trade-off**: More complex schema, but clearer semantics.

### 3. **Confidence Score (0.0–1.0) + Deduplication**
- **Choice**: Store only high-confidence facts (≥0.8), deduplicate lessons with Jaccard similarity (≥0.7)
- **Why**: Prevents noisy memory pollution.
- **Trade-off**: May miss subtle patterns; requires tuning thresholds.

### 4. **SQLite (Built-in) vs. External DB**
- **Choice**: SQLite with WAL mode
- **Why**: No external dependencies, zero ops, WAL allows concurrent reads, PRAGMA controls durability.
- **Trade-off**: Not suitable for multi-process concurrency (but pi is single-user per session).

### 5. **Selective vs. All Lessons Injection**
- **Choice**: Configurable (default="all", opt-in="selective")
- **Why**: "all" preserves backward compatibility; "selective" reduces context waste.
- **Trade-off**: Selective mode requires FTS or heuristics; may miss edge-case lessons.

### 6. **Bootstrap (Batch Consolidation)**
- **Choice**: Process historical sessions in batches (default 15/batch)
- **Why**: Reduces LLM calls; patterns across sessions more likely to surface.
- **Trade-off**: Patterns from single outlier sessions may get lost.

---

## Integration Points with pi SDK

### Required Peer Dependencies
```json
{
  "peerDependencies": {
    "@mariozechner/pi-coding-agent": "*",
    "@sinclair/typebox": "*"
  }
}
```

### Lifecycle Hook Signatures (from pi SDK)
```typescript
// Expects extension to export these hooks:
export function session_start(args: SessionStartArgs): void
export function before_agent_start(args: BeforeAgentStartArgs): void
export function agent_end(args: AgentEndArgs): void
export function session_shutdown(args: SessionShutdownArgs): void

// And expose these tools:
export const tools: { [name: string]: ToolDefinition }
export const commands: { [name: string]: CommandHandler }
```

### LLM Integration
- Uses `pi -p <prompt> --print` to invoke LLM
- Expects JSON response matching consolidation schema
- Falls back gracefully if pi command fails

---

## What Makes It "Extremely Simple Yet Useful"

### Simplicity (Architectural)
1. **No external services** — SQLite is self-contained
2. **Single lifecycle** — 4 hooks cover the entire flow
3. **Stateless LLM calls** — No streaming, no complex handshakes
4. **Minimal schema** — 3 tables, straightforward relationships

### Usefulness (Practical)
1. **Automatic learning** — Happens in background; no manual effort
2. **Smart injection** — Relevant memories, not all memories (selective mode)
3. **Corrections stick** — Things you correct once don't come back
4. **Low context cost** — ~8KB capped, and can be even lower in selective mode
5. **Cross-project isolation** — Option to keep project memories separate

### Why People Adopt It
- **Feels like the agent is learning** (because it is)
- **Solves the "I told you this yesterday" problem**
- **No UX overhead** — works in background
- **Debuggable** — can read memory via `memory_search` tool
- **Composable** — designed to work with session-search and knowledge-search (pi-total-recall)

---

## Configuration & Customization

### Global Settings (`~/.pi/agent/settings.json`)
```json
{
  "memory": {
    "lessonInjection": "selective",    // "all" or "selective"
    "contextCapChars": 8000,           // Max context block size
    "minUserMessagesForConsolidation": 3  // Only consolidate if ≥ N user msgs
  }
}
```

### Project-Local Settings (`{project}/.pi/settings.json`)
```json
{
  "pi-memory": {
    "localPath": ".pi/memory"          // Isolate project memory
  }
}
```

### Environment
- `DATABASE_PATH`: Override resolved DB path
- `PI_MEMORY_DEBUG`: Enable verbose logging

---

## Testing Strategy

### Unit Tests (`.test.ts` files)
- `store.test.ts` — CRUD operations, FTS fallback, migrations
- `injector.test.ts` — Context block building, selective filtering
- `localpath.test.ts` — Path resolution cascading

### Integration Points
- Verify LLM consolidation prompt structure
- Mock `pi -p` execution
- Ensure deduplication works correctly

---

## Known Limitations & Future Work

### Limitations
1. **Single-user per session** — SQLite not designed for multi-process writes
2. **No versioning** — Can't track fact evolution (only `updated_at`)
3. **FTS5 optional** — Falls back to LIKE if unavailable (slower search)
4. **LLM cost** — Every consolidation calls an LLM (even if free tier, there's latency)
5. **Selective injection heuristics** — May miss relevant lessons (threshold tuning needed)

### Potential Improvements
- **Fact versioning** — Track how values changed over time
- **Multi-session deduplication** — Better consolidation across users
- **Offline extraction** — Use local embeddings instead of LLM calls
- **Fact confidence decay** — Lower confidence of old facts automatically
- **Custom consolidation prompts** — Let users define what to extract

---

## Summary for Recreation

### Minimal Implementation Steps
1. **Create SQLite schema** (semantic, lessons, events tables)
2. **Implement MemoryStore class** (CRUD + search)
3. **Implement Injector** (build context block for system prompt)
4. **Implement Consolidator** (LLM extraction + deduplication)
5. **Hook into agent lifecycle** (session_start, before_agent_start, agent_end, session_shutdown)
6. **Expose tools** (memory_search, memory_remember, memory_forget, etc.)

### Key Primitives to Reuse
- SQLite + WAL mode (reliability + concurrent reads)
- JSON-based LLM extraction (simple, flexible)
- Confidence scores (avoid memory pollution)
- Lessons with negative flag (captures corrections vs. validations)
- Path resolution cascade (multi-project support)

### Integration Patterns
- **For Claude/Copilot MCP servers**: Replace pi SDK hooks with MCP lifecycle (tool calls, resources, subscriptions)
- **For local agents**: Keep pi SDK hooks as-is
- **For browser-based agents**: Use IndexedDB or Web SQLite instead of node:sqlite

