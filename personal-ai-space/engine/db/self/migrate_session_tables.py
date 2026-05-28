# engine/db/self/migrate_session_tables.py
"""Add session extraction tables to self.db."""
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).parent / "self.db"

MIGRATION_SQL = """
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
"""


def migrate():
    conn = sqlite3.connect(str(DB_PATH))
    conn.executescript(MIGRATION_SQL)
    conn.commit()
    conn.close()
    print(f"Migration complete: {DB_PATH}")


if __name__ == "__main__":
    migrate()
