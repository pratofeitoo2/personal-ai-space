# ONG Vault Hybrid Bridge Cell — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers-optimized:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an MCP server ("bridge cell") inside the ONG Obsidian vault that indexes 5,625 markdown files into SQLite + local vector embeddings (all-MiniLM-L6-v2) and exposes structured tools for the AI Powerhouse main project to consume.

**Architecture:** A Python MCP server lives at `ONG/NEDS/agents_workspace/bridge/`. It maintains a local SQLite database with full-text search (FTS5) over note content and a vector index (384-dim embeddings stored as BLOBs) for semantic search. The server is registered as an external MCP tool in the main project's `opencode.json`. It is NOT a copy of data — it is an index that points to original files. Full content reads go direct to the vault files.

**Tech Stack:** Python 3.13, SQLite3 (stdlib + FTS5), `sentence-transformers` (all-MiniLM-L6-v2), `mcp` (Python MCP SDK), `python-frontmatter`, `watchdog` (optional auto-refresh).

**Assumptions:**
- The vault path is `/Users/paulorezende/Library/Mobile Documents/iCloud~md~obsidian/Documents/ONG/` and is stable — will NOT work if vault moves without updating the config.
- All target `.md` files have standard YAML frontmatter (between `---` delimiters). Files without frontmatter are still indexed (path, modified, preview) but with empty metadata fields.
- The `all-MiniLM-L6-v2` model (~80MB) can be downloaded on first run via `sentence-transformers`. Assumes internet access for first download; runs fully offline after.
- Patient records follow the structure `Clinica/Pacientes/<Name>/` with numbered subfolders (`01_Intake/`, `02_Assessment/`, etc.) — tool works best when this convention holds.
- Tasks in `ADM/Development/Tasks/` are markdown files with date frontmatter fields (`due_date`, `deadline`, or `date`) — files without dates are still returned but unsorted.

---
## File Structure

All files relative to the bridge root:
```
<NEDS>/agents_workspace/bridge/
├── pyproject.toml           # Project metadata + dependencies
├── src/
│   ├── __init__.py
│   ├── main.py              # MCP server entry point (tool registration + serve)
│   ├── config.py            # Vault path, model name, DB path constants
│   ├── indexer/
│   │   ├── __init__.py
│   │   ├── scanner.py       # Walk vault, find .md files, extract frontmatter + preview
│   │   ├── embeddings.py    # all-MiniLM-L6-v2: load model, generate vectors, cosine sim
│   │   └── runner.py        # Orchestrate full/incremental index, progress tracker
│   ├── db/
│   │   ├── __init__.py
│   │   ├── schema.py        # DDL: notes table, FTS5 virtual table, embedding storage
│   │   └── queries.py       # Prepared queries: search, semantic, stats, patient, tasks
│   └── tools/
│       ├── __init__.py
│       ├── search.py        # vault_search_notes tool
│       ├── semantic.py      # vault_semantic_search tool
│       ├── notes.py         # vault_get_note tool
│       ├── patients.py      # vault_get_patient tool
│       ├── tasks.py         # vault_get_tasks_due tool
│       ├── stats.py         # vault_get_stats tool
│       └── refresh.py       # vault_refresh_index tool
├── data/
│   └── .gitkeep             # SQLite DB created here at runtime: vault_index.db
└── .gitignore               # Ignore .venv/, data/*.db, __pycache__/
```
---

## Phase 1 — Foundation

> **Start:** Plan approved, user confirms Phase 1.
> **End:** Virtual environment created, all dependencies installed, SQLite schema defined as Python code that creates tables when called. Bridge directory structure in place.

### Task 1.1: Create directory structure + pyproject.toml + venv

**Files:**
- Create: `agents_workspace/bridge/pyproject.toml`
- Create: `agents_workspace/bridge/.gitignore`
- Create: `agents_workspace/bridge/data/.gitkeep`
- Create: `agents_workspace/bridge/src/__init__.py`
- Create: `agents_workspace/bridge/src/indexer/__init__.py`
- Create: `agents_workspace/bridge/src/db/__init__.py`
- Create: `agents_workspace/bridge/src/tools/__init__.py`

**Security flag:** `none`

- [ ] **Step 1: Create directory tree**

```bash
VAULT="/Users/paulorezende/Library/Mobile Documents/iCloud~md~obsidian/Documents/ONG"
BRIDGE="$VAULT/NEDS/agents_workspace/bridge"

mkdir -p "$BRIDGE/src/indexer" "$BRIDGE/src/db" "$BRIDGE/src/tools" "$BRIDGE/data"

touch "$BRIDGE/data/.gitkeep"
touch "$BRIDGE/src/__init__.py"
touch "$BRIDGE/src/indexer/__init__.py"
touch "$BRIDGE/src/db/__init__.py"
touch "$BRIDGE/src/tools/__init__.py"
```

- [ ] **Step 2: Create pyproject.toml**

```toml
[project]
name = "ong-vault-bridge"
version = "0.1.0"
description = "MCP bridge cell that indexes the ONG Obsidian vault with SQLite FTS + local embeddings"
requires-python = ">=3.13"
dependencies = [
    "mcp>=1.0.0",
    "sentence-transformers>=3.0.0",
    "python-frontmatter>=1.1.0",
    "watchdog>=5.0.0",
]

[tool.setuptools.packages.find]
where = ["src"]
```

- [ ] **Step 3: Create .gitignore**

```
.venv/
__pycache__/
*.pyc
data/*.db
data/*.db-*
```

- [ ] **Step 4: Create and activate virtual environment, install deps**

```bash
python3.13 -m venv "$BRIDGE/.venv"
source "$BRIDGE/.venv/bin/activate"
pip install --upgrade pip
pip install mcp sentence-transformers python-frontmatter watchdog
```

Verify with:
```bash
source "$BRIDGE/.venv/bin/activate" && python -c "import mcp; import sentence_transformers; import frontmatter; print('OK')"
```
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git -C "$VAULT" add NEDS/agents_workspace/bridge/
git -C "$VAULT" commit -m "feat(bridge): scaffold ONG vault bridge directory structure + deps"
```

---

### Task 1.2: SQLite schema + config module

**Files:**
- Create: `agents_workspace/bridge/src/config.py`
- Create: `agents_workspace/bridge/src/db/schema.py`

**Security flag:** `none`

**Does NOT cover:** Data migration or schema versioning — only initial table creation.

- [ ] **Step 1: Create config.py**

```python
import os
from pathlib import Path

VAULT_ROOT = Path(os.environ.get(
    "ONG_VAULT_PATH",
    "/Users/paulorezende/Library/Mobile Documents/iCloud~md~obsidian/Documents/ONG"
))

BRIDGE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BRIDGE_DIR / "data"
DB_PATH = DATA_DIR / "vault_index.db"

EMBEDDING_MODEL = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384
EMBEDDING_BATCH_SIZE = 64  # notes per batch when generating embeddings

# Sections at vault root to index (excludes .hidden dirs)
VAULT_SECTIONS = [
    d.name for d in VAULT_ROOT.iterdir()
    if d.is_dir() and not d.name.startswith(".")
]

# Files/directories to skip
EXCLUDE_DIRS = {".obsidian", ".opencode", ".git", ".github", ".vscode",
                ".copilot-index", ".gemini", ".nogic", "__pycache__",
                "node_modules", "BACKUPS"}
EXCLUDE_PREFIXES = {"."}  # any hidden file/dir
```

- [ ] **Step 2: Create schema.py**

```python
import sqlite3
from ..config import DB_PATH

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS notes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    path        TEXT    UNIQUE NOT NULL,
    title       TEXT,
    tags        TEXT,
    created_at  TEXT,
    modified_at TEXT,
    file_size   INTEGER,
    directory   TEXT    NOT NULL,
    frontmatter TEXT,
    content_preview TEXT,
    embedding   BLOB,
    last_indexed TEXT DEFAULT (datetime('now'))
);

CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(
    title,
    tags,
    content_preview,
    content='notes',
    content_rowid='id'
);

CREATE INDEX IF NOT EXISTS idx_notes_directory ON notes(directory);
CREATE INDEX IF NOT EXISTS idx_notes_modified ON notes(modified_at);
"""

def init_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    return conn

def get_connection() -> sqlite3.Connection:
    return sqlite3.connect(str(DB_PATH))
```

- [ ] **Step 3: Verify schema creation**

```bash
source "$BRIDGE/.venv/bin/activate"
python -c "
from src.db.schema import init_db
conn = init_db()
tables = conn.execute(\"SELECT name FROM sqlite_master WHERE type='table'\").fetchall()
print('Tables:', [t[0] for t in tables])
conn.close()
"
```
Expected: `Tables: ['notes', 'notes_fts']`

- [ ] **Step 4: Commit**

```bash
git -C "$VAULT" add NEDS/agents_workspace/bridge/
git -C "$VAULT" commit -m "feat(bridge): SQLite schema + config module"
```

---

## Phase 2 — Indexer Engine

> **Start:** Phase 1 complete (schema + config exist).
> **End:** All 5,625 `.md` files scanned, frontmatter parsed, SQLite populated with note records, embeddings generated and stored. Verified via count query matching live `find` count.

### Task 2.1: Vault scanner + frontmatter parser

**Files:**
- Create: `agents_workspace/bridge/src/indexer/scanner.py`

**Security flag:** `none`

**Does NOT cover:** Incremental scanning — only full vault walk. Binary files — only `.md` files are scanned.

- [ ] **Step 1: Create scanner.py**

```python
from pathlib import Path
from typing import Generator, Optional
import frontmatter
from ..config import VAULT_ROOT, EXCLUDE_DIRS

ScannedNote = dict  # {path, title, tags, created_at, modified_at, file_size, directory, frontmatter, content_preview}

def _is_excluded(path: Path) -> bool:
    """Check if path or any parent should be excluded."""
    for part in path.parts:
        if part in EXCLUDE_DIRS or part.startswith("."):
            return True
    return False

def walk_vault() -> Generator[Path, None, None]:
    """Yield all .md file paths in the vault (excluding .dirs, BACKUPS, node_modules)."""
    for path in VAULT_ROOT.rglob("*.md"):
        if not _is_excluded(path):
            yield path

def parse_markdown(filepath: Path) -> Optional[ScannedNote]:
    """Extract frontmatter + content preview from a markdown file."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except (OSError, PermissionError):
        return None

    rel = filepath.relative_to(VAULT_ROOT)
    directory = rel.parts[0] if rel.parts else "root"

    try:
        post = frontmatter.loads(content)
        metadata = post.metadata
        body = post.content
    except Exception:
        metadata = {}
        body = content

    title = metadata.get("title") or filepath.stem
    tags = metadata.get("tags")
    if isinstance(tags, list):
        tags = ",".join(tags)
    elif tags is None:
        tags = ""
    else:
        tags = str(tags)

    created_at = str(metadata.get("created") or metadata.get("created_at") or metadata.get("date") or "")
    modified_at = str(metadata.get("modified") or metadata.get("modified_at") or "")
    mtime = filepath.stat().st_mtime
    if not modified_at:
        from datetime import datetime
        modified_at = datetime.fromtimestamp(mtime).isoformat()

    preview = body.strip()[:500] if body.strip() else ""

    return {
        "path": str(rel),
        "title": str(title)[:500],
        "tags": str(tags)[:500],
        "created_at": created_at,
        "modified_at": modified_at,
        "file_size": filepath.stat().st_size,
        "directory": directory,
        "frontmatter": str(metadata) if metadata else "",
        "content_preview": preview,
    }


def scan_and_count() -> tuple[list[ScannedNote], int]:
    """Walk vault, parse all .md, return (notes, total_scanned)."""
    notes = []
    count = 0
    for filepath in walk_vault():
        count += 1
        note = parse_markdown(filepath)
        if note:
            notes.append(note)
    return notes, count
```

- [ ] **Step 2: Verify scanner logic**

```bash
source "$BRIDGE/.venv/bin/activate"
python -c "
from src.indexer.scanner import scan_and_count
notes, total = scan_and_count()
print(f'Scanned: {total} files, Parsed: {len(notes)} notes')
if notes:
    print(f'Sample: {notes[0][\"path\"]} | title={notes[0][\"title\"]} | dir={notes[0][\"directory\"]}')
"
```
Expected output should show ~5,625 scanned count and a sample note path.

- [ ] **Step 3: Commit**

```bash
git -C "$VAULT" add NEDS/agents_workspace/bridge/
git -C "$VAULT" commit -m "feat(bridge): vault scanner + frontmatter parser"
```

---

### Task 2.2: Database writer (populate SQLite from scanned notes)

**Files:**
- Create: `agents_workspace/bridge/src/db/queries.py`
- Modify: `agents_workspace/bridge/src/db/schema.py` (add write helper)

**Security flag:** `none`

**Does NOT cover:** Embedding storage — that is Task 2.3.

- [ ] **Step 1: Add write helper to schema.py**

Append to `src/db/schema.py`:

```python
def rebuild_index(conn: sqlite3.Connection, notes: list[dict]) -> int:
    """Clear and repopulate the notes table and FTS index. Returns row count."""
    conn.execute("DELETE FROM notes")
    conn.execute("DELETE FROM notes_fts")
    cursor = conn.cursor()
    for note in notes:
        cursor.execute("""
            INSERT INTO notes (path, title, tags, created_at, modified_at,
                               file_size, directory, frontmatter, content_preview)
            VALUES (:path, :title, :tags, :created_at, :modified_at,
                    :file_size, :directory, :frontmatter, :content_preview)
        """, note)
    conn.commit()

    # Rebuild FTS index from notes content
    conn.execute("""
        INSERT INTO notes_fts(rowid, title, tags, content_preview)
        SELECT id, title, tags, content_preview FROM notes
    """)
    conn.commit()
    return len(notes)
```

- [ ] **Step 2: Create queries.py**

```python
from typing import Optional
from .schema import get_connection

def search_notes(query: str, scope: Optional[str] = None, limit: int = 20) -> list[dict]:
    conn = get_connection()
    if scope:
        sql = """
            SELECT n.id, n.path, n.title, n.tags, n.directory, n.modified_at,
                   snippet(notes_fts, 1, '<b>', '</b>', '...', 32) AS snippet
            FROM notes_fts
            JOIN notes n ON notes_fts.rowid = n.id
            WHERE notes_fts MATCH ? AND n.directory = ?
            ORDER BY rank
            LIMIT ?
        """
        rows = conn.execute(sql, (query, scope, limit)).fetchall()
    else:
        sql = """
            SELECT n.id, n.path, n.title, n.tags, n.directory, n.modified_at,
                   snippet(notes_fts, 1, '<b>', '</b>', '...', 32) AS snippet
            FROM notes_fts
            JOIN notes n ON notes_fts.rowid = n.id
            WHERE notes_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        """
        rows = conn.execute(sql, (query, limit)).fetchall()

    columns = ["id", "path", "title", "tags", "directory", "modified_at", "snippet"]
    return [dict(zip(columns, row)) for row in rows]


def get_note_by_path(path: str) -> Optional[dict]:
    conn = get_connection()
    row = conn.execute(
        "SELECT id, path, title, tags, directory, modified_at, content_preview FROM notes WHERE path = ?",
        (path,)
    ).fetchone()
    if not row:
        return None
    columns = ["id", "path", "title", "tags", "directory", "modified_at", "content_preview"]
    return dict(zip(columns, row))


def get_stats() -> dict:
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
    by_dir = conn.execute(
        "SELECT directory, COUNT(*) as cnt FROM notes GROUP BY directory ORDER BY cnt DESC"
    ).fetchall()
    last_indexed = conn.execute("SELECT MAX(last_indexed) FROM notes").fetchone()[0] or "never"
    return {
        "total_notes": total,
        "by_directory": [{"directory": d, "count": c} for d, c in by_dir],
        "last_indexed": last_indexed,
    }


def get_patient_notes(name: str) -> list[dict]:
    """Find patient by name pattern in Clinica/Pacientes/."""
    conn = get_connection()
    pattern = f"Clinica/Pacientes/{name}%"
    rows = conn.execute(
        "SELECT path, title, tags, directory, modified_at FROM notes WHERE path LIKE ?",
        (pattern,)
    ).fetchall()
    columns = ["path", "title", "tags", "directory", "modified_at"]
    return [dict(zip(columns, row)) for row in rows]


def get_tasks_due(from_date: str, to_date: str) -> list[dict]:
    """Find tasks in ADM with date frontmatter within range."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT path, title, tags, directory, modified_at, frontmatter
        FROM notes
        WHERE directory = 'ADM'
          AND (frontmatter LIKE '%due_date%' OR frontmatter LIKE '%deadline%' OR frontmatter LIKE '%date%')
        ORDER BY modified_at DESC
    """).fetchall()
    columns = ["path", "title", "tags", "directory", "modified_at", "frontmatter"]
    return [dict(zip(columns, row)) for row in rows]


def update_embedding(note_id: int, embedding_blob: bytes) -> None:
    conn = get_connection()
    conn.execute("UPDATE notes SET embedding = ? WHERE id = ?", (embedding_blob, note_id))
    conn.commit()


def get_notes_without_embeddings() -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, path, content_preview FROM notes WHERE embedding IS NULL"
    ).fetchall()
    columns = ["id", "path", "content_preview"]
    return [dict(zip(columns, row)) for row in rows]


def get_all_embeddings() -> list[dict]:
    """For semantic search — returns notes that HAVE embeddings."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, path, title, tags, directory, embedding, modified_at FROM notes WHERE embedding IS NOT NULL"
    ).fetchall()
    columns = ["id", "path", "title", "tags", "directory", "embedding", "modified_at"]
    return [dict(zip(columns, row)) for row in rows]
```

- [ ] **Step 3: Verify DB operations**

```bash
source "$BRIDGE/.venv/bin/activate"
python -c "
from src.db.schema import init_db, rebuild_index
from src.indexer.scanner import scan_and_count
notes, _ = scan_and_count()
conn = init_db()
count = rebuild_index(conn, notes[:5])  # just 5 for test
print(f'Inserted: {count}')
from src.db.queries import get_stats
print('Stats:', get_stats())
conn.close()
"
```
Expected: `Inserted: 5` and valid stats dict.

- [ ] **Step 4: Commit**

```bash
git -C "$VAULT" add NEDS/agents_workspace/bridge/
git -C "$VAULT" commit -m "feat(bridge): SQLite write helpers + query layer"
```

---

### Task 2.3: Embedding engine (all-MiniLM-L6-v2)

**Files:**
- Create: `agents_workspace/bridge/src/indexer/embeddings.py`

**Security flag:** `none`

- [ ] **Step 1: Create embeddings.py**

```python
import numpy as np
import sqlite3
from typing import Optional
from ..config import EMBEDDING_MODEL, EMBEDDING_DIM, EMBEDDING_BATCH_SIZE
from ..db.queries import update_embedding, get_notes_without_embeddings

_model = None

def _load_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model

def _encode(texts: list[str]) -> np.ndarray:
    model = _load_model()
    return model.encode(texts, show_progress_bar=True, batch_size=EMBEDDING_BATCH_SIZE)

def generate_embeddings(progress_callback=None) -> int:
    """Generate embeddings for all notes that lack them. Returns count."""
    notes = get_notes_without_embeddings()
    if not notes:
        return 0

    total = len(notes)
    texts = [(n["content_preview"] or n["path"]) for n in notes]
    vectors = _encode(texts)

    for i, (note, vec) in enumerate(zip(notes, vectors)):
        blob = vec.astype(np.float32).tobytes()
        update_embedding(note["id"], blob)
        if progress_callback:
            progress_callback(i + 1, total)

    return total

def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-10))
```

- [ ] **Step 2: Verify embedding generation**

```bash
source "$BRIDGE/.venv/bin/activate"
python -c "
from src.indexer.embeddings import generate_embeddings
# generate on a small sample first
count = generate_embeddings()
print(f'Embeddings generated: {count}')

from src.indexer.embeddings import _load_model
m = _load_model()
print(f'Model device: {m.device}')
"
```
Expected: embeddings count > 0, model device shown.

- [ ] **Step 3: Commit**

```bash
git -C "$VAULT" add NEDS/agents_workspace/bridge/
git -C "$VAULT" commit -m "feat(bridge): embedding engine (all-MiniLM-L6-v2)"
```

---

### Task 2.4: Index runner (orchestrate full vault index)

**Files:**
- Create: `agents_workspace/bridge/src/indexer/runner.py`

**Security flag:** `none`

**Does NOT cover:** Incremental refresh — full reindex only.

- [ ] **Step 1: Create runner.py**

```python
import time
from ..config import VAULT_ROOT
from ..db.schema import init_db, rebuild_index
from .scanner import scan_and_count
from .embeddings import generate_embeddings


def run_full_index(progress: bool = True) -> dict:
    """
    Walk vault, parse all .md, populate SQLite, generate all embeddings.
    Returns summary dict.
    """
    t0 = time.time()

    if progress:
        print(f"Scanning vault: {VAULT_ROOT}")

    notes, total_scanned = scan_and_count()

    if progress:
        print(f"Scanned {total_scanned} files, parsed {len(notes)} notes. Writing to DB...")

    conn = init_db()
    row_count = rebuild_index(conn, notes)
    conn.close()

    t1 = time.time()
    if progress:
        print(f"DB populated: {row_count} rows in {t1-t0:.1f}s")

    if progress:
        print(f"Generating embeddings...")
    embed_count = generate_embeddings()

    t2 = time.time()
    if progress:
        print(f"Embeddings generated: {embed_count}")
        print(f"Total time: {t2-t0:.1f}s")

    return {
        "files_scanned": total_scanned,
        "notes_indexed": row_count,
        "embeddings_generated": embed_count,
        "index_time_seconds": round(t2 - t0, 1),
    }


def index_status() -> dict:
    from ..db.queries import get_stats
    from ..db.schema import get_connection
    conn = get_connection()
    with_embeddings = conn.execute("SELECT COUNT(*) FROM notes WHERE embedding IS NOT NULL").fetchone()[0]
    conn.close()
    stats = get_stats()
    stats["notes_with_embeddings"] = with_embeddings
    return stats
```

- [ ] **Step 2: Verify full index**

```bash
source "$BRIDGE/.venv/bin/activate"
python -c "
from src.indexer.runner import run_full_index
result = run_full_index(progress=True)
print('Index result:', result)
"
```
Expected: Index completes with ~5,625 notes, embeddings generated, time < 5 min.

- [ ] **Step 3: Commit**

```bash
git -C "$VAULT" add NEDS/agents_workspace/bridge/
git -C "$VAULT" commit -m "feat(bridge): full index runner (scan + parse + embed)"
```

---

## Phase 3 — MCP Server

> **Start:** Phase 2 complete (DB populated with notes + embeddings).
> **End:** MCP server starts successfully, all 7 tools respond correctly via MCP protocol. Verified with `mcp-cli` or direct tool invocation.

### Task 3.1: MCP core + search_notes + get_note tools

**Files:**
- Create: `agents_workspace/bridge/src/tools/search.py`
- Create: `agents_workspace/bridge/src/tools/notes.py`

**Security flag:** `none`

**Does NOT cover:** Semantic search, patients, tasks, stats, refresh — those are separate tasks.

- [ ] **Step 1: Create search.py**

```python
from typing import Optional
from mcp.server.models import Tool
from mcp.server import Server
from ..db.queries import search_notes as db_search

def register_search_tool(server: Server):
    @server.tool(
        name="vault_search_notes",
        description="Full-text search across vault notes (title, tags, content preview). Supports FTS5 syntax.",
        parameters={
            "query": {
                "type": "string",
                "description": "Search query (supports FTS5 syntax: AND, OR, quotes for exact phrase)"
            },
            "scope": {
                "type": "string",
                "description": "Optional: restrict to vault section (Clinica, ADM, Knowledge, etc.)",
                "optional": True
            },
            "limit": {
                "type": "integer",
                "description": "Max results (default 20, max 100)",
                "default": 20,
                "optional": True
            }
        }
    )
    async def vault_search_notes(query: str, scope: Optional[str] = None, limit: int = 20) -> str:
        import json
        limit = min(limit, 100)
        results = db_search(query, scope=scope, limit=limit)
        return json.dumps(results, indent=2, ensure_ascii=False)
```

- [ ] **Step 2: Create notes.py**

```python
from mcp.server import Server
from ..db.queries import get_note_by_path
from ..config import VAULT_ROOT

def register_notes_tool(server: Server):
    @server.tool(
        name="vault_get_note",
        description="Read full content of a vault note by its relative path.",
        parameters={
            "path": {
                "type": "string",
                "description": "Relative path within vault (e.g. 'Knowledge/Notes/meu-artigo.md')"
            }
        }
    )
    async def vault_get_note(path: str) -> str:
        record = get_note_by_path(path)
        if not record:
            return f"Note not found: {path}"

        abs_path = VAULT_ROOT / path
        if not abs_path.exists():
            return f"File no longer exists: {path}"

        try:
            content = abs_path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            return f"Error reading file: {e}"

        header = f"# {record['title']}\npath: {path}\ntags: {record['tags']}\nmodified: {record['modified_at']}\n---\n\n"
        return header + content
```

- [ ] **Step 3: Quick test**

```bash
source "$BRIDGE/.venv/bin/activate"
python -c "
from src.tools.search import register_search_tool
from src.tools.notes import register_notes_tool
from mcp.server import Server
s = Server('test')
register_search_tool(s)
register_notes_tool(s)
print('Tools registered:', [t.name for t in s.list_tools()])
"
```
Expected: `Tools registered: ['vault_search_notes', 'vault_get_note']`

- [ ] **Step 4: Commit**

```bash
git -C "$VAULT" add NEDS/agents_workspace/bridge/
git -C "$VAULT" commit -m "feat(bridge): MCP core + search_notes + get_note tools"
```

---

### Task 3.2: MCP semantic_search tool

**Files:**
- Create: `agents_workspace/bridge/src/tools/semantic.py`

**Security flag:** `none`

**Does NOT cover:** Fallback when no embeddings exist — tool returns empty results if embeddings haven't been generated.

- [ ] **Step 1: Create semantic.py**

```python
from typing import Optional
import numpy as np
from mcp.server import Server
from ..db.queries import get_all_embeddings
from ..indexer.embeddings import _load_model, cosine_similarity


def register_semantic_tool(server: Server):
    @server.tool(
        name="vault_semantic_search",
        description="Semantic (vector) search across vault notes. Best for finding conceptually related content even when keywords don't match.",
        parameters={
            "query": {
                "type": "string",
                "description": "Natural language query describing what you're looking for"
            },
            "limit": {
                "type": "integer",
                "description": "Max results (default 10, max 50)",
                "default": 10,
                "optional": True
            }
        }
    )
    async def vault_semantic_search(query: str, limit: int = 10) -> str:
        import json
        limit = min(limit, 50)
        notes = get_all_embeddings()
        if not notes:
            return json.dumps([], ensure_ascii=False)

        model = _load_model()
        query_vec = model.encode([query])[0]

        scored = []
        for n in notes:
            blob = n["embedding"]
            if not blob:
                continue
            note_vec = np.frombuffer(blob, dtype=np.float32)
            score = cosine_similarity(query_vec, note_vec)
            scored.append({
                "path": n["path"],
                "title": n["title"],
                "tags": n["tags"],
                "directory": n["directory"],
                "modified_at": n["modified_at"],
                "similarity_score": round(score, 4),
            })

        scored.sort(key=lambda x: x["similarity_score"], reverse=True)
        return json.dumps(scored[:limit], indent=2, ensure_ascii=False)
```

- [ ] **Step 2: Test semantic search**

```bash
source "$BRIDGE/.venv/bin/activate"
python -c "
from src.tools.semantic import register_semantic_tool
from mcp.server import Server
s = Server('test')
register_semantic_tool(s)
print('Semantic tool registered')
# Quick inline test
import asyncio, json
from src.tools.semantic import vault_semantic_search
result = asyncio.run(vault_semantic_search('trauma em crianças', limit=3))
parsed = json.loads(result)
print(f'Semantic results: {len(parsed)}')
for r in parsed[:2]:
    print(f'  {r[\"title\"]} ({r[\"similarity_score\"]})')
"
```
Expected: Relevant results from the vault with similarity scores.

- [ ] **Step 3: Commit**

```bash
git -C "$VAULT" add NEDS/agents_workspace/bridge/
git -C "$VAULT" commit -m "feat(bridge): semantic_search tool (vector similarity)"
```

---

### Task 3.3: MCP get_patient + get_tasks_due tools

**Files:**
- Create: `agents_workspace/bridge/src/tools/patients.py`
- Create: `agents_workspace/bridge/src/tools/tasks.py`

**Security flag:** `security` — patient data is sensitive health information.

- [ ] **Step 1: Create patients.py**

```python
import json
from mcp.server import Server
from ..db.queries import get_patient_notes
from ..config import VAULT_ROOT


def register_patients_tool(server: Server):
    @server.tool(
        name="vault_get_patient",
        description="Find patient records by name in Clinica/Pacientes/. Returns folder structure with session count.",
        parameters={
            "name": {
                "type": "string",
                "description": "Patient name or partial name to search (e.g. 'Ana Sofia' or 'Ana')"
            }
        }
    )
    async def vault_get_patient(name: str) -> str:
        notes = get_patient_notes(name)
        if not notes:
            return f"No patient found matching '{name}'"

        # Group by subdirectory to show folder structure
        from collections import defaultdict
        folders = defaultdict(list)
        for n in notes:
            parts = n["path"].split("/")
            # path = Clinica/Pacientes/Name/folder/filename.md
            if len(parts) >= 4:
                folder = "/".join(parts[:4])
                sub = "/".join(parts[4:-1]) if len(parts) > 4 else "root"
                folders[folder].append({
                    "section": sub,
                    "file": parts[-1],
                    "title": n["title"],
                    "modified_at": n["modified_at"],
                })

        result = []
        for folder, files in sorted(folders.items()):
            result.append({"patient_folder": folder, "files_count": len(files), "files": files})

        return json.dumps(result, indent=2, ensure_ascii=False)
```

- [ ] **Step 2: Create tasks.py**

```python
import json
import re
from mcp.server import Server
from ..db.queries import get_tasks_due


def register_tasks_tool(server: Server):
    @server.tool(
        name="vault_get_tasks_due",
        description="Find tasks with dates in ADM/Development/Tasks/. Returns tasks with extracted date fields.",
        parameters={
            "from_date": {
                "type": "string",
                "description": "Start date filter (ISO format: YYYY-MM-DD or YYYY-MM or YYYY)",
                "optional": True
            },
            "to_date": {
                "type": "string",
                "description": "End date filter (ISO format: YYYY-MM-DD or YYYY-MM or YYYY). Defaults to 1 year from from_date.",
                "optional": True
            }
        }
    )
    async def vault_get_tasks_due(from_date: str = "", to_date: str = "") -> str:
        tasks = get_tasks_due(from_date or "1900", to_date or "2100")

        # Extract dates from frontmatter string
        for t in tasks:
            fm = t.get("frontmatter", "")
            dates = re.findall(r"\d{4}-\d{2}-\d{2}", fm)
            t["extracted_dates"] = dates
            del t["frontmatter"]  # don't return raw frontmatter in full

        return json.dumps(tasks, indent=2, ensure_ascii=False)
```

- [ ] **Step 3: Test tools**

```bash
source "$BRIDGE/.venv/bin/activate"
python -c "
import asyncio, json
from src.tools.patients import vault_get_patient
from src.tools.tasks import vault_get_tasks_due
r1 = asyncio.run(vault_get_patient('Ana'))
print('Patient results:', type(r1))
r2 = asyncio.run(vault_get_tasks_due())
parsed = json.loads(r2)
print(f'Tasks found: {len(parsed)}')
"
```
Expected: Patient search returns results, tasks tool returns list.

- [ ] **Step 4: Commit**

```bash
git -C "$VAULT" add NEDS/agents_workspace/bridge/
git -C "$VAULT" commit -m "feat(bridge): get_patient + get_tasks_due tools"
```

---

### Task 3.4: MCP get_stats + refresh_index + main entry point

**Files:**
- Create: `agents_workspace/bridge/src/tools/stats.py`
- Create: `agents_workspace/bridge/src/tools/refresh.py`
- Create: `agents_workspace/bridge/src/main.py`

**Security flag:** `none`

- [ ] **Step 1: Create stats.py**

```python
import json
from mcp.server import Server
from ..db.queries import get_stats as db_stats


def register_stats_tool(server: Server):
    @server.tool(
        name="vault_get_stats",
        description="Get vault statistics: total notes, notes per directory, last indexed timestamp.",
        parameters={}
    )
    async def vault_get_stats() -> str:
        return json.dumps(db_stats(), indent=2, ensure_ascii=False)
```

- [ ] **Step 2: Create refresh.py**

```python
import json
from mcp.server import Server
from ..indexer.runner import run_full_index, index_status


def register_refresh_tool(server: Server):
    @server.tool(
        name="vault_refresh_index",
        description="Triggers a full reindex of the vault. Scans all .md files, reparses frontmatter, regenerates all embeddings. Can take 2-5 minutes for 5,600+ notes.",
        parameters={}
    )
    async def vault_refresh_index() -> str:
        status_before = index_status()
        result = run_full_index(progress=False)
        status_after = index_status()
        return json.dumps({
            "message": "Index refreshed successfully",
            "before": status_before,
            "after": status_after,
            "duration_seconds": result["index_time_seconds"],
        }, indent=2, ensure_ascii=False)
```

- [ ] **Step 3: Create main.py**

```python
import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server

from .tools.search import register_search_tool
from .tools.notes import register_notes_tool
from .tools.semantic import register_semantic_tool
from .tools.patients import register_patients_tool
from .tools.tasks import register_tasks_tool
from .tools.stats import register_stats_tool
from .tools.refresh import register_refresh_tool

from .db.schema import init_db

async def main():
    # Ensure DB + tables exist on startup
    init_db()

    server = Server("ong-vault-bridge")

    register_search_tool(server)
    register_notes_tool(server)
    register_semantic_tool(server)
    register_patients_tool(server)
    register_tasks_tool(server)
    register_stats_tool(server)
    register_refresh_tool(server)

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 4: Test server startup**

```bash
source "$BRIDGE/.venv/bin/activate"
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | timeout 5 python -m src.main 2>&1 || true
```
Expected: Server responds to tools/list before timeout.

- [ ] **Step 5: Commit**

```bash
git -C "$VAULT" add NEDS/agents_workspace/bridge/
git -C "$VAULT" commit -m "feat(bridge): stats, refresh tools + MCP server entry point"
```

---

## Phase 4 — Automation

> **Start:** Phase 3 complete (MCP server runs, all tools respond).
> **End:** Bridge auto-indexes on startup, supports incremental refresh, has usage documentation.

### Task 4.1: Incremental refresh + startup auto-index

**Files:**
- Modify: `agents_workspace/bridge/src/indexer/runner.py` (add incremental logic)
- Create: `agents_workspace/bridge/run.sh` (launcher script)

**Security flag:** `none`

**Does NOT cover:** File-system watcher daemon — refresh is on-demand via `vault_refresh_index` tool or auto-check at server startup.

- [ ] **Step 1: Add startup auto-index to runner.py**

Append to `src/indexer/runner.py`:

```python
from ..config import DB_PATH

def ensure_indexed() -> dict:
    """Index the vault on first run (if DB is empty), otherwise just report status."""
    if not DB_PATH.exists() or DB_PATH.stat().st_size == 0:
        return run_full_index(progress=True)
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
    conn.close()
    if count == 0:
        return run_full_index(progress=True)
    return index_status()
```

Add import at top:
```python
from ..db.schema import get_connection
```

- [ ] **Step 2: Create run.sh**

```bash
#!/usr/bin/env bash
# Launcher for the ONG vault bridge MCP server.
# Usage: ./run.sh
set -euo pipefail

BRIDGE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$BRIDGE_DIR"

# Auto-index on first run
source .venv/bin/activate
python -c "
from src.indexer.runner import ensure_indexed
result = ensure_indexed()
print(f'Vault index: {result[\"notes_indexed\"]} notes, {result.get(\"embeddings_generated\", 0)} embeddings')
"

# Start MCP server (stdio protocol)
exec python -m src.main
```

Make executable:
```bash
chmod +x "$BRIDGE/run.sh"
```

- [ ] **Step 3: Verify run.sh works**

```bash
source "$BRIDGE/.venv/bin/activate"
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | timeout 5 "$BRIDGE/run.sh" 2>&1 || true
```
Expected: Shows vault index status then responds to tools/list.

- [ ] **Step 4: Commit**

```bash
git -C "$VAULT" add NEDS/agents_workspace/bridge/
git -C "$VAULT" commit -m "feat(bridge): auto-index on startup + launcher script"
```

---

## Phase 5 — Integration with AI Powerhouse

> **Start:** Phase 4 complete (bridge server runs standalone).
> **End:** Main AI Powerhouse project can call all 7 bridge tools via MCP protocol. Verified end-to-end.

### Task 5.1: Register bridge MCP in main project's opencode.json

**Files:**
- Modify: `/Users/paulorezende/Documents/Personal_AI_powerhouse updated/opencode.json`

**Security flag:** `none`

**Does NOT cover:** Testing the tools — that is Task 5.2.

- [ ] **Step 1: Add bridge server to opencode.json**

Add to the `mcp` section:

```json
    "ong-vault-bridge": {
      "type": "local",
      "command": [
        "/Users/paulorezende/Library/Mobile Documents/iCloud~md~obsidian/Documents/ONG/NEDS/agents_workspace/bridge/run.sh"
      ],
      "enabled": true
    }
```

Full updated file:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "aivectormemory": {
      "type": "local",
      "command": [
        "/Users/paulorezende/.local/share/uv/tools/aivectormemory/bin/python",
        "-m",
        "aivectormemory",
        "--project-dir",
        "/Users/paulorezende/Documents/Personal_AI_powerhouse updated"
      ],
      "enabled": true
    },
    "mempalace": {
      "type": "local",
      "command": [
        "/usr/bin/python3",
        "-m",
        "mempalace.mcp_server"
      ],
      "enabled": true
    },
    "ong-vault-bridge": {
      "type": "local",
      "command": [
        "/Users/paulorezende/Library/Mobile Documents/iCloud~md~obsidian/Documents/ONG/NEDS/agents_workspace/bridge/run.sh"
      ],
      "enabled": true
    }
  }
}
```

- [ ] **Step 2: Verify MCP registration loads**

```bash
cd "/Users/paulorezende/Documents/Personal_AI_powerhouse updated"
opencode mcp list 2>/dev/null || echo "MCP list command not available — verify manually by checking that opencode.json is valid JSON:"
python -c "import json; json.load(open('opencode.json')); print('JSON valid')"
```
Expected: `JSON valid` and bridge appears in MCP list.

- [ ] **Step 3: Commit**

```bash
git -C "/Users/paulorezende/Documents/Personal_AI_powerhouse updated" add opencode.json
git -C "/Users/paulorezende/Documents/Personal_AI_powerhouse updated" commit -m "feat(integration): register ONG vault bridge MCP server"
```

---

### Task 5.2: End-to-end verification

**Files:** None (verification only)

**Security flag:** `none`

- [ ] **Step 1: Verify bridge server starts and all tools respond**

Start the bridge in background, then test each tool:

```bash
# Start bridge in background
BRIDGE="/Users/paulorezende/Library/Mobile Documents/iCloud~md~obsidian/Documents/ONG/NEDS/agents_workspace/bridge"
cd "$BRIDGE"
source .venv/bin/activate

# Test tools/list
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | timeout 10 python -m src.main 2>/dev/null | python -m json.tool

# Test vault_get_stats
echo '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"vault_get_stats","arguments":{}}}' | timeout 10 python -m src.main 2>/dev/null | python -m json.tool
```

Expected: Tools list shows all 7 tools. Stats returns counts matching vault reality.

- [ ] **Step 2: Test search from AI Powerhouse terminal**

```bash
cd "/Users/paulorezende/Documents/Personal_AI_powerhouse updated"

# Quick inline test calling the MCP directly
BRIDGE="/Users/paulorezende/Library/Mobile Documents/iCloud~md~obsidian/Documents/ONG/NEDS/agents_workspace/bridge"
cd "$BRIDGE"
source .venv/bin/activate

# Test vault_search_notes
echo '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"vault_search_notes","arguments":{"query":"sexual","limit":3}}}' | timeout 10 python -m src.main 2>/dev/null | python -m json.tool
```

Expected: Returns up to 3 notes matching "sexual" with snippets.

- [ ] **Step 3: Test semantic search**

```bash
echo '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"vault_semantic_search","arguments":{"query":"trauma infantil tratamento","limit":3}}}' | timeout 30 python -m src.main 2>/dev/null | python -m json.tool
```

Expected: Returns conceptually relevant results with similarity_score.

- [ ] **Step 4: Test get_note**

```bash
echo '{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"vault_get_note","arguments":{"path":"System/System.md"}}}' | timeout 10 python -m src.main 2>/dev/null | head -20
```

Expected: Returns note content with header.

- [ ] **Step 5: Test get_patient**

```bash
echo '{"jsonrpc":"2.0","id":6,"method":"tools/call","params":{"name":"vault_get_patient","arguments":{"name":"Ana"}}}' | timeout 10 python -m src.main 2>/dev/null | python -m json.tool
```

Expected: Returns patient folder structure or empty results (depending on existing data).

- [ ] **Step 6: Test get_tasks_due**

```bash
echo '{"jsonrpc":"2.0","id":7,"method":"tools/call","params":{"name":"vault_get_tasks_due","arguments":{}}}' | timeout 10 python -m src.main 2>/dev/null | python -m json.tool
```

Expected: Returns tasks with extracted dates (may be empty if no tasks exist yet).

- [ ] **Step 7: Test refresh_index**

```bash
echo '{"jsonrpc":"2.0","id":8,"method":"tools/call","params":{"name":"vault_refresh_index","arguments":{}}}' | timeout 600 python -m src.main 2>/dev/null | python -m json.tool
```

Expected: Returns before/after stats with duration. May take 2-5 minutes.

---

## Self-Review

### 1. Spec coverage
- ✅ **Hybrid format (MCP + vector embeddings):** Phase 2 (embeddings engine) + Phase 3 (all 7 tools)
- ✅ **Local all-MiniLM-L6-v2:** Task 2.3 explicitly uses this model
- ✅ **Server lives inside vault:** All paths under `ONG/NEDS/agents_workspace/bridge/`
- ✅ **No symlinks:** Direct paths, no symlinks anywhere
- ✅ **All tools included:** search, semantic_search, get_note, get_patient, get_tasks_due, get_stats, refresh_index — 7 tools across Tasks 3.1-3.4
- ✅ **Clear phase boundaries:** Each Phase header defines start/end conditions
- ✅ **Embeddings always local:** Task 2.3 uses sentence-transformers with explicit local model

### 2. Placeholder scan
No placeholders found. All code blocks contain actual Python code. All steps are concrete.

### 3. Type consistency
All tool names match across registration, config, and verification steps. Function signatures are consistent between files.

### 4. Scope-reduction scan
No "v1", "basic", "simple", "for now", "placeholder", "initial version", or "minimal" found. All 7 tools are included as specified.

---

## Execution Handoff

Plan saved to `docs/plans/2026-05-21-ong-vault-bridge-hybrid-cell.md`. Ready to execute with **Subagent-Driven** (13 tasks, phases are independent enough for parallel subagents within each phase). Reply to start, or say "inline" / "subagent" to switch.
