# Data Intake System

## Purpose

Staging area for importing files from Obsidian vault (or any external source) into the Personal AI Space project. Automatically processes and routes files to the correct destinations.

## Directory Structure

```
intake/
├── staging/           ← Drop files here for processing
├── processed/         ← Completed imports (logged for audit)
├── knowledge/         ← Articles, research, references (→ knowledge/articles/)
├── notes/             ← Notes and thoughts (→ knowledge/notes/)
├── articles/          ← Long-form content (→ knowledge/articles/)
├── projects/          ← Project files (→ knowledge/projects/)
└── reference/         ← Reference materials (→ knowledge/references/)
```

## Workflow

### 1. Drop Files into Staging

```bash
# Copy your Obsidian files into staging/
# The Obsidian vault is the project root (Personal_AI_powerhouse)
cp /path/to/your/file.md /path/to/intake/staging/
```

### 2. Process Files

```bash
# Run the intake processor
python3 process_intake.py
```

### 3. Verify & Archive

```bash
# Check processed imports
ls -la intake/processed/

# Files are logged with:
# - Original path
# - Destination
# - Processing timestamp
# - Extraction metadata (tags, links, etc.)
```

## File Types Supported

| Extension | Destination | Processing |
|-----------|-------------|-----------|
| `.md` | knowledge/ | Parse frontmatter, extract links, index |
| `.txt` | knowledge/notes | Convert to markdown |
| `.pdf` | knowledge/reference | Store as attachment |
| `.jpg/.png` | knowledge/reference | Store with metadata |
| `.csv` | command/ or data/ | Parse + import |

## Automatic Routing

Files are routed based on:
1. **Frontmatter tags** (YAML): `tags: [article, research]` → knowledge/articles
2. **Filename prefix**: `project_*` → knowledge/projects
3. **File type**: `.md` with links → knowledge/notes
4. **Directory hint**: `staging/knowledge/` → knowledge/

## CLI

```bash
# Process all files in staging
python3 process_intake.py

# Show what would be processed (dry run)
python3 process_intake.py --dry-run
```

## Integration with Learning System

Imported files are automatically:
- Indexed by `knowledge_indexer` agent
- Scanned for patterns by observer
- Stored as MCP facts (if extraction succeeds)
- Logged to audit trail

Example auto-learned fact after import:
```
behavior.imported_knowledge = "25 articles, 120 notes"
behavior.knowledge_categories = ["research", "finance", "productivity"]
```

## Storage & Permissions

- Staging: Read/write (yours + system)
- Processed: Read-only archive
- Destinations: Managed by respective systems (knowledge/, command/, etc.)

All imports logged to `intake/intake.log` for audit trail.

---

**Next:** Drop your Obsidian files into `staging/` and run `python3 process_intake.py`
