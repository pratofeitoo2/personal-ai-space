"""
AppConfig — Centralized configuration from environment variables.

All hardcoded paths, URLs, and magic numbers have been replaced
with this config loader. Defaults match the original hardcoded values.

Environment variables (all optional — defaults shown):
    OLLAMA_URL=http://localhost:11434/api/embed
    OLLAMA_MODEL=nomic-embed-text:137m-v1.5-fp16
    MEMORY_DB_DIR=<project_root>/personal-ai-space/engine/db
    DATA_DIR=<project_root>/personal-ai-space
    MCP_REGISTRY_PATH=<project_root>/personal-ai-space/engine/mcp_tools/registry.json
    LOG_LEVEL=INFO
    CONTEXT_TTL_SECONDS=300
    PROFILE_PATH=<project_root>/personal-ai-space/self/profile.json
    MCP_SERVER_DIR=<project_root>/personal-ai-space/engine/memory/mcp-server
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, ClassVar

from pydantic import BaseModel, Field, field_validator, model_validator


# Resolve project root: go up from this file to the project root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


class AppConfig(BaseModel):
    """
    Application-wide configuration loaded from environment variables.
    Singleton pattern — call AppConfig.instance() to get the shared config.
    """
    model_config = {"extra": "forbid"}

    # Ollama embedding server
    ollama_url: str = Field(
        default="http://localhost:11434/api/embed",
        description="Ollama API endpoint for text embeddings",
    )
    ollama_model: str = Field(
        default="nomic-embed-text:137m-v1.5-fp16",
        description="Embedding model name",
    )

    # Database paths
    memory_db_dir: Path = Field(
        default=_PROJECT_ROOT / "personal-ai-space" / "engine" / "db",
        description="Directory containing SQLite database files",
    )

    # Project directories
    data_dir: Path = Field(
        default=_PROJECT_ROOT / "personal-ai-space",
        description="Root data directory",
    )

    # MCP configuration
    mcp_registry_path: Path = Field(
        default=_PROJECT_ROOT / "personal-ai-space" / "engine" / "mcp_tools" / "registry.json",
        description="Path to MCP server registry JSON",
    )
    mcp_server_dir: Path = Field(
        default=_PROJECT_ROOT / "personal-ai-space" / "engine" / "memory" / "mcp-server",
        description="Path to Node.js pi-memory MCP server directory",
    )

    # User profile
    profile_path: Path = Field(
        default=_PROJECT_ROOT / "personal-ai-space" / "self" / "profile.json",
        description="Path to user profile JSON",
    )

    # Logging
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)",
    )

    # Cache TTL
    context_ttl_seconds: int = Field(
        default=300,
        description="Context cache TTL in seconds",
        ge=0,
    )

    # MCP transport defaults
    mcp_timeout_seconds: int = Field(
        default=30,
        description="Default MCP server timeout in seconds",
        ge=1,
    )
    mcp_max_retries: int = Field(
        default=2,
        description="Default MCP server retry count",
        ge=0,
    )

    # ── Singleton ─────────────────────────────────────────────────────────────

    _instance: ClassVar[Optional["AppConfig"]] = None

    @model_validator(mode="after")
    def _validate_paths(self) -> "AppConfig":
        """Validate that critical paths exist."""
        # Only validate paths that are required for basic operation
        required_paths = {
            "memory_db_dir": self.memory_db_dir,
            "mcp_server_dir": self.mcp_server_dir,
        }
        for name, path in required_paths.items():
            if not path.exists():
                logger_warning = __import__("logging").getLogger(__name__)
                logger_warning.warning(
                    "Config path '%s' does not exist: %s — creating", name, path
                )
                path.mkdir(parents=True, exist_ok=True)
        return self

    @classmethod
    def instance(cls) -> "AppConfig":
        """Return or create the singleton config instance."""
        if cls._instance is None:
            cls._instance = cls._load_from_env()
        return cls._instance

    @classmethod
    def _load_from_env(cls) -> "AppConfig":
        """Load config from environment variables, falling back to defaults."""
        return cls(
            ollama_url=os.environ.get("OLLAMA_URL", "http://localhost:11434/api/embed"),
            ollama_model=os.environ.get("OLLAMA_MODEL", "nomic-embed-text:137m-v1.5-fp16"),
            memory_db_dir=Path(os.environ.get("MEMORY_DB_DIR", str(_PROJECT_ROOT / "personal-ai-space" / "engine" / "db"))),
            data_dir=Path(os.environ.get("DATA_DIR", str(_PROJECT_ROOT / "personal-ai-space"))),
            mcp_registry_path=Path(os.environ.get("MCP_REGISTRY_PATH", str(_PROJECT_ROOT / "personal-ai-space" / "engine" / "mcp_tools" / "registry.json"))),
            mcp_server_dir=Path(os.environ.get("MCP_SERVER_DIR", str(_PROJECT_ROOT / "personal-ai-space" / "engine" / "memory" / "mcp-server"))),
            profile_path=Path(os.environ.get("PROFILE_PATH", str(_PROJECT_ROOT / "personal-ai-space" / "self" / "profile.json"))),
            log_level=os.environ.get("LOG_LEVEL", "INFO"),
            context_ttl_seconds=int(os.environ.get("CONTEXT_TTL_SECONDS", "300")),
            mcp_timeout_seconds=int(os.environ.get("MCP_TIMEOUT_SECONDS", "30")),
            mcp_max_retries=int(os.environ.get("MCP_MAX_RETRIES", "2")),
        )

    def reload(self):
        """Force reload from environment variables."""
        fresh = self._load_from_env()
        for field_name in self.model_fields:
            setattr(self, field_name, getattr(fresh, field_name))