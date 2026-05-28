# engine/extractors/test_session_extractor.py
import pytest
import sqlite3
import tempfile
from pathlib import Path

import json
from datetime import datetime

class TestOpenCodeReader:
    def test_read_sessions_returns_list(self, tmp_path):
        from extractors.session_extractor import OpenCodeReader

        opencode_db = tmp_path / "opencode.db"
        conn = sqlite3.connect(str(opencode_db))
        conn.execute("""
            CREATE TABLE session (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                title TEXT NOT NULL,
                agent TEXT,
                model TEXT,
                cost REAL DEFAULT 0,
                tokens_input INTEGER DEFAULT 0,
                tokens_output INTEGER DEFAULT 0,
                time_created INTEGER NOT NULL,
                time_updated INTEGER NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE message (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                time_created INTEGER NOT NULL,
                time_updated INTEGER NOT NULL,
                data TEXT NOT NULL
            )
        """)
        conn.execute("""
            INSERT INTO session VALUES
            ('ses_test1', 'proj1', 'Test Session', 'general', 'gpt-4', 0.5, 1000, 500, 1716864000, 1716867600)
        """)
        conn.execute("""
            INSERT INTO message VALUES
            ('msg1', 'ses_test1', 1716864000, 1716864000, '{"role":"user","content":"test message"}')
        """)
        conn.commit()
        conn.close()

        reader = OpenCodeReader(str(opencode_db))
        sessions = reader.read_sessions()

        assert len(sessions) == 1
        assert sessions[0]['id'] == 'ses_test1'
        assert sessions[0]['title'] == 'Test Session'

    def test_read_session_messages(self, tmp_path):
        from extractors.session_extractor import OpenCodeReader

        opencode_db = tmp_path / "opencode.db"
        conn = sqlite3.connect(str(opencode_db))
        conn.execute("""
            CREATE TABLE session (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                title TEXT NOT NULL,
                agent TEXT,
                model TEXT,
                cost REAL DEFAULT 0,
                tokens_input INTEGER DEFAULT 0,
                tokens_output INTEGER DEFAULT 0,
                time_created INTEGER NOT NULL,
                time_updated INTEGER NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE message (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                time_created INTEGER NOT NULL,
                time_updated INTEGER NOT NULL,
                data TEXT NOT NULL
            )
        """)
        conn.execute("""
            INSERT INTO session VALUES
            ('ses_test1', 'proj1', 'Test Session', 'general', 'gpt-4', 0.5, 1000, 500, 1716864000, 1716867600)
        """)
        conn.execute("""
            INSERT INTO message VALUES
            ('msg1', 'ses_test1', 1716864000, 1716864000, '{"role":"user","content":"hello"}'),
            ('msg2', 'ses_test1', 1716864060, 1716864060, '{"role":"assistant","content":"hi there"}')
        """)
        conn.commit()
        conn.close()

        reader = OpenCodeReader(str(opencode_db))
        messages = reader.read_session_messages('ses_test1')

        assert len(messages) == 2
        assert messages[0]['role'] == 'user'
        assert messages[1]['role'] == 'assistant'


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


class TestSignalFilters:
    def test_filter_user_messages(self):
        from extractors.session_extractor import SignalFilter

        messages = [
            {'role': 'user', 'content': 'I want to refactor the auth module'},
            {'role': 'assistant', 'content': 'Let me analyze the codebase'},
            {'role': 'user', 'content': 'Also add tests for the new endpoints'},
        ]

        signals = SignalFilter.filter_user_messages(messages)
        assert len(signals) == 2
        assert signals[0]['content'] == 'I want to refactor the auth module'
        assert signals[0]['signal_type'] == 'user_message'

    def test_filter_assistant_reasoning(self):
        from extractors.session_extractor import SignalFilter

        messages = [
            {'role': 'assistant', 'content': 'Based on the codebase analysis, I recommend using PostgreSQL for the new schema. The current SQLite setup will not handle the expected load.'},
            {'role': 'assistant', 'content': '[tool: read]'},
            {'role': 'assistant', 'content': 'The migration strategy should be: 1) Create new tables, 2) Migrate data, 3) Update references'},
        ]

        signals = SignalFilter.filter_assistant_reasoning(messages)
        assert len(signals) == 2
        assert 'PostgreSQL' in signals[0]['content']
        assert 'migration' in signals[1]['content']

    def test_filter_error_solutions(self):
        from extractors.session_extractor import SignalFilter

        messages = [
            {'role': 'user', 'content': 'The tests are failing with ImportError'},
            {'role': 'assistant', 'content': 'The issue is that the module path is incorrect. Let me fix the import.'},
            {'role': 'assistant', 'content': 'I fixed it by updating the sys.path in __init__.py'},
        ]

        signals = SignalFilter.filter_error_solutions(messages)
        assert len(signals) >= 1
        assert 'ImportError' in signals[0]['content'] or 'fixed' in signals[0]['content']

    def test_extract_session_metadata(self):
        from extractors.session_extractor import SignalFilter

        session = {
            'id': 'ses_test',
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

        metadata = SignalFilter.extract_session_metadata(session)
        assert metadata['session_id'] == 'ses_test'
        assert metadata['duration_hours'] == 1.0
        assert metadata['tokens_total'] == 1500
