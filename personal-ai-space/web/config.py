"""Central configuration for the web app."""
import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent  # personal-ai-space/
ENGINE_DIR = BASE_DIR / "engine"
DB_DIR = ENGINE_DIR / "db"

# Database paths (read-only)
DB_PATHS = {
    "tasks": DB_DIR / "tasks" / "tasks.db",
    "self": DB_DIR / "self" / "self.db",
    "calendar": DB_DIR / "calendar" / "calendar.db",
    "jobs": DB_DIR / "jobs" / "jobs.db",
}

# Daemon HTTP API
DAEMON_BASE = os.environ.get("PAI_DAEMON_URL", "http://127.0.0.1:19876")

# Ollama LLM
OLLAMA_BASE = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")

# Web server
WEB_HOST = os.environ.get("PAI_WEB_HOST", "0.0.0.0")
WEB_PORT = int(os.environ.get("PAI_WEB_PORT", "5001"))

# Security: local network only (no auth for now, but rate limiting)
MAX_REQUESTS_PER_MINUTE = 60
