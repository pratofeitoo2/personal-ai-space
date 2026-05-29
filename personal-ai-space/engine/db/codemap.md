# personal-ai-space/engine/db/

## Responsibility
SQLite persistence layer — 8 databases with dedicated schemas, migration scripts, and architecture documentation. All databases initialized by `init_engine.py` on first run.

## Database Catalog

| Database File   | Schema File               | Purpose                                     | Key Tables                                                       |
|-----------------|---------------------------|---------------------------------------------|------------------------------------------------------------------|
| `memories.db`   | `schema_memories.sql`     | Agent interactions and context              | `interactions`, `contexts`, `embeddings`                         |
| `self.db`       | `schema_self.sql`         | Profile, habits, traits, needs (9 tables)   | `profile`, `habits`, `traits`, `needs`, `goals`, `relationships` |
| `tasks.db`      | `schema_tasks.sql`        | Tasks, projects, calendar (5 tables)        | `tasks`, `projects`, `calendar_events`, `dependencies`           |
| `knowledge.db`  | `schema_knowledge.sql`    | Articles, notes, references (6 tables)      | `articles`, `notes`, `references`, `tags`, `links`               |
| `git.db`        | `schema_git_repos.sql`    | Git repository tracking                     | `repos`, `commits`, `branches`                                   |
| `activities.db` | `schema_activities.sql`   | User activity logging                       | `activities`                                                     |
| `calendar.db`   | `schema_calendar.sql`     | Calendar events from Apple/iCal             | `events`                                                         |
| `jobs.db`       | `schema_jobs.sql`         | Job applications tracking                   | `companies`, `applications`, `interviews`, `contacts`            |

## Migration Strategy
- Migration scripts run on engine startup if detected schema version mismatch
- `migrate_schema_v2.py` — Major schema migration to v2
- `migrate_tasks.py` — Tasks table migrations
- `migrate_knowledge.py` — Knowledge table migrations
- `migrate_goals.py` — Goals table migrations
- `migrate_cleanup.py` — Data cleanup post-migration

## Schema Overview
- All databases use WAL mode for concurrent read performance
- Foreign keys enforced via `PRAGMA foreign_keys = ON`
- Timestamps stored as ISO-8601 text
- Full-text search via FTS5 on knowledge and notes tables

## Integration Points
- **Consumed by**: `db_manager.py` (connection pooling), all agents, `mcp_bridge.py`
- **Created by**: `init_engine.py` (schema creation on first run)
- **Synced from Obsidian**: `sync/sync_jobs.py` reads `obsidian/jobs/*.md` frontmatter → `jobs.db`
- **CLI**: `cli.py jobs sync|list|statuses` — sync, query, and pipeline overview
- **Scheduler**: Periodic `jobs_sync` runs every 60 minutes via `orchestrator/scheduler.py`
- **Architecture doc**: `DATABASE_ARCHITECTURE.md` for detailed ERD
