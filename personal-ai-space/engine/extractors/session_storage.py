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
        """Get session IDs already in session_metadata."""
        conn = self._get_conn()
        try:
            rows = conn.execute("""
                SELECT session_id FROM session_metadata
            """).fetchall()
            return [row['session_id'] for row in rows]
        finally:
            conn.close()
