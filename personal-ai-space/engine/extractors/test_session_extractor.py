# engine/extractors/test_session_extractor.py
import pytest
import sqlite3
import tempfile
from pathlib import Path

class TestSessionTablesExist:
    def test_session_signals_table_exists(self, tmp_path):
        """session_signals table should exist after migration."""
        db_path = tmp_path / "self.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE session_signals (
                id TEXT PRIMARY KEY,
                signal_type TEXT NOT NULL,
                content TEXT NOT NULL,
                session_id TEXT NOT NULL,
                agent TEXT,
                model TEXT,
                source TEXT,
                observed_at TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        result = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='session_signals'").fetchone()
        assert result is not None
        conn.close()

    def test_session_metadata_table_exists(self, tmp_path):
        """session_metadata table should exist after migration."""
        db_path = tmp_path / "self.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE session_metadata (
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
            )
        """)
        result = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='session_metadata'").fetchone()
        assert result is not None
        conn.close()
