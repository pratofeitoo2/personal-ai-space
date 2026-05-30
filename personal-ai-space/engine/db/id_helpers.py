"""
id_helpers.py — Semantic ID generation for all database entities.

Every ID is human-readable and self-documenting:
  task-groceries-comprar-pregador   # task under project "Groceries"
  proj-knowledge-mgmt               # project "Knowledge Management"
  dep-deploy-ci-on-setup            # dependency between two tasks
  beh-emotion-20260530-a1b2         # behavioral observation
  sig-ses_abc123-0001              # session signal

Convention: {entity_prefix}-{context_slug}-{distinguisher}

Always call these functions instead of uuid.uuid4().hex for database IDs.
The short random suffix on some entities (e.g., behaviors) prevents collisions
while keeping the ID readable — best of both worlds.
"""

import datetime
import hashlib
import re
import time
import uuid


def slugify(text: str, max_len: int = 40) -> str:
    """Convert text to a URL-safe slug.

    Strips emoji, accented chars → ascii, collapses whitespace/punctuation.
    >>> slugify("Comprar pregador!")  →  "comprar-pregador"
    >>> slugify("📋 Tarefas do Dia")  →  "tarefas-do-dia"
    """
    import unicodedata
    # Normalize unicode (NFKD decomposes accented chars)
    s = unicodedata.normalize("NFKD", str(text))
    # Remove combining marks (accents etc.)
    s = s.encode("ascii", "ignore").decode("ascii")
    s = s.lower().strip()
    # Remove emoji and non-alphanumeric characters
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    s = re.sub(r"-+", "-", s)
    if len(s) > max_len:
        s = s[:max_len].rstrip("-")
    return s


# ── Tasks Database (tasks.db) ────────────────────────────────────────────────


def for_project(name: str) -> str:
    """Semantic project ID from its name."""
    return f"proj-{slugify(name, 48)}"


def for_task(title: str, project_id: str | None = None, *, _suffix: str = "") -> str:
    """Semantic task ID.

    Includes the project slug for traceability when project_id is available.
    Falls back to a short unique suffix when title alone would cause collisions.
    """
    title_slug = slugify(title, 36) or "untitled"
    if project_id:
        proj_part = project_id.removeprefix("proj-")
        base = f"task-{proj_part}-{title_slug}"
    else:
        base = f"task-{title_slug}"
    if _suffix:
        base = f"{base}-{_suffix}"
    if len(base) > 72:
        base = base[:72].rstrip("-")
    return base


def for_task_unique(title: str, project_id: str | None = None) -> str:
    """Like for_task but appends a short nonce for collision safety.

    Use this when creating new tasks from external sources (reminders, CLI)
    where identical titles in the same project are possible.
    """
    return for_task(title, project_id, _suffix=uuid.uuid4().hex[:6])


def for_dependency(task_id: str, depends_on_id: str) -> str:
    """Semantic dependency ID: dep-{task_short}-on-{depends_short}."""
    def _short(tid: str) -> str:
        return tid.removeprefix("task-").removeprefix("proj-")[:24]
    short = f"dep-{_short(task_id)}-on-{_short(depends_on_id)}"
    return short[:72]


def for_history(task_id: str) -> str:
    """Semantic history event ID with timestamp for ordering."""
    ts = int(time.time())
    short = task_id.removeprefix("task-").removeprefix("hist-")[:28]
    return f"hist-{short}-{ts}"


def for_doc_link(entity_type: str, entity_id: str) -> str:
    """Semantic doc_link ID."""
    short = entity_id.removeprefix("proj-").removeprefix("task-")[:36]
    return f"dl-{entity_type[:4]}-{short}"


def for_sync_state(entity_type: str, entity_id: str | None = None) -> str:
    """Semantic sync_state ID."""
    if entity_id:
        short = entity_id.removeprefix("proj-").removeprefix("task-")[:30]
        return f"sync-{entity_type[:8]}-{short}"
    return f"sync-{entity_type[:8]}-{uuid.uuid4().hex[:12]}"


# ── Self Database (self.db) ───────────────────────────────────────────────────


def for_behavior(behavior_type: str) -> str:
    """Semantic behavior ID with date + short nonce."""
    date_str = datetime.date.today().isoformat()
    return f"beh-{slugify(behavior_type, 16)}-{date_str}-{uuid.uuid4().hex[:4]}"


def for_observation(obs_type: str) -> str:
    """Semantic observation ID with date + short nonce."""
    date_str = datetime.date.today().isoformat()
    return f"obs-{slugify(obs_type, 20)}-{date_str}-{uuid.uuid4().hex[:4]}"


def for_session_signal(session_id: str, sequence: int = 0) -> str:
    """Semantic session_signal ID with sequence number for ordering."""
    short = (session_id or "unknown")[:16]
    return f"sig-{short}-{sequence:04d}"


def for_session_metadata(session_id: str) -> str:
    """Semantic session_metadata ID."""
    short = (session_id or "unknown")[:16]
    return f"meta-{short}"


def for_habit_log(habit_id: str, *,
                  _date: str | None = None) -> str:
    """Semantic habit_log ID with date + short nonce."""
    d = _date or datetime.date.today().isoformat()
    short_habit = habit_id.removeprefix("h-").removeprefix("habit_")[:20]
    return f"hl-{short_habit}-{d}-{uuid.uuid4().hex[:4]}"


# ── Memories Database (memories.db) ───────────────────────────────────────────


def for_interaction(agent_id: str) -> str:
    """Semantic interaction ID for memories.db."""
    short = slugify(agent_id, 16)
    ts = int(time.time())
    return f"iact-{short}-{ts}-{uuid.uuid4().hex[:4]}"


def for_agent_memory(agent_id: str) -> str:
    """Semantic agent_memory ID."""
    short = slugify(agent_id, 16)
    return f"mem-{short}-{uuid.uuid4().hex[:8]}"


def for_context_snapshot(session_id: str) -> str:
    """Semantic context_window ID."""
    short = (session_id or "session")[:16]
    return f"ctx-{short}-{uuid.uuid4().hex[:6]}"


# ── Knowledge Database (knowledge.db) ─────────────────────────────────────────


def for_note(title: str) -> str:
    """Semantic knowledge note ID."""
    title_slug = slugify(title, 40) or "note"
    return f"note-{title_slug}"


def for_knowledge_index(term: str) -> str:
    """Deterministic knowledge index ID from search term."""
    return hashlib.md5(term.encode()).hexdigest()
