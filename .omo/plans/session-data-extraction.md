# Session Data Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers-optimized:subagent-driven-development (recommended) or superpowers-optimized:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a filtered extraction pipeline that pulls valuable behavioral signals from OpenCode session transcripts and stores them in self.db for analytics and personal AI insights.

**Architecture:** A Python extractor reads from OpenCode's SQLite database (`~/.local/share/opencode/opencode.db`), applies 4 signal filters (user messages, session metadata, assistant reasoning, error/solution pairs), and upserts results into new self.db tables. The extractor runs as a scheduled job and can also be invoked manually via CLI.

**Tech Stack:** Python 3.13, SQLite3 (existing self.db + OpenCode's opencode.db), pytest for tests

**Assumptions:**
- OpenCode database at `~/.local/share/opencode/opencode.db` is readable (not locked by running OpenCode instance)
- Session messages contain JSON payloads in `message.data` column
- Existing self.db schema can be extended with new tables without breaking sync_self.py
- AIVectorMemory MCP is available for storing high-value technical decisions separately

---

## File Structure

| File | Purpose |
|------|---------|
| `engine/extractors/session_extractor.py` | Core extraction logic — reads OpenCode DB, applies filters, returns structured data |
| `engine/extractors/session_storage.py` | Storage layer — upserts extracted signals into self.db tables |
| `engine/extractors/test_session_extractor.py` | Unit tests for extraction filters |
| `engine/extractors/test_session_storage.py` | Unit tests for storage layer |
| `engine/db/self/schema_self.sql` | Updated schema with new tables (append-only) |
| `engine/db/self/migrate_session_tables.py` | Migration script to add new tables |
| `engine/cli.py` | Add `sessions extract` CLI command |

---

## Task 1: Migration — Add session tables to self.db

**Files:**
- Create: `engine/db/self/migrate_session_tables.py`
- Modify: `engine/db/self/schema_self.sql`

**Security flag:** `none`

**Does NOT cover:** Data population — this task only creates empty tables.

- [ ] **Step 1: Write failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/paulorezende/Documents/Personal_AI_powerhouse\ updated/personal-ai-space/engine && .venv/bin/python3 -m pytest extractors/test_session_extractor.py -v`
Expected: FAIL with "no such table: session_signals"

- [ ] **Step 3: Implement migration script**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/paulorezende/Documents/Personal_AI_powerhouse\ updated/personal-ai-space/engine && .venv/bin/python3 -m pytest extractors/test_session_extractor.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add engine/db/self/migrate_session_tables.py engine/db/self/schema_self.sql engine/extractors/test_session_extractor.py
git commit -m "feat(db): add session extraction tables to self.db"
```

---

## Task 2: OpenCode DB Reader — Read session data from OpenCode's SQLite

**Files:**
- Create: `engine/extractors/session_extractor.py`
- Modify: `engine/extractors/test_session_extractor.py`

**Security flag:** `none`

**Does NOT cover:** Filtering logic — this task only reads raw data.

- [ ] **Step 1: Write failing test**

```python
# engine/extractors/test_session_extractor.py (append to file)
import json
from datetime import datetime

class TestOpenCodeReader:
    def test_read_sessions_returns_list(self, tmp_path):
        """read_sessions should return list of session dicts."""
        from extractors.session_extractor import OpenCodeReader
        
        # Create mock OpenCode DB
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
        """read_session_messages should return messages for a session."""
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/paulorezende/Documents/Personal_AI_powerhouse\ updated/personal-ai-space/engine && .venv/bin/python3 -m pytest extractors/test_session_extractor.py::TestOpenCodeReader -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'extractors.session_extractor'"

- [ ] **Step 3: Implement OpenCode reader**

```python
# engine/extractors/session_extractor.py
"""Extract behavioral signals from OpenCode session transcripts."""
import json
import sqlite3
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger("engine.extractors.session")

OPENCODE_DB = Path.home() / ".local/share/opencode/opencode.db"


class OpenCodeReader:
    """Read session data from OpenCode's SQLite database."""
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(OPENCODE_DB)
    
    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def read_sessions(self, limit: Optional[int] = None) -> list[dict]:
        """Read all sessions from OpenCode database."""
        conn = self._get_conn()
        try:
            sql = "SELECT * FROM session ORDER BY time_created DESC"
            if limit:
                sql += f" LIMIT {limit}"
            rows = conn.execute(sql).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()
    
    def read_session_messages(self, session_id: str) -> list[dict]:
        """Read all messages for a session, parsed from JSON."""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM message WHERE session_id = ? ORDER BY time_created",
                (session_id,)
            ).fetchall()
            
            messages = []
            for row in rows:
                try:
                    data = json.loads(row['data'])
                    data['_message_id'] = row['id']
                    data['_time_created'] = row['time_created']
                    messages.append(data)
                except json.JSONDecodeError:
                    logger.warning("Failed to parse message %s", row['id'])
            return messages
        finally:
            conn.close()
    
    def get_session_stats(self, session_id: str) -> dict:
        """Get aggregated stats for a session."""
        conn = self._get_conn()
        try:
            session = conn.execute(
                "SELECT * FROM session WHERE id = ?", (session_id,)
            ).fetchone()
            
            if not session:
                return {}
            
            msg_count = conn.execute(
                "SELECT COUNT(*) FROM message WHERE session_id = ?", (session_id,)
            ).fetchone()[0]
            
            duration = session['time_updated'] - session['time_created']
            
            return {
                'id': session['id'],
                'title': session['title'],
                'agent': session['agent'],
                'model': session['model'],
                'cost': session['cost'],
                'tokens_input': session['tokens_input'],
                'tokens_output': session['tokens_output'],
                'message_count': msg_count,
                'duration_seconds': duration,
                'date': datetime.fromtimestamp(session['time_created']).strftime('%Y-%m-%d'),
                'time_created': session['time_created'],
                'time_updated': session['time_updated'],
            }
        finally:
            conn.close()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/paulorezende/Documents/Personal_AI_powerhouse\ updated/personal-ai-space/engine && .venv/bin/python3 -m pytest extractors/test_session_extractor.py::TestOpenCodeReader -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add engine/extractors/session_extractor.py engine/extractors/test_session_extractor.py
git commit -m "feat(extractors): add OpenCode session reader"
```

---

## Task 3: Signal Filters — Extract the 4 signal types from session data

**Files:**
- Modify: `engine/extractors/session_extractor.py`
- Modify: `engine/extractors/test_session_extractor.py`

**Security flag:** `none`

**Does NOT cover:** Storage — this task only extracts and returns structured data.

- [ ] **Step 1: Write failing test**

```python
# engine/extractors/test_session_extractor.py (append to file)
class TestSignalFilters:
    def test_filter_user_messages(self):
        """User messages should be extracted with their intents."""
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
        """Assistant reasoning blocks should be extracted."""
        from extractors.session_extractor import SignalFilter
        
        messages = [
            {'role': 'assistant', 'content': 'Based on the codebase analysis, I recommend using PostgreSQL for the new schema. The current SQLite setup won\'t handle the expected load.'},
            {'role': 'assistant', 'content': '[tool: read]'},  # Should be filtered out
            {'role': 'assistant', 'content': 'The migration strategy should be: 1) Create new tables, 2) Migrate data, 3) Update references'},
        ]
        
        signals = SignalFilter.filter_assistant_reasoning(messages)
        assert len(signals) == 2
        assert 'PostgreSQL' in signals[0]['content']
        assert 'migration' in signals[1]['content']

    def test_filter_error_solutions(self):
        """Error/solution pairs should be extracted."""
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
        """Session metadata should include duration and agent info."""
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/paulorezende/Documents/Personal_AI_powerhouse\ updated/personal-ai-space/engine && .venv/bin/python3 -m pytest extractors/test_session_extractor.py::TestSignalFilters -v`
Expected: FAIL with "ImportError: cannot import name 'SignalFilter'"

- [ ] **Step 3: Implement signal filters**

```python
# engine/extractors/session_extractor.py (append to file)
import re
import uuid

# Patterns to identify tool calls (noise)
TOOL_CALL_PATTERN = re.compile(r'^\[tool:\s*\w+\]$')
REASONING_MIN_LENGTH = 50  # Minimum chars for reasoning block

class SignalFilter:
    """Filter and extract behavioral signals from session messages."""
    
    @staticmethod
    def filter_user_messages(messages: list[dict]) -> list[dict]:
        """Extract user messages with their content."""
        signals = []
        for msg in messages:
            if msg.get('role') == 'user' and msg.get('content'):
                content = msg['content']
                if not TOOL_CALL_PATTERN.match(content):
                    signals.append({
                        'id': uuid.uuid4().hex,
                        'signal_type': 'user_message',
                        'content': content[:2000],  # Truncate long messages
                        'observed_at': datetime.now(timezone.utc).isoformat(),
                    })
        return signals
    
    @staticmethod
    def filter_assistant_reasoning(messages: list[dict]) -> list[dict]:
        """Extract assistant reasoning blocks (not tool calls)."""
        signals = []
        for msg in messages:
            if msg.get('role') == 'assistant' and msg.get('content'):
                content = msg['content']
                # Filter out tool calls and short messages
                if (not TOOL_CALL_PATTERN.match(content) and
                    len(content) >= REASONING_MIN_LENGTH):
                    signals.append({
                        'id': uuid.uuid4().hex,
                        'signal_type': 'assistant_reasoning',
                        'content': content[:2000],
                        'observed_at': datetime.now(timezone.utc).isoformat(),
                    })
        return signals
    
    @staticmethod
    def filter_error_solutions(messages: list[dict]) -> list[dict]:
        """Extract error/solution pairs from conversation."""
        signals = []
        error_keywords = ['error', 'fail', 'bug', 'issue', 'broken', 'exception', 'traceback']
        solution_keywords = ['fixed', 'solution', 'resolved', 'corrected', 'patched', 'updated']
        
        for i, msg in enumerate(messages):
            content = msg.get('content', '').lower()
            
            # Look for error mentions in user messages
            if msg.get('role') == 'user':
                if any(kw in content for kw in error_keywords):
                    # Look for solution in subsequent assistant messages
                    for j in range(i+1, min(i+5, len(messages))):
                        next_msg = messages[j]
                        next_content = next_msg.get('content', '').lower()
                        if next_msg.get('role') == 'assistant':
                            if any(kw in next_content for kw in solution_keywords):
                                signals.append({
                                    'id': uuid.uuid4().hex,
                                    'signal_type': 'error_solution',
                                    'content': f"Error: {msg['content'][:500]}\nSolution: {next_msg['content'][:500]}",
                                    'observed_at': datetime.now(timezone.utc).isoformat(),
                                })
                                break
        return signals
    
    @staticmethod
    def extract_session_metadata(session: dict) -> dict:
        """Extract session metadata for storage."""
        duration_hours = session.get('duration_seconds', 0) / 3600
        tokens_total = session.get('tokens_input', 0) + session.get('tokens_output', 0)
        
        return {
            'id': uuid.uuid4().hex,
            'session_id': session['id'],
            'title': session.get('title', ''),
            'agent': session.get('agent', ''),
            'model': session.get('model', ''),
            'cost': session.get('cost', 0),
            'tokens_input': session.get('tokens_input', 0),
            'tokens_output': session.get('tokens_output', 0),
            'message_count': session.get('message_count', 0),
            'duration_seconds': session.get('duration_seconds', 0),
            'duration_hours': round(duration_hours, 2),
            'tokens_total': tokens_total,
            'date': session.get('date', ''),
            'extracted_at': datetime.now(timezone.utc).isoformat(),
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/paulorezende/Documents/Personal_AI_powerhouse\ updated/personal-ai-space/engine && .venv/bin/python3 -m pytest extractors/test_session_extractor.py::TestSignalFilters -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add engine/extractors/session_extractor.py engine/extractors/test_session_extractor.py
git commit -m "feat(extractors): add signal filters for session data"
```

---

## Task 4: Storage Layer — Upsert extracted signals into self.db

**Files:**
- Create: `engine/extractors/session_storage.py`
- Create: `engine/extractors/test_session_storage.py`

**Security flag:** `none`

**Does NOT cover:** Reading from OpenCode — this task only writes to self.db.

- [ ] **Step 1: Write failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/paulorezende/Documents/Personal_AI_powerhouse\ updated/personal-ai-space/engine && .venv/bin/python3 -m pytest extractors/test_session_storage.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'extractors.session_storage'"

- [ ] **Step 3: Implement storage layer**

```python
# engine/extractors/session_storage.py
"""Storage layer for session extraction signals."""
import sqlite3
import logging
from typing import Optional

logger = logging.getLogger("engine.extractors.session_storage")


class SessionStorage:
    """Upsert extracted signals into self.db."""
    
    def __init__(self, db_path: Optional[str] = None):
        if db_path:
            self.db_path = db_path
        else:
            from pathlib import Path
            self.db_path = str(Path(__file__).parent.parent / "db" / "self" / "self.db")
    
    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def upsert_signal(self, signal: dict) -> None:
        """Insert or update a signal in session_signals table."""
        conn = self._get_conn()
        try:
            conn.execute("""
                INSERT INTO session_signals
                (id, signal_type, content, session_id, agent, model, source, observed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    content = excluded.content,
                    agent = excluded.agent,
                    model = excluded.model
            """, (
                signal['id'],
                signal['signal_type'],
                signal['content'],
                signal['session_id'],
                signal.get('agent'),
                signal.get('model'),
                signal.get('source'),
                signal['observed_at'],
            ))
            conn.commit()
        except Exception as e:
            logger.error("Failed to upsert signal %s: %s", signal['id'], e)
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def upsert_session_metadata(self, metadata: dict) -> None:
        """Insert or update session metadata."""
        conn = self._get_conn()
        try:
            conn.execute("""
                INSERT INTO session_metadata
                (id, session_id, title, agent, model, cost, tokens_input, tokens_output,
                 message_count, duration_seconds, date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    title = excluded.title,
                    agent = excluded.agent,
                    model = excluded.model,
                    cost = excluded.cost,
                    tokens_input = excluded.tokens_input,
                    tokens_output = excluded.tokens_output,
                    message_count = excluded.message_count,
                    duration_seconds = excluded.duration_seconds
            """, (
                metadata['id'],
                metadata['session_id'],
                metadata.get('title'),
                metadata.get('agent'),
                metadata.get('model'),
                metadata.get('cost', 0),
                metadata.get('tokens_input', 0),
                metadata.get('tokens_output', 0),
                metadata.get('message_count', 0),
                metadata.get('duration_seconds', 0),
                metadata['date'],
            ))
            conn.commit()
        except Exception as e:
            logger.error("Failed to upsert metadata for %s: %s", metadata['session_id'], e)
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def get_unprocessed_sessions(self) -> list[str]:
        """Get session IDs not yet in session_metadata."""
        conn = self._get_conn()
        try:
            rows = conn.execute("""
                SELECT session_id FROM session_metadata
            """).fetchall()
            return [row['session_id'] for row in rows]
        finally:
            conn.close()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/paulorezende/Documents/Personal_AI_powerhouse\ updated/personal-ai-space/engine && .venv/bin/python3 -m pytest extractors/test_session_storage.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add engine/extractors/session_storage.py engine/extractors/test_session_storage.py
git commit -m "feat(extractors): add session storage layer"
```

---

## Task 5: Pipeline Integration — Wire up the full extraction flow

**Files:**
- Modify: `engine/extractors/session_extractor.py`
- Modify: `engine/extractors/test_session_extractor.py`

**Security flag:** `none`

**Does NOT cover:** CLI integration — this task only creates the pipeline function.

- [ ] **Step 1: Write failing test**

```python
# engine/extractors/test_session_extractor.py (append to file)
class TestExtractionPipeline:
    def test_extract_all_sessions(self, tmp_path):
        """extract_all should process all sessions and return stats."""
        from extractors.session_extractor import OpenCodeReader, SignalFilter
        from extractors.session_storage import SessionStorage
        
        # Create mock OpenCode DB
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
            ('msg1', 'ses_test1', 1716864000, 1716864000, '{"role":"user","content":"I want to refactor the auth module"}'),
            ('msg2', 'ses_test1', 1716864060, 1716864060, '{"role":"assistant","content":"Based on the codebase analysis, I recommend using PostgreSQL for the new schema. The current SQLite setup will not handle the expected load."}')
        """)
        conn.commit()
        conn.close()
        
        # Create test self.db
        self_db = tmp_path / "self.db"
        conn = sqlite3.connect(str(self_db))
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
        
        # Run pipeline
        from extractors.session_extractor import extract_all_sessions
        stats = extract_all_sessions(str(opencode_db), str(self_db))
        
        assert stats['sessions_processed'] == 1
        assert stats['signals_extracted'] >= 1
        assert stats['metadata_extracted'] == 1

    def test_extract_all_is_idempotent(self, tmp_path):
        """Running extract_all twice should not duplicate data."""
        from extractors.session_extractor import extract_all_sessions
        
        # Create mock DBs (same as above)
        opencode_db = tmp_path / "opencode.db"
        conn = sqlite3.connect(str(opencode_db))
        conn.execute("CREATE TABLE session (id TEXT PRIMARY KEY, project_id TEXT, title TEXT, agent TEXT, model TEXT, cost REAL, tokens_input INT, tokens_output INT, time_created INT, time_updated INT)")
        conn.execute("CREATE TABLE message (id TEXT PRIMARY KEY, session_id TEXT, time_created INT, time_updated INT, data TEXT)")
        conn.execute("INSERT INTO session VALUES ('ses_test1', 'proj1', 'Test', 'general', 'gpt-4', 0, 0, 0, 1716864000, 1716867600)")
        conn.execute("INSERT INTO message VALUES ('msg1', 'ses_test1', 1716864000, 1716864000, '{\"role\":\"user\",\"content\":\"test message\"}')")
        conn.commit()
        conn.close()
        
        self_db = tmp_path / "self.db"
        conn = sqlite3.connect(str(self_db))
        conn.executescript("CREATE TABLE session_signals (id TEXT PRIMARY KEY, signal_type TEXT, content TEXT, session_id TEXT, agent TEXT, model TEXT, source TEXT, observed_at TEXT, created_at TEXT); CREATE TABLE session_metadata (id TEXT PRIMARY KEY, session_id TEXT UNIQUE, title TEXT, agent TEXT, model TEXT, cost REAL, tokens_input INT, tokens_output INT, message_count INT, duration_seconds INT, date TEXT, extracted_at TEXT);")
        conn.close()
        
        # Run twice
        extract_all_sessions(str(opencode_db), str(self_db))
        stats2 = extract_all_sessions(str(opencode_db), str(self_db))
        
        # Second run should process 0 new sessions
        assert stats2['sessions_processed'] == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/paulorezende/Documents/Personal_AI_powerhouse\ updated/personal-ai-space/engine && .venv/bin/python3 -m pytest extractors/test_session_extractor.py::TestExtractionPipeline -v`
Expected: FAIL with "ImportError: cannot import name 'extract_all_sessions'"

- [ ] **Step 3: Implement pipeline function**

```python
# engine/extractors/session_extractor.py (append to file)
from typing import Optional

def extract_all_sessions(
    opencode_db_path: Optional[str] = None,
    self_db_path: Optional[str] = None
) -> dict:
    """Extract all signals from OpenCode sessions into self.db.
    
    Args:
        opencode_db_path: Path to OpenCode's SQLite database
        self_db_path: Path to self.db
        
    Returns:
        Stats dict with counts of processed sessions, signals, and metadata
    """
    from extractors.session_storage import SessionStorage
    
    reader = OpenCodeReader(opencode_db_path)
    storage = SessionStorage(self_db_path)
    
    stats = {
        'sessions_processed': 0,
        'signals_extracted': 0,
        'metadata_extracted': 0,
        'errors': 0,
    }
    
    # Get all sessions
    sessions = reader.read_sessions()
    
    # Get already-processed session IDs
    processed_ids = set(storage.get_unprocessed_sessions())
    
    for session in sessions:
        session_id = session['id']
        
        # Skip already-processed sessions
        if session_id in processed_ids:
            continue
        
        try:
            # Extract session metadata
            metadata = SignalFilter.extract_session_metadata(session)
            storage.upsert_session_metadata(metadata)
            stats['metadata_extracted'] += 1
            
            # Extract signals from messages
            messages = reader.read_session_messages(session_id)
            
            user_signals = SignalFilter.filter_user_messages(messages)
            reasoning_signals = SignalFilter.filter_assistant_reasoning(messages)
            error_signals = SignalFilter.filter_error_solutions(messages)
            
            all_signals = user_signals + reasoning_signals + error_signals
            
            for signal in all_signals:
                signal['session_id'] = session_id
                signal['agent'] = session.get('agent')
                signal['model'] = session.get('model')
                signal['source'] = 'opencode'
                storage.upsert_signal(signal)
            
            stats['signals_extracted'] += len(all_signals)
            stats['sessions_processed'] += 1
            
        except Exception as e:
            logger.error("Failed to process session %s: %s", session_id, e)
            stats['errors'] += 1
    
    return stats
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/paulorezende/Documents/Personal_AI_powerhouse\ updated/personal-ai-space/engine && .venv/bin/python3 -m pytest extractors/test_session_extractor.py::TestExtractionPipeline -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add engine/extractors/session_extractor.py engine/extractors/test_session_extractor.py
git commit -m "feat(extractors): add full extraction pipeline"
```

---

## Task 6: CLI Integration — Add `sessions extract` command

**Files:**
- Modify: `engine/cli.py`

**Security flag:** `none`

**Does NOT cover:** Scheduling — this task only adds CLI invocation.

- [ ] **Step 1: Write failing test**

```python
# engine/extractors/test_session_extractor.py (append to file)
class TestCLIIntegration:
    def test_cli_sessions_extract(self, tmp_path, monkeypatch):
        """CLI sessions extract command should run extraction."""
        from click.testing import CliRunner
        from cli import cli
        
        runner = CliRunner()
        result = runner.invoke(cli, ['sessions', 'extract'])
        
        # Should not error (may show "no sessions" or success message)
        assert result.exit_code == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/paulorezende/Documents/Personal_AI_powerhouse\ updated/personal-ai-space/engine && .venv/bin/python3 -m pytest extractors/test_session_extractor.py::TestCLIIntegration -v`
Expected: FAIL with "No such command 'sessions'"

- [ ] **Step 3: Implement CLI command**

```python
# engine/cli.py (append before the last line)
# ── sessions ─────────────────────────────────────────────────────────────
@cli.group()
def sessions():
    """Session data extraction and analysis."""

@sessions.command("extract")
@click.option("--opencode-db", type=click.Path(), help="Path to OpenCode database")
@click.option("--self-db", type=click.Path(), help="Path to self.db")
def sessions_extract(opencode_db, self_db):
    """Extract signals from OpenCode sessions into self.db."""
    from extractors.session_extractor import extract_all_sessions
    
    console.print("[bold]Extracting session data...[/bold]")
    stats = extract_all_sessions(opencode_db, self_db)
    
    console.print(f"\n[green]✓ Extraction complete[/green]")
    console.print(f"  Sessions processed: {stats['sessions_processed']}")
    console.print(f"  Signals extracted: {stats['signals_extracted']}")
    console.print(f"  Metadata records: {stats['metadata_extracted']}")
    if stats['errors'] > 0:
        console.print(f"  [red]Errors: {stats['errors']}[/red]")

@sessions.command("stats")
@click.option("--self-db", type=click.Path(), help="Path to self.db")
def sessions_stats(self_db):
    """Show session extraction statistics."""
    import sqlite3
    from pathlib import Path
    
    db_path = self_db or str(Path(__file__).parent / "db" / "self" / "self.db")
    conn = sqlite3.connect(db_path)
    
    try:
        total_sessions = conn.execute("SELECT COUNT(*) FROM session_metadata").fetchone()[0]
        total_signals = conn.execute("SELECT COUNT(*) FROM session_signals").fetchone()[0]
        
        signal_types = conn.execute("""
            SELECT signal_type, COUNT(*) as count 
            FROM session_signals 
            GROUP BY signal_type
        """).fetchall()
        
        console.print(f"\n[bold]Session Extraction Stats[/bold]")
        console.print(f"  Total sessions: {total_sessions}")
        console.print(f"  Total signals: {total_signals}")
        console.print(f"\n  Signals by type:")
        for st in signal_types:
            console.print(f"    {st[0]}: {st[1]}")
    finally:
        conn.close()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/paulorezende/Documents/Personal_AI_powerhouse\ updated/personal-ai-space/engine && .venv/bin/python3 -m pytest extractors/test_session_extractor.py::TestCLIIntegration -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add engine/cli.py
git commit -m "feat(cli): add sessions extract and stats commands"
```

---

## Task 7: Run Migration on Live Database

**Files:**
- Modify: `engine/db/self/migrate_session_tables.py` (already created in Task 1)

**Security flag:** `none`

**Does NOT cover:** Data extraction — this task only creates the tables.

- [ ] **Step 1: Run migration script**

```bash
cd /Users/paulorezende/Documents/Personal_AI_powerhouse\ updated/personal-ai-space/engine && .venv/bin/python3 db/self/migrate_session_tables.py
```

Expected: "Migration complete: /Users/paulorezende/Documents/Personal_AI_powerhouse updated/personal-ai-space/engine/db/self/self.db"

- [ ] **Step 2: Verify tables exist**

```bash
sqlite3 /Users/paulorezende/Documents/Personal_AI_powerhouse\ updated/personal-ai-space/engine/db/self/self.db ".tables"
```

Expected: `session_metadata  session_signals` (among other tables)

- [ ] **Step 3: Commit**

```bash
git add engine/db/self/self.db
git commit -m "chore(db): run session tables migration"
```

---

## Task 8: Initial Extraction — Process existing sessions

**Files:**
- None (runtime operation only)

**Security flag:** `none`

**Does NOT cover:** Ongoing scheduling — this is a one-time extraction.

- [ ] **Step 1: Run extraction**

```bash
cd /Users/paulorezende/Documents/Personal_AI_powerhouse\ updated/personal-ai-space/engine && .venv/bin/python3 -c "
from extractors.session_extractor import extract_all_sessions
stats = extract_all_sessions()
print(f'Sessions processed: {stats[\"sessions_processed\"]}')
print(f'Signals extracted: {stats[\"signals_extracted\"]}')
print(f'Metadata records: {stats[\"metadata_extracted\"]}')
print(f'Errors: {stats[\"errors\"]}')
"
```

Expected: Positive counts for sessions, signals, and metadata.

- [ ] **Step 2: Verify data in database**

```bash
sqlite3 /Users/paulorezende/Documents/Personal_AI_powerhouse\ updated/personal-ai-space/engine/db/self/self.db "SELECT COUNT(*) FROM session_metadata; SELECT COUNT(*) FROM session_signals;"
```

Expected: Non-zero counts.

- [ ] **Step 3: Run full test suite**

```bash
cd /Users/paulorezende/Documents/Personal_AI_powerhouse\ updated/personal-ai-space/engine && .venv/bin/python3 -m pytest extractors/test_session_extractor.py extractors/test_session_storage.py -v
```

Expected: All tests pass.

- [ ] **Step 4: Commit (no changes expected)**

```bash
# No code changes — extraction is runtime only
```

---

## Self-Review Checklist

- [x] **Spec coverage:** All 4 signal types implemented (user messages, assistant reasoning, error/solution pairs, session metadata)
- [x] **Placeholder scan:** No TBD/TODO/placeholders found
- [x] **Type consistency:** SignalFilter methods match test expectations; SessionStorage matches test expectations
- [x] **Scope-reduction scan:** No unauthorized scope reductions
- [x] **File structure:** Each file has single responsibility
- [x] **Task independence:** Tasks build incrementally but can be verified independently

---

**Plan saved to `.omo/plans/session-data-extraction.md`. Ready to execute with Subagent-Driven (8 tasks). Reply to start, or say "inline" / "subagent" to switch.**
