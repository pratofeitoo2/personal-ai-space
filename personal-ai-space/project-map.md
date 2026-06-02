# Project Map
_Generated: 2026-05-30 12:30 | Staleness: timestamps_

## Directory Structure
- `engine/` — Core Python engine for personal AI system (database, LLM integration, memory management)
- `engine/db/self/` — SQLite database (`self.db`) with profile, habits, traits, goals, behaviors, observations
- `intake/` — Data intake and processing (watchers, parsers)
- `knowledge/` — Knowledge base (articles, notes)
- `self/` — Personal data organization (goals, traits, needs, habits, profile, documents, relationships)
- `command/` — Task management, calendar, inbox, activities, finances
- `docs/` — Documentation (architecture, data flows, setup guides, reports)
- `tools/` — Utility scripts and dashboards

## Key Files
- `engine/db/self/self.db` — Main SQLite database containing all personal data (profile, habits, traits, goals, behaviors, observations, session data)
- `engine/db/self/schema_self.sql` — Database schema definition (12 tables: profile, habits, habit_logs, traits, needs, behaviors, relationships, goals, observations, documents, session_signals, session_metadata)
- `engine/engine.py` — Core engine logic for personal AI system
- `engine/llm_bridge.py` — LLM integration for AI-powered insights
- `tools/mempalace_dashboard.py` — Existing dashboard utility (reference implementation)
- `docs/ARCHITECTURE.md` — System architecture documentation
- `docs/DATABASE_ARCHITECTURE.md` — Database design and relationships
- `docs/DATA_FLOWS.md` — Data flow documentation
- `codemap.md` — Project structure overview

## Critical Constraints
- Database path: `engine/db/self/self.db` (read-only access for dashboard)
- Database contains 12 tables with foreign key relationships (habit_logs → habits)
- SQLite database is ~2.9MB with WAL mode enabled
- Python dependencies: better-sqlite3 (Node.js) or sqlite3 (Python standard library)
- Dashboard must not modify database — read-only access only
- Profile table has single record (id: self_profile_001)
- Habits table has 4 active habits with Portuguese names
- Traits table has session-inferred traits with confidence scores

## Hot Files
- `engine/db/self/self.db`, `engine/db/self/schema_self.sql`, `engine/engine.py`, `tools/mempalace_dashboard.py`