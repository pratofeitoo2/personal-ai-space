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
