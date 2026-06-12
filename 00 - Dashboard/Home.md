---
tags:
  - moc
  - home
created: 2026-06-12
---

# Home

Welcome to the Personal AI Powerhouse vault.

## Navigation

### [[02 - Self/MOC - Self|Self]]
Digital twin — goals, habits, relationships, documents

### [[03 - Knowledge/MOC - Knowledge|Knowledge]]
Learning & research — articles, notes, study plans

### [[04 - Career/MOC - Career|Career]]
Professional development — resumes, interviews, certificates

### [[05 - System/MOC - System|System]]
Technical documentation — architecture, operations, specs

## Quick Links

### Daily Notes
- [[01 - Daily/Daily Notes Dashboard|Dashboard]]
- Create new daily note from Obsidian toolbar

### Active Goals
```dataview
TABLE status, progress, target_date
FROM "02 - Self/Goals"
WHERE status = "active"
SORT target_date ASC
```

### Recent Activity
```dataview
TABLE file.mtime as "Modified", file.link as "Note"
FROM ""
WHERE file.mtime > date(today) - dur(7 days)
SORT file.mtime DESC
LIMIT 10
```

## Vault Stats

```dataview
LIST length(rows) as "Count"
FROM ""
GROUP BY file.folder
```
