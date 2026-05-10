-- tasks.db: Task tracking, priorities, completions
CREATE TABLE IF NOT EXISTS tasks (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  description TEXT,
  project_id TEXT,
  priority TEXT NOT NULL DEFAULT 'normal'
    CHECK(priority IN ('critical','high','normal','low')),
  status TEXT NOT NULL DEFAULT 'pending'
    CHECK(status IN ('pending','in_progress','blocked','completed','cancelled')),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  due_date DATETIME,
  completed_at DATETIME,
  estimated_hours FLOAT,
  actual_hours FLOAT,
  assigned_to TEXT,
  tags TEXT,
  recurrence TEXT,
  category TEXT DEFAULT 'general'
);

CREATE TABLE IF NOT EXISTS task_dependencies (
  id TEXT PRIMARY KEY,
  task_id TEXT NOT NULL,
  depends_on TEXT NOT NULL,
  FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
  FOREIGN KEY (depends_on) REFERENCES tasks(id) ON DELETE CASCADE,
  UNIQUE(task_id, depends_on)
);

CREATE TABLE IF NOT EXISTS task_history (
  id TEXT PRIMARY KEY,
  task_id TEXT NOT NULL,
  changed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  field TEXT NOT NULL,
  old_value TEXT,
  new_value TEXT,
  FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS projects (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT,
  status TEXT DEFAULT 'active'
    CHECK(status IN ('active','paused','completed','archived')),
  start_date DATE,
  end_date DATE,
  total_tasks INTEGER DEFAULT 0,
  completed_tasks INTEGER DEFAULT 0,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS calendar_events (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  start_time DATETIME NOT NULL,
  end_time DATETIME,
  category TEXT DEFAULT 'general',
  status TEXT DEFAULT 'scheduled'
    CHECK(status IN ('scheduled','confirmed','cancelled','completed')),
  notes TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON tasks(due_date);
CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks(project_id);
CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority);
CREATE INDEX IF NOT EXISTS idx_history_task ON task_history(task_id);
CREATE INDEX IF NOT EXISTS idx_depends_task ON task_dependencies(task_id);
CREATE INDEX IF NOT EXISTS idx_events_time ON calendar_events(start_time);
CREATE INDEX IF NOT EXISTS idx_events_category ON calendar_events(category);
CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);
