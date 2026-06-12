# PRODUCT SPEC: Obsidian Vault Restructure

## Problem

The current codebase is a **flat hybrid** where Obsidian vault content (notes, daily logs, goals, relationships) lives alongside Python engine code, SQLite databases, and configuration files. This creates:

1. **Broken functionality** — Daily notes save to non-existent paths, templates reference deleted directories
2. **No navigation** — No Map of Content (MOC), no Home note, no way to discover related content
3. **Mixed concerns** — Engine code, database files, and personal notes all at the same level
4. **Missing plugins** — Dataview (required for Dashboard), Heatmap Tracker not installed
5. **Inconsistent naming** — Daily notes use 5+ different date formats
6. **Stale cross-references** — Wikilinks point to old `personal-ai-space/` paths

## Desired Experience

A clean, navigable Obsidian vault where:
- **Opening Obsidian** shows a Home dashboard with links to all areas
- **Daily notes** auto-create in the correct folder with proper templates
- **Graph view** shows meaningful connections between goals, habits, knowledge, and daily activity
- **Searching** finds notes by tag, property, or content — not by hunting through folders
- **Engine code** is clearly separated from vault content (still in the same repo, but visually distinct)

## Target Users

- **Primary**: Paulo Rezende (vault owner)
- **Secondary**: AI agents (OpenCode, Claude) that read the vault for context

## Invariants

1. **All existing content is preserved** — no data loss
2. **Engine code remains functional** — Python paths still work after restructure
3. **Git history is maintained** — moves are tracked as renames
4. **Backward compatibility** — existing wikilinks are updated to new paths

## Success Criteria

- [ ] Daily notes create in `Daily/` with ISO date format (`YYYY-MM-DD.md`)
- [ ] Templates load from `_Templates/` folder
- [ ] Home note exists and links to all major areas
- [ ] MOC files exist for Self, Knowledge, Career, and System
- [ ] Graph view shows connected knowledge graph
- [ ] All broken wikilinks are fixed
- [ ] Engine code paths still resolve correctly
- [ ] No `.DS_Store` or cache files in vault content

## Validation

1. Open vault in Obsidian — Home note loads, no broken links in graph
2. Create a new daily note — saves to `Daily/YYYY-MM-DD.md` with template
3. Run `python engine/cli.py status` — engine still works
4. Run `scripts/export_all_databases.py` — exports still work
5. Check graph view — meaningful clusters visible
