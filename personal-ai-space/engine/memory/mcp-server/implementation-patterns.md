# pi-memory: Practical Implementation Guide

## Quick Reference: Core Patterns You Can Reuse

### Pattern 1: SQLite + WAL for Single-User Memory
```typescript
import { DatabaseSync } from "node:sqlite";
import { mkdirSync, existsSync } from "node:fs";
import { dirname } from "node:path";

class PersistentMemory {
  private db: DatabaseSync;

  constructor(dbPath: string) {
    const dir = dirname(dbPath);
    if (!existsSync(dir)) mkdirSync(dir, { recursive: true });

    this.db = new DatabaseSync(dbPath);
    this.db.exec("PRAGMA journal_mode = WAL");        // Concurrent reads
    this.db.exec("PRAGMA busy_timeout = 5000");       // Wait on locks
    this.db.exec("PRAGMA foreign_keys = ON");         // Enforce integrity
    this.migrate();
  }

  private migrate(): void {
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS facts (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        confidence REAL DEFAULT 0.8,
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now'))
      );
      
      CREATE INDEX IF NOT EXISTS idx_facts_updated 
        ON facts(updated_at DESC);
    `);
  }

  set(key: string, value: string, confidence: number = 0.8): void {
    const stmt = this.db.prepare(
      `INSERT OR REPLACE INTO facts (key, value, confidence, updated_at)
       VALUES (?, ?, ?, datetime('now'))`
    );
    stmt.run(key, value, confidence);
  }

  get(key: string): string | null {
    const stmt = this.db.prepare("SELECT value FROM facts WHERE key = ?");
    const result = stmt.get(key) as { value: string } | undefined;
    return result?.value ?? null;
  }

  close(): void {
    this.db.close();
  }
}
```

### Pattern 2: Confidence-Based Storage (Avoid Noise)
```typescript
/**
 * Only store facts the LLM is confident about.
 * Prevents weak signals from polluting memory.
 */

interface ExtractedFact {
  key: string;
  value: string;
  confidence: number; // 0.0 - 1.0
}

const MIN_CONFIDENCE = 0.8;

function applyFacts(store: PersistentMemory, facts: ExtractedFact[]): void {
  for (const fact of facts) {
    if (fact.confidence >= MIN_CONFIDENCE) {
      store.set(fact.key, fact.value, fact.confidence);
    }
  }
}
```

### Pattern 3: LLM-Based Extraction (Smart, Not Brittle)
```typescript
/**
 * Instead of regex/rule-based extraction, ask LLM to extract.
 * This is resilient to phrasing changes and understands context.
 */

const EXTRACTION_PROMPT = `
Extract structured knowledge from this conversation.

Focus on:
1. User preferences (key: "pref.X", value: "...")
2. Learned corrections (rule: "...", negative: true/false)
3. Tool preferences (key: "tool.X", value: "...")

Confidence >= 0.8 only. Respond with JSON:
{
  "facts": [
    { "key": "string", "value": "string", "confidence": 0.8 }
  ],
  "lessons": [
    { "rule": "string", "negative": boolean, "category": "string" }
  ]
}

Messages to analyze:
${userMessages.join("\n\n")}
`;

async function extractKnowledge(messages: string[]): Promise<ExtractedKnowledge> {
  const response = await llm.generate({ prompt: EXTRACTION_PROMPT });
  return JSON.parse(response.text);
}
```

### Pattern 4: Selective Injection (Smart Context)
```typescript
/**
 * Don't inject all facts every time. Only inject relevant ones.
 * Reduces context waste, improves signal-to-noise.
 */

interface ContextBlock {
  text: string;
  factCount: number;
  lessonCount: number;
}

function buildContextBlock(
  store: PersistentMemory,
  userPrompt: string,
  maxChars: number = 8000
): ContextBlock {
  const relevant = store.searchRelevant(userPrompt, limit: 10);
  
  const lines: string[] = [];
  let charCount = 0;

  for (const fact of relevant) {
    const line = `• ${fact.key}: ${fact.value}`;
    if (charCount + line.length > maxChars) break;
    lines.push(line);
    charCount += line.length;
  }

  return {
    text: lines.join("\n"),
    factCount: lines.length,
    lessonCount: 0
  };
}
```

### Pattern 5: Deduplication with Jaccard Similarity
```typescript
/**
 * Lessons often express the same idea with different wording.
 * Jaccard similarity detects these and avoids storing duplicates.
 */

function jaccardSimilarity(a: string, b: string): number {
  const tokensA = new Set(a.toLowerCase().split(/\s+/));
  const tokensB = new Set(b.toLowerCase().split(/\s+/));

  const intersection = [...tokensA].filter(t => tokensB.has(t)).length;
  const union = tokensA.size + tokensB.size - intersection;

  return intersection / union;
}

const DEDUP_THRESHOLD = 0.7;

function deduplicateLessons(lessons: LessonEntry[], existing: LessonEntry[]): LessonEntry[] {
  const result: LessonEntry[] = [];

  for (const lesson of lessons) {
    const isDuplicate = existing.some(
      e => jaccardSimilarity(lesson.rule, e.rule) >= DEDUP_THRESHOLD
    );
    if (!isDuplicate) {
      result.push(lesson);
    }
  }

  return result;
}
```

### Pattern 6: Path Resolution Cascade (Multi-Project Support)
```typescript
/**
 * Allow projects to have isolated memory, fall back to global.
 * Priority: project-local > team-local > global
 */

import { join } from "node:path";
import { readFileSync } from "node:fs";
import { homedir } from "node:os";

function resolveMemoryPath(cwd: string): string {
  // 1. Check project-local override
  try {
    const projectConfig = JSON.parse(
      readFileSync(join(cwd, ".pi", "settings.json"), "utf8")
    );
    const localPath = projectConfig?.["pi-memory"]?.localPath;
    if (localPath) {
      return join(localPath, "memory.db");
    }
  } catch {
    // No local config, continue
  }

  // 2. Check team/org override
  try {
    const teamConfig = JSON.parse(
      readFileSync(join(cwd, "../../.pi/settings.json"), "utf8")
    );
    const cascadePath = teamConfig?.["pi-total-recall"]?.localPath;
    if (cascadePath) {
      return join(cascadePath, "memory", "memory.db");
    }
  } catch {
    // No team config, use global
  }

  // 3. Fall back to global
  return join(homedir(), ".pi", "memory", "memory.db");
}
```

### Pattern 7: Lifecycle Hooks (Session Integration)
```typescript
/**
 * Typical pattern for agent frameworks:
 * - on_session_start: load & inject
 * - on_agent_message: collect for consolidation
 * - on_session_end: consolidate & store
 */

class MemoryAgent {
  private store: PersistentMemory;
  private messages: { role: string; content: string }[] = [];

  async onSessionStart(cwd: string): Promise<string> {
    const dbPath = resolveMemoryPath(cwd);
    this.store = new PersistentMemory(dbPath);
    
    // Show summary in status
    const facts = this.store.list();
    return `📚 Memory loaded: ${facts.length} facts`;
  }

  async onBeforeAgentStart(prompt: string): Promise<string> {
    const context = buildContextBlock(this.store, prompt);
    return `<memory>\n${context.text}\n</memory>`;
  }

  async onAgentMessage(msg: { role: string; content: string }): Promise<void> {
    this.messages.push(msg);
  }

  async onSessionEnd(): Promise<void> {
    // Only consolidate if enough messages
    const userMsgs = this.messages.filter(m => m.role === "user");
    if (userMsgs.length < 3) return;

    // Extract knowledge from session
    const knowledge = await extractKnowledge(
      this.messages.map(m => `[${m.role}] ${m.content}`)
    );

    // Deduplicate & store
    const existing = this.store.list();
    const newLessons = deduplicateLessons(knowledge.lessons, existing);
    
    for (const lesson of newLessons) {
      this.store.addLesson(lesson);
    }
    
    this.store.close();
  }
}
```

---

## Architecture: Dataflow Diagram (ASCII)

```
┌──────────────────────────────────────────────────────────────────┐
│                         Agent Framework                          │
│  (Claude MCP, pi, custom agent, etc.)                            │
└──────────────────────────────────────────────────────────────────┘
                              ↑↓
        ┌─────────────────────────────────────────────┐
        │      Memory Extension (pi-memory)            │
        ├─────────────────────────────────────────────┤
        │                                             │
        │  1. session_start()                         │
        │     └→ open(dbPath)                         │
        │     └→ show stats                           │
        │                                             │
        │  2. before_agent_start(prompt, cwd)         │
        │     └→ buildContextBlock(store, prompt)     │
        │     └→ inject "<memory>" in system prompt   │
        │                                             │
        │  3. agent_end(messages)                     │
        │     └→ queue for consolidation              │
        │                                             │
        │  4. session_shutdown()                      │
        │     └→ consolidate(messages)                │
        │     └→ close(store)                         │
        │                                             │
        │  Tools:                                     │
        │  - memory_search(query)                     │
        │  - memory_remember(key, value)              │
        │  - memory_forget(key)                       │
        │                                             │
        └─────────────────────────────────────────────┘
                              ↓↓
        ┌─────────────────────────────────────────────┐
        │       Memory Store (SQLite)                 │
        ├─────────────────────────────────────────────┤
        │                                             │
        │  Tables:                                    │
        │  ┌────────────────────────────────────┐    │
        │  │ semantic                            │    │
        │  │ (key, value, confidence, updated)  │    │
        │  └────────────────────────────────────┘    │
        │                                             │
        │  ┌────────────────────────────────────┐    │
        │  │ lessons                             │    │
        │  │ (rule, category, negative, source) │    │
        │  └────────────────────────────────────┘    │
        │                                             │
        │  ┌────────────────────────────────────┐    │
        │  │ events (audit log)                  │    │
        │  └────────────────────────────────────┘    │
        │                                             │
        │  Pragmas:                                   │
        │  - journal_mode = WAL                       │
        │  - busy_timeout = 5000                      │
        │  - foreign_keys = ON                        │
        │                                             │
        │  {cwd}/.pi/memory/memory.db                 │
        │  or ~/.pi/memory/memory.db                  │
        │                                             │
        └─────────────────────────────────────────────┘
                              ↓↓
        ┌─────────────────────────────────────────────┐
        │      LLM (Consolidation)                    │
        ├─────────────────────────────────────────────┤
        │                                             │
        │  Input:                                     │
        │  - Session messages (user + assistant)      │
        │  - Current memory state (for dedup)         │
        │                                             │
        │  Process:                                   │
        │  "Extract preferences, patterns,            │
        │   corrections from this conversation"       │
        │                                             │
        │  Output (JSON):                             │
        │  {                                          │
        │    "facts": [                               │
        │      {"key": "pref.X", "value": "...",     │
        │       "confidence": 0.9}                    │
        │    ],                                       │
        │    "lessons": [                             │
        │      {"rule": "...", "negative": true}     │
        │    ]                                        │
        │  }                                          │
        │                                             │
        └─────────────────────────────────────────────┘
```

---

## Common Use Cases & Implementation

### Use Case 1: Tool Learning
```typescript
/**
 * User: "I always use sed for vault notes, not echo >>"
 * Memory extracts: pref.vault_tool = "sed"
 *                  lesson: "DON'T use echo >> for vault"
 * Next session: Agent is reminded & avoids mistake
 */

// In consolidator:
const extractedLessons = [
  {
    rule: "Use sed to insert after '## Notes' header, not echo >> which appends after Tags",
    category: "vault",
    negative: true
  }
];

// In next session, injected into prompt:
// "Lessons (3 learned corrections): DON'T use echo >> for vault—use sed instead"
```

### Use Case 2: Project Pattern Detection
```typescript
/**
 * Consolidator sees multiple sessions in project "rosie" using:
 * - Go (not Python)
 * - Dagger (for DI)
 * - PostgreSQL
 * Extracts and stores for next session on "rosie"
 */

// Bootstrap from session history:
const projectPatterns = [
  { key: "project.rosie.language", value: "Go", confidence: 0.95 },
  { key: "project.rosie.di", value: "Dagger dependency injection", confidence: 0.9 },
  { key: "project.rosie.db", value: "PostgreSQL", confidence: 0.95 }
];

// In next session on rosie, injected:
// "Project rosie: Go, Dagger DI, PostgreSQL"
```

### Use Case 3: User Preference Accumulation
```typescript
/**
 * Over 10+ sessions, agent learns:
 * - pref.commit_style = "conventional commits"
 * - pref.test_first = "true"
 * - pref.documentation = "docstrings + README"
 * Becomes implicit context for all future sessions
 */

// Persisted preferences, injected on every session start:
// "User preferences: conventional commits, TDD, comprehensive docs"
```

### Use Case 4: Selective Injection (Context Budget)
```typescript
/**
 * User has 50+ lessons learned. But this session is about "pentest".
 * Instead of injecting all 50, inject only:
 * - Lessons with "pentest", "security", "exploit" keywords
 * - General lessons (always relevant)
 * Result: ~5 lessons instead of 50 = more context for reasoning
 */

function getRelevantLessons(store, prompt, cwd) {
  // FTS search on prompt
  const promptMatches = store.searchLessons(prompt, limit: 10);

  // Category inference
  if (prompt.includes("pentest")) {
    const categoryMatches = store.lessonsByCategory("security", limit: 5);
    // merge, deduplicate
  }

  // Always include general lessons
  const general = store.lessonsByCategory("general", limit: 10);

  return mergeAndDedup([promptMatches, categoryMatches, general]);
}
```

---

## Migration Path: From Scratch to Production

### Phase 1: Minimal (Week 1)
- [x] SQLite schema (1 table: facts)
- [x] MemoryStore CRUD
- [x] Lifecycle hooks (session_start, session_end)
- [x] Manual memory_remember tool

**Test**: Can store & retrieve facts across sessions

### Phase 2: Consolidation (Week 2)
- [x] Build consolidation prompt
- [x] LLM extraction (call to LLM)
- [x] Parse JSON response
- [x] Auto-store extracted facts

**Test**: Consolidation happens on session end, new facts appear next session

### Phase 3: Deduplication & Lessons (Week 3)
- [x] Lessons table (separate from facts)
- [x] Jaccard similarity dedup
- [x] Store lessons with negative flag

**Test**: Duplicate lessons rejected; corrections encoded as negative

### Phase 4: Selective Injection (Week 4)
- [x] Search semantic memory (FTS or LIKE)
- [x] Search lessons by relevance
- [x] Build context block (capped at 8KB)
- [x] Inject into system prompt

**Test**: Relevant memory injected; context stays under limit

### Phase 5: Multi-Project Support (Week 5)
- [x] Path resolution cascade
- [x] Project-local memory directories
- [x] Fallback to global

**Test**: Multiple projects have isolated memory

### Phase 6: Tools & UX (Week 6)
- [x] memory_search tool
- [x] memory_forget tool
- [x] memory_stats tool
- [x] /memory-consolidate command

**Test**: Users can debug and control memory

---

## Checklist for Creating Your Own

- [ ] **Database**
  - [ ] SQLite with WAL pragma
  - [ ] semantic table (key, value, confidence, source, created_at)
  - [ ] lessons table (rule, category, negative, source, created_at)
  - [ ] events table (audit log)

- [ ] **Storage Layer (MemoryStore)**
  - [ ] set/get facts
  - [ ] search facts (FTS or LIKE)
  - [ ] list lessons
  - [ ] add/delete lessons
  - [ ] deduplication (exact + Jaccard)

- [ ] **Consolidation**
  - [ ] Build extraction prompt
  - [ ] Call LLM
  - [ ] Parse JSON response
  - [ ] Apply with confidence threshold (≥0.8)

- [ ] **Injection**
  - [ ] Build context block
  - [ ] Filter by relevance (if selective)
  - [ ] Cap at 8KB
  - [ ] Format for system prompt

- [ ] **Lifecycle**
  - [ ] Hook: session_start (open store)
  - [ ] Hook: before_agent_start (inject context)
  - [ ] Hook: agent_end (queue messages)
  - [ ] Hook: session_shutdown (consolidate & close)

- [ ] **Tools**
  - [ ] memory_search
  - [ ] memory_remember
  - [ ] memory_forget
  - [ ] memory_stats

- [ ] **Path Resolution**
  - [ ] Project-local override (.pi/settings.json)
  - [ ] Cascade to parent/team level
  - [ ] Fall back to global (~/.pi/memory)

- [ ] **Testing**
  - [ ] Unit: CRUD ops, dedup, search
  - [ ] Integration: full session cycle
  - [ ] Edge cases: large memory, missing config, LLM failure

---

## Why This Pattern Works

1. **Automatic** — No manual intervention, happens in background
2. **Smart** — LLM understands context, not brittle rules
3. **Lightweight** — SQLite, no extra services
4. **Reusable** — Memory persists across sessions, grows with use
5. **Debuggable** — Audit log (events table) + tools to inspect
6. **Composable** — Works alongside other knowledge sources (session-search, knowledge-search)

