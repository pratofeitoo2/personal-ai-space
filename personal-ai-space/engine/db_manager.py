"""
Engine core: database connection manager.
Handles all SQLite connections and queries.
"""
import sqlite3
import json
import logging
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Optional
from collections.abc import Sequence

logger = logging.getLogger("engine.db")

DB_DIR = Path(__file__).parent / "db"

DB_PATHS = {
    "memories": DB_DIR / "memories.db",
    "self":     DB_DIR / "self.db",
    "tasks":    DB_DIR / "tasks.db",
    "knowledge": DB_DIR / "knowledge.db",
}


def dict_factory(cursor, row):
    """Return rows as dicts instead of tuples."""
    return {col[0]: row[i] for i, col in enumerate(cursor.description)}


@contextmanager
def get_conn(db_name: str):
    """Context manager for database connections."""
    path = DB_PATHS.get(db_name)
    if not path:
        raise ValueError(f"Unknown database: {db_name}")
    conn = sqlite3.connect(str(path))
    conn.row_factory = dict_factory
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def query(db_name: str, sql: str, params: tuple = ()) -> list[dict]:
    """Execute a SELECT query and return all rows."""
    with get_conn(db_name) as conn:
        cur = conn.execute(sql, params)
        return cur.fetchall()


def execute(db_name: str, sql: str, params: tuple = ()) -> int:
    """Execute INSERT/UPDATE/DELETE, return rowcount."""
    with get_conn(db_name) as conn:
        cur = conn.execute(sql, params)
        return cur.rowcount


def execute_many(db_name: str, sql: str, params_list: list) -> int:
    """Execute many rows at once."""
    with get_conn(db_name) as conn:
        cur = conn.executemany(sql, params_list)
        return cur.rowcount


def init_all():
    """Initialize all databases from schema files."""
    schema_dir = DB_DIR
    for db_name, db_path in DB_PATHS.items():
        schema_file = schema_dir / f"schema_{db_name}.sql"
        if not schema_file.exists():
            logger.warning(f"Schema missing: {schema_file}")
            continue
        conn = sqlite3.connect(str(db_path))
        with open(schema_file) as f:
            conn.executescript(f.read())
        conn.close()
        logger.info(f"Initialized: {db_name}.db")


def log_interaction(
    agent_id: str, action: str, input_data: Any = None,
    output_data: Any = None, duration_ms: int = 0,
    status: str = "success", error_message: str = None,
    context: dict = None
) -> str:
    """Log an agent interaction to memories.db."""
    import uuid as _uid
    import json as _json
    interaction_id = _uid.uuid4().hex
    execute("memories", """
        INSERT INTO interactions
        (id, agent_id, action, input_data, output_data, duration_ms,
         status, error_message, context)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        interaction_id, agent_id, action,
        _json.dumps(input_data) if input_data else None,
        _json.dumps(output_data) if output_data else None,
        duration_ms, status, error_message,
        _json.dumps(context) if context else None,
    ))
    return interaction_id


def store_agent_memory(
    agent_id: str, key: str, value: str,
    ttl_seconds: int = None
) -> bool:
    """Upsert a key-value pair into agent_memory table."""
    import uuid as _uid
    memory_id = _uid.uuid4().hex
    try:
        execute("memories", """
            INSERT OR REPLACE INTO agent_memory
            (id, agent_id, key, value, ttl_seconds)
            VALUES (?, ?, ?, ?, ?)
        """, (memory_id, agent_id, key, value, ttl_seconds))
        return True
    except Exception:
        return False


def get_agent_memory(agent_id: str, key: str = None) -> list[dict]:
    """Retrieve memories for an agent, optionally filtered by key."""
    if key:
        return query("memories",
            "SELECT * FROM agent_memory WHERE agent_id=? AND key=? ORDER BY created_at DESC",
            (agent_id, key))
    return query("memories",
        "SELECT * FROM agent_memory WHERE agent_id=? ORDER BY created_at DESC",
        (agent_id,))


def store_context_snapshot(
    session_id: str, content: str, relevance: float = 1.0,
    ttl_hours: int = 24
) -> str:
    """Store a context snapshot with expiry. Keeps newest 50 entries."""
    import uuid as _uid
    import json as _json
    from datetime import timedelta, timezone
    cid = _uid.uuid4().hex
    now = datetime.now(timezone.utc)
    execute("memories", """
        INSERT INTO context_window (id, session_id, timestamp, content, relevance_score, expires_at)
        VALUES (?,?,?,?,?,?)
    """, (cid, session_id, now.isoformat(), _json.dumps(content) if not isinstance(content, str) else content,
          relevance, (now + timedelta(hours=ttl_hours)).isoformat()))
    execute("memories", """
        DELETE FROM context_window WHERE id NOT IN (
            SELECT id FROM context_window ORDER BY timestamp DESC LIMIT 50
        )
    """)
    return cid


def get_recent_interactions(limit: int = 10) -> list[dict]:
    """Return most recent agent interactions."""
    return query("memories",
        "SELECT * FROM interactions ORDER BY timestamp DESC LIMIT ?",
        (limit,))


def health_check() -> dict:
    """Check all databases are accessible."""
    results = {}
    for db_name, db_path in DB_PATHS.items():
        try:
            rows = query(db_name, "SELECT count(*) as n FROM sqlite_master WHERE type='table'")
            results[db_name] = {"ok": True, "tables": rows[0]["n"]}
        except Exception as e:
            results[db_name] = {"ok": False, "error": str(e)}
    return results
