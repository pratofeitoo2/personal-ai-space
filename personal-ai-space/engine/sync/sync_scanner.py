"""
sync_scanner.py — Auto-sync .md frontmatter with database on engine start.

Phase 3: Scans .md files, matches them to tasks/projects/goals via frontmatter
conventions, reconciles status/progress, seeds doc_links, updates sync_state.

Safety: Phase 3 is read-only (file → DB). No file writes.
"""

import hashlib
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger("engine.sync")

# Imported lazily to avoid circular deps
_db = None


def _get_db():
    global _db
    if _db is None:
        import db_manager as db
        _db = db
    return _db


def _file_mtime(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime).isoformat()


def _file_hash(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def _read_frontmatter(path: Path) -> dict:
    content = path.read_text(encoding="utf-8", errors="replace")
    if not content.startswith("---"):
        return {}
    try:
        import yaml
        parts = content.split("---", 2)
        return yaml.safe_load(parts[1]) or {} if len(parts) >= 2 else {}
    except Exception:
        return {}


def _load_tasks_cache(db) -> dict[str, dict]:
    """Return {title_lower: task} for all tasks (active + archived)."""
    rows = db.query("tasks", "SELECT id, title, status, progress_pct, project_id FROM tasks_v")
    cache = {}
    for r in rows:
        key = (r["title"] or "").strip().lower()
        if key:
            cache[key] = r
    return cache


def _load_projects_cache(db) -> dict[str, dict]:
    """Return {name_lower: project} for all projects."""
    rows = db.query("tasks", "SELECT id, name, status, progress_pct FROM projects")
    return {(r["name"] or "").strip().lower(): r for r in rows}


def _load_goals_cache(db) -> dict[str, dict]:
    """Return {title_lower: goal} for all goals."""
    try:
        rows = db.query("self", "SELECT id, title, status, progress FROM goals")
        return {(r["title"] or "").strip().lower(): r for r in rows}
    except Exception:
        return {}


def _upsert_doc_link(db, entity_type: str, entity_id: str, file_path: str,
                     fm_status: Optional[str]) -> str:
    link_id = uuid.uuid4().hex
    db.execute(
        "tasks",
        "INSERT OR IGNORE INTO doc_links "
        "(id, entity_type, entity_id, file_path, link_type, frontmatter_status, last_synced) "
        "VALUES (?,?,?,?,?,?,?)",
        (link_id, entity_type, entity_id, str(file_path), "documents",
         fm_status, datetime.now(timezone.utc).isoformat()),
    )
    # If insert failed (duplicate), update existing
    rows = db.query(
        "tasks",
        "SELECT id FROM doc_links WHERE entity_type=? AND entity_id=? AND file_path=?",
        (entity_type, entity_id, str(file_path)),
    )
    if rows:
        db.execute(
            "tasks",
            "UPDATE doc_links SET frontmatter_status=?, last_synced=? WHERE id=?",
            (fm_status, datetime.now(timezone.utc).isoformat(), rows[0]["id"]),
        )
        return rows[0]["id"]
    return link_id


def _upsert_sync_state(db, entity_type: str, entity_id: Optional[str],
                       file_path: str, file_hash_val: str, mtime: str):
    rows = db.query(
        "tasks",
        "SELECT id FROM sync_state WHERE entity_type=? AND entity_id=? AND file_path=?",
        (entity_type, entity_id or "", str(file_path)),
    )
    if rows:
        db.execute(
            "tasks",
            "UPDATE sync_state SET file_hash=?, last_modified=?, last_synced=? WHERE id=?",
            (file_hash_val, mtime, datetime.now(timezone.utc).isoformat(), rows[0]["id"]),
        )
    else:
        db.execute(
            "tasks",
            "INSERT INTO sync_state (id, entity_type, entity_id, file_path, file_hash, last_modified, last_synced, direction) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (uuid.uuid4().hex, entity_type, entity_id or "", str(file_path),
             file_hash_val, mtime, datetime.now(timezone.utc).isoformat(), "file_to_db"),
        )


def _match_and_sync(db, path: Path, fm: dict, tasks_cache: dict,
                    projects_cache: dict, goals_cache: dict) -> dict:
    """Try to match a file to a DB entity and sync.

    Returns dict with match info for logging.
    """
    rel_path = path.relative_to(Path(__file__).parent.parent)
    fm_status = fm.get("status")
    fm_title = (fm.get("title") or path.stem).strip()
    fm_type = fm.get("type", "")

    result = {
        "file": str(rel_path),
        "matched": False,
        "entity_type": None,
        "entity_id": None,
        "action": "no_match",
    }

    # Priority 1: frontmatter has task_id
    task_id = fm.get("task_id")
    if task_id:
        task = _get_db().query("tasks", "SELECT id FROM tasks_v WHERE id=?", (task_id,))
        if task:
            result.update(matched=True, entity_type="task", entity_id=task_id, action="linked")
            _upsert_doc_link(db, "task", task_id, str(path), fm_status)
            _upsert_sync_state(db, "task", task_id, str(path), _file_hash(path), _file_mtime(path))
            return result

    # Priority 2: match by title to tasks
    key = fm_title.lower()
    if key in tasks_cache:
        task = tasks_cache[key]
        result.update(matched=True, entity_type="task", entity_id=task["id"], action="matched_title")
        _sync_task_status(db, task["id"], fm_status)
        _upsert_doc_link(db, "task", task["id"], str(path), fm_status)
        _upsert_sync_state(db, "task", task["id"], str(path), _file_hash(path), _file_mtime(path))
        return result

    # Priority 3: match by title to projects
    if key in projects_cache:
        proj = projects_cache[key]
        result.update(matched=True, entity_type="project", entity_id=proj["id"], action="matched_title")
        _upsert_doc_link(db, "project", proj["id"], str(path), fm_status)
        _upsert_sync_state(db, "project", proj["id"], str(path), _file_hash(path), _file_mtime(path))
        return result

    # Priority 4: match by title to goals
    if key in goals_cache:
        goal = goals_cache[key]
        result.update(matched=True, entity_type="goal", entity_id=str(goal["id"]), action="matched_goal")
        _upsert_doc_link(db, "project", str(goal["id"]), str(path), fm_status)
        _upsert_sync_state(db, "project", str(goal["id"]), str(path), _file_hash(path), _file_mtime(path))
        return result

    # No match — seed a generic doc_link for any status-bearing file
    if fm_status:
        _upsert_sync_state(db, "unmatched", None, str(path), _file_hash(path), _file_mtime(path))
        result["action"] = "staged_unmatched"

    return result


def _sync_task_status(db, task_id: str, fm_status: Optional[str]):
    """One-way sync: file frontmatter → DB task status."""
    if not fm_status:
        return
    # Normalize status values
    status_map = {
        "draft": "pending", "pending": "pending", "active": "in_progress",
        "in progress": "in_progress", "in-progress": "in_progress", "in_progress": "in_progress",
        "blocked": "blocked", "on hold": "blocked", "on-hold": "blocked",
        "done": "completed", "completed": "completed", "finished": "completed",
        "archived": "cancelled", "cancelled": "cancelled",
    }
    db_status = status_map.get(fm_status.lower())
    if not db_status:
        return

    current = db.query("tasks", "SELECT status FROM tasks WHERE id=?", (task_id,))
    if not current or current[0]["status"] == db_status:
        return

    # Update task status — propagator.on_task_updated will handle the rest
    db.execute(
        "tasks",
        "UPDATE tasks SET status=?, updated_at=? WHERE id=?",
        (db_status, datetime.now(timezone.utc).isoformat(), task_id),
    )
    logger.info("  sync: task %s status %s → %s (from frontmatter)", task_id, current[0]["status"], db_status)


def run_scan(scan_root: Optional[Path] = None) -> dict:
    """Main entry: scan .md files, sync frontmatter → DB.

    Args:
        scan_root: Root directory to scan. Defaults to project root.

    Returns:
        Summary dict with counts of matched/synced/staged files.
    """
    import yaml  # lazy import for resilience

    db = _get_db()
    root = scan_root or Path(__file__).parent.parent
    stats = {"scanned": 0, "with_frontmatter": 0, "matched": 0, "synced": 0, "staged": 0}

    tasks_cache = _load_tasks_cache(db)
    projects_cache = _load_projects_cache(db)
    goals_cache = _load_goals_cache(db)

    logger.info("Sync scan starting (root: %s)", root)

    for md_path in sorted(root.rglob("*.md")):
        rel = md_path.relative_to(root)
        # Skip hidden dirs and node_modules
        if any(p.startswith(".") for p in rel.parts):
            continue
        if "node_modules" in rel.parts:
            continue

        stats["scanned"] += 1
        fm = _read_frontmatter(md_path)
        if not fm:
            continue

        stats["with_frontmatter"] += 1
        result = _match_and_sync(db, md_path, fm, tasks_cache, projects_cache, goals_cache)

        if result["matched"]:
            stats["matched"] += 1
            if result.get("synced"):
                stats["synced"] += 1
        elif result["action"] == "staged_unmatched":
            stats["staged"] += 1

    logger.info(
        "Sync scan complete: %d scanned, %d frontmatter, %d matched, %d staged",
        stats["scanned"], stats["with_frontmatter"], stats["matched"], stats["staged"],
    )
    return stats


def summarize(stats: dict) -> str:
    """Return a human-readable summary string."""
    lines = [
        f"  Scanned {stats['scanned']} .md files",
        f"  Found {stats['with_frontmatter']} with frontmatter",
        f"  Matched {stats['matched']} to DB entities",
        f"  Staged {stats['staged']} unmatched status-bearing files",
    ]
    return "\n".join(lines)
