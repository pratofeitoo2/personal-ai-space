import pytest
import tempfile
import subprocess
from pathlib import Path

from agents.github_git_ops import GitOps, GitOperationError


@pytest.fixture
def repo():
    tmp = tempfile.mkdtemp()
    subprocess.run(["git", "init"], cwd=tmp, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=tmp, capture_output=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=tmp, capture_output=True)
    Path(tmp).joinpath("init.txt").write_text("init")
    g = GitOps(tmp)
    g.add()
    g.commit("initial")
    return tmp


class TestGitOps:
    def test_init_not_git_repo(self):
        tmp = tempfile.mkdtemp()
        with pytest.raises(GitOperationError):
            GitOps(tmp)

    def test_status_clean(self, repo):
        g = GitOps(repo)
        s = g.status()
        assert s["branch"] in ("main", "master")
        assert s["staged"] == []
        assert s["modified"] == []
        assert s["untracked"] == []

    def test_status_untracked(self, repo):
        g = GitOps(repo)
        Path(repo).joinpath("new.txt").write_text("hello")
        s = g.status()
        assert "new.txt" in s["untracked"]

    def test_branch_current(self, repo):
        g = GitOps(repo)
        assert g.branch_current() in ("main", "master")

    def test_branch_list(self, repo):
        g = GitOps(repo)
        branches = g.branch_list()
        assert len(branches) == 1
        assert branches[0]["current"] is True

    def test_branch_create_and_delete(self, repo):
        g = GitOps(repo)
        g.branch_create("feature-x")
        branches = g.branch_list()
        names = [b["name"] for b in branches]
        assert "feature-x" in names
        g.branch_delete("feature-x")
        branches = g.branch_list()
        names = [b["name"] for b in branches]
        assert "feature-x" not in names

    def test_add_and_commit(self, repo):
        g = GitOps(repo)
        Path(repo).joinpath("added.txt").write_text("staged")
        g.add(["added.txt"])
        r = g.commit("add file")
        assert r["hash"]
        assert not g.has_uncommitted()

    def test_log(self, repo):
        g = GitOps(repo)
        log = g.log(5)
        assert log["count"] >= 1
        assert log["commits"][0]["message"] == "initial"

    def test_log_empty_repo(self):
        tmp = tempfile.mkdtemp()
        subprocess.run(["git", "init"], cwd=tmp, capture_output=True)
        g = GitOps(tmp)
        log = g.log(1)
        assert log["count"] == 0

    def test_has_uncommitted(self, repo):
        g = GitOps(repo)
        assert not g.has_uncommitted()
        Path(repo).joinpath("dirty.txt").write_text("dirty")
        assert g.has_uncommitted()

    def test_diff(self, repo):
        g = GitOps(repo)
        # Modify an existing tracked file (not a new file — that's untracked)
        Path(repo).joinpath("init.txt").write_text("modified content")
        d = g.diff()
        assert "modified content" in d

    def test_force_push_guardrail_main(self, repo):
        g = GitOps(repo)
        with pytest.raises(GitOperationError, match="Guardrail"):
            g.push(force=True)

    def test_worktree_list(self, repo):
        g = GitOps(repo)
        wts = g.worktree_list()
        assert isinstance(wts, list)

    def test_init_method(self):
        tmp = tempfile.mkdtemp()
        repo_path = str(Path(tmp) / "myrepo")
        g = GitOps.init(repo_path)
        assert (Path(repo_path) / ".git").exists()
        assert g.branch_current() in ("main", "master")

    def test_clone_local(self):
        tmp = tempfile.mkdtemp()
        src = str(Path(tmp) / "src")
        dst = str(Path(tmp) / "dst")
        g = GitOps.init(src)
        subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=src, capture_output=True)
        subprocess.run(["git", "config", "user.name", "T"], cwd=src, capture_output=True)
        Path(src).joinpath("f.txt").write_text("data")
        g.add()
        g.commit("first")
        g2 = GitOps.clone(src, dst)
        assert g2.branch_current() in ("main", "master")
        assert (Path(dst) / "f.txt").exists()
