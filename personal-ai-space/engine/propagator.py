"""
propagator.py — Route task changes across all databases.

Called by task_coordinator, comprehensive_extractor, init_engine, and engine.py
whenever a task is created or updated. Propagates to:
  - task_history (tasks.db)
  - project progress (tasks.db, averaged from child tasks)
  - goal progress (self.db, if project name matches goal title)
  - interactions (memories.db)
  - semantic facts (agent_memory.db via MCP bridge)

All failures are caught and logged — never raised. MCP bridge is optional.
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Optional

logger = logging.getLogger("engine.propagator")

_db = None
_mcp = None


def _get_db():
    global _db
    if _db is None:
        import db_manager as db
        _db = db
    return _db


def _get_mcp():
    global _mcp
    if _mcp is None:
        try:
            from memory.mcp_bridge import MCPMemoryBridge
            _mcp = MCPMemoryBridge()
        except Exception:
            _mcp = False
    return _mcp if _mcp else None


def _get_task(task_id: str) -> Optional[dict]:
    db = _get_db()
    rows = db.query("tasks", "SELECT * FROM tasks WHERE id=?", (task_id,))
    return rows[0] if rows else None


def _log_history(task_id: str, field: str, old_value, new_value):
    db = _get_db()
    try:
        db.execute(
            "tasks",
            "INSERT INTO task_history (id, task_id, field, old_value, new_value, changed_by, changed_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (
                uuid.uuid4().hex,
                task_id,
                field,
                str(old_value) if old_value is not None else None,
                str(new_value) if new_value is not None else None,
                "propagator",
                datetime.utcnow().isoformat(),
            ),
        )
    except Exception as e:
        logger.warning("Failed to log task_history for %s: %s", task_id, e)


def _log_to_memories(action: str, details: dict):
    db = _get_db()
    try:
        db.log_interaction(
            agent_id="propagator",
            action=action,
            input_data=None,
            output_data=details,
            duration_ms=0,
            status="success",
        )
    except Exception as e:
        logger.debug("Failed to log to memories.db: %s", e)


def _update_mcp_fact(key: str, value: str):
    mcp = _get_mcp()
    if not mcp:
        return
    try:
        mcp.add_fact(key, value, confidence=0.9, category="task", source="propagator")
    except Exception as e:
        logger.debug("Failed to update MCP fact %s: %s", key, e)


def _recalc_project_progress(project_id: Optional[str]):
    """Average child task progress_pct into project.progress_pct.

    Also syncs to self.db goals if project name matches goal title.
    """
    if not project_id:
        return
    db = _get_db()
    try:
        rows = db.query(
            "tasks",
            "SELECT progress_pct FROM tasks WHERE project_id=? AND status != 'cancelled'",
            (project_id,),
        )
        if not rows:
            return
        avg = sum(r["progress_pct"] or 0 for r in rows) / len(rows)
        db.execute(
            "tasks",
            "UPDATE projects SET progress_pct=?, updated_at=? WHERE id=?",
            (round(avg), datetime.utcnow().isoformat(), project_id),
        )
        _sync_goal_from_project(project_id, round(avg))
    except Exception as e:
        logger.warning("Failed to recalc progress for project %s: %s", project_id, e)


def _sync_goal_from_project(project_id: str, progress: int):
    """If a goal title matches this project name, sync progress."""
    db = _get_db()
    try:
        proj = db.query("tasks", "SELECT name FROM projects WHERE id=?", (project_id,))
        if not proj:
            return
        pname = proj[0]["name"]
        db.execute(
            "self",
            "UPDATE goals SET progress=?, updated_at=? WHERE title=?",
            (progress, datetime.utcnow().isoformat(), pname),
        )
    except Exception as e:
        logger.debug("Failed to sync goal from project %s: %s", project_id, e)


def _touch_updated_at(table: str, row_id: str):
    db = _get_db()
    try:
        db.execute(
            "tasks",
            f"UPDATE {table} SET updated_at=? WHERE id=?",
            (datetime.utcnow().isoformat(), row_id),
        )
    except Exception as e:
        logger.debug("Failed to touch updated_at on %s.%s: %s", table, row_id, e)


# ── Public API ─────────────────────────────────────────────────────


recalc_project_progress = _recalc_project_progress


def on_task_created(task_id: str) -> None:
    """Propagate a newly created task to all systems."""
    task = _get_task(task_id)
    if not task:
        logger.warning("Task %s not found for propagation", task_id)
        return
    _log_history(task_id, "created", None, task.get("status"))
    _recalc_project_progress(task.get("project_id"))
    _update_mcp_fact(f"task.{task_id}.status", task.get("status", "pending"))
    _update_mcp_fact(f"task.{task_id}.title", task.get("title", ""))


def on_task_updated(task_id: str, old_values: Optional[dict] = None) -> None:
    """Propagate task changes.

    If old_values is provided, only changed fields are logged.
    If not, a generic 'updated' entry is recorded (simpler but less granular).
    """
    task = _get_task(task_id)
    if not task:
        logger.warning("Task %s not found for propagation", task_id)
        return

    if old_values:
        changes = {
            k: (old_values.get(k), task.get(k))
            for k in old_values
            if old_values.get(k) != task.get(k)
        }
    else:
        changes = {"updated": (None, "updated")}

    for field, (old, new) in changes.items():
        _log_history(task_id, field, old, new)

    if "status" in changes or "progress_pct" in changes:
        _recalc_project_progress(task.get("project_id"))
        _update_mcp_fact(f"task.{task_id}.status", task.get("status"))
        _update_mcp_fact(f"task.{task_id}.progress", str(task.get("progress_pct", 0)))

    _touch_updated_at("tasks", task_id)
    if changes:
        _log_to_memories("task_updated", {
            "task_id": task_id,
            "changes": list(changes.keys()),
        })


def on_task_deleted(task_id: str) -> None:
    """Log deletion and recalc project progress."""
    db = _get_db()
    proj = None
    try:
        rows = db.query("tasks", "SELECT project_id FROM tasks WHERE id=?", (task_id,))
        if rows:
            proj = rows[0]["project_id"]
    except Exception:
        pass
    _log_history(task_id, "deleted", "exists", "deleted")
    _log_to_memories("task_deleted", {"task_id": task_id})
    if proj:
        _recalc_project_progress(proj)
