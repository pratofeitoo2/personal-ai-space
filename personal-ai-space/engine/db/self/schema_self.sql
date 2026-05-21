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
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
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
  frequency INTEGER,
  effectiveness FLOAT,
  observed_date DATE
);

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
  completed_at TEXT
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
