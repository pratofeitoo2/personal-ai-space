"""Tests for the type-safe registry loader."""
from __future__ import annotations

import json

import pytest

from transport.registry import Registry, RegistryConfig, ServerConfig
from pydantic import ValidationError


class TestServerConfig:
    def test_stdio_server_requires_command(self):
        with pytest.raises(ValidationError):
            ServerConfig(id="test", transport="stdio")

    def test_http_server_requires_url(self):
        with pytest.raises(ValidationError):
            ServerConfig(id="test", transport="http")

    def test_stdio_server_with_command(self):
        cfg = ServerConfig(id="test", transport="stdio", command="python3")
        assert cfg.id == "test"
        assert cfg.command == "python3"

    def test_http_server_with_url(self):
        cfg = ServerConfig(id="test", transport="http", url="http://localhost:8080/mcp")
        assert cfg.url == "http://localhost:8080/mcp"

    def test_default_values(self):
        cfg = ServerConfig(id="test", transport="stdio", command="python3")
        assert cfg.enabled is False
        assert cfg.args == []
        assert cfg.headers == {}
        assert cfg.env == {}


class TestRegistryConfig:
    def test_rejects_duplicate_ids(self):
        with pytest.raises(ValidationError):
            RegistryConfig(
                servers=[
                    ServerConfig(id="dup", transport="stdio", command="a"),
                    ServerConfig(id="dup", transport="stdio", command="b"),
                ]
            )


class TestRegistry:
    def test_load_from_existing_file(self, tmp_path):
        reg_file = tmp_path / "registry.json"
        reg_file.write_text(json.dumps({
            "servers": [
                {
                    "id": "mail",
                    "name": "Mail MCP",
                    "transport": "stdio",
                    "command": "mail-mcp",
                    "enabled": True,
                }
            ],
            "defaults": {"timeout_seconds": 30},
        }))
        r = Registry(str(reg_file))
        assert len(r.servers) == 1
        assert r.servers[0].id == "mail"

    def test_load_nonexistent_file(self, tmp_path):
        r = Registry(str(tmp_path / "nonexistent.json"))
        assert r.servers == []

    def test_enabled_servers_filter(self, tmp_path):
        reg_file = tmp_path / "registry.json"
        reg_file.write_text(json.dumps({
            "servers": [
                {"id": "a", "transport": "stdio", "command": "cmd1", "enabled": True},
                {"id": "b", "transport": "stdio", "command": "cmd2", "enabled": False},
            ]
        }))
        r = Registry(str(reg_file))
        assert len(r.enabled_servers) == 1
        assert r.enabled_servers[0].id == "a"

    def test_get_server(self, tmp_path):
        reg_file = tmp_path / "registry.json"
        reg_file.write_text(json.dumps({
            "servers": [
                {"id": "mail", "transport": "stdio", "command": "mail-mcp", "enabled": True},
            ]
        }))
        r = Registry(str(reg_file))
        assert r.get_server("mail") is not None
        assert r.get_server("nonexistent") is None

    def test_add_and_remove_server(self, tmp_path):
        r = Registry(str(tmp_path / "empty.json"))
        cfg = ServerConfig(id="new-server", transport="stdio", command="python3", enabled=True)
        assert r.add_server(cfg) is True
        assert len(r.servers) == 1
        assert r.add_server(cfg) is False  # duplicate
        assert r.remove_server("new-server") is True
        assert len(r.servers) == 0

    def test_save_and_reload(self, tmp_path):
        reg_file = tmp_path / "registry.json"
        r1 = Registry(str(reg_file))
        cfg = ServerConfig(id="saved", transport="stdio", command="python3")
        r1.add_server(cfg)
        assert r1.save() is True

        r2 = Registry(str(reg_file))
        assert len(r2.servers) == 1
        assert r2.servers[0].id == "saved"
