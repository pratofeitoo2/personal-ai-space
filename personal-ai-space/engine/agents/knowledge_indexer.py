"""
Knowledge Indexer Agent.
Manages articles, notes, cross-references, term indexing and curation queue.
"""
import hashlib
import re
import uuid
from pathlib import Path
from datetime import datetime
from collections import Counter

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.base_agent import BaseAgent
import db_manager as db

# ── stop words (English + Portuguese) ─────────────────────────────────────
_STOP_WORDS = frozenset({
    # English
    'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be',
    'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
    'would', 'could', 'should', 'may', 'might', 'can', 'shall', 'not',
    'no', 'nor', 'so', 'if', 'then', 'than', 'that', 'this', 'these',
    'those', 'it', 'its', 'i', 'me', 'my', 'we', 'our', 'you', 'your',
    'he', 'him', 'his', 'she', 'her', 'they', 'them', 'their', 'what',
    'which', 'who', 'whom', 'when', 'where', 'why', 'how', 'all', 'each',
    'every', 'both', 'few', 'more', 'most', 'some', 'any', 'into', 'over',
    'up', 'out', 'about', 'just', 'also', 'very', 'too', 'here', 'there',
    'only', 'own', 'same', 'other', 'even', 'still', 'much', 'than',
    # Portuguese
    'a', 'e', 'o', 'as', 'os', 'ao', 'aos', 'na', 'nas', 'no', 'nos',
    'da', 'das', 'do', 'dos', 'num', 'numa', 'dum', 'duma',
    'de', 'em', 'para', 'com', 'sem', 'sob', 'por', 'entre',
    'que', 'como', 'mas', 'ou', 'se', 'lá', 'cá', 'sim', 'não',
    'ele', 'ela', 'eles', 'elas', 'meu', 'minha', 'seu', 'sua',
    'nosso', 'nossa', 'um', 'uma', 'uns', 'umas', 'isto', 'isso',
    'aquele', 'aquela', 'este', 'esta', 'esse', 'essa',
    'já', 'mais', 'menos', 'muito', 'pouco', 'bem', 'mal',
    'são', 'ser', 'estar', 'ter', 'vir', 'poder', 'fazer',
    'foi', 'era', 'tem', 'têm', 'está', 'estão', 'pelo', 'pela',
    'durante', 'sempre', 'depois', 'antes', 'até', 'desde',
    'tudo', 'nada', 'algo', 'cada', 'qual', 'quais', 'quem',
    'onde', 'quando', 'porque', 'pois', 'então', 'assim',
    'contra', 'sobre', 'perante', 'trás',
})


def _tokenize(text: str) -> list[str]:
    """Extract meaningful lowercase terms from text, filtering stop words."""
    if not text:
        return []
    terms = re.findall(r'[a-záàâãéèêíïóôõöúüçñ][a-záàâãéèêíïóôõöúüçñ0-9]*', text.lower())
    return [t for t in terms if len(t) >= 2 and t not in _STOP_WORDS]


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
        refs     = self._safe_ref_count()
        pending  = db.query(
            "knowledge",
            "SELECT count(*) as n FROM articles WHERE status='pending'"
        )
        index    = db.query(
            "knowledge",
            "SELECT count(*) as n FROM knowledge_index"
        )
        return {
            "articles": (articles[0]["n"] if articles else 0),
            "notes":    (notes[0]["n"]    if notes    else 0),
            "references": refs,
            "pending_curation": (pending[0]["n"] if pending else 0),
            "knowledge_index": (index[0]["n"] if index else 0),
        }

    def _safe_ref_count(self) -> int:
        try:
            rows = db.query("knowledge", 'SELECT count(*) as n FROM "references"')
            return rows[0]["n"] if rows else 0
        except Exception:
            return 0

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

    # ── index builder ─────────────────────────────────────────────────────

    def build_index(self) -> dict:
        """(Re)build the knowledge_index term-frequency table from all notes."""
        self.logger.info("Rebuilding knowledge index from notes…")

        rows = db.query(
            "knowledge",
            "SELECT id, title, content, tags FROM notes"
        )
        if not rows:
            self.logger.info("No notes to index")
            return {"indexed_terms": 0, "processed_notes": 0}

        # Step 1: per-note unique terms
        note_terms: dict[str, set[str]] = {}
        term_freq: dict[str, int] = {}
        for row in rows:
            note_id = row["id"]
            combined = " ".join(filter(None, [
                row.get("title", ""),
                row.get("content", ""),
                row.get("tags", ""),
            ]))
            terms = set(_tokenize(combined))
            note_terms[note_id] = terms
            for t in terms:
                term_freq[t] = term_freq.get(t, 0) + 1

        # Step 2: term → note-ids reverse index
        term_notes: dict[str, list[str]] = {}
        for note_id, terms in note_terms.items():
            for t in terms:
                term_notes.setdefault(t, []).append(note_id)

        # Step 3: compute co-occurrences and write
        now = datetime.now().isoformat()
        inserted = 0

        db.execute("knowledge", "DELETE FROM knowledge_index")

        for term, freq in term_freq.items():
            co_occur: Counter = Counter()
            for note_id in term_notes.get(term, []):
                co_occur.update(
                    other for other in note_terms.get(note_id, set())
                    if other != term
                )
            top_related = [t for t, _ in co_occur.most_common(10)]
            term_id = hashlib.md5(term.encode()).hexdigest()

            db.execute(
                "knowledge",
                "INSERT INTO knowledge_index "
                "(id, term, frequency, last_updated, related_terms) "
                "VALUES (?, ?, ?, ?, ?)",
                (term_id, term, freq, now, ", ".join(top_related))
            )
            inserted += 1

        self.logger.info(f"Indexed {inserted} terms from {len(rows)} notes")
        return {"indexed_terms": inserted, "processed_notes": len(rows)}

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
        if cmd in ("build_index", "index"):
            return self._ok(self.build_index())

        return self._unknown(cmd)
