# Folder Structure — Before & After

```mermaid
graph LR
  subgraph After["After — Flattened"]
    direction TB
    A1("personal-ai-space/") --- A2(".git")
    A1 --- A3(".gitignore")
    A1 --- A4(".obsidian")
    A1 --- A5("command/")
    A1 --- A6("db/")
    A1 --- A7("docs/")
    A1 --- A8("engine/")
    A1 --- A9("exports/")
    A1 --- A10("INDEX.md")
    A1 --- A11("intake/")
    A1 --- A12("knowledge/")
    A1 --- A13("MCP Server Guides/")
    A1 --- A14("self/")
  end

  subgraph Before["Before — Double-Nested"]
    direction TB
    B1("personal-ai-space/") --- B2(".git")
    B1 --- B3(".obsidian")
    B1 --- B4("MCP Server Guides/")
    B1 --- B5("personal-ai-space/")
    B5 --- B6(".gitignore")
    B5 --- B7("command/")
    B5 --- B8("db/")
    B5 --- B9("docs/")
    B5 --- B10("engine/")
    B5 --- B11("exports/")
    B5 --- B12("INDEX.md")
    B5 --- B13("intake/")
    B5 --- B14("knowledge/")
    B5 --- B15("self/")
  end
```

**Key change:** the inner `personal-ai-space/` directory was eliminated. Its children (`.gitignore`, `command/`, `db/`, `docs/`, `engine/`, `exports/`, `INDEX.md`, `intake/`, `knowledge/`, `self/`) moved up one level to sit directly under the outer `personal-ai-space/` alongside `.git`, `.obsidian`, and `MCP Server Guides/`.
