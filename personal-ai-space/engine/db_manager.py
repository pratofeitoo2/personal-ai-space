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
