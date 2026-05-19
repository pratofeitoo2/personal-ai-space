-- calendar.db: Scheduled events and calendar entries
-- Replaces command/calendar/upcoming.csv

CREATE TABLE IF NOT EXISTS upcoming (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_date TEXT NOT NULL,
  event_name TEXT NOT NULL,
  event_time TEXT NOT NULL DEFAULT '',
  duration_hours REAL DEFAULT 1.0,
  category TEXT NOT NULL DEFAULT 'general',
  status TEXT NOT NULL DEFAULT 'scheduled',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_upcoming_date ON upcoming(event_date);
CREATE INDEX IF NOT EXISTS idx_upcoming_status ON upcoming(status);
CREATE INDEX IF NOT EXISTS idx_upcoming_category ON upcoming(category);
