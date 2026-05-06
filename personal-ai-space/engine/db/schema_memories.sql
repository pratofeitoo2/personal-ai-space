-- memories.db: Indexed interactions and context
CREATE TABLE IF NOT EXISTS interactions (
  id TEXT PRIMARY KEY,
  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
  agent_id TEXT NOT NULL,
  action TEXT NOT NULL,
  input_data TEXT,
  output_data TEXT,
  duration_ms INTEGER,
  status TEXT,
  error_message TEXT,
  context TEXT
);

CREATE TABLE IF NOT EXISTS context_window (
  id TEXT PRIMARY KEY,
  session_id TEXT,
  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
  content TEXT,
  embedding BLOB,
  relevance_score FLOAT,
  expires_at DATETIME
);

CREATE TABLE IF NOT EXISTS agent_memory (
  id TEXT PRIMARY KEY,
  agent_id TEXT,
  key TEXT,
  value TEXT,
  ttl_seconds INTEGER,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(agent_id, key)
);

CREATE INDEX IF NOT EXISTS idx_interactions_agent ON interactions(agent_id);
CREATE INDEX IF NOT EXISTS idx_interactions_timestamp ON interactions(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_context_session ON context_window(session_id);
