# personal-ai-space/intake/

## Responsibility
Zero-touch file import pipeline — monitors a staging directory, automatically processes incoming files, and routes them to the correct destinations. Runs as a macOS launchd service.

## Architecture
```
File dropped in staging/
    │
    ▼
watcher.py (poll every 10s, 60s debounce)
    │
    ▼
process_intake.py (route + convert + archive)
    │
    ├── command/inbox/     ← Daily Notes, timestamped captures
    ├── command/finances/  ← CVs, cover letters, financial docs
    ├── knowledge/notes/   ← Notes without specific routing
    ├── knowledge/articles/ ← Research articles
    └── processed/         ← Archived copies of all processed files
```

## Routing Rules
- Filename contains "Daily Notes" or date prefix (YYYY-MM-DD) → `command/inbox/`
- Filename contains "PF", "financial", "CV", "LinkedIn" → `command/finances/`
- Frontmatter tag `article` → `knowledge/articles/`
- Frontmatter tag `project` → `knowledge/projects/`
- All other .md files → `knowledge/notes/`
- Non-markdown files (.txt, .pdf, .docx) → auto-converted to .md first

## Files

| File | Role | Key Functions |
|------|------|--------------|
| `watcher.py` | macOS launchd daemon — polls staging/ every 10s, 60s debounce, triggers processor on new files | `watch()`, `debounce()` |
| `process_intake.py` | File processor — routes by filename/frontmatter, converts formats, archives originals | `process_file()`, `route_by_tags()`, `convert_and_index()` |
| `intake.log` | Import audit trail — timestamps, source paths, destinations | — |
| `watcher.log` | Watcher daemon activity log | — |
| `processed/` | Archive of imported files organized by category | — |

## Integration Points
- **Outputs to**: `command/inbox/`, `command/finances/`, `knowledge/notes/`, `knowledge/articles/`
- **Triggered by**: macOS launchd service (`com.personalai.intake-watcher`)
- **Post-process**: Imported files indexed by `knowledge_indexer` agent and logged via `log_manager`
