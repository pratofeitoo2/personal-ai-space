# pi-memory Reverse Engineering: Complete Analysis

This directory contains a comprehensive reverse engineering of the `@samfp/pi-memory` package—an extremely useful persistent memory system for AI agents that learns from sessions and injects knowledge into future conversations.

## 📚 Documents in This Analysis

### 1. **pi-memory-reverse-engineering.md** (Main Report)
   - **Executive summary** of the package and its purpose
   - **Architecture overview** (three-phase lifecycle)
   - **Complete database schema** (semantic, lessons, events tables)
   - **File structure** breakdown (src/ organization)
   - **Core components** deep-dive (MemoryStore, Injector, Consolidator, Bootstrap)
   - **Data flow diagrams** (injection and consolidation)
   - **Key design decisions** and trade-offs
   - **Integration points** with pi SDK
   - **Why it works**: simplicity + usefulness explained
   - **Configuration & customization** options

### 2. **implementation-patterns.md** (Practical Patterns)
   - **7 reusable code patterns** you can apply to your own projects
   - Real TypeScript examples for:
     - SQLite + WAL setup
     - Confidence-based storage
     - LLM-based extraction
     - Selective injection
     - Jaccard similarity deduplication
     - Path resolution cascading
     - Lifecycle hooks integration
   - **Architecture dataflow diagram** (ASCII art)
   - **4 common use cases** with implementations
   - **6-week implementation roadmap** (from scratch to production)
   - **Complete checklist** for your own memory system

### 3. **technical-deep-dive.md** (Reference)
   - **One-page overview** of what/why/how
   - **Database tables explained** with examples
   - **Core classes & methods** reference
   - **All 4 lifecycle hooks** detailed
   - **5 tools exposed** (MCP interface)
   - **Deduplication strategy** (exact + Jaccard)
   - **Path resolution** priority order
   - **Consolidation prompt** (what to extract, what not to)
   - **SQLite pragmas** explained
   - **Performance characteristics** (storage, speed, cost)
   - **What makes it special** (vs alternatives)
   - **Potential pitfalls** and mitigations
   - **Extensibility points** for customization

---

## 🎯 Quick Start: Which Document to Read?

**I want to understand the architecture...**
→ Start with `pi-memory-reverse-engineering.md`

**I want to build my own memory system...**
→ Go to `implementation-patterns.md` (skip to Phase 1 checklist)

**I need a quick reference for specifics...**
→ Use `technical-deep-dive.md` (one-page lookup)

**I need working code examples...**
→ `implementation-patterns.md` has 7 ready-to-use patterns

---

## 🏗️ Architecture Summary

### The Core Idea
```
Session Start
    ↓
[INJECT] Load memory → inject into system prompt
    ↓
Session Running
    ↓
[COLLECT] Queue messages for consolidation
    ↓
Session End
    ↓
[CONSOLIDATE] Extract structured knowledge (via LLM) → store
    ↓
[REUSE] Memory injected in next session
```

### Key Innovation
Unlike simple keystroke recording, pi-memory:
- **Extracts high-confidence facts** (e.g., "pref.commit_style" → "conventional commits")
- **Learns from corrections** (e.g., "don't use echo >>, use sed")
- **Deduplicates intelligently** (Jaccard similarity ≥0.7)
- **Injects selectively** by relevance (can filter lessons to save context)

---

## 💾 Database Schema (3 Tables)

```sql
-- 1. Semantic facts (key-value preferences & patterns)
semantic (
  key TEXT PRIMARY KEY,           -- pref.X, project.Y.Z, tool.A
  value TEXT,                     -- "conventional commits"
  confidence REAL (0.0-1.0),      -- 0.8+ to avoid noise
  source TEXT,                    -- 'consolidation' | 'user' | 'correction'
  created_at TEXT,
  updated_at TEXT,
  last_accessed TEXT
)

-- 2. Lessons (learned corrections & validations)
lessons (
  id TEXT PRIMARY KEY,
  rule TEXT,                      -- "Use sed, not echo >>"
  category TEXT,                  -- "vault", "git", "devops"
  negative INTEGER,               -- 1 = avoid, 0 = validated
  source TEXT,
  is_deleted INTEGER,             -- soft delete
  created_at TEXT
)

-- 3. Events (audit log)
events (
  id INTEGER PRIMARY KEY,
  event_type TEXT,                -- 'store', 'update', 'delete'
  memory_type TEXT,               -- 'semantic' | 'lesson'
  memory_key TEXT,                -- which fact/lesson
  details TEXT,                   -- source session, etc
  created_at TEXT
)
```

---

## 🔄 Lifecycle Hooks

| Hook | Trigger | Action |
|------|---------|--------|
| `session_start` | Session begins | Open store, inject memory stats |
| `before_agent_start` | Agent about to run | Build context block, inject into system prompt |
| `agent_end` | Agent message sent | Queue for consolidation |
| `session_shutdown` | Session ending | Consolidate (if ≥3 user msgs), close store |

---

## 🛠️ Tools Exposed (MCP)

| Tool | Purpose |
|------|---------|
| `memory_search(query)` | Search facts by keyword |
| `memory_remember(key, value)` | Manually add/update fact |
| `memory_forget(key)` | Delete fact |
| `memory_lessons(category?)` | List learned corrections |
| `memory_stats()` | Show memory statistics |

---

## 🧠 Why It's Useful

### The Problem It Solves
Agents forget everything between sessions. Every session starts from scratch, even if you corrected the same mistake yesterday or used the same tool consistently.

### The Solution
Automatically:
1. Learn what works (consolidation via LLM)
2. Remember what you learned (persistent SQLite)
3. Inject relevant knowledge (selective + smart filtering)
4. Reuse across sessions (transparent, no manual effort)

### The Key Insight
Instead of recording *what you did* (imperative history), record *what you learned* (declarative knowledge).

---

## 📊 Performance

- **Database size**: ~1MB per 1000 facts (with events log)
- **Search speed**: <50ms (FTS5), <200ms (LIKE fallback)
- **Memory injection**: <5ms
- **LLM cost**: ~$0.01-0.05 per session (gpt-4o-mini, if ≥3 messages)
- **Typical growth**: ~100 facts + 20 lessons per 50 sessions

---

## 🔧 Implementation Roadmap

| Phase | Focus | Duration |
|-------|-------|----------|
| 1 | SQLite schema + CRUD | Week 1 |
| 2 | LLM consolidation | Week 2 |
| 3 | Dedup + lessons | Week 3 |
| 4 | Selective injection | Week 4 |
| 5 | Multi-project support | Week 5 |
| 6 | Tools + UX | Week 6 |

See `implementation-patterns.md` for detailed checklist.

---

## 🎨 Design Patterns You Can Reuse

1. **SQLite + WAL** for concurrent reads
2. **Confidence scores** to avoid noise
3. **LLM extraction** (smart, not brittle)
4. **Selective injection** (preserve context)
5. **Jaccard similarity** for dedup
6. **Path cascade** for multi-project
7. **Lifecycle hooks** for agent integration

All documented with code examples in `implementation-patterns.md`.

---

## 🔍 What Makes It "Simple Yet Powerful"

### Simplicity (Architectural)
- ✅ No external services (SQLite is self-contained)
- ✅ Single lifecycle (4 hooks cover everything)
- ✅ Stateless LLM calls (no streaming, no complex state)
- ✅ Minimal schema (3 tables, straightforward)

### Power (Practical)
- ✅ Automatic learning (happens in background)
- ✅ Smart injection (relevant memories, not all)
- ✅ Corrections stick (learn from mistakes once)
- ✅ Low context cost (8KB max, or less with selective mode)
- ✅ Cross-project isolation (projects can have separate memory)

---

## 📁 Source Location

Package: `@samfp/pi-memory` v1.0.4
Repository: https://github.com/samfoy/pi-memory
Installed at: `~/.npm-global/lib/node_modules/@samfp/pi-memory/`

Source files:
- `src/index.ts` — Extension entry point (lifecycle hooks, tools)
- `src/store.ts` — SQLite wrapper (CRUD + search)
- `src/injector.ts` — Context block builder (selective/fallback modes)
- `src/consolidator.ts` — LLM extraction + dedup
- `src/bootstrap.ts` — One-time migration tool

---

## 🚀 Next Steps

1. **For learning**: Read `pi-memory-reverse-engineering.md` (complete overview)
2. **For building**: Reference `implementation-patterns.md` (7 patterns + roadmap)
3. **For debugging**: Use `technical-deep-dive.md` (quick lookup)
4. **For code**: Check `~/.npm-global/lib/node_modules/@samfp/pi-memory/src/` (real implementation)

---

## 💡 Key Takeaway

**pi-memory succeeds because it combines**:
- Simple storage (SQLite, not distributed databases)
- Smart extraction (LLM, not brittle rules)
- Confidence filtering (high bar, not all noise)
- Selective injection (relevant facts, not context bloat)
- Path resolution (multi-project, not single-user thinking)

**The result**: Feels like the agent is learning. Works transparently. No UX overhead. Debuggable. Extensible.

---

Generated: 2026-05-05
Analyzed: `@samfp/pi-memory@1.0.4`
