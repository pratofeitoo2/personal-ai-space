#!/usr/bin/env python3
"""
Fix articles table: extract proper author, summary, source, relevance_score,
published_date from the actual source files.

Run: PYTHONPATH="personal-ai-space/engine:$PYTHONPATH" python3 fix_articles.py
"""
import sys
import re
import yaml
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent / "personal-ai-space" / "engine"))
import db_manager as db

ARTICLES_DIR = Path(__file__).parent / "personal-ai-space" / "knowledge" / "articles"

# ── Helpers ──────────────────────────────────────────────────────────────────

def _read_frontmatter_and_body(file_path: Path):
    """Parse YAML frontmatter and body from a markdown file."""
    try:
        text = file_path.read_text(encoding="utf-8")
    except Exception:
        return {}, ""
    if not text.startswith("---"):
        return {}, text
    m = re.match(r"^---\s*\n(.*?)\n(?:---|\.\.\.)\s*\n?", text, re.DOTALL)
    if not m:
        return {}, text
    fm = yaml.safe_load(m.group(1))
    body = text[m.end():].strip()
    return (fm if isinstance(fm, dict) else {}), body


def _is_valid_author(val):
    """Check if a string looks like a real author name (not a sentence fragment)."""
    if not val or not isinstance(val, str):
        return False
    val = val.strip()
    if not val or len(val) > 60:
        return False
    # Single-word "names" like "outro", "quê?" are not valid
    words_raw = val.split()
    if len(words_raw) <= 1:
        return False
    # Strip punctuation for word matching
    clean = re.sub(r'[^\w\sà-úÀ-Ú]', ' ', val.lower())
    snippet_words = {"de", "para", "que", "como", "com", "sem", "por", "entre",
                     "mais", "menos", "muito", "pouco", "sobre", "após", "até",
                     "foi", "era", "tem", "está", "são", "ser", "ter", "poder",
                     "fazer", "tudo", "nada", "cada", "qual", "quais", "quem",
                     "onde", "quando", "porque", "pois", "então", "assim",
                     "desta", "deste", "nesse", "neste", "nessa", "nessas",
                     "lo", "la", "las", "los", "ela", "ele", "eles", "elas",
                     "deles", "delas", "seu", "sua", "seus", "suas", "meu",
                     "minha", "nosso", "nossa", "aquele", "aquela", "este",
                     "esta", "esse", "essa", "isto", "isso", "já", "mais",
                     "discute", "pertinência", "emergência", "consequente",
                     "procederam", "pesquisadores", "criação", "bancos",
                     "outro", "outra", "tanto", "ello",
                     "profesores", "catedráticos", "investigação",
                     "metodologia", "resultados", "conclusão", "introdução",
                     "abstract", "introduction", "method", "results"}
    words = set(clean.split())
    match_count = len(words & snippet_words)
    total = len(words)
    if total > 0 and match_count / total > 0.3:
        return False
    # "outro" alone is not a valid author
    if val.lower().strip() == "outro":
        return False
    return True


def _extract_author_from_title(title: str) -> str:
    """Extract author name from title if present (e.g. 'ALINE SARDINHA')."""
    m = re.search(r'(?i)(ali?ne?\s+sardinha)', title)
    if m:
        return "Aline Sardinha"
    m = re.search(r'(?i)autor:\s*([A-ZÀ-Ú][a-zà-ú]+(?:\s+[A-ZÀ-Ú][a-zà-ú]+){1,3})', title)
    if m:
        return m.group(1).strip()
    return ""


def _extract_summary(body: str, full_content: str, article_title: str = "", max_chars: int = 300) -> str:
    """Extract first meaningful paragraph as summary."""
    text = body or full_content or ""
    if not text.strip():
        return ""

    lines = text.split('\n')
    cleaned = []
    in_frontmatter = False
    skipped_h1 = False

    for line in lines:
        if line.strip() == '---':
            if not in_frontmatter:
                in_frontmatter = True
                continue
            else:
                in_frontmatter = False
                continue
        if in_frontmatter:
            continue
        line = re.sub(r'!\[.*?\]\(.*?\)', '', line)
        line = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', line)
        line = re.sub(r'\*\*|\*|__|~~', '', line)
        line = line.strip()
        if not line:
            cleaned.append('')
            continue

        h1 = re.match(r'^#\s+(.+)$', line)
        if h1:
            if not skipped_h1:
                skipped_h1 = True
                continue
            line = h1.group(1).strip()

        line = re.sub(r'^#{1,6}\s+', '', line).strip()
        cleaned.append(line)

    text = '\n'.join(cleaned)
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]

    for p in paragraphs:
        if re.search(r'^- \[.*\]\(#', p, re.MULTILINE):
            continue
        p_clean = re.sub(r'[-•·|#*]{3,}', '', p).strip()
        if len(p_clean) < 60:
            continue
        if re.match(r'^[\s!\[\]\(\)#\-\*•|]+$', p_clean):
            continue
        p_clean = re.sub(r'\s+', ' ', p_clean).strip()
        if len(p_clean) > max_chars:
            p_clean = p_clean[:max_chars].rsplit(' ', 1)[0] + '…'
        return p_clean

    cleaned_flat = re.sub(r'\s+', ' ', ' '.join(cleaned)).strip()
    if len(cleaned_flat) > max_chars:
        cleaned_flat = cleaned_flat[:max_chars].rsplit(' ', 1)[0] + '…'
    return cleaned_flat[:max_chars]


def _assign_relevance(fm: dict, file_ext: str, has_body: bool) -> float:
    """Assign relevance score based on content type and quality."""
    content_type = str(fm.get("type", "")).lower()
    category = str(fm.get("category", "")).lower()
    has_doi = bool(fm.get("doi"))
    tags = fm.get("tags", [])

    # Academic papers with DOI → highest value
    if has_doi or "academic-paper" in (tags if isinstance(tags, list) else []):
        return 0.90
    if content_type == "transcript" or "video-transcript" in (tags if isinstance(tags, list) else []):
        return 0.85
    if content_type in ("analysis", "career-planning"):
        return 0.80
    if "research-article" in content_type:
        return 0.80
    if "study" in (tags if isinstance(tags, list) else []):
        return 0.70
    # PDF/DOCX with no text extraction
    if not has_body:
        return 0.40
    return 0.60


def _file_extension(url: str) -> str:
    """Extract file extension from URL."""
    try:
        return Path(url).suffix.lower()
    except Exception:
        return ""


def _clean_title(fm: dict, file_path: Path) -> str:
    """Get a proper title from frontmatter or filename."""
    title = str(fm.get("title", "")).strip().strip("\"'")
    # Bad patterns that mean we need the filename instead
    bad_patterns = [
        r'^Revista Brasileira de$',
        r'^DOI:\s*10\.',
        r'^EDUR\s*•',
        r'^o campo da sexologia no brasil$',
        r'^\d{4}\s+Texto do artigo',
    ]
    for pat in bad_patterns:
        if re.search(pat, title, re.IGNORECASE):
            break
    else:
        # Title looks OK
        if len(title) > 5:
            return title

    # Fallback: use filename as title (cleaned)
    stem = file_path.stem if file_path else title
    if file_path:
        stem = re.sub(r'\.md$|\.pdf$|\.docx$', '', str(file_path.name))
        stem = stem.replace('_', ' ').replace('  ', ' ').strip()
        # Remove leading/trailing dashes and spaces
        stem = stem.strip('-').strip()
    return stem if stem else title


def _determine_source(fm: dict, file_ext: str) -> str:
    """Determine the source of the article."""
    # Check frontmatter source field
    src = fm.get("source", "")
    if src and isinstance(src, str) and src.startswith("http"):
        if "youtube" in src or "youtu.be" in src:
            return "YouTube"
        return "Website"

    content_type = str(fm.get("type", "")).lower()
    if content_type == "transcript":
        return "YouTube"
    if content_type in ("research-article", "academic-paper"):
        return "Academic Journal"
    if fm.get("doi"):
        return "Academic Journal"
    if file_ext == ".pdf":
        return "PDF Document"
    if file_ext == ".docx":
        return "Word Document"

    tags = fm.get("tags", [])
    if isinstance(tags, list) and "video-transcript" in tags:
        return "YouTube"
    return "Unknown"


def fix_all_articles():
    """Main fix routine."""
    articles = db.query("knowledge", "SELECT id, title, url, source, author, summary, relevance_score, published_date, full_content, tags FROM articles ORDER BY id")
    print(f"Found {len(articles)} articles to fix")

    fixed_counts = {"title": 0, "author": 0, "summary": 0, "source": 0, "relevance": 0, "published_date": 0}
    errors = []

    for art in articles:
        aid = art["id"]
        url = art["url"] or ""

        # Convert file:/// URI to local filesystem path
        local_path = url
        if local_path.startswith("file://"):
            local_path = local_path[7:]  # strip "file://"
        file_path = Path(local_path) if local_path else None

        fm = {}
        body = ""
        has_body = False

        # Read source file
        if file_path and file_path.exists():
            ext = file_path.suffix.lower()
            if ext == ".md":
                fm, body = _read_frontmatter_and_body(file_path)
                has_body = bool(body)
                if not fm and not body:
                    # Try reading without frontmatter
                    try:
                        body = file_path.read_text(encoding="utf-8")
                        has_body = bool(body.strip())
                    except Exception:
                        pass
            elif ext == ".docx":
                has_body = bool(art.get("full_content", ""))
            elif ext == ".pdf":
                has_body = bool(art.get("full_content", ""))
                if art.get("full_content") != "[PDF file — full text extraction requires OCR/PDF tooling]":
                    has_body = True

        # ── Build updates ──────────────────────────────────────────────
        updates = {}
        old = {}

        # 1. Title
        new_title = _clean_title(fm, file_path) if file_path else art["title"]
        if new_title != art["title"]:
            old["title"] = art["title"]
            updates["title"] = new_title

        # 2. Author
        new_author = ""
        old_author = art.get("author", "")
        # Try frontmatter first
        if fm and _is_valid_author(fm.get("author")):
            new_author = str(fm["author"]).strip()
        # Try extracting from title
        if not new_author:
            new_author = _extract_author_from_title(art["title"] or "")
        if not new_author and file_path:
            new_author = _extract_author_from_title(file_path.stem)
        if new_author != old_author:
            old["author"] = old_author
            updates["author"] = new_author

        # 3. Summary
        current_title = updates.get("title", art.get("title", ""))
        new_summary = _extract_summary(body, art.get("full_content", ""), article_title=current_title)
        if new_summary != art.get("summary", ""):
            old["summary"] = art.get("summary", "")
            updates["summary"] = new_summary

        # 4. Source
        ext = file_path.suffix.lower() if file_path else ""
        new_source = _determine_source(fm, ext)
        if new_source != art.get("source", ""):
            old["source"] = art.get("source", "")
            updates["source"] = new_source

        # 5. Relevance score
        new_relevance = _assign_relevance(fm, ext, has_body)
        old_relevance = art.get("relevance_score")
        if new_relevance != old_relevance:
            old["relevance_score"] = old_relevance
            updates["relevance_score"] = new_relevance

        # 6. Published date
        new_date = ""
        if fm and fm.get("publication_date"):
            pd = str(fm["publication_date"]).strip().strip("'\"")
            # Normalize date format
            try:
                dt = datetime.fromisoformat(pd)
                new_date = dt.strftime("%Y-%m-%d")
            except ValueError:
                if re.match(r"^\d{4}-\d{2}-\d{2}", pd):
                    new_date = pd[:10]
                else:
                    new_date = pd
        old_date = art.get("published_date")
        if new_date != old_date:
            old["published_date"] = old_date
            updates["published_date"] = new_date

        # ── Apply updates ──────────────────────────────────────────────
        if updates:
            set_clause = ", ".join(f"{col} = ?" for col in updates)
            values = list(updates.values()) + [aid]
            db.execute("knowledge", f"UPDATE articles SET {set_clause} WHERE id = ?", values)
            for col in updates:
                fixed_counts[col] = fixed_counts.get(col, 0) + 1
            print(f"  ✓ {aid[:8]}... ({art['title'][:40]:40s}) → {', '.join(f'{k}={v}' for k, v in updates.items() if k in ('title', 'author', 'source'))}")
        else:
            print(f"  - {aid[:8]}... ({art['title'][:40]:40s}) — no changes needed")

    # ── Summary ────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("FIX SUMMARY")
    print("=" * 60)
    for col, count in fixed_counts.items():
        print(f"  {col}: {count} articles updated")
    if errors:
        print(f"\n  Errors: {len(errors)}")
        for e in errors:
            print(f"    - {e}")
    print(f"\nTotal articles processed: {len(articles)}")
    return fixed_counts


if __name__ == "__main__":
    fix_all_articles()
