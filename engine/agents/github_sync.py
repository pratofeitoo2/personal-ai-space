import threading
import time
import logging
from datetime import datetime, timezone
from pathlib import Path


class SyncEngine:
    """Manages periodic git sync with idle detection."""

    def __init__(self, git_ops_cls=None, discovery=None, db_manager=None, config: dict = None):
        self._git_ops_cls = git_ops_cls
        self._discovery = discovery
        self._db = db_manager
        self.idle_timeout = (config or {}).get("idle_timeout", 120)
        self.sync_interval = (config or {}).get("sync_interval", 900)
        self.auto_push = (config or {}).get("auto_push", False)
        self.allow_main_commit = (config or {}).get("allow_main_commit", False)
        self.enabled = (config or {}).get("enabled", True)
        self._timer = None
        self._running = False
        self._last_sync_time = datetime.min
        self._last_activity_time = datetime.now()
        self._logger = logging.getLogger("engine.sync")

    def start(self):
        """Start the background sync loop."""
        if self._running:
            return
        self._running = True
        self._last_sync_time = datetime.now()
        self._timer = threading.Thread(target=self._loop, daemon=True)
        self._timer.start()
        self._logger.info(f"SyncEngine started (interval={self.sync_interval}s, idle={self.idle_timeout}s)")

    def stop(self):
        """Stop the background sync loop."""
        self._running = False
        self._logger.info("SyncEngine stopped")

    def _loop(self):
        """Background loop: periodic sync + idle checks."""
        while self._running:
            try:
                if not self.enabled:
                    time.sleep(10)
                    continue
                now = datetime.now()
                elapsed_since_sync = (now - self._last_sync_time).total_seconds()
                idle_duration = (now - self._last_activity_time).total_seconds()
                if elapsed_since_sync >= self.sync_interval:
                    self._logger.info("Periodic sync triggered")
                    self.sync_all_registered()
                elif idle_duration >= self.idle_timeout and self._has_idle_work():
                    self._logger.info("Idle-detected sync triggered")
                    self.sync_all_registered()
            except Exception as e:
                self._logger.warning(f"Sync loop error: {e}")
            time.sleep(min(30, self.idle_timeout / 2))

    def _has_idle_work(self) -> bool:
        """Check if there are repos with uncommitted changes."""
        repos = self._get_registered_repos()
        for repo in repos:
            try:
                g = self._git_ops_for(repo["path"])
                if g and g.has_uncommitted():
                    return True
            except Exception:
                continue
        return False

    def _git_ops_for(self, repo_path: str):
        """Get GitOps instance for a path."""
        if self._git_ops_cls:
            try:
                return self._git_ops_cls(repo_path)
            except Exception:
                return None
        return None

    def _get_registered_repos(self) -> list:
        """Get registered repos from discovery module or DB."""
        if self._discovery:
            return self._discovery.get_registered_repos()
        if self._db:
            try:
                return self._db.query("git", "SELECT * FROM repos WHERE is_registered=1")
            except Exception:
                return []
        return []

    def sync_repo(self, repo_path: str, message: str = None) -> dict:
        """Sync a single repo: commit uncommitted changes."""
        g = self._git_ops_for(repo_path)
        if not g:
            return {"path": repo_path, "committed": False, "error": "not a git repo"}
        if not g.has_uncommitted():
            return {"path": repo_path, "committed": False, "reason": "clean"}
        try:
            current_branch = g.branch_current()
            if current_branch in ("main", "master") and not self.allow_main_commit:
                # Check if there are any commits yet — fresh repos have no valid refs
                has_commits = bool(g.log(1).get("commits"))
                branch_name = f"auto-sync-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
                if has_commits:
                    g.branch_create(branch_name, current_branch)
                    return {"path": repo_path, "committed": False,
                            "reason": "main/master guardrail", "created_branch": branch_name}
                # Fresh repo with no commits: commit to main is safe
            g.add()
            msg = message or f"chore(sync): auto-sync {datetime.now().isoformat()}"
            result = g.commit(msg)
            self._log_sync(repo_path, "commit", "success", result.get("hash"))
            if self.auto_push:
                try:
                    g.push()
                    self._log_sync(repo_path, "push", "success", result.get("hash"))
                except Exception as e:
                    self._log_sync(repo_path, "push", "failed", str(e))
            self._last_sync_time = datetime.now()
            return {"path": repo_path, "committed": True, "hash": result.get("hash"), "message": msg}
        except Exception as e:
            self._log_sync(repo_path, "commit", "failed", str(e))
            return {"path": repo_path, "committed": False, "error": str(e)}

    def sync_all_registered(self) -> dict:
        """Sync all registered repos."""
        repos = self._get_registered_repos()
        results = []
        for repo in repos:
            r = self.sync_repo(repo["path"])
            results.append(r)
        self._last_sync_time = datetime.now()
        return {"synced": len(results), "results": results}

    def _log_sync(self, repo_path: str, action: str, status: str, detail: str = None):
        """Record a sync operation in git.db and update last_synced_at."""
        if not self._db:
            return
        try:
            repo_rows = self._db.query("git", "SELECT id FROM repos WHERE path=?", (repo_path,))
            if not repo_rows:
                return
            repo_id = repo_rows[0]["id"]
            now = datetime.now().isoformat()
            self._db.execute(
                "git",
                "INSERT INTO sync_log (repo_id, action, status, commit_hash, details, started_at, completed_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (repo_id, action, status, detail if status == "success" else None,
                 detail if status != "success" else None,
                 now, now),
            )
            if status == "success":
                self._db.execute(
                    "git",
                    "UPDATE repos SET last_synced_at=?, updated_at=? WHERE id=?",
                    (now, now, repo_id)
                )
        except Exception:
            logger.debug("Auto-commit failed (expected when no changes)")

    def report(self) -> dict:
        """Return sync status report."""
        repos = self._get_registered_repos()
        return {
            "running": self._running,
            "last_sync": self._last_sync_time.isoformat() if self._last_sync_time else None,
            "tracked_repos": len(repos),
            "auto_push": self.auto_push,
            "idle_timeout": self.idle_timeout,
            "sync_interval": self.sync_interval,
        }

    def record_activity(self):
        """Mark activity timestamp (called by agent on any operation)."""
        self._last_activity_time = datetime.now()
