-- calendar.db: Scheduled events and calendar entries
-- Syncs from Apple Calendar via calendar-bridge + manual tasks.

CREATE TABLE IF NOT EXISTS upcoming (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_date TEXT NOT NULL,
  event_name TEXT NOT NULL,
  event_time TEXT NOT NULL DEFAULT '',
  duration_hours REAL DEFAULT 1.0,
  category TEXT NOT NULL DEFAULT 'general',
  status TEXT NOT NULL DEFAULT 'scheduled',
  account TEXT DEFAULT '',             -- Apple Calendar account (iCloud, Google, etc.)
  calendar_name TEXT DEFAULT '',       -- Calendar name (Home, Família, Feriados, etc.)
  location TEXT DEFAULT '',            -- Event location / @mention
  source TEXT DEFAULT 'manual',        -- 'apple-calendar' or 'manual'
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_upcoming_date ON upcoming(event_date);
CREATE INDEX IF NOT EXISTS idx_upcoming_status ON upcoming(status);
CREATE INDEX IF NOT EXISTS idx_upcoming_category ON upcoming(category);
CREATE INDEX IF NOT EXISTS idx_upcoming_source ON upcoming(source);
CREATE INDEX IF NOT EXISTS idx_upcoming_account ON upcoming(account);
