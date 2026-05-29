# Session Handoff — 2026-05-29

## What We Built

### 1. WhatsApp Jobs Import Pipeline
- **File:** `sync/whatsapp_jobs_import.py`
- Parses WhatsApp `.txt` exports → extracts job URLs (30+ job boards) → filters March 2026+ → fetches HTML metadata → generates `.md` files in `obsidian/jobs/`
- **Result:** 117 URLs extracted, 87 `.md` files created, 57 unique applications in `jobs.db`
- **Usage:** `python3 sync/whatsapp_jobs_import.py /path/to/chat.txt [--no-fetch] [--dry-run]`

### 2. Jobs CLI Commands
- `cli.py` additions: `jobs sync`, `jobs list`, `jobs statuses`
- Scheduler: hourly `sync_jobs` task wired in `orchestrator/scheduler.py`

### 3. sync_self.py Fix (this session)
- **Problem:** `sync/sync_self.py` failed with `ModuleNotFoundError: No module named 'db_manager'` when run directly
- **Root cause:** Missing `_ENGINE_DIR` sys.path bootstrap (all other sync scripts have it)
- **Fix:** Added 3-line path insert before `import db_manager` at `sync/sync_self.py:22`
- **Verified:** `python3 sync/sync_self.py --quick` now works; habits table syncs correctly

## Key Files

| File | Role |
|------|------|
| `sync/sync_jobs.py` | Syncs `obsidian/jobs/*.md` → `jobs.db` |
| `sync/whatsapp_jobs_import.py` | WhatsApp → `.md` generator |
| `sync/sync_self.py` | Syncs `self/` files → `self.db` |
| `cli.py` | CLI entry for jobs commands |
| `orchestrator/scheduler.py` | Schedules all periodic syncs |
| `db_manager.py` | DB connection manager (has `jobs` in DB_PATHS) |

## Databases (all 8)

| DB | Tables | Rows | Sync Script |
|----|--------|------|-------------|
| `jobs` | 4 | 113 | `sync_jobs.py` |
| `self` | 13 | 2,781 | `sync_self.py` |
| `tasks` | 8 | 74 | reminders + scanner |
| `knowledge` | 6 | 11,211 | `sync_knowledge.py` |
| `memories` | 3 | 54 | — |
| `git` | 5 | 144 | — |
| `calendar` | 3 | 3 | `sync_calendar.py` |
| `activities` | 1 | 0 | — |

## Pitfalls Recorded
- **sync_self.py missing sys.path** — all sync scripts need `_ENGINE_DIR` path insert before `import db_manager`

## Running Full Sync
```bash
cd personal-ai-space/engine
.venv/bin/python3 sync/sync_jobs.py
.venv/bin/python3 sync/sync_self.py
.venv/bin/python3 sync/sync_reminders.py
.venv/bin/python3 sync/sync_calendar.py
.venv/bin/python3 sync/sync_knowledge.py
PYTHONPATH=. .venv/bin/python3 -c "from sync.sync_scanner import run_scan, summarize; print(summarize(run_scan()))"
```
