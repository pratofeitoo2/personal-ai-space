"""
Knowledge Indexer Agent.
Manages articles, notes, cross-references and curation queue.
"""
import uuid
from pathlib import Path
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.base_agent import BaseAgent
import db_manager as db


class KnowledgeIndexer(BaseAgent):
    def __init__(self):
        super().__init__("knowledge-indexer")

    def initialize(self) -> bool:
        self.state = "ready"
        self.logger.info("Knowledge Indexer ready")
        return True

    # ── stats ─────────────────────────────────────────────────────────────

    def stats(self) -> dict:
        articles = db.query("knowledge", "SELECT count(*) as n FROM articles")
        notes    = db.query("knowledge", "SELECT count(*) as n FROM notes")
        refs     = db.query("knowledge", 'SELECT count(*) as n FROM "references"')
        pending  = db.query(
            "knowledge",
            "SELECT count(*) as n FROM articles WHERE status='pending'"
        )
        return {
            "articles": (articles[0]["n"] if articles else 0),
            "notes":    (notes[0]["n"]    if notes    else 0),
            "references": (refs[0]["n"]   if refs     else 0),
            "pending_curation": (pending[0]["n"] if pending else 0),
        }

    def search_notes(self, query: str, limit: int = 10) -> list[dict]:
        return db.query(
            "knowledge",
            "SELECT id, title, category, tags, created_at FROM notes "
            "WHERE title LIKE ? OR content LIKE ? OR tags LIKE ? "
            "ORDER BY created_at DESC LIMIT ?",
            (f"%{query}%", f"%{query}%", f"%{query}%", limit)
        )

    def add_note(self, data: dict) -> str:
        note_id = f"note_{uuid.uuid4().hex[:8]}"
        now = datetime.now().isoformat()
        db.execute(
            "knowledge",
            "INSERT INTO notes (id, title, content, created_at, updated_at, tags, category, importance_level) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (
                note_id,
                data.get("title", "Untitled"),
                data.get("content", ""),
                now, now,
                data.get("tags", ""),
                data.get("category", "general"),
                data.get("importance_level", 3),
            )
        )
        self.logger.info(f"Note added: {note_id}")
        return note_id

    def recent_notes(self, limit: int = 10) -> list[dict]:
        return db.query(
            "knowledge",
            "SELECT id, title, category, tags, created_at FROM notes "
            "ORDER BY created_at DESC LIMIT ?",
            (limit,)
        )

    # ── router ────────────────────────────────────────────────────────────

    def process(self, message: dict) -> dict:
        cmd  = message.get("payload", {}).get("command", "")
        data = message.get("payload", {}).get("data", {})

        if cmd == "stats":
            return self._ok(self.stats())
        if cmd == "search":
            q = message.get("payload", {}).get("query", "")
            return self._ok(self.search_notes(q))
        if cmd == "add_note":
            return self._ok({"note_id": self.add_note(data)})
        if cmd == "recent":
            return self._ok(self.recent_notes())

        return self._unknown(cmd)
