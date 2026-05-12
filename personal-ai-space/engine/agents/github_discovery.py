from pathlib import Path
from datetime import datetime
import uuid
import subprocess

GitHubDiscoveryError = type("GitHubDiscoveryError", (Exception,), {})


class GitHubDiscovery:
    """Discovers, registers, and tracks git repositories."""

    def __init__(self, db_manager=None, config_paths: list = None):
        self._db = db_manager
        self._paths = config_paths or []

    # -- discovery --

    def discover(self, paths: list = None) -> list:
        """Scan paths for .git directories. Returns list of repo dicts."""
        scan_paths = paths or self._paths or ["."]
        found = []
        for base in scan_paths:
            base_path = Path(base).resolve()
            self._walk_for_git(base_path, found, depth=0, max_depth=5)
        return found

    def _walk_for_git(self, path: Path, found: list, depth: int, max_depth: int):
        """Recursively walk a path looking for .git directories."""
        if depth > max_depth:
            return
        try:
            entries = sorted(path.iterdir()) if path.is_dir() else []
        except (PermissionError, FileNotFoundError):
            return
        for entry in entries:
            if entry.name == ".git" and entry.is_dir():
                info = self._read_repo_info(entry.parent)
                if info:
                    found.append(info)
                continue
            if entry.is_dir() and not entry.name.startswith("."):
                self._walk_for_git(entry, found, depth + 1, max_depth)

    def _read_repo_info(self, repo_path: Path) -> dict:
        """Read metadata from a discovered git repository."""
        try:
            cp = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=str(repo_path), capture_output=True, text=True, timeout=10,
            )
            remote = cp.stdout.strip() if cp.returncode == 0 else None
        except Exception:
            remote = None
        try:
            cp = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=str(repo_path), capture_output=True, text=True, timeout=10,
            )
            branch = cp.stdout.strip() if cp.returncode == 0 else "unknown"
        except Exception:
            branch = "unknown"
        try:
            cp = subprocess.run(
                ["git", "log", "-1", "--format=%cI"],
                cwd=str(repo_path), capture_output=True, text=True, timeout=10,
            )
            last_commit = cp.stdout.strip() if cp.returncode == 0 else None
        except Exception:
            last_commit = None
        try:
            cp = subprocess.run(
                ["git", "branch", "--list"],
                cwd=str(repo_path), capture_output=True, text=True, timeout=10,
            )
            branch_count = len([l for l in cp.stdout.split("\n") if l.strip()])
        except Exception:
            branch_count = 0
        return {
            "path": str(repo_path.resolve()),
            "name": repo_path.name,
            "remote_url": remote,
            "current_branch": branch,
            "last_commit": last_commit,
            "branch_count": branch_count,
        }

    # -- registration --

    def register(self, repo_path: str, auto_register: bool = True) -> bool:
        """Upsert a repo into git.db."""
        if not self._db:
            return False
        path = str(Path(repo_path).resolve())
        repo_id = uuid.uuid4().hex[:12]
        now = datetime.now().isoformat()
        name = Path(path).name
        remote = None
        try:
            cp = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=path, capture_output=True, text=True, timeout=10,
            )
            remote = cp.stdout.strip() if cp.returncode == 0 else None
        except Exception:
            pass
        try:
            existing = self._db.query(
                "git", "SELECT id FROM repos WHERE path=?",
                (path,))
        except Exception:
            existing = []
        if existing:
            self._db.execute(
                "git",
                "UPDATE repos SET name=?, remote_url=?, updated_at=?, is_registered=? WHERE path=?",
                (name, remote, now, 1 if auto_register else 1, path),
            )
        else:
            self._db.execute(
                "git",
                "INSERT INTO repos (id, name, path, remote_url, is_registered, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (repo_id, name, path, remote, 1, now, now),
            )
        return True

    def is_registered(self, repo_path: str) -> bool:
        """Check if a repo is registered in git.db."""
        if not self._db:
            return False
        path = str(Path(repo_path).resolve())
        rows = self._db.query(
            "git", "SELECT id FROM repos WHERE path=? AND is_registered=1",
            (path,))
        return len(rows) > 0

    def get_registered_repos(self) -> list:
        """Return all registered repos from git.db."""
        if not self._db:
            return []
        return self._db.query(
            "git", "SELECT * FROM repos WHERE is_registered=1 ORDER BY updated_at DESC")

    def discover_and_register(self, paths: list = None) -> list:
        """Discover repos and auto-register new ones."""
        discovered = self.discover(paths)
        registered = []
        for repo in discovered:
            if not self.is_registered(repo["path"]):
                self.register(repo["path"])
                registered.append(repo)
        return registered

    def unregister(self, repo_path: str) -> bool:
        """Remove a repo from tracking (keep on disk)."""
        if not self._db:
            return False
        path = str(Path(repo_path).resolve())
        self._db.execute(
            "git", "UPDATE repos SET is_registered=0, updated_at=? WHERE path=?",
            (datetime.now().isoformat(), path))
        return True
