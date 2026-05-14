"""
Type-safe registry.json loader.

Validates MCP server configurations using Pydantic models.
Matches the existing registry.json format exactly (additive only).
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

logger = logging.getLogger("engine.transport.registry")


class ServerConfig(BaseModel):
    """Validated configuration for a single MCP server."""

    id: str = Field(..., min_length=1, description="Unique server identifier")
    name: str = ""
    description: str = ""
    transport: str = Field(default="stdio", pattern="^(stdio|http)$")
    command: Optional[str] = None
    args: list[str] = Field(default_factory=list)
    url: Optional[str] = None
    headers: dict[str, str] = Field(default_factory=dict)
    env: dict[str, str] = Field(default_factory=dict)
    enabled: bool = False
    tools: list[dict] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_transport_requirements(self) -> "ServerConfig":
        if self.transport == "stdio" and not self.command:
            raise ValueError("stdio transport requires a 'command'")
        if self.transport == "http" and not self.url:
            raise ValueError("http transport requires a 'url'")
        return self


class RegistryConfig(BaseModel):
    """Top-level registry structure."""

    servers: list[ServerConfig] = Field(default_factory=list)
    defaults: dict[str, Any] = Field(default_factory=dict)
    schema_version: str = "1.0"

    @field_validator("servers")
    @classmethod
    def _unique_server_ids(cls, v: list[ServerConfig]) -> list[ServerConfig]:
        ids = [s.id for s in v]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate server IDs in registry")
        return v


class Registry:
    """
    Loads, validates, and saves MCP server registry.json files.

    Usage:
        registry = Registry("path/to/registry.json")
        for server in registry.servers:
            print(server.id, server.transport)
        registry.save()
    """

    def __init__(self, path: str | Path):
        self._path = Path(path)
        self._config: Optional[RegistryConfig] = None
        self._load()

    def _load(self):
        """Load and validate the registry file."""
        if not self._path.exists():
            logger.warning("Registry file not found: %s — using defaults", self._path)
            self._config = RegistryConfig()
            return

        with open(self._path) as f:
            data = json.load(f)
        self._config = RegistryConfig(**data)
        logger.info("Loaded registry: %d servers from %s", len(self._config.servers), self._path)

    @property
    def servers(self) -> list[ServerConfig]:
        """All configured servers."""
        if not self._config:
            return []
        return self._config.servers

    @property
    def enabled_servers(self) -> list[ServerConfig]:
        """Only enabled servers."""
        return [s for s in self.servers if s.enabled]

    def get_server(self, server_id: str) -> Optional[ServerConfig]:
        """Get a specific server by ID."""
        for s in self.servers:
            if s.id == server_id:
                return s
        return None

    def add_server(self, config: ServerConfig) -> bool:
        """Add a new server configuration."""
        if self.get_server(config.id):
            logger.warning("Server '%s' already exists in registry", config.id)
            return False
        if not self._config:
            self._config = RegistryConfig()
        self._config.servers.append(config)
        logger.info("Added server '%s' to registry", config.id)
        return True

    def remove_server(self, server_id: str) -> bool:
        """Remove a server by ID."""
        if not self._config:
            return False
        original = len(self._config.servers)
        self._config.servers = [s for s in self._config.servers if s.id != server_id]
        removed = original - len(self._config.servers)
        if removed:
            logger.info("Removed server '%s' from registry", server_id)
        return removed > 0

    def save(self, path: Optional[str | Path] = None) -> bool:
        """Save registry to disk (defaults to original path)."""
        target = Path(path) if path else self._path
        if not self._config:
            return False
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            with open(target, "w") as f:
                json.dump(self._config.model_dump(exclude_none=True), f, indent=2)
            logger.info("Saved registry to %s", target)
            return True
        except Exception as e:
            logger.error("Failed to save registry: %s", e)
            return False

    def to_dict(self) -> dict:
        """Export as plain dict for backward compatibility."""
        if not self._config:
            return {"servers": []}
        return self._config.model_dump(exclude_none=True)
