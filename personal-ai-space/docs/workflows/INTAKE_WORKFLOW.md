# Data Intake Workflow

## Quick Start: Import from Obsidian

### Step 1: Prepare Your Files

Organize files in your Obsidian vault with frontmatter tags:

```markdown
---
tags: [article, research]
category: finance
---

# My Financial Research Article

Content here...
```

### Step 2: Copy to Staging

```bash
# Copy individual files
cp ~/Obsidian/vault/article.md ~/Personal_AI_powerhouse/personal-ai-space/intake/staging/

# Or bulk copy
cp ~/Obsidian/vault/knowledge/*.md ~/Personal_AI_powerhouse/personal-ai-space/intake/staging/
```

### Step 3: Preview & Process

```bash
# Preview (dry run - no changes)
cd ~/Personal_AI_powerhouse/personal-ai-space/intake
python3 process_intake.py --dry-run

# Process for real
python3 process_intake.py
```

### Step 4: Verify

```bash
# Check what was imported
python3 process_intake.py --history

# View the files in their new locations
ls knowledge/articles/
ls knowledge/notes/
```

---

## File Routing Rules

Files are automatically routed based on:

| Rule | Destination | Example |
|------|-------------|---------|
| Tag: `article` or `research` | `knowledge/articles/` | Financial analysis |
| Tag: `project` | `knowledge/projects/` | "Build API" |
| Tag: `reference` | `knowledge/references/` | Links, citations |
| Tag: `task` or `todo` | `command/tasks/` | Action items |
| Filename: `project_*` | `knowledge/projects/` | `project_website.md` |
| Filename: `note_*` or `idea_*` | `knowledge/notes/` | `note_morning_thoughts.md` |
| Filename: `article_*` or `research_*` | `knowledge/articles/` | `article_economics.md` |
| Default | `knowledge/notes/` | Unmarked files |

---

## Optimal Frontmatter Format

Add this to your Obsidian files before importing:

```yaml
---
title: "Article Title"
tags: [article, category-name]
category: finance
author: "Your Name"
created: "2026-05-06"
source: "obsidian"
---
```

Supported tags:
- `article` — Long-form research/writing
- `research` — Detailed investigation
- `reference` — Sources, links, citations
- `project` — Project documentation
- `task` — Action items
- `idea` — Thoughts, brainstorms
- `meeting` — Meeting notes
- `template` — Reusable templates

---

## What Happens After Import

1. **Indexed** — File immediately searchable via `knowledge_indexer` agent
2. **Observed** — Learning system notes the import (`behavior.imported_knowledge`)
3. **Linked** — Links within file are extracted and indexed
4. **Archived** — Original logged in `processed/` for audit trail
5. **Removed** — File removed from staging after successful import

---

## Advanced Usage

### Bulk Import with Custom Routing

```bash
# Import specific category
cp ~/Obsidian/vault/finance/*.md intake/staging/
python3 process_intake.py
```

### View Import History

```bash
# Last 10 imports
python3 process_intake.py --history --limit 10

# Full log
cat intake/intake.log | tail -50
```

### Rollback Import

```bash
# Copy from archive back to staging
cp intake/processed/my_file.md.imported intake/staging/my_file.md

# Re-process to fix routing
python3 process_intake.py
```

---

## Directory Tree (After Import)

```
knowledge/
├── articles/              ← Imported articles + research
├── notes/                 ← Imported notes + ideas
├── references/            ← Links, citations, sources
├── projects/              ← Project documentation
└── INDEX.md               ← Auto-updated index

command/
└── tasks/                 ← Imported action items

intake/
├── staging/               ← Drop files here
├── processed/             ← Archive of imported files
└── intake.log             ← Audit trail
```

---

## Integration with Learning System

After importing 25+ files, the system learns:

```
$ python3 cli.py memory facts --prefix knowledge
🧠 Knowledge Facts:
  • behavior.imported_knowledge = "120 items"
  • behavior.knowledge_categories = ["finance", "productivity", "research"]
  • behavior.knowledge_sources = ["obsidian", "web"]
```

---

**Ready to import?** 

1. Copy files to `intake/staging/`
2. Run `python3 process_intake.py --dry-run`
3. If good, run `python3 process_intake.py`
4. Check `knowledge/` for your imports!
