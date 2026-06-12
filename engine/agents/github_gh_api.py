import subprocess
import json

GitHubAPIError = type("GitHubAPIError", (Exception,), {})


class GitHubAPI:
    """Read-only wrapper around GitHub CLI (gh) for API operations."""

    def __init__(self):
        self._auth_checked = False
        self._authenticated = False

    def _gh(self, *args: str) -> dict:
        """Run a gh command and return parsed JSON output."""
        try:
            cp = subprocess.run(
                ["gh"] + list(args),
                capture_output=True, text=True, timeout=30,
            )
        except FileNotFoundError:
            raise GitHubAPIError("gh CLI not found. Install with: brew install gh")
        except subprocess.TimeoutExpired:
            raise GitHubAPIError("gh command timed out")
        if cp.returncode != 0:
            raise GitHubAPIError(cp.stderr.strip() or cp.stdout.strip())
        if not cp.stdout.strip():
            return {}
        try:
            return json.loads(cp.stdout)
        except json.JSONDecodeError:
            return {"raw": cp.stdout.strip()}

    def _gh_text(self, *args: str) -> str:
        """Run a gh command and return raw text output."""
        cp = subprocess.run(
            ["gh"] + list(args),
            capture_output=True, text=True, timeout=30,
        )
        if cp.returncode != 0:
            raise GitHubAPIError(cp.stderr.strip() or cp.stdout.strip())
        return cp.stdout.strip()

    def check_auth(self):
        """Verify gh CLI is authenticated."""
        try:
            cp = subprocess.run(
                ["gh", "auth", "status"],
                capture_output=True, text=True, timeout=10,
            )
            self._authenticated = cp.returncode == 0
        except FileNotFoundError:
            self._authenticated = False
        self._auth_checked = True
        return self._authenticated

    def is_authenticated(self) -> bool:
        if not self._auth_checked:
            self.check_auth()
        return self._authenticated

    def repo_info(self, owner: str, repo: str) -> dict:
        data = self._gh("repo", "view", f"{owner}/{repo}",
                        "--json", "name,description,url,defaultBranchRef,stargazerCount,forkCount,updatedAt,issues,pullRequests")
        default_branch = None
        if data.get("defaultBranchRef"):
            default_branch = data["defaultBranchRef"].get("name")
        return {
            "name": data.get("name"),
            "description": data.get("description"),
            "url": data.get("url"),
            "default_branch": default_branch,
            "stars": data.get("stargazerCount", 0),
            "forks": data.get("forkCount", 0),
            "updated_at": data.get("updatedAt"),
            "open_issues": data.get("issues", {}).get("totalCount", 0),
            "open_prs": data.get("pullRequests", {}).get("totalCount", 0),
        }

    def pr_list(self, owner: str, repo: str, state: str = "open") -> list:
        data = self._gh("pr", "list",
                        "--repo", f"{owner}/{repo}",
                        "--state", state,
                        "--json", "number,title,state,headRefName,author,createdAt,updatedAt",
                        "--limit", "30")
        return [{
            "number": p.get("number"),
            "title": p.get("title"),
            "state": p.get("state"),
            "branch": p.get("headRefName"),
            "author": p.get("author", {}).get("login"),
            "created_at": p.get("createdAt"),
            "updated_at": p.get("updatedAt"),
        } for p in (data or [])]

    def issue_list(self, owner: str, repo: str, state: str = "open") -> list:
        data = self._gh("issue", "list",
                        "--repo", f"{owner}/{repo}",
                        "--state", state,
                        "--json", "number,title,state,author,createdAt,updatedAt",
                        "--limit", "30")
        return [{
            "number": i.get("number"),
            "title": i.get("title"),
            "state": i.get("state"),
            "author": i.get("author", {}).get("login"),
            "created_at": i.get("createdAt"),
            "updated_at": i.get("updatedAt"),
        } for i in (data or [])]

    def ci_status(self, owner: str, repo: str, branch: str = None) -> list:
        args = ["run", "list",
                "--repo", f"{owner}/{repo}",
                "--json", "databaseId,displayTitle,status,conclusion,createdAt,headBranch",
                "--limit", "10"]
        if branch:
            args.extend(["--branch", branch])
        data = self._gh(*args)
        return [{
            "id": r.get("databaseId"),
            "title": r.get("displayTitle"),
            "status": r.get("status"),
            "conclusion": r.get("conclusion"),
            "branch": r.get("headBranch"),
            "created_at": r.get("createdAt"),
        } for r in (data or [])]

    def repo_list_for_user(self, limit: int = 30) -> list:
        data = self._gh("repo", "list",
                        "--json", "name,owner,description,isPrivate,url,defaultBranch,updatedAt",
                        "--limit", str(limit))
        return [{
            "name": r.get("name"),
            "owner": r.get("owner", {}).get("login"),
            "description": r.get("description"),
            "private": r.get("isPrivate", False),
            "url": r.get("url"),
            "default_branch": r.get("defaultBranch"),
            "updated_at": r.get("updatedAt"),
        } for r in (data or [])]

    def check_rate_limit(self) -> dict:
        try:
            data = self._gh("api", "rate_limit")
            core = data.get("resources", {}).get("core", {})
            return {
                "limit": core.get("limit"),
                "remaining": core.get("remaining"),
                "reset": core.get("reset"),
                "used": core.get("used"),
            }
        except GitHubAPIError:
            return {"error": "could not check rate limit"}
