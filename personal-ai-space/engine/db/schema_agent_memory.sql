-- agent_memory.db: Key-value semantic memory managed by the pi-memory MCP server
-- Schema controlled by personal-ai-space/engine/memory/mcp-server/src/store.ts
-- This file documents what store.ts creates at bootstrap.

-- Permanent facts about the user, the system, and the world.
-- Each row is a single atomic assertion with a confidence score.
CREATE TABLE IF NOT EXISTS semantic (
    id TEXT PRIMARY KEY,
    key TEXT UNIQUE NOT NULL,            -- e.g. 'user.full_name', 'project.ai_powerhouse.status'
    value TEXT NOT NULL,                 -- the fact itself
    confidence REAL NOT NULL DEFAULT 0.8,
    category TEXT,                       -- 'user', 'project', 'system', 'preference', etc.
    source TEXT DEFAULT 'user',          -- 'user', 'inference', 'synthesis', 'extraction'
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    last_accessed TEXT
);

-- Learned do/don't rules from behavior observation and corrections.
-- negative=1 means "don't do this", negative=0 means "do this".
CREATE TABLE IF NOT EXISTS lessons (
    id TEXT PRIMARY KEY,
    text TEXT NOT NULL,
    category TEXT,
    negative INTEGER NOT NULL DEFAULT 0,
    source TEXT DEFAULT 'user',
    created_at TEXT NOT NULL,
    used_count INTEGER NOT NULL DEFAULT 0
);

-- Append-only audit log of every write operation against this database.
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action TEXT NOT NULL,                 -- 'add_fact', 'update_fact', 'delete_fact', 'add_lesson', etc.
    details TEXT,                         -- JSON payload with key/value/old_value
    timestamp TEXT NOT NULL
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_semantic_key        ON semantic(key);
CREATE INDEX IF NOT EXISTS idx_semantic_updated     ON semantic(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_semantic_category    ON semantic(category);
CREATE INDEX IF NOT EXISTS idx_semantic_confidence  ON semantic(confidence DESC);
CREATE INDEX IF NOT EXISTS idx_lessons_category     ON lessons(category);
CREATE INDEX IF NOT EXISTS idx_lessons_negative     ON lessons(negative);
CREATE INDEX IF NOT EXISTS idx_lessons_created      ON lessons(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_timestamp     ON events(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_events_action        ON events(action);
