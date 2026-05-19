-- activities.db: Disciplined routines & activity tracking
-- Replaces command/activities/disciplined_routines.json

CREATE TABLE IF NOT EXISTS disciplined_routines (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  frequency TEXT NOT NULL,
  time TEXT NOT NULL DEFAULT '',
  duration_minutes INTEGER DEFAULT 0,
  discipline_level TEXT NOT NULL DEFAULT 'medium',
  status TEXT NOT NULL DEFAULT 'active',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_routines_status ON disciplined_routines(status);
CREATE INDEX IF NOT EXISTS idx_routines_frequency ON disciplined_routines(frequency);
