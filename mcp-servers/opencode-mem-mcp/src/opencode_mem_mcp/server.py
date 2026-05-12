from __future__ import annotations

from fastmcp import FastMCP

from opencode_mem_mcp.tools.memory import mcp as memory_mcp

mcp = FastMCP(
    "opencode-mem-mcp",
    instructions=(
        "MCP interface to the opencode-mem vector memory plugin. "
        "Stores and searches memories using Ollama nomic-embed-text locally. "
        "Use store_memory() to persist information, search_memories() for "
        "semantic lookup, and list_memories() to browse recent entries."
    ),
)

mcp.mount(memory_mcp, namespace=None)


def serve() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    serve()
