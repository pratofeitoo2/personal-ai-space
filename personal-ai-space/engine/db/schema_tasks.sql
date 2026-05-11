-- tasks.db: Task management hub — projects, tasks, subtasks, dependencies, progress, doc sync
-- This is the canonical schema. The actual DB may lag behind; run migrate_schema_v2.py to catch up.

CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    project_id TEXT,
    parent_task_id TEXT REFERENCES tasks(id),
    priority TEXT NOT NULL DEFAULT 'normal'
        CHECK(priority IN ('critical','high','normal','low')),
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK(status IN ('pending','in_progress','blocked','completed','cancelled')),
    progress_pct INTEGER DEFAULT 0 CHECK(progress_pct BETWEEN 0 AND 100),
    estimated_hours FLOAT,
    actual_hours FLOAT,
    sort_order INTEGER DEFAULT 0,
    assigned_to TEXT,
    tags TEXT,
    recurrence TEXT,
    category TEXT DEFAULT 'general',
    due_date DATETIME,
    completed_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS task_dependencies (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    depends_on TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    dependency_type TEXT DEFAULT 'blocks'
        CHECK(dependency_type IN ('blocks','blocked_by','relates_to','duplicate_of')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(task_id, depends_on)
);

CREATE TABLE IF NOT EXISTS task_history (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    field TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    changed_by TEXT DEFAULT 'system',
    changed_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'active'
        CHECK(status IN ('active','paused','completed','archived')),
    priority TEXT DEFAULT 'normal'
        CHECK(priority IN ('critical','high','normal','low')),
    start_date DATE,
    end_date DATE,
    progress_pct INTEGER DEFAULT 0 CHECK(progress_pct BETWEEN 0 AND 100),
    total_tasks INTEGER DEFAULT 0,
    completed_tasks INTEGER DEFAULT 0,
    category TEXT DEFAULT 'general',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS calendar_events (
    id TEXT PRIMARY KEY,
    task_id TEXT REFERENCES tasks(id),
    title TEXT NOT NULL,
    start_time DATETIME NOT NULL,
    end_time DATETIME,
    category TEXT DEFAULT 'general',
    status TEXT DEFAULT 'scheduled'
        CHECK(status IN ('scheduled','confirmed','cancelled','completed')),
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS doc_links (
    id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL CHECK(entity_type IN ('project','task')),
    entity_id TEXT NOT NULL,
    file_path TEXT NOT NULL,
    link_type TEXT DEFAULT 'documents'
        CHECK(link_type IN ('documents','specifies','notes','journal','reference','goal')),
    frontmatter_status TEXT,
    last_synced DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(entity_type, entity_id, file_path)
);

CREATE TABLE IF NOT EXISTS sync_state (
    id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id TEXT,
    file_path TEXT NOT NULL,
    file_hash TEXT,
    last_modified DATETIME,
    last_synced DATETIME,
    direction TEXT DEFAULT 'bidirectional'
        CHECK(direction IN ('db_to_file','file_to_db','bidirectional')),
    UNIQUE(entity_type, entity_id, file_path)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_tasks_status    ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_due_date  ON tasks(due_date);
CREATE INDEX IF NOT EXISTS idx_tasks_project   ON tasks(project_id);
CREATE INDEX IF NOT EXISTS idx_tasks_priority  ON tasks(priority);
CREATE INDEX IF NOT EXISTS idx_tasks_parent    ON tasks(parent_task_id);
CREATE INDEX IF NOT EXISTS idx_tasks_progress  ON tasks(progress_pct);
CREATE INDEX IF NOT EXISTS idx_tasks_updated   ON tasks(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_history_task    ON task_history(task_id);
CREATE INDEX IF NOT EXISTS idx_depends_task    ON task_dependencies(task_id);
CREATE INDEX IF NOT EXISTS idx_events_time     ON calendar_events(start_time);
CREATE INDEX IF NOT EXISTS idx_events_category ON calendar_events(category);
CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);
CREATE INDEX IF NOT EXISTS idx_projects_priority ON projects(priority);
CREATE INDEX IF NOT EXISTS idx_projects_updated  ON projects(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_doclinks_entity   ON doc_links(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_doclinks_file     ON doc_links(file_path);
CREATE INDEX IF NOT EXISTS idx_sync_file         ON sync_state(file_path);
CREATE INDEX IF NOT EXISTS idx_sync_entity       ON sync_state(entity_type, entity_id);
