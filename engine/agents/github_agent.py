"""
GitHub Specialist Agent.

Manages git repositories, branches, worktrees, commits, and syncs.
Maintains bidirectional communication with all other agents to track work.

Registered commands (defined in agents.config.json):
  status, branch_list, branch_create, branch_delete, commit, log,
  pull, push, clone, init, worktree_add, worktree_list,
  repo_discover, repo_register, repo_list, sync_now, sync_metadata,
  gh_repo_info, gh_pr_list, gh_ci_status
"""
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.base_agent import BaseAgent
from log_manager import audit


class GitHubAgent(BaseAgent):
    """Orchestrates git/GitHub operations and cross-agent tracking."""

    def __init__(self):
        super().__init__("github-agent")
        self._discovery = None
        self._git_ops = None
        self._gh_api = None
        self._sync_engine = None
        self._subscribed_events = {}
        self._registered_repos_cache = []
        self._auto_wired = False

    def initialize(self) -> bool:
        """Set up agent. Auto-wires helpers if available."""
        self._auto_wire_helpers()
        self.state = "ready"
        self.logger.info("GitHub Agent ready")
        return True

    def _auto_wire_helpers(self):
        """Try to auto-import and wire helper modules."""
        if self._auto_wired:
            return
        try:
            import db_manager as _db
            _db.init_git_db()
            from agents.github_git_ops import GitOps
            from agents.github_gh_api import GitHubAPI
            from agents.github_discovery import GitHubDiscovery
            import db_manager as db
            project_root = str(Path(__file__).parent.parent.parent)
            disc = GitHubDiscovery(db, [project_root])
            self.wire_discovery(disc)
            self._gh_api = GitHubAPI()
            registered = disc.discover_and_register()
            if registered:
                self.logger.info("Auto-registered %d repo(s)", len(registered))
            self._registered_repos_cache = disc.get_registered_repos()
            self.logger.info("Auto-wired: discovery, gh_api (%d repo(s) tracked)",
                             len(self._registered_repos_cache))
        except Exception as e:
            self.logger.debug(f"Auto-wire skipped: {e}")
        self._auto_wired = True

    def _git_ops_for(self, repo_path: str):
        """Lazy-init GitOps for a given repo path."""
        if repo_path and not self._git_ops:
            from agents.github_git_ops import GitOps
            try:
                self._git_ops = GitOps(repo_path)
            except Exception as e:
                self.logger.warning(f"GitOps init failed for {repo_path}: {e}")
        return self._git_ops

    def shutdown(self) -> None:
        """Clean shutdown. Flush pending syncs."""
        if self._sync_engine:
            try:
                self._sync_engine.stop()
            except Exception as e:
                self.logger.warning(f"Sync engine stop error: {e}")
        self._subscribed_events.clear()
        self.state = "stopped"
        super().shutdown()

    # -- message routing --

    def process(self, message: dict) -> dict:
        """Route incoming message by payload.command to handler."""
        payload = message.get("payload", {})
        command = payload.get("command", "unknown")
        params = payload.get("parameters", {})

        handler = self._get_handler(command)
        if handler is None:
            return self._unknown(command)

        repo_path = params.get("repo_path")
        if repo_path and command not in ("repo_discover", "repo_register", "repo_list"):
            if not self._is_registered_repo(repo_path):
                return self._error(
                    f"Guardrail: repo not registered: {repo_path}. "
                    f"Use repo_discover or repo_register first.")
        try:
            return self._ok(handler(params))
        except Exception as e:
            self.logger.error(f"Command [{command}] failed: {e}", exc_info=True)
            return self._error(str(e))

    def _get_handler(self, command: str):
        """Map command name to handler method."""
        handlers = {
            "status": self._cmd_status,
            "branch_list": self._cmd_branch_list,
            "branch_create": self._cmd_branch_create,
            "branch_delete": self._cmd_branch_delete,
            "commit": self._cmd_commit,
            "log": self._cmd_log,
            "pull": self._cmd_pull,
            "push": self._cmd_push,
            "clone": self._cmd_clone,
            "init": self._cmd_init,
            "worktree_add": self._cmd_worktree_add,
            "worktree_list": self._cmd_worktree_list,
            "repo_discover": self._cmd_repo_discover,
            "repo_register": self._cmd_repo_register,
            "repo_list": self._cmd_repo_list,
            "sync_now": self._cmd_sync_now,
            "sync_metadata": self._cmd_sync_metadata,
            "gh_repo_info": self._cmd_gh_repo_info,
            "gh_pr_list": self._cmd_gh_pr_list,
            "gh_ci_status": self._cmd_gh_ci_status,
            "event": self._cmd_handle_event,
        }
        return handlers.get(command)

    def _resolve_gitops(self, repo_path: str):
        """Get or create GitOps for a path."""
        if self._git_ops:
            return self._git_ops
        return self._git_ops_for(repo_path)

    # -- base command handlers --

    def _cmd_status(self, params: dict) -> dict:
        repo_path = params.get("repo_path")
        if not repo_path:
            return {"message": "GitHub Agent ready",
                    "repos_tracked": len(self._registered_repos_cache)}
        g = self._resolve_gitops(repo_path)
        if g:
            return g.status()
        return {"repo_path": repo_path, "error": "repo_path invalid or not a git repo"}

    def _cmd_branch_list(self, params: dict) -> dict:
        repo_path = params.get("repo_path")
        if not repo_path:
            return {"branches": []}
        g = self._resolve_gitops(repo_path)
        if g:
            return {"branches": g.branch_list()}
        return {"branches": []}

    def _cmd_branch_create(self, params: dict) -> dict:
        repo_path = params.get("repo_path")
        name = params.get("name")
        if not repo_path or not name:
            return {"error": "repo_path and name required"}
        g = self._resolve_gitops(repo_path)
        if g:
            return g.branch_create(name, params.get("base"))
        return {"error": "invalid repo_path"}

    def _cmd_branch_delete(self, params: dict) -> dict:
        repo_path = params.get("repo_path")
        name = params.get("name")
        if not repo_path or not name:
            return {"error": "repo_path and name required"}
        g = self._resolve_gitops(repo_path)
        if g:
            return g.branch_delete(name, params.get("force", False))
        return {"error": "invalid repo_path"}

    def _cmd_commit(self, params: dict) -> dict:
        repo_path = params.get("repo_path")
        g = self._resolve_gitops(repo_path)
        if g:
            g.add(params.get("files"))
            return g.commit(params.get("message", "auto-sync"))
        return {"error": "repo_path required"}

    def _cmd_log(self, params: dict) -> dict:
        repo_path = params.get("repo_path")
        g = self._resolve_gitops(repo_path)
        if g:
            return g.log(params.get("n", 10))
        return {"commits": [], "error": "repo_path required"}

    def _cmd_pull(self, params: dict) -> dict:
        repo_path = params.get("repo_path")
        g = self._resolve_gitops(repo_path)
        if g:
            return g.pull(params.get("remote", "origin"), params.get("branch"))
        return {"error": "repo_path required"}

    def _cmd_push(self, params: dict) -> dict:
        repo_path = params.get("repo_path")
        g = self._resolve_gitops(repo_path)
        if g:
            return g.push(params.get("remote", "origin"), params.get("branch"),
                          params.get("force", False),
                          params.get("allow_force", False))
        return {"error": "repo_path required"}

    def _cmd_clone(self, params: dict) -> dict:
        from agents.github_git_ops import GitOps
        url = params.get("url")
        path = params.get("path")
        if not url or not path:
            return {"error": "url and path required"}
        try:
            g = GitOps.clone(url, path, params.get("branch"))
            return {"cloned": True, "path": path}
        except Exception as e:
            return {"error": str(e)}

    def _cmd_init(self, params: dict) -> dict:
        from agents.github_git_ops import GitOps
        path = params.get("path")
        if not path:
            return {"error": "path required"}
        try:
            g = GitOps.init(path)
            if self._discovery:
                self._discovery.register(path)
            return {"initialized": True, "path": path}
        except Exception as e:
            return {"error": str(e)}

    def _cmd_worktree_add(self, params: dict) -> dict:
        repo_path = params.get("repo_path")
        g = self._resolve_gitops(repo_path)
        if g:
            return g.worktree_add(params["path"], params["branch"])
        return {"error": "repo_path required"}

    def _cmd_worktree_list(self, params: dict) -> dict:
        repo_path = params.get("repo_path")
        g = self._resolve_gitops(repo_path)
        if g:
            return {"worktrees": g.worktree_list()}
        return {"worktrees": [], "error": "repo_path required"}

    def _cmd_repo_list(self, params: dict) -> dict:
        return {"repos": self._registered_repos_cache,
                "count": len(self._registered_repos_cache)}

    def _cmd_sync_now(self, params: dict) -> dict:
        if self._sync_engine:
            repo_path = params.get("repo_path")
            if repo_path:
                return self._sync_engine.sync_repo(repo_path, params.get("message"))
            return self._sync_engine.sync_all_registered()
        return {"synced": False, "note": "Sync engine not wired (T10)"}

    def _cmd_sync_metadata(self, params: dict) -> dict:
        if not self._discovery:
            return {"error": "Discovery helper not wired"}
        repo_path = params.get("repo_path")
        if not repo_path:
            # Sync all registered
            repos = self._discovery.get_registered_repos()
            for r in repos:
                self._discovery.sync_repo_metadata(r["id"], r["path"])
            return {"synced_count": len(repos)}
        
        # Sync specific repo
        path = str(Path(repo_path).resolve())
        rows = self._discovery._db.query("git", "SELECT id FROM repos WHERE path=?", (path,))
        if rows:
            self._discovery.sync_repo_metadata(rows[0]["id"], path)
            return {"synced": True, "path": path}
        return {"error": f"Repo not registered: {repo_path}"}

    def _cmd_repo_discover(self, params: dict) -> dict:
        if self._discovery:
            paths = params.get("paths", [])
            repos = self._discovery.discover_and_register(paths)
            self._registered_repos_cache = self._discovery.get_registered_repos()
            return {"discovered": repos}
        return {"discovered": [], "note": "Discovery not wired"}

    def _cmd_repo_register(self, params: dict) -> dict:
        repo_path = params.get("repo_path")
        if not repo_path:
            return {"error": "repo_path required"}
        if self._discovery:
            self._discovery.register(repo_path)
            self._registered_repos_cache = self._discovery.get_registered_repos()
            return {"registered": True, "path": repo_path}
        return {"registered": False, "note": "Discovery not wired"}

    def _cmd_gh_repo_info(self, params: dict) -> dict:
        owner = params.get("owner")
        repo = params.get("repo")
        if not owner or not repo:
            return {"error": "owner and repo required"}
        if self._gh_api:
            return self._gh_api.repo_info(owner, repo)
        return {"error": "gh_api not wired"}

    def _cmd_gh_pr_list(self, params: dict) -> dict:
        owner = params.get("owner")
        repo = params.get("repo")
        if not owner or not repo:
            return {"error": "owner and repo required"}
        if self._gh_api:
            return {"prs": self._gh_api.pr_list(owner, repo, params.get("state", "open"))}
        return {"error": "gh_api not wired"}

    def _cmd_gh_ci_status(self, params: dict) -> dict:
        owner = params.get("owner")
        repo = params.get("repo")
        if not owner or not repo:
            return {"error": "owner and repo required"}
        if self._gh_api:
            return {"runs": self._gh_api.ci_status(owner, repo, params.get("branch"))}
        return {"error": "gh_api not wired"}

    def _cmd_handle_event(self, params: dict) -> dict:
        event_type = params.get("event_type", "unknown")
        data = params.get("data", {})
        handler = self._subscribed_events.get(event_type)
        if handler:
            return handler(data)
        self.logger.debug(f"No handler for event: {event_type}")
        return {"handled": False, "event_type": event_type}

    # -- guardrails --

    def _is_registered_repo(self, repo_path: str) -> bool:
        if not repo_path:
            return False
        if self._discovery:
            return self._discovery.is_registered(repo_path)
        return any(r["path"] == repo_path for r in self._registered_repos_cache)

    # -- cross-agent integration --

    def set_observer(self, observer):
        super().set_observer(observer)
        self.logger.debug("Observer wired to GitHub agent")

    def subscribe_to_event(self, event_type: str, handler):
        self._subscribed_events[event_type] = handler

    def on_agent_work_completed(self, data: dict) -> dict:
        agent_id = data.get("agent_id", "?")
        action = data.get("action", "?")
        self.logger.info(f"Agent work completed: {agent_id}/{action}")
        if self._sync_engine and data.get("repo_path"):
            self._sync_engine.sync_repo(data["repo_path"],
                                        f"auto: {agent_id}/{action}")
        return {"tracked": True, "agent_id": agent_id, "action": action}

    # -- helper wiring methods --

    def wire_git_ops(self, git_ops):
        self._git_ops = git_ops

    def wire_gh_api(self, gh_api):
        self._gh_api = gh_api

    def wire_discovery(self, discovery):
        self._discovery = discovery
        if discovery:
            self._registered_repos_cache = discovery.get_registered_repos()

    def wire_sync_engine(self, sync_engine):
        self._sync_engine = sync_engine
