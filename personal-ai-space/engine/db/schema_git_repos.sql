-- git.db: Repository tracking for the GitHub Specialist Agent
-- Schema for tracking git repos, branches, sync operations, and worktrees.

-- Registered git repositories
CREATE TABLE IF NOT EXISTS repos (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    path TEXT UNIQUE NOT NULL,
    remote_url TEXT,
    default_branch TEXT,
    last_synced_at TEXT,
    is_registered INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Tracked branches per repository
CREATE TABLE IF NOT EXISTS branches (
    id TEXT PRIMARY KEY,
    repo_id TEXT NOT NULL REFERENCES repos(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    is_active_worktree INTEGER NOT NULL DEFAULT 0,
    last_committed_at TEXT,
    created_at TEXT NOT NULL
);

-- Append-only log of sync operations
CREATE TABLE IF NOT EXISTS sync_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repo_id TEXT NOT NULL REFERENCES repos(id) ON DELETE CASCADE,
    action TEXT NOT NULL,
    status TEXT NOT NULL,
    commit_hash TEXT,
    details TEXT,
    started_at TEXT NOT NULL,
    completed_at TEXT
);

-- Git worktree tracking
CREATE TABLE IF NOT EXISTS worktrees (
    id TEXT PRIMARY KEY,
    repo_id TEXT NOT NULL REFERENCES repos(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    path TEXT,
    branch TEXT,
    created_at TEXT NOT NULL
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_repos_path           ON repos(path);
CREATE INDEX IF NOT EXISTS idx_repos_registered     ON repos(is_registered);
CREATE INDEX IF NOT EXISTS idx_branches_repo        ON branches(repo_id);
CREATE INDEX IF NOT EXISTS idx_sync_log_repo        ON sync_log(repo_id);
CREATE INDEX IF NOT EXISTS idx_sync_log_status      ON sync_log(status);
CREATE INDEX IF NOT EXISTS idx_sync_log_started     ON sync_log(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_worktrees_repo       ON worktrees(repo_id);
