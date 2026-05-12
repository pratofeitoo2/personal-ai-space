from __future__ import annotations

import sqlite3
import time
import random
import string
from pathlib import Path
from typing import Any

OPCMEM_DIR = Path.home() / ".opencode-mem" / "data" / "projects"


def _make_id() -> str:
    ts = int(time.time() * 1000)
    rand = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"mem_{ts}_{rand}"


def _find_shard(project_path: str | None = None) -> list[dict[str, Any]]:
    """Resolve shard for a project path. Returns all shards if path unknown."""
    meta_db = OPCMEM_DIR.parent / "metadata.db"
    results: list[dict[str, Any]] = []

    if meta_db.exists():
        conn = sqlite3.connect(str(meta_db))
        rows = conn.execute(
            "SELECT shard_index, scope, scope_hash, db_path, vector_count FROM shards WHERE is_active = 1"
        ).fetchall()
        conn.close()
        for row in rows:
            shard_path = (OPCMEM_DIR.parent / row[3]).resolve()
            results.append({
                "shard_index": row[0],
                "scope": row[1],
                "scope_hash": row[2],
                "db_path": str(shard_path),
                "vector_count": row[4],
            })
    else:
        for f in sorted(OPCMEM_DIR.glob("*.db")):
            if "-wal" not in f.name and "-shm" not in f.name:
                results.append({
                    "shard_index": 0,
                    "scope": "project",
                    "scope_hash": f.stem,
                    "db_path": str(f),
                    "vector_count": _count_vectors(str(f)),
                })

    return results


def _count_vectors(db_path: str) -> int:
    conn = sqlite3.connect(db_path)
    count = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
    conn.close()
    return count


def _all_shards() -> list[str]:
    return [s["db_path"] for s in _find_shard()]


def store(
    content: str,
    vector: bytes,
    tags: str = "",
    type_: str = "context",
    display_name: str = "",
    project_path: str | None = None,
    project_name: str | None = None,
) -> dict[str, Any]:
    now = int(time.time() * 1000)
    mid = _make_id()
    shards = _find_shard(project_path)
    if not shards:
        return {"error": "No database shard found"}

    db_path = shards[0]["db_path"]
    container_tag = f"opencode_project_{shards[0]['scope_hash']}"

    conn = sqlite3.connect(db_path)
    conn.execute(
        """INSERT INTO memories
        (id, content, vector, container_tag, type, tags, created_at, updated_at,
         display_name, project_path, project_name)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (mid, content, sqlite3.Binary(vector), container_tag,
         type_, tags, now, now, display_name, project_path or "", project_name or ""),
    )
    conn.commit()
    conn.close()

    return {"id": mid, "created_at": now, "container_tag": container_tag}


def search(query_vector: bytes, limit: int = 10) -> list[dict[str, Any]]:
    """Naive cosine similarity search across all shards."""
    import struct
    import math

    def cosine_sim(a: bytes, b: bytes) -> float:
        dim = len(a) // 4
        fa = struct.unpack(f"{dim}f", a)
        fb = struct.unpack(f"{dim}f", b)
        dot = sum(x * y for x, y in zip(fa, fb))
        na = math.sqrt(sum(x * x for x in fa))
        nb = math.sqrt(sum(y * y for y in fb))
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)

    results: list[tuple[float, dict[str, Any]]] = []
    vec_dim = len(query_vector) // 4

    for db_path in _all_shards():
        conn = sqlite3.connect(db_path)
        rows = conn.execute(
            "SELECT id, content, type, tags, display_name, project_name, created_at, vector FROM memories"
        ).fetchall()
        conn.close()

        for r in rows:
            db_vec = r[7]
            if len(db_vec) // 4 != vec_dim:
                continue
            sim = cosine_sim(query_vector, db_vec)
            results.append((sim, {
                "id": r[0],
                "content": r[1],
                "type": r[2],
                "tags": r[3],
                "display_name": r[4],
                "project_name": r[5],
                "created_at": r[6],
                "similarity": round(sim, 4),
            }))

    results.sort(key=lambda x: x[0], reverse=True)
    return [r[1] for r in results[:limit]]


def list_memories(limit: int = 20, offset: int = 0, type_: str | None = None) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for db_path in _all_shards():
        conn = sqlite3.connect(db_path)
        if type_:
            rows = conn.execute(
                "SELECT id, content, type, tags, display_name, project_name, created_at FROM memories WHERE type = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (type_, limit, offset),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, content, type, tags, display_name, project_name, created_at FROM memories ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
        conn.close()
        for r in rows:
            results.append({
                "id": r[0],
                "content": r[1],
                "type": r[2],
                "tags": r[3],
                "display_name": r[4],
                "project_name": r[5],
                "created_at": r[6],
            })
    return results


def delete(memory_id: str) -> bool:
    for db_path in _all_shards():
        conn = sqlite3.connect(db_path)
        cur = conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        conn.commit()
        deleted = cur.rowcount > 0
        conn.close()
        if deleted:
            return True
    return False


def stats() -> dict[str, Any]:
    total = 0
    by_type: dict[str, int] = {}
    by_project: dict[str, int] = {}
    shard_info: list[dict[str, Any]] = []

    for s in _find_shard():
        db_path = s["db_path"]
        conn = sqlite3.connect(db_path)
        count = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        total += count
        shard_info.append({
            "path": db_path,
            "container_tag": s.get("scope_hash", ""),
            "vector_count": count,
        })
        for row in conn.execute("SELECT type, COUNT(*) FROM memories GROUP BY type").fetchall():
            by_type[row[0]] = by_type.get(row[0], 0) + row[1]
        for row in conn.execute("SELECT project_name, COUNT(*) FROM memories WHERE project_name != '' GROUP BY project_name").fetchall():
            by_project[row[0]] = by_project.get(row[0], 0) + row[1]
        conn.close()

    return {
        "total_memories": total,
        "shards": len(shard_info),
        "by_type": by_type,
        "by_project": by_project,
    }
