# pi-memory Source Code Reference

## Package Location
```
Installed at: ~/.npm-global/lib/node_modules/@samfp/pi-memory/
Repository:  https://github.com/samfoy/pi-memory
Version:     1.0.4
License:     MIT
```

---

## Source Files (src/)

### 1. **index.ts** (Main Extension)
- **Purpose**: Extension entry point, lifecycle hooks, tool definitions
- **Size**: ~600 lines
- **Key Exports**:
  - `export default function (pi: ExtensionAPI)`
  - `resolveDbPath(cwd: string): string`
  - `readSettingsConfig(cwd?: string): InjectorConfig`
- **Implements**:
  - `session_start` hook (open store, show stats)
  - `before_agent_start` hook (inject context)
  - `agent_end` hook (collect messages)
  - `session_shutdown` hook (consolidate & close)
  - 5 tools: memory_search, memory_remember, memory_forget, memory_lessons, memory_stats
  - 1 command: /memory-consolidate

### 2. **store.ts** (SQLite Wrapper)
- **Purpose**: Database layer, CRUD operations, search
- **Size**: ~500+ lines
- **Key Classes**:
  - `MemoryStore` — Main database interface
- **Key Methods**:
  - `setSemantic(key, value, confidence, source)`
  - `getSemantic(key): SemanticEntry | undefined`
  - `searchSemantic(query, limit): SemanticEntry[]`
  - `setLesson(rule, category, negative, source)`
  - `listLessons(category?, limit): LessonEntry[]`
  - `stats(): { semantic, lessons, events }`
- **Interfaces**:
  - `SemanticEntry` (key-value fact)
  - `LessonEntry` (learned correction)
  - `MemoryEvent` (audit log)
- **Pragmas**:
  - WAL mode (concurrent reads)
  - busy_timeout = 5000ms (lock wait)
  - foreign_keys = ON (referential integrity)

### 3. **injector.ts** (Context Block Builder)
- **Purpose**: Build memory context for system prompt injection
- **Size**: ~350+ lines
- **Key Functions**:
  - `buildContextBlock(store, cwd?, prompt?, config?): ContextBlock`
  - `buildSelectiveBlock(store, prompt, cwd?, config?)` (search-based)
  - `buildFallbackBlock(store, cwd?)` (prefix-based)
  - `getRelevantLessons(store, prompt, cwd): LessonEntry[]`
- **Interfaces**:
  - `ContextBlock` { text, stats }
  - `InjectorConfig` { lessonInjection?: "all" | "selective" }
- **Features**:
  - FTS5 search for semantic facts
  - Category-based lesson filtering
  - 8KB context cap

### 4. **consolidator.ts** (LLM Extraction)
- **Purpose**: Extract structured knowledge from session conversations
- **Size**: ~400+ lines
- **Key Functions**:
  - `buildConsolidationPrompt(input, currentFacts?, currentLessons?): string`
  - `parseConsolidationResponse(jsonText: string): ExtractedMemory`
  - `applyExtracted(store, extracted, source): { semantic, lessons }`
  - `jaccard(a: string, b: string): number` (similarity scoring)
- **Interfaces**:
  - `ConsolidationInput` { userMessages, assistantMessages, cwd, sessionId }
  - `ExtractedMemory` { semantic[], lessons[] }
- **Constants**:
  - `CONSOLIDATION_PROMPT` (LLM extraction instructions)
  - `MIN_CONFIDENCE = 0.8` (filter threshold)
  - `JACCARD_THRESHOLD = 0.7` (dedup threshold)
- **Features**:
  - LLM extraction via pi SDK
  - Exact string deduplication
  - Jaccard similarity deduplication
  - Confidence filtering

### 5. **bootstrap.ts** (Migration Tool)
- **Purpose**: Seed memory from historical session-search index
- **Size**: ~150 lines
- **Executable**: `#!/usr/bin/env npx tsx`
- **CLI Args**:
  - `--dry-run` (preview without storing)
  - `--limit N` (max sessions to process)
  - `--batch-size N` (sessions per LLM call)
- **Workflow**:
  - Read `~/.pi/session-search/index/session-index.json`
  - Batch sessions (default 15/batch)
  - Consolidate each batch
  - Apply with deduplication
  - Log stats

### Test Files
- `consolidator.test.ts` — Consolidation logic tests
- `injector.test.ts` — Context block building tests
- `localpath.test.ts` — Path resolution cascade tests
- `store.test.ts` — Database CRUD tests

---

## TypeScript Types

### Core Types

```typescript
// Semantic fact entry
interface SemanticEntry {
  key: string;                    // "pref.commit_style"
  value: string;                  // "conventional commits"
  confidence: number;             // 0.0-1.0
  source: "user" | "consolidation" | "correction";
  created_at: string;
  updated_at: string;
  last_accessed?: string;
}

// Learned correction/validation
interface LessonEntry {
  id: string;                     // uuid
  rule: string;                   // "Use sed, not echo >>"
  category: string;               // "vault", "git", etc
  source: string;
  negative: boolean;              // true=avoid, false=validated
  created_at: string;
}

// Context block for injection
interface ContextBlock {
  text: string;                   // formatted markdown
  stats: { semantic: number; lessons: number };
}

// LLM extraction input/output
interface ConsolidationInput {
  userMessages: string[];
  assistantMessages: string[];
  cwd?: string;
  sessionId?: string;
}

interface ExtractedMemory {
  semantic: Array<{ key: string; value: string; confidence: number }>;
  lessons: Array<{ rule: string; category: string; negative: boolean }>;
}

// Configuration
interface InjectorConfig {
  lessonInjection?: "all" | "selective";
}
```

---

## File Dependencies

```
index.ts (entry point)
├── store.ts (MemoryStore)
├── injector.ts (buildContextBlock)
├── consolidator.ts (buildConsolidationPrompt, etc)
└── pi SDK (@mariozechner/pi-coding-agent)

store.ts (database layer)
├── node:sqlite (DatabaseSync)
├── node:fs (file I/O)
└── node:path (path resolution)

injector.ts (injection logic)
├── store.ts (search)
└── No external deps

consolidator.ts (LLM integration)
├── store.ts (dedup)
├── pi SDK (LLM execution)
└── node:child_process (execFileSync)

bootstrap.ts (migration tool)
├── store.ts
├── consolidator.ts
├── node:fs
├── node:child_process
└── pi SDK
```

---

## Configuration Files

### package.json
```json
{
  "name": "@samfp/pi-memory",
  "version": "1.0.4",
  "pi": {
    "extensions": ["./src/index.ts"]
  },
  "peerDependencies": {
    "@mariozechner/pi-coding-agent": "*",
    "@sinclair/typebox": "*"
  }
}
```

### settings.json (Global)
Location: `~/.pi/agent/settings.json`
```json
{
  "memory": {
    "lessonInjection": "selective",     // "all" or "selective"
    "contextCapChars": 8000,            // max context size
    "minUserMessagesForConsolidation": 3  // consolidate threshold
  }
}
```

### settings.json (Project-Local)
Location: `{cwd}/.pi/settings.json`
```json
{
  "pi-memory": {
    "localPath": ".pi/memory"           // isolate project memory
  }
}
```

---

## SQLite Schema

### Schema Creation (from store.ts migrate())

```sql
-- Semantic facts table
CREATE TABLE IF NOT EXISTS semantic (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  confidence REAL NOT NULL DEFAULT 0.8,
  source TEXT NOT NULL DEFAULT 'consolidation',
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now')),
  last_accessed TEXT
);

-- Lessons table
CREATE TABLE IF NOT EXISTS lessons (
  id TEXT PRIMARY KEY,
  rule TEXT NOT NULL,
  category TEXT NOT NULL DEFAULT 'general',
  source TEXT NOT NULL DEFAULT 'consolidation',
  negative INTEGER NOT NULL DEFAULT 0,
  is_deleted INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Events audit log
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_type TEXT NOT NULL,
  memory_type TEXT NOT NULL,
  memory_key TEXT NOT NULL,
  details TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- FTS5 indexes (optional, if FTS5 available)
CREATE VIRTUAL TABLE semantic_fts USING fts5(key, value);
CREATE VIRTUAL TABLE lessons_fts USING fts5(rule, category);

-- Triggers to keep FTS indexes in sync
CREATE TRIGGER semantic_ai AFTER INSERT ON semantic ...
CREATE TRIGGER semantic_ad AFTER DELETE ON semantic ...
CREATE TRIGGER semantic_au AFTER UPDATE ON semantic ...
(... similar for lessons ...)
```

---

## Key Algorithms

### Search Algorithm (Semantic)

```typescript
// If FTS5 available: BM25 ranking
SELECT s.key, s.value, ...
FROM semantic s
JOIN semantic_fts fts ON s.rowid = fts.rowid
WHERE semantic_fts MATCH ?
ORDER BY bm25(semantic_fts)
LIMIT ?

// Fallback: Term coverage scoring
tokens(a) = terms in query
tokens(b) = terms in fact.key + fact.value
score = count(tokens(a) ∩ tokens(b)) / count(tokens(a))
sort by score DESC, limit
```

### Deduplication Algorithm

```typescript
// 1. Exact match (fast path)
if (newLesson.rule === existingLesson.rule) skip()

// 2. Jaccard similarity (slow path)
tokensA = new Set(a.toLowerCase().split(/\s+/))
tokensB = new Set(b.toLowerCase().split(/\s+/))
intersection = |tokensA ∩ tokensB|
union = |tokensA| + |tokensB| - intersection
similarity = intersection / union
if (similarity >= 0.7) skip()
```

### Confidence Filtering

```typescript
// Only store if confidence high enough
const MIN_CONFIDENCE = 0.8

// Upsert logic: higher confidence wins
if (existing.confidence > new.confidence) {
  skip()  // keep existing
} else {
  replace()  // update to new
}
```

---

## How to Read the Source Code

### Start Here
1. **index.ts** — Understand the lifecycle and hooks
2. **store.ts** — Learn the database layer
3. **injector.ts** — See how context is built
4. **consolidator.ts** — Deep-dive into extraction logic

### Then Deep-Dive
5. **bootstrap.ts** — Migration strategy (advanced)
6. **Test files** — Real usage patterns

### External References
- [pi SDK types](https://github.com/badlogic/pi-mono) — ExtensionAPI, lifecycle
- [SQLite pragmas](https://www.sqlite.org/pragma.html) — WAL, busy_timeout
- [FTS5](https://www.sqlite.org/fts5.html) — Full-text search

---

## Running the Code Locally

### Install
```bash
npm install
```

### Test
```bash
npm run test
```

### Type Check
```bash
npm run typecheck
```

### Build/Pack
```bash
npm pack
```

### Use Bootstrap (Migration)
```bash
npx tsx src/bootstrap.ts --limit 100 --batch-size 20
```

---

## Integration with pi CLI

### How pi executes this extension
```
1. pi loads ~/.pi/agent/settings.json
2. Sees "packages": ["npm:@samfp/pi-memory"]
3. Imports ./src/index.ts's default export
4. Calls on("session_start", ...) hook
5. Calls on("before_agent_start", ...) hook
6. Collects messages via on("agent_end", ...)
7. Consolidates on("session_shutdown", ...)
```

### How consolidation calls LLM
```typescript
// In consolidator.ts:
const result = execFileSync(
  "pi",
  ["-p", prompt, "--print"],  // Ask LLM to print extraction
  { encoding: "utf8", timeout: 120_000, cwd: homedir() }
);

// Pi SDK parses the prompt as LLM input, returns result
// Then consolidator.ts parses JSON response
```

---

## Recommended Extensions/Related Packages

- **pi-session-search** — Find historical sessions (what you did)
- **pi-knowledge-search** — Find documents/wikis (external knowledge)
- **pi-total-recall** — Bundle all three (complete context stack)

