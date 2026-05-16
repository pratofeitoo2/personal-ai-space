import os
import json
import json5
import logging
from pathlib import Path

logger = logging.getLogger("engine.github_config")

DEFAULTS = {
    "sync_interval": 900,
    "idle_timeout": 120,
    "auto_sync": True,
    "auto_push": False,
    "allow_main_commit": False,
    "discovery_paths": [],
    "max_discovery_depth": 5,
    "log_level": "INFO",
}


class GitHubConfig:
    """Configuration manager for the GitHub Specialist agent.
    Resolution order: env vars > config file > defaults.
    """

    def __init__(self, config_dir: str = None):
        self._data = dict(DEFAULTS)
        if config_dir:
            self._config_path = Path(config_dir) / "github_agent.json"
        else:
            self._config_path = Path(__file__).parent.parent / "config" / "github_agent.json"
        self._load_file()
        self._load_env()

    def _load_file(self):
        """Load config from JSON file."""
        if self._config_path and self._config_path.exists():
            try:
                with open(self._config_path) as f:
                    file_data = json5.load(f)
                self._data.update(file_data)
            except (json.JSONDecodeError, OSError) as e:
                logger.debug("No saved GitHub config found: %s", e)

    def _load_env(self):
        """Override config from environment variables."""
        env_map = {
            "GH_SYNC_INTERVAL": ("sync_interval", int),
            "GH_IDLE_TIMEOUT": ("idle_timeout", int),
            "GH_AUTO_SYNC": ("auto_sync", lambda v: v.lower() == "true"),
            "GH_AUTO_PUSH": ("auto_push", lambda v: v.lower() == "true"),
            "GH_ALLOW_MAIN_COMMIT": ("allow_main_commit", lambda v: v.lower() == "true"),
            "GH_LOG_LEVEL": ("log_level", str),
        }
        for env_key, (config_key, converter) in env_map.items():
            val = os.environ.get(env_key)
            if val is not None:
                try:
                    self._data[config_key] = converter(val)
                except (ValueError, TypeError) as e:
                    logger.debug("Invalid GitHub config value: %s", e)

    def get(self, key: str, default=None):
        """Get a config value."""
        return self._data.get(key, default)

    def set(self, key: str, value):
        """Set a config value (runtime only, does not persist)."""
        if key in DEFAULTS:
            self._data[key] = value

    def save(self):
        """Persist config to file."""
        if not self._config_path:
            return False
        try:
            self._config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._config_path, "w") as f:
                json.dump(self._data, f, indent=2)
            return True
        except OSError:
            return False

    def validate(self) -> list:
        """Validate config values. Returns list of issues."""
        issues = []
        if not isinstance(self._data.get("sync_interval"), (int, float)) or self._data["sync_interval"] < 10:
            issues.append("sync_interval must be >= 10 seconds")
        if not isinstance(self._data.get("idle_timeout"), (int, float)) or self._data["idle_timeout"] < 5:
            issues.append("idle_timeout must be >= 5 seconds")
        if self._data.get("max_discovery_depth", 0) < 1:
            issues.append("max_discovery_depth must be >= 1")
        if self._data.get("log_level") not in ("DEBUG", "INFO", "WARNING", "ERROR"):
            issues.append("log_level must be DEBUG, INFO, WARNING, or ERROR")
        return issues

    def all(self) -> dict:
        """Return all config values."""
        return dict(self._data)

    def reset(self):
        """Reset all values to defaults."""
        self._data = dict(DEFAULTS)
