"""
Migration: Add original_format column to notes table.

Tracks which source format a note was converted from (pdf, docx, txt, md).
Enables filtering and analytics on ingested content sources.
"""
import sqlite3
from pathlib import Path

ROOT = Path("/Users/paulorezende/Documents/Personal_AI_powerhouse/personal-ai-space")
DB_PATH = ROOT / "engine/db/knowledge.db"


def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(notes)")
    columns = {row[1] for row in cursor.fetchall()}

    if "original_format" not in columns:
        cursor.execute("""
            ALTER TABLE notes
            ADD COLUMN original_format TEXT
            DEFAULT 'md'
        """)
        print("  Added column: original_format")
    else:
        print("  Column original_format already exists, skipping.")

    if "conversion_metadata" not in columns:
        cursor.execute("""
            ALTER TABLE notes
            ADD COLUMN conversion_metadata TEXT
        """)
        print("  Added column: conversion_metadata")
    else:
        print("  Column conversion_metadata already exists, skipping.")

    conn.commit()
    conn.close()
    print("Migration complete.")


if __name__ == "__main__":
    migrate()