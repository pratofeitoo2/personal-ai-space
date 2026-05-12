import pytest
import tempfile
import subprocess
from pathlib import Path

import db_manager
from agents.github_discovery import GitHubDiscovery


@pytest.fixture
def db():
    db_manager.init_git_db()
    return db_manager


@pytest.fixture
def git_repo():
    tmp = tempfile.mkdtemp()
    subprocess.run(["git", "init"], cwd=tmp, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=tmp, capture_output=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=tmp, capture_output=True)
    Path(tmp).joinpath("f.txt").write_text("init")
    # Do initial commit so branch references work
    subprocess.run(["git", "add", "--all"], cwd=tmp, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=tmp, capture_output=True)
    return tmp


class TestGitHubDiscovery:
    def test_discover_finds_repo(self, db, git_repo):
        d = GitHubDiscovery(db)
        repos = d.discover([git_repo])
        assert len(repos) == 1
        assert repos[0]["name"] == Path(git_repo).name

    def test_discover_empty_dir(self, db):
        tmp = tempfile.mkdtemp()
        d = GitHubDiscovery(db)
        repos = d.discover([tmp])
        assert len(repos) == 0

    def test_register_and_is_registered(self, db, git_repo):
        d = GitHubDiscovery(db)
        assert not d.is_registered(git_repo)
        d.register(git_repo)
        assert d.is_registered(git_repo)

    def test_get_registered_repos(self, db, git_repo):
        d = GitHubDiscovery(db)
        d.register(git_repo)
        repos = d.get_registered_repos()
        assert len(repos) >= 1
        paths = [r["path"] for r in repos]
        assert str(Path(git_repo).resolve()) in paths

    def test_unregister(self, db, git_repo):
        d = GitHubDiscovery(db)
        d.register(git_repo)
        assert d.is_registered(git_repo)
        d.unregister(git_repo)
        assert not d.is_registered(git_repo)

    def test_discover_and_register(self, db, git_repo):
        d = GitHubDiscovery(db)
        registered = d.discover_and_register([git_repo])
        # Should have registered the repo
        assert d.is_registered(git_repo)

    def test_discover_twice_no_duplicate(self, db, git_repo):
        d = GitHubDiscovery(db)
        d.discover_and_register([git_repo])
        # Second discover_and_register should not duplicate
        d2 = GitHubDiscovery(db)
        d2.discover_and_register([git_repo])
        repos = d2.get_registered_repos()
        paths = [r["path"] for r in repos]
        matches = [p for p in paths if str(Path(git_repo).resolve()) == p]
        assert len(matches) == 1
