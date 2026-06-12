-- self.db: Your profile, habits, traits, behaviors
CREATE TABLE IF NOT EXISTS profile (
  id TEXT PRIMARY KEY,
  name TEXT,
  age INTEGER,
  timezone TEXT,
  work_style TEXT,
  energy_peak_hours TEXT,
  communication_preference TEXT,
  decision_style TEXT,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  core_values TEXT DEFAULT '',
  feedback_preference TEXT DEFAULT '',
  goals_current_year TEXT DEFAULT '',
  constraints TEXT DEFAULT '',
  created_at TEXT
);

CREATE TABLE IF NOT EXISTS habits (
  id TEXT PRIMARY KEY,
  habit_name TEXT,
  category TEXT,
  frequency TEXT,
  start_date DATE,
  current_streak INTEGER DEFAULT 0,
  total_completions INTEGER DEFAULT 0,
  last_completed DATETIME,
  target_streak INTEGER,
  status TEXT
);

CREATE TABLE IF NOT EXISTS habit_logs (
  id TEXT PRIMARY KEY,
  habit_id TEXT,
  completed_at DATETIME,
  notes TEXT,
  confidence_level FLOAT,
  FOREIGN KEY (habit_id) REFERENCES habits(id)
);

CREATE TABLE IF NOT EXISTS traits (
  id TEXT PRIMARY KEY,
  trait_name TEXT,
  category TEXT,
  confidence_score FLOAT,
  inferred_from TEXT,
  discovered_date DATE,
  updated_at DATETIME
);

CREATE TABLE IF NOT EXISTS needs (
  id TEXT PRIMARY KEY,
  category TEXT,
  name TEXT,
  priority TEXT,
  status TEXT,
  description TEXT,
  linked_tasks TEXT,
  created_at DATETIME
);

CREATE TABLE IF NOT EXISTS behaviors (
  id TEXT PRIMARY KEY,
  behavior_type TEXT,
  trigger TEXT,
  response TEXT,
  frequency INTEGER DEFAULT 1,
  effectiveness FLOAT DEFAULT 0.5,
  observed_date DATE
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_behaviors_unique ON behaviors(behavior_type, response, observed_date);

CREATE INDEX IF NOT EXISTS idx_habits_category ON habits(category);
CREATE INDEX IF NOT EXISTS idx_habits_status ON habits(status);
CREATE INDEX IF NOT EXISTS idx_habit_logs_habit ON habit_logs(habit_id);
CREATE TABLE IF NOT EXISTS relationships (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  email TEXT,
  phone TEXT,
  cpf TEXT,
  birth_date TEXT,
  relationship_type TEXT,
  notes TEXT,
  created_at TEXT,
  updated_at TEXT
);

CREATE TABLE IF NOT EXISTS goals (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  description TEXT,
  category TEXT,
  status TEXT DEFAULT 'active',
  priority INTEGER DEFAULT 0,
  progress REAL DEFAULT 0 CHECK(progress BETWEEN 0 AND 100),
  target_date TEXT,
  progress_source TEXT DEFAULT 'independent',
  created_at TEXT,
  updated_at TEXT,
  completed_at TEXT,
  tags TEXT DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_traits_confidence ON traits(confidence_score DESC);

-- Observations: persistent behavioral data collected by the monitoring system
-- Survives engine restarts for cross-session learning and pattern analysis
CREATE TABLE IF NOT EXISTS observations (
  id TEXT PRIMARY KEY,
  obs_type TEXT NOT NULL,
  observed_at DATETIME NOT NULL,
  data TEXT NOT NULL,
  source TEXT DEFAULT 'engine',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_observations_type ON observations(obs_type);
CREATE INDEX IF NOT EXISTS idx_observations_observed_at ON observations(observed_at);

-- Documents: structured metadata for personal documents (resumes, bios, portfolios, etc.)
-- Supports both .md with frontmatter and binary formats referenced via index.json
CREATE TABLE IF NOT EXISTS documents (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  doc_type TEXT NOT NULL,
  subcategory TEXT DEFAULT '',
  tags TEXT DEFAULT '[]',
  file_path TEXT DEFAULT '',
  file_format TEXT DEFAULT '',
  content TEXT DEFAULT '',
  metadata TEXT DEFAULT '{}',
  created_at TEXT,
  updated_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_documents_type ON documents(doc_type);
CREATE INDEX IF NOT EXISTS idx_documents_subcategory ON documents(subcategory);

-- Session signals: extracted behavioral signals from OpenCode transcripts
CREATE TABLE IF NOT EXISTS session_signals (
    id TEXT PRIMARY KEY,
    signal_type TEXT NOT NULL,
    content TEXT NOT NULL,
    session_id TEXT NOT NULL,
    agent TEXT,
    model TEXT,
    source TEXT,
    observed_at TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_session_signals_type ON session_signals(signal_type);
CREATE INDEX IF NOT EXISTS idx_session_signals_session ON session_signals(session_id);
CREATE INDEX IF NOT EXISTS idx_session_signals_observed ON session_signals(observed_at);

-- Session metadata: aggregate stats per OpenCode session
CREATE TABLE IF NOT EXISTS session_metadata (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL UNIQUE,
    title TEXT,
    agent TEXT,
    model TEXT,
    cost REAL DEFAULT 0,
    tokens_input INTEGER DEFAULT 0,
    tokens_output INTEGER DEFAULT 0,
    message_count INTEGER DEFAULT 0,
    duration_seconds INTEGER DEFAULT 0,
    date TEXT NOT NULL,
    extracted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_session_metadata_date ON session_metadata(date);
CREATE INDEX IF NOT EXISTS idx_session_metadata_agent ON session_metadata(agent);
