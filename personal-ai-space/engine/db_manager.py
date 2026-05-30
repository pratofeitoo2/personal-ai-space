"""
Engine core: database connection manager.
Handles all SQLite connections and queries.
Features:
  - Thread-local connection caching (each thread owns its connections)
  - Transaction context manager for atomic multi-table operations
  - WAL checkpoint management to prevent unbounded WAL growth
  - WAL mode + foreign keys on all connections
"""
import sqlite3
import json
import logging
import threading
import uuid as _uid
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Optional
from collections.abc import Sequence
from db.id_helpers import for_interaction, for_agent_memory, for_context_snapshot

logger = logging.getLogger("engine.db")

DB_DIR = Path(__file__).parent / "db"

DB_PATHS = {
    "memories":   DB_DIR / "memories" / "memories.db",
    "self":       DB_DIR / "self" / "self.db",
    "tasks":      DB_DIR / "tasks" / "tasks.db",
    "knowledge":  DB_DIR / "knowledge" / "knowledge.db",
    "git":        DB_DIR / "git" / "git.db",
    "activities": DB_DIR / "activities" / "activities.db",
    "calendar":   DB_DIR / "calendar" / "calendar.db",
    "jobs":       DB_DIR / "jobs" / "jobs.db",
}

# ── Thread-Local Connections ─────────────────────────────────────────────────
# Each thread gets its own SQLite connections, one per database file.
# This avoids the "SQLite objects created in a thread can only be used
# in that same thread" error entirely.
# WAL mode allows concurrent reads across threads safely.

_thread_local = threading.local()


def _pool_key(path: Path) -> str:
    return str(path.resolve())


def _get_local_conns() -> dict[str, sqlite3.Connection]:
    if not hasattr(_thread_local, "conns"):
        _thread_local.conns = {}
    return _thread_local.conns


def _create_conn(path: Path) -> sqlite3.Connection:
    """Create a new SQLite connection with standard settings."""
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = dict_factory
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def acquire_conn(path: Path) -> sqlite3.Connection:
    """Get a connection for the current thread. Thread-local cached."""
    key = _pool_key(path)
    local_conns = _get_local_conns()
    if key not in local_conns:
        local_conns[key] = _create_conn(path)
        logger.debug("Created %s connection for thread %s",
                     path.name, threading.current_thread().name)
    return local_conns[key]


def release_conn(path: Path, conn: sqlite3.Connection) -> None:
    """No-op — thread keeps its own connections until GC at thread exit."""


def close_thread_connections() -> None:
    local_conns = _get_local_conns()
    for key, conn in list(local_conns.items()):
        try:
            conn.close()
        except Exception:
            pass
    _get_local_conns().clear()


def clear_pool() -> None:
    close_thread_connections()


def dict_factory(cursor, row):
    """Return rows as dicts instead of tuples."""
    return {col[0]: row[i] for i, col in enumerate(cursor.description)}


@contextmanager
def get_conn(db_name: str):
    """Context manager for pooled database connections.
    
    Acquires a connection from the pool, commits on success,
    rolls back on exception, and returns the connection to the pool.
    """
    path = DB_PATHS.get(db_name)
    if not path:
        raise ValueError(f"Unknown database: {db_name}")
    conn = acquire_conn(path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        release_conn(path, conn)


@contextmanager
def transaction(db_name: str):
    """Context manager for atomic transactions.
    
    Wraps operations in BEGIN IMMEDIATE / COMMIT / ROLLBACK.
    Use for multi-table operations that need atomicity.
    
    Example:
        with transaction(\"self\") as conn:
            conn.execute(\"INSERT INTO habit_logs ...\", ...)
            conn.execute(\"UPDATE habits SET ...\", ...)
    
    Note: Use ``conn.execute()`` (not the module-level ``query()/execute()``)
    inside this block to share the same connection + transaction.
    """
    with get_conn(db_name) as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            yield conn
        except Exception:
            conn.rollback()
            raise


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


def wal_checkpoint(db_name: str) -> dict:
    """Run WAL checkpoint (TRUNCATE) on a database.
    
    Returns checkpoint result dict with keys like 'busy', 'log', 'checkpointed'.
    Call periodically or after bulk writes to keep WAL files bounded.
    """
    with get_conn(db_name) as conn:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        row = conn.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
        result = dict(row) if row else {}
        if result.get("busy", 0) > 0:
            logger.warning("WAL checkpoint blocked on %s: %s busy frames", db_name, result["busy"])
        return result


def checkpoint_all():
    """Run WAL checkpoint on all databases."""
    for db_name in DB_PATHS:
        try:
            result = wal_checkpoint(db_name)
            logger.debug("WAL checkpoint %s: %s", db_name, result)
        except Exception as e:
            logger.warning("WAL checkpoint failed for %s: %s", db_name, e)


def init_git_db():
    """Initialize git.db from schema file."""
    schema_file = DB_DIR / "git" / "schema_git_repos.sql"
    if not schema_file.exists():
        logger.warning(f"Schema missing: {schema_file}")
        return
    conn = sqlite3.connect(str(DB_PATHS["git"]))
    with open(schema_file) as f:
        conn.executescript(f.read())
    conn.close()
    logger.info("Initialized: git.db")


def init_all():
    """Initialize all databases from schema files."""
    for db_name, db_path in DB_PATHS.items():
        if db_name == "git":
            continue  # init_git_db() handles git.db separately with correct filename
        schema_file = DB_DIR / db_name / f"schema_{db_name}.sql"
        if not schema_file.exists():
            logger.warning(f"Schema missing: {schema_file}")
            continue
        conn = sqlite3.connect(str(db_path))
        with open(schema_file) as f:
            conn.executescript(f.read())
        conn.close()
        logger.info(f"Initialized: {db_name}.db")
    init_git_db()
    checkpoint_all()
    logger.info("All databases initialized, WAL checkpoints done")


def log_interaction(
    agent_id: str, action: str, input_data: Any = None,
    output_data: Any = None, duration_ms: int = 0,
    status: str = "success", error_message: str = None,
    context: dict = None
) -> str:
    """Log an agent interaction to memories.db."""
    import json as _json
    interaction_id = for_interaction(agent_id)
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
    memory_id = for_agent_memory(agent_id)
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
    import json as _json
    from datetime import timedelta, timezone
    cid = for_context_snapshot(session_id)
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
