import os
import sqlite3
import uuid
import yaml
from pathlib import Path
from datetime import datetime

# Path constants
ROOT = Path("/Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space")
KNOWLEDGE_DIR = ROOT / "knowledge"
DB_PATH = ROOT / "engine/db/knowledge.db"

def parse_md(file_path):
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    
    # Simple YAML frontmatter parser
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            try:
                frontmatter = yaml.safe_load(parts[1])
                body = parts[2].strip()
                return frontmatter, body
            except:
                pass
    return {}, content

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Notes
    notes_dir = KNOWLEDGE_DIR / "notes"
    print(f"Migrating notes from {notes_dir}...")
    for file in notes_dir.glob("*.md"):
        fm, body = parse_md(file)
        
        # Mapping
        note_id = f"note_{uuid.uuid4().hex[:8]}"
        title = str(fm.get("title", file.stem))
        created = str(fm.get("created", datetime.now().isoformat()))
        updated = str(fm.get("updated", created))
        
        tags_list = fm.get("tags", [])
        tags = ",".join(tags_list) if isinstance(tags_list, list) else str(tags_list)
        
        category = str(fm.get("category", "general"))
        
        try:
            cursor.execute("""
                INSERT INTO notes (id, title, content, created_at, updated_at, tags, category, importance_level)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (note_id, title, body, created, updated, tags, category, 3))
            print(f"  Migrated note: {title}")
        except Exception as e:
            print(f"  Error migrating note {title}: {e}")

    # 2. Articles
    articles_dir = KNOWLEDGE_DIR / "articles"
    print(f"Migrating articles from {articles_dir}...")
    for file in articles_dir.glob("*.md"):
        fm, body = parse_md(file)
        
        # Mapping
        article_id = f"art_{uuid.uuid4().hex[:8]}"
        title = str(fm.get("title", file.stem))
        tags_list = fm.get("tags", [])
        tags = ",".join(tags_list) if isinstance(tags_list, list) else str(tags_list)
        
        try:
            cursor.execute("""
                INSERT INTO articles (id, title, full_content, tags, status)
                VALUES (?, ?, ?, ?, ?)
            """, (article_id, title, body, tags, "imported"))
            print(f"  Migrated article: {title}")
        except Exception as e:
            print(f"  Error migrating article {title}: {e}")

    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
