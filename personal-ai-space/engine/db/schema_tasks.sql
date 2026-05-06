-- tasks.db: Task tracking, priorities, completions
CREATE TABLE IF NOT EXISTS tasks (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  description TEXT,
  project_id TEXT,
  priority TEXT,
  status TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  due_date DATETIME,
  completed_at DATETIME,
  estimated_hours FLOAT,
  actual_hours FLOAT,
  assigned_to TEXT,
  tags TEXT,
  recurrence TEXT
);

CREATE TABLE IF NOT EXISTS task_dependencies (
  id TEXT PRIMARY KEY,
  task_id TEXT,
  depends_on TEXT,
  FOREIGN KEY (task_id) REFERENCES tasks(id),
  FOREIGN KEY (depends_on) REFERENCES tasks(id)
);

CREATE TABLE IF NOT EXISTS task_history (
  id TEXT PRIMARY KEY,
  task_id TEXT,
  changed_at DATETIME,
  field TEXT,
  old_value TEXT,
  new_value TEXT,
  FOREIGN KEY (task_id) REFERENCES tasks(id)
);

CREATE TABLE IF NOT EXISTS projects (
  id TEXT PRIMARY KEY,
  name TEXT,
  description TEXT,
  status TEXT,
  start_date DATE,
  end_date DATE,
  total_tasks INTEGER,
  completed_tasks INTEGER,
  created_at DATETIME
);

CREATE TABLE IF NOT EXISTS calendar_events (
  id TEXT PRIMARY KEY,
  title TEXT,
  start_time DATETIME,
  end_time DATETIME,
  category TEXT,
  status TEXT,
  notes TEXT,
  created_at DATETIME
);

CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON tasks(due_date);
CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks(project_id);
CREATE INDEX IF NOT EXISTS idx_events_time ON calendar_events(start_time);
