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
                # Skip common large non-repo dirs
                if entry.name in ("node_modules", "venv", ".venv", "__pycache__"):
                    continue
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
            # Try to get default branch from remote or common names
            cp = subprocess.run(
                ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
                cwd=str(repo_path), capture_output=True, text=True, timeout=10,
            )
            if cp.returncode == 0:
                default_branch = cp.stdout.strip().split("/")[-1]
            else:
                # Fallback: check if main or master exists
                for b in ("main", "master"):
                    cp = subprocess.run(
                        ["git", "show-ref", "--verify", f"refs/heads/{b}"],
                        cwd=str(repo_path), capture_output=True, timeout=5,
                    )
                    if cp.returncode == 0:
                        default_branch = b
                        break
                else:
                    default_branch = "main"
        except Exception:
            default_branch = "main"

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
            "default_branch": default_branch,
            "current_branch": branch,
            "last_commit": last_commit,
            "branch_count": branch_count,
        }

    # -- registration --

    def register(self, repo_path: str, auto_register: bool = True) -> bool:
        """Upsert a repo into git.db and sync its metadata."""
        if not self._db:
            return False
        path = str(Path(repo_path).resolve())
        repo_id = uuid.uuid4().hex[:12]
        now = datetime.now().isoformat()
        name = Path(path).name
        
        info = self._read_repo_info(Path(path))
        remote = info.get("remote_url")
        default_branch = info.get("default_branch", "main")

        try:
            existing = self._db.query(
                "git", "SELECT id FROM repos WHERE path=?",
                (path,))
        except Exception:
            existing = []
            
        if existing:
            repo_id = existing[0]["id"]
            self._db.execute(
                "git",
                "UPDATE repos SET name=?, remote_url=?, default_branch=?, updated_at=?, is_registered=? WHERE path=?",
                (name, remote, default_branch, now, 1 if auto_register else 1, path),
            )
        else:
            self._db.execute(
                "git",
                "INSERT INTO repos (id, name, path, remote_url, default_branch, is_registered, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (repo_id, name, path, remote, default_branch, 1, now, now),
            )
            
        # Full metadata sync
        self.sync_repo_metadata(repo_id, path)
        return True

    def sync_repo_metadata(self, repo_id: str, repo_path: str):
        """Populate branches and worktrees tables for a repository. Also updates repo metadata."""
        if not self._db:
            return
        now = datetime.now().isoformat()
        path_obj = Path(repo_path)
        
        # 0. Update basic repo metadata
        info = self._read_repo_info(path_obj)
        self._db.execute(
            "git",
            "UPDATE repos SET remote_url=?, default_branch=?, updated_at=? WHERE id=?",
            (info.get("remote_url"), info.get("default_branch"), now, repo_id)
        )
        
        # 1. Branches
        try:
            cp = subprocess.run(
                ["git", "branch", "--list", "--format=%(refname:short)||%(objectname:short)||%(committerdate:iso8601)"],
                cwd=repo_path, capture_output=True, text=True, timeout=10
            )
            if cp.returncode == 0:
                # Clear existing branches for this repo
                self._db.execute("git", "DELETE FROM branches WHERE repo_id=?", (repo_id,))
                
                # Get current branch
                cp_curr = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], 
                                       cwd=repo_path, capture_output=True, text=True)
                current = cp_curr.stdout.strip() if cp_curr.returncode == 0 else ""

                for line in cp.stdout.strip().split("\n"):
                    if not line: continue
                    parts = line.split("||")
                    if len(parts) >= 1:
                        b_name = parts[0]
                        b_id = uuid.uuid4().hex[:12]
                        # Convert ISO date or fallback
                        last_commit = parts[2] if len(parts) > 2 else now
                        is_active = 1 if b_name == current else 0
                        self._db.execute(
                            "git",
                            "INSERT INTO branches (id, repo_id, name, is_active_worktree, last_committed_at, created_at) "
                            "VALUES (?, ?, ?, ?, ?, ?)",
                            (b_id, repo_id, b_name, is_active, last_commit, now)
                        )
        except Exception as e:
            if hasattr(self, "logger"):
                self.logger.error(f"Failed to sync branches for {repo_path}: {e}")

        # 2. Worktrees
        try:
            cp = subprocess.run(
                ["git", "worktree", "list", "--porcelain"],
                cwd=repo_path, capture_output=True, text=True, timeout=10
            )
            if cp.returncode == 0:
                self._db.execute("git", "DELETE FROM worktrees WHERE repo_id=?", (repo_id,))
                
                current_wt = {}
                lines = cp.stdout.strip().split("\n")
                for line in lines:
                    if not line:
                        if "path" in current_wt:
                            wt_id = uuid.uuid4().hex[:12]
                            self._db.execute(
                                "git",
                                "INSERT INTO worktrees (id, repo_id, name, path, branch, created_at) "
                                "VALUES (?, ?, ?, ?, ?, ?)",
                                (wt_id, repo_id, Path(current_wt.get("path")).name, 
                                 current_wt.get("path"), current_wt.get("branch", ""), now)
                            )
                        current_wt = {}
                        continue
                    if line.startswith("worktree "): current_wt["path"] = line[9:]
                    elif line.startswith("branch "): current_wt["branch"] = line[7:].replace("refs/heads/", "")
                
                # Handle last entry if missing trailing newline
                if "path" in current_wt:
                    wt_id = uuid.uuid4().hex[:12]
                    self._db.execute(
                        "git",
                        "INSERT INTO worktrees (id, repo_id, name, path, branch, created_at) "
                        "VALUES (?, ?, ?, ?, ?, ?)",
                        (wt_id, repo_id, Path(current_wt.get("path")).name, 
                         current_wt.get("path"), current_wt.get("branch", ""), now)
                    )
        except Exception as e:
            if hasattr(self, "logger"):
                self.logger.error(f"Failed to sync worktrees for {repo_path}: {e}")

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
