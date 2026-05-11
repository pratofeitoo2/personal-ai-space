-- knowledge.db: Articles, notes, references
CREATE TABLE IF NOT EXISTS articles (
  id TEXT PRIMARY KEY,
  title TEXT,
  url TEXT UNIQUE,
  source TEXT,
  author TEXT,
  published_date DATE,
  imported_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  tags TEXT,
  summary TEXT,
  full_content TEXT,
  relevance_score FLOAT,
  status TEXT
);

CREATE TABLE IF NOT EXISTS notes (
  id TEXT PRIMARY KEY,
  title TEXT,
  content TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME,
  tags TEXT,
  linked_to TEXT,
  category TEXT,
  importance_level INTEGER,
  original_format TEXT DEFAULT 'md',
  conversion_metadata TEXT
);

CREATE TABLE IF NOT EXISTS "references" (
  id TEXT PRIMARY KEY,
  title TEXT,
  url TEXT,
  source TEXT,
  reference_type TEXT,
  category TEXT,
  tags TEXT,
  notes TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS projects_knowledge (
  id TEXT PRIMARY KEY,
  name TEXT,
  status TEXT,
  description TEXT,
  start_date DATE,
  end_date DATE,
  linked_articles TEXT,
  linked_notes TEXT,
  created_at DATETIME
);

CREATE TABLE IF NOT EXISTS knowledge_index (
  id TEXT PRIMARY KEY,
  term TEXT UNIQUE,
  frequency INTEGER,
  last_updated DATETIME,
  related_terms TEXT
);

CREATE TABLE IF NOT EXISTS cross_references (
  id TEXT PRIMARY KEY,
  from_id TEXT,
  from_type TEXT,
  to_id TEXT,
  to_type TEXT,
  relationship TEXT,
  created_at DATETIME
);

CREATE INDEX IF NOT EXISTS idx_articles_tags ON articles(tags);
CREATE INDEX IF NOT EXISTS idx_notes_category ON notes(category);
CREATE INDEX IF NOT EXISTS idx_notes_created ON notes(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_knowledge_index_term ON knowledge_index(term);
CREATE INDEX IF NOT EXISTS idx_notes_original_format ON notes(original_format);
