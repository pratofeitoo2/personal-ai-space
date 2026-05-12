import subprocess
from pathlib import Path
from datetime import datetime

GitOperationError = type("GitOperationError", (Exception,), {})


class GitOps:
    """Thin wrapper around git CLI for a single repository."""

    def __init__(self, repo_path: str):
        self._path = Path(repo_path).resolve()
        if not (self._path / ".git").exists():
            raise GitOperationError(f"Not a git repository: {repo_path}")

    def _run(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git"] + list(args),
            cwd=str(self._path),
            capture_output=True,
            text=True,
            shell=False,
            timeout=60,
        )

    def _require_zero(self, cp: subprocess.CompletedProcess, msg: str = None):
        if cp.returncode != 0:
            detail = msg or cp.stderr.strip() or cp.stdout.strip()
            raise GitOperationError(f"git error: {detail}")

    def status(self) -> dict:
        branch = self.branch_current()
        cp = self._run("status", "--porcelain")
        lines = [l for l in cp.stdout.split("\n") if l.strip()]
        staged, modified, untracked = [], [], []
        for line in lines:
            code = line[:2]
            filepath = line[3:].strip()
            if code == "??":
                untracked.append(filepath)
            elif code[0] != " ":
                staged.append(filepath)
            else:
                modified.append(filepath)
        cp2 = self._run("rev-list", "--left-right", "--count",
                        f"{branch}@{{upstream}}...{branch}")
        ahead = behind = 0
        if cp2.returncode == 0 and cp2.stdout.strip():
            parts = cp2.stdout.strip().split("\t")
            if len(parts) == 2:
                ahead, behind = int(parts[0]), int(parts[1])
        return {
            "branch": branch, "staged": staged,
            "modified": modified, "untracked": untracked,
            "ahead": ahead, "behind": behind,
        }

    def branch_current(self) -> str:
        cp = self._run("rev-parse", "--abbrev-ref", "HEAD")
        if cp.returncode != 0:
            cp2 = self._run("symbolic-ref", "--short", "HEAD")
            if cp2.returncode == 0:
                return cp2.stdout.strip()
            return "detached"
        return cp.stdout.strip()

    def branch_list(self) -> list:
        cp = self._run("branch")
        self._require_zero(cp)
        return [{"name": l.lstrip("* ").strip(), "current": l.startswith("*")}
                for l in cp.stdout.split("\n") if l.strip()]

    def branch_create(self, name: str, base: str = None) -> dict:
        args = ["branch", name]
        if base:
            args.append(base)
        self._require_zero(self._run(*args))
        return {"branch": name, "base": base or "HEAD"}

    def branch_delete(self, name: str, force: bool = False) -> dict:
        flag = "-D" if force else "-d"
        self._require_zero(self._run("branch", flag, name))
        return {"deleted": name}

    def add(self, paths: list = None) -> dict:
        if paths:
            self._run("add", "--", *paths)
        else:
            self._run("add", "--all")
        return {"staged": paths or "all"}

    def commit(self, message: str, author: str = None) -> dict:
        args = ["commit", "-m", message]
        if author:
            args.extend(["--author", author])
        cp = self._run(*args)
        self._require_zero(cp)
        out = cp.stdout.strip()
        hash_val = ""
        for line in out.split("\n"):
            if line.startswith("["):
                parts = line.split("]")[0].split()
                if parts:
                    hash_val = parts[-1]
                break
        return {"hash": hash_val, "message": message, "output": out}

    def log(self, n: int = 10) -> dict:
        """Return recent commits. Returns empty list for repos with no commits."""
        fmt = "--format=%H||%an||%ae||%ai||%s"
        cp = self._run("log", f"-{n}", fmt)
        if cp.returncode != 0:
            # Empty repo with no commits
            return {"commits": [], "count": 0, "error": cp.stderr.strip()}
        commits = []
        for line in cp.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split("||", 4)
            if len(parts) == 5:
                commits.append(dict(zip(
                    ["hash", "author", "email", "date", "message"], parts)))
        return {"commits": commits, "count": len(commits)}

    def pull(self, remote: str = "origin", branch: str = None) -> dict:
        args = ["pull", remote]
        if branch:
            args.append(branch)
        self._require_zero(self._run(*args))
        return {"output": "ok"}

    def push(self, remote: str = "origin", branch: str = None,
             force: bool = False, allow_force: bool = False) -> dict:
        current = branch or self.branch_current()
        if force and current in ("main", "master") and not allow_force:
            raise GitOperationError(
                f"Guardrail: force push refused on '{current}'. "
                f"Set allow_force=True to override.")
        args = ["push", remote, current]
        if force:
            args.insert(1, "--force")
        self._require_zero(self._run(*args))
        return {"output": "ok"}

    def has_uncommitted(self) -> bool:
        cp = self._run("status", "--porcelain")
        return bool(cp.stdout.strip())

    def diff(self) -> str:
        return self._run("diff").stdout

    @classmethod
    def clone(cls, url: str, path: str, branch: str = None) -> "GitOps":
        args = ["git", "clone", url, path]
        if branch:
            args.extend(["--branch", branch])
        cp = subprocess.run(args, capture_output=True, text=True, timeout=300)
        if cp.returncode != 0:
            raise GitOperationError(f"clone failed: {cp.stderr.strip()}")
        return cls(path)

    @classmethod
    def init(cls, path: str) -> "GitOps":
        Path(path).mkdir(parents=True, exist_ok=True)
        cp = subprocess.run(
            ["git", "init"],
            cwd=path, capture_output=True, text=True, timeout=30,
        )
        if cp.returncode != 0:
            raise GitOperationError(f"init failed: {cp.stderr.strip()}")
        return cls(path)

    def worktree_add(self, path: str, branch: str) -> dict:
        self._require_zero(self._run("worktree", "add", path, branch))
        return {"path": path, "branch": branch}

    def worktree_list(self) -> list:
        cp = self._run("worktree", "list", "--porcelain")
        self._require_zero(cp)
        entries, current = [], {}
        for line in cp.stdout.strip().split("\n"):
            if not line:
                if current:
                    entries.append(current)
                    current = {}
                continue
            if line.startswith("worktree "):
                current["path"] = line[9:]
            elif line.startswith("HEAD "):
                current["head"] = line[5:]
            elif line.startswith("branch "):
                current["branch"] = line[7:]
        if current:
            entries.append(current)
        return entries

    def last_commit_time(self):
        cp = self._run("log", "-1", "--format=%cI")
        self._require_zero(cp)
        raw = cp.stdout.strip()
        return datetime.fromisoformat(raw) if raw else datetime.min
