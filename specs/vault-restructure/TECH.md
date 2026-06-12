# TECH SPEC: Obsidian Vault Restructure

## Architecture Decision

**Approach: PARA-inspired flat structure with numbered prefixes**

The vault will use a hybrid PARA/MOC structure:
- Numbered folders for broad categories (visual ordering)
- MOC notes for navigation within categories
- Atomic notes for knowledge
- Separate system folders for templates and attachments

This avoids deep nesting while maintaining clear separation between vault content and project code.

## Target Directory Structure

```
vault-root/
├── _System/                          # Vault config (sorted first)
│   ├── _Templates/                   # Note templates
│   │   ├── _Daily.md
│   │   ├── _Goal.md
│   │   ├── _Habit.md
│   │   ├── _Knowledge Note.md
│   │   ├── _Career Document.md
│   │   ├── _Meeting.md
│   │   └── _MOC.md
│   └── _Attachments/                 # Images, PDFs, media
│
├── 00 - Dashboard/                   # Entry point
│   ├── Home.md                       # Main navigation hub
│   ├── Session Log.md                # Development session log
│   └── State.md                      # Current session state
│
├── 01 - Daily/                       # Daily notes (auto-created)
│   ├── Daily Notes Dashboard.md      # Dataview dashboard
│   ├── Daily Notes.base              # Bases view
│   └── YYYY-MM-DD.md                 # Daily notes (ISO format)
│
├── 02 - Self/                        # Personal data (digital twin)
│   ├── MOC - Self.md                 # Navigation hub
│   ├── Profile/                      # Profile data
│   │   ├── Paulo Rezende.md          # Main profile (from profile.json)
│   │   └── Personality.md            # Traits (from inferred_personality.json)
│   ├── Goals/                        # Goal tracking
│   ├── Habits/                       # Habit tracking
│   ├── Needs/                        # Needs assessment
│   ├── Relationships/                # People connections
│   │   └── People.base               # Bases view
│   └── Documents/                    # Identity documents (SENSITIVE)
│       ├── Healthcare/
│       ├── Kids/
│       ├── Military/
│       ├── Work Card/
│       ├── Birth Certificate/
│       └── Voter Registration/
│
├── 03 - Knowledge/                   # Learning & research
│   ├── MOC - Knowledge.md            # Navigation hub
│   ├── Articles/                     # Academic articles
│   ├── Notes/                        # Research notes
│   ├── MCP Server Guides/            # Tool documentation
│   └── Study Plans/                  # Learning roadmaps
│
├── 04 - Career/                      # Professional development
│   ├── MOC - Career.md               # Navigation hub
│   ├── Resumes/                      # CVs (EN + PT-BR)
│   ├── Cover Letters/                # Application letters
│   ├── Profiles/                     # Professional profiles
│   ├── Certificates/                 # Academic credentials
│   ├── Job Board.base                # Bases view
│   └── Interviews/                   # Interview notes
│
├── 05 - System/                      # Technical documentation
│   ├── MOC - System.md               # Navigation hub
│   ├── Architecture/                 # System design docs
│   ├── Operations/                   # Operational handbooks
│   ├── Plans/                        # Implementation plans
│   ├── Specs/                        # Design specifications
│   ├── Reports/                      # Build/extraction reports
│   └── Diagrams/                     # Visual architecture
│
├── engine/                           # PROJECT CODE (not vault)
├── db/                               # DATABASES (not vault)
├── intake/                           # PIPELINE (not vault)
├── scripts/                          # SCRIPTS (not vault)
├── tools/                            # TOOLS (not vault)
├── web/                              # WEB APP (not vault)
├── exports/                          # DATA EXPORTS (not vault)
└── .obsidian/                        # VAULT CONFIG
```

## Migration Plan

### Phase 1: Fix Broken Config (immediate)

**Files to modify:**
- `.obsidian/daily-notes.json` — Update folder to `01 - Daily`
- `.obsidian/templates.json` — Update folder to `_System/_Templates`
- `.obsidian/community-plugins.json` — Add `dataview`, `calendar`

**Actions:**
1. Create `_System/_Templates/` directory
2. Create template files with proper frontmatter
3. Update `.obsidian/daily-notes.json`:
   ```json
   {
     "folder": "01 - Daily",
     "format": "YYYY-MM-DD",
     "template": "_System/_Templates/_Daily"
   }
   ```
4. Update `.obsidian/templates.json`:
   ```json
   {
     "folder": "_System/_Templates",
     "dateFormat": "YYYY-MM-DD"
   }
   ```

### Phase 2: Create Navigation (MOCs)

**New files to create:**
- `00 - Dashboard/Home.md` — Main entry point
- `02 - Self/MOC - Self.md` — Self area navigation
- `03 - Knowledge/MOC - Knowledge.md` — Knowledge navigation
- `04 - Career/MOC - Career.md` — Career navigation
- `05 - System/MOC - System.md` — System navigation

**MOC template:**
```yaml
---
tags:
  - moc
created: 2026-06-12
---

# {{title}}

## Overview
<!-- One-paragraph description -->

## Sections

### Section Name
- [[note-1]]
- [[note-2]]

## Related MOCs
- [[Home]]
```

### Phase 3: Move Vault Content

**Move operations (git mv):**

| Source | Destination |
|--------|-------------|
| `self/inbox/*` | `01 - Daily/` |
| `self/goals/*` | `02 - Self/Goals/` |
| `self/habits/*` | `02 - Self/Habits/` |
| `self/needs/*` | `02 - Self/Needs/` |
| `self/relationships/*` | `02 - Self/Relationships/` |
| `self/documents/*` | `02 - Self/Documents/` |
| `self/interviews/*` | `04 - Career/Interviews/` |
| `self/finances/*.md` | `04 - Career/` (split by type) |
| `self/finances/*.pdf` | `04 - Career/` (keep alongside) |
| `self/finances/Job Board.base` | `04 - Career/` |
| `knowledge/articles/*` | `03 - Knowledge/Articles/` |
| `knowledge/notes/*` | `03 - Knowledge/Notes/` |
| `knowledge/INDEX.md` | `03 - Knowledge/MOC - Knowledge.md` |
| `docs/*.md` | `05 - System/Architecture/` |
| `docs/plans/*` | `05 - System/Plans/` |
| `docs/specs/*` | `05 - System/Specs/` |
| `docs/reports/*` | `05 - System/Reports/` |
| `docs/diagrams/*` | `05 - System/Diagrams/` |
| `INDEX.md` | `00 - Dashboard/Home.md` |
| `session-log.md` | `00 - Dashboard/Session Log.md` |
| `state.md` | `00 - Dashboard/State.md` |

**Files to create:**
- `02 - Self/Profile/Paulo Rezende.md` — From `profile.json`
- `02 - Self/Profile/Personality.md` — From `inferred_personality.json`

### Phase 4: Fix Wikilinks

**Find and replace across all `.md` files:**

| Old Pattern | New Pattern |
|-------------|-------------|
| `personal-ai-space/self/` | `02 - Self/` |
| `personal-ai-space/knowledge/` | `03 - Knowledge/` |
| `personal-ai-space/command/inbox/` | `01 - Daily/` |
| `self/inbox/` | `01 - Daily/` |
| `self/goals/` | `02 - Self/Goals/` |
| `self/habits/` | `02 - Self/Habits/` |
| `self/relationships/` | `02 - Self/Relationships/` |
| `knowledge/articles/` | `03 - Knowledge/Articles/` |
| `knowledge/notes/` | `03 - Knowledge/Notes/` |
| `PERSONAL/People/` | `02 - Self/Relationships/` |

**Approach:** Use `ast_grep_replace` or sed for bulk replacements, then manual review of edge cases.

### Phase 5: Clean Up

**Delete empty directories:**
- `self/inbox/` (after move)
- `self/goals/` (after move)
- `self/habits/` (after move)
- `self/needs/` (after move)
- `self/relationships/` (after move)
- `self/documents/` (after move)
- `self/interviews/` (after move)
- `self/finances/` (after move)
- `knowledge/articles/` (after move)
- `knowledge/notes/` (after move)
- `docs/` (after move)

**Delete duplicate files:**
- `knowledge/notes/20260511_134831_Processo Seletivo - Talentos.md` (duplicate of `Processo Seletivo - Talentos.md`)

**Delete stale files:**
- `self/needs/current_needs.json` (mirrors .md files)
- `self/codemap.md` (technical doc, not vault content)

**Update `.gitignore`:**
- Add `.obsidian/workspace.json`
- Add `.obsidian/cache`
- Add `.DS_Store` (already there)

## Engine Path Updates

**Files requiring path updates:**

| File | Current Path | New Path |
|------|-------------|----------|
| `engine/db_manager.py` | `DB_DIR = Path(__file__).parent.parent / "db"` | No change needed (db/ stays at root) |
| `engine/cli.py` | `db_path = ... / "db" / "self" / "self.db"` | No change needed |
| `web/config.py` | `DB_DIR = BASE_DIR / "db"` | No change needed |
| `scripts/export_all_databases.py` | `DB_DIR = ROOT / "db"` | No change needed |

**Note:** Engine code is NOT being moved. Only vault content is restructured. The `engine/`, `db/`, `intake/`, `scripts/`, `tools/`, `web/`, `exports/` directories stay at root level as project code.

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| Broken wikilinks after move | Bulk find-replace + manual review |
| Engine code paths break | Engine paths not changing (db/ stays at root) |
| Daily notes stop working | Fix .obsidian config BEFORE moving files |
| Template loading fails | Create templates FIRST, then update config |
| Git history loses renames | Use `git mv` for all moves (preserves history) |
| Dataview queries break | Update folder references in Dashboard.md |

## Testing Checklist

- [ ] Open vault in Obsidian — no errors on startup
- [ ] Home note loads with links to all MOCs
- [ ] Create new daily note — saves to `01 - Daily/YYYY-MM-DD.md`
- [ ] Daily note template applies automatically
- [ ] Graph view shows connected knowledge graph
- [ ] Dataview queries in Dashboard render correctly
- [ ] All MOC links resolve (no red links)
- [ ] `python engine/cli.py status` works
- [ ] `scripts/export_all_databases.py` works
- [ ] `git status` shows clean renames (not delete+create)
