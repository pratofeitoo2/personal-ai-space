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


import re
import uuid

PATTERNS_TOOL_CALL = re.compile(r'^\[tool:\s*\w+\]$')
REASONING_MIN_LENGTH = 50


class SignalFilter:
    """Filter and extract behavioral signals from session messages."""

    @staticmethod
    def filter_user_messages(messages: list[dict]) -> list[dict]:
        signals = []
        for msg in messages:
            if msg.get('role') == 'user' and msg.get('content'):
                content = msg['content']
                if not PATTERNS_TOOL_CALL.match(content):
                    signals.append({
                        'id': uuid.uuid4().hex,
                        'signal_type': 'user_message',
                        'content': content[:2000],
                        'observed_at': datetime.now(timezone.utc).isoformat(),
                    })
        return signals

    @staticmethod
    def filter_assistant_reasoning(messages: list[dict]) -> list[dict]:
        signals = []
        for msg in messages:
            if msg.get('role') == 'assistant' and msg.get('content'):
                content = msg['content']
                if (not PATTERNS_TOOL_CALL.match(content) and
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
        signals = []
        error_keywords = ['error', 'fail', 'bug', 'issue', 'broken', 'exception', 'traceback']
        solution_keywords = ['fixed', 'solution', 'resolved', 'corrected', 'patched', 'updated']

        for i, msg in enumerate(messages):
            content = msg.get('content', '').lower()

            if msg.get('role') == 'user':
                if any(kw in content for kw in error_keywords):
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


def extract_all_sessions(
    opencode_db_path: Optional[str] = None,
    self_db_path: Optional[str] = None
) -> dict:
    from extractors.session_storage import SessionStorage

    reader = OpenCodeReader(opencode_db_path)
    storage = SessionStorage(self_db_path)

    stats = {
        'sessions_processed': 0,
        'signals_extracted': 0,
        'metadata_extracted': 0,
        'errors': 0,
    }

    sessions = reader.read_sessions()
    processed_ids = set(storage.get_unprocessed_sessions())

    for session in sessions:
        session_id = session['id']
        if session_id in processed_ids:
            continue

        try:
            metadata = SignalFilter.extract_session_metadata(session)
            storage.upsert_session_metadata(metadata)
            stats['metadata_extracted'] += 1

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
