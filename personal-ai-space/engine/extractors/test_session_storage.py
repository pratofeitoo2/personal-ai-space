# engine/extractors/test_session_storage.py
import pytest
import sqlite3
import tempfile
from pathlib import Path


class TestSessionStorage:
    def setup_method(self):
        """Create in-memory test database with schema."""
        self.db_path = tempfile.mktemp(suffix='.db')
        conn = sqlite3.connect(self.db_path)
        conn.executescript("""
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
            );
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
            );
        """)
        conn.close()

    def teardown_method(self):
        """Clean up test database."""
        Path(self.db_path).unlink(missing_ok=True)

    def test_upsert_signal(self):
        """Upserting a signal should insert it into session_signals."""
        from extractors.session_storage import SessionStorage

        storage = SessionStorage(self.db_path)
        signal = {
            'id': 'test_signal_1',
            'signal_type': 'user_message',
            'content': 'I want to refactor the auth module',
            'session_id': 'ses_test1',
            'agent': 'general',
            'model': 'gpt-4',
            'source': 'opencode',
            'observed_at': '2026-05-28T12:00:00Z',
        }

        storage.upsert_signal(signal)

        conn = sqlite3.connect(self.db_path)
        row = conn.execute("SELECT * FROM session_signals WHERE id = ?", ('test_signal_1',)).fetchone()
        conn.close()

        assert row is not None
        assert row[1] == 'user_message'  # signal_type
        assert row[2] == 'I want to refactor the auth module'  # content

    def test_upsert_session_metadata(self):
        """Upserting session metadata should insert it."""
        from extractors.session_storage import SessionStorage

        storage = SessionStorage(self.db_path)
        metadata = {
            'id': 'test_meta_1',
            'session_id': 'ses_test1',
            'title': 'Test Session',
            'agent': 'general',
            'model': 'gpt-4',
            'cost': 0.5,
            'tokens_input': 1000,
            'tokens_output': 500,
            'message_count': 10,
            'duration_seconds': 3600,
            'date': '2026-05-28',
        }

        storage.upsert_session_metadata(metadata)

        conn = sqlite3.connect(self.db_path)
        row = conn.execute("SELECT * FROM session_metadata WHERE session_id = ?", ('ses_test1',)).fetchone()
        conn.close()

        assert row is not None
        assert row[2] == 'Test Session'  # title

    def test_upsert_is_idempotent(self):
        """Upserting same signal twice should not duplicate."""
        from extractors.session_storage import SessionStorage

        storage = SessionStorage(self.db_path)
        signal = {
            'id': 'test_signal_1',
            'signal_type': 'user_message',
            'content': 'I want to refactor the auth module',
            'session_id': 'ses_test1',
            'agent': 'general',
            'model': 'gpt-4',
            'source': 'opencode',
            'observed_at': '2026-05-28T12:00:00Z',
        }

        storage.upsert_signal(signal)
        storage.upsert_signal(signal)  # Duplicate

        conn = sqlite3.connect(self.db_path)
        count = conn.execute("SELECT COUNT(*) FROM session_signals WHERE id = ?", ('test_signal_1',)).fetchone()[0]
        conn.close()

        assert count == 1
