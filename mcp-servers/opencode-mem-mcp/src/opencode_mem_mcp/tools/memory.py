from __future__ import annotations

from typing import Optional

from fastmcp import FastMCP

from opencode_mem_mcp.core import database as db
from opencode_mem_mcp.core import embedder

mcp = FastMCP("opencode-mem-tools")


@mcp.tool()
def store_memory(
    content: str,
    tags: str = "",
    type: str = "context",
    display_name: str = "",
    project_path: str = "",
    project_name: str = "",
) -> dict:
    """Store a new memory with local embedding (Ollama nomic-embed-text)."""
    vector = embedder.embed(content)
    return db.store(
        content=content,
        vector=embedder.pack(vector),
        tags=tags,
        type_=type,
        display_name=display_name,
        project_path=project_path or None,
        project_name=project_name or None,
    )


@mcp.tool()
def search_memories(
    query: str,
    limit: int = 10,
) -> list[dict]:
    """Semantic search across all memories using cosine similarity."""
    query_vector = embedder.embed(query)
    return db.search(embedder.pack(query_vector), limit=limit)


@mcp.tool()
def list_memories(
    limit: int = 20,
    offset: int = 0,
    type: Optional[str] = None,
) -> list[dict]:
    """List stored memories, newest first. Optionally filter by type.

    Available types from the plugin: 'context' (auto-captured), 'test', custom types.
    """
    return db.list_memories(limit=limit, offset=offset, type_=type)


@mcp.tool()
def delete_memory(memory_id: str) -> dict:
    """Delete a memory by its ID. Returns success status."""
    ok = db.delete(memory_id)
    return {"deleted": ok, "memory_id": memory_id}


@mcp.tool()
def get_memory_stats() -> dict:
    """Get aggregate statistics about stored memories across all project shards.

    Returns total count, count by type, count by project, and shard info.
    """
    return db.stats()


@mcp.tool()
def list_projects() -> list[dict]:
    """List all project shards that have memories stored."""
    return db._find_shard()
