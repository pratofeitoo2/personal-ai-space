import pytest
import json
import tempfile
from pathlib import Path

from agents.github_config import GitHubConfig, DEFAULTS


class TestGitHubConfig:
    def test_defaults(self):
        cfg = GitHubConfig()
        assert cfg.get("sync_interval") == 900
        assert cfg.get("idle_timeout") == 120
        assert cfg.get("auto_push") is False
        assert cfg.get("allow_main_commit") is False

    def test_set_and_get(self):
        cfg = GitHubConfig()
        cfg.set("idle_timeout", 300)
        assert cfg.get("idle_timeout") == 300
        cfg.set("idle_timeout", 120)

    def test_all_returns_copy(self):
        cfg = GitHubConfig()
        all_vals = cfg.all()
        assert all_vals["sync_interval"] == 900
        assert "auto_sync" in all_vals

    def test_validate_clean(self):
        cfg = GitHubConfig()
        issues = cfg.validate()
        assert issues == []

    def test_validate_bad_values(self):
        cfg = GitHubConfig()
        cfg.set("sync_interval", 1)
        cfg.set("log_level", "TRACE")
        issues = cfg.validate()
        assert len(issues) >= 2

    def test_reset(self):
        cfg = GitHubConfig()
        cfg.set("sync_interval", 999)
        cfg.reset()
        assert cfg.get("sync_interval") == 900

    def test_save_and_load(self):
        tmp = tempfile.mkdtemp()
        cfg = GitHubConfig(config_dir=tmp)
        cfg.set("idle_timeout", 60)
        cfg.save()
        # Verify persisted
        config_path = Path(tmp) / "github_agent.json"
        assert config_path.exists()
        data = json.loads(config_path.read_text())
        assert data["idle_timeout"] == 60
