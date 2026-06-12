---
tags:
  - moc
  - knowledge
created: 2026-06-12
---

# MOC - Knowledge

Learning & research — articles, notes, and study plans.

## Articles
```dataview
TABLE file.link as "Article"
FROM "03 - Knowledge/Articles"
SORT file.name ASC
```

## Notes
```dataview
TABLE type, status, file.mtime as "Modified"
FROM "03 - Knowledge/Notes"
WHERE file.name != "MOC - Knowledge"
SORT file.mtime DESC
```

## MCP Server Guides
- [[03 - Knowledge/MCP Server Guides/whatsapp-mcp|WhatsApp MCP]]
- [[03 - Knowledge/MCP Server Guides/mail-mcp|Mail MCP]]

## Study Plans
```dataview
TABLE file.link as "Plan"
FROM "03 - Knowledge/Study Plans"
SORT file.name ASC
```

## Related MOCs
- [[Home]]
- [[04 - Career/MOC - Career|Career]]
- [[05 - System/MOC - System|System]]
