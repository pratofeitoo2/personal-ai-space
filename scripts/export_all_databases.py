#!/usr/bin/env python3
"""
Export ALL tables from ALL SQLite databases to CSV.
Usage: python export_all_databases.py
"""
import sqlite3
import csv
import os
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent.parent
DB_DIR = ROOT / "personal-ai-space" / "engine" / "db"
EXPORT_DIR = ROOT / "exports"

# Database paths and their subdirectories
DATABASES = {
    "activities": DB_DIR / "activities" / "activities.db",
    "calendar": DB_DIR / "calendar" / "calendar.db",
    "git": DB_DIR / "git" / "git.db",
    "jobs": DB_DIR / "jobs" / "jobs.db",
    "knowledge": DB_DIR / "knowledge" / "knowledge.db",
    "memories": DB_DIR / "memories" / "memories.db",
    "self": DB_DIR / "self" / "self.db",
    "tasks": DB_DIR / "tasks" / "tasks.db",
}

def export_table(conn, table_name, output_path):
    """Export a single table to CSV."""
    cursor = conn.cursor()
    
    # Get column names
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    
    # Get all data
    cursor.execute(f"SELECT * FROM {table_name}")
    rows = cursor.fetchall()
    
    # Write CSV
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        writer.writerows(rows)
    
    return len(rows)

def export_database(db_name, db_path):
    """Export all tables from a database."""
    if not db_path.exists():
        print(f"  ⚠️  {db_name}: database not found at {db_path}")
        return {}
    
    # Handle symlink
    if db_path.is_symlink():
        target = db_path.resolve()
        if not target.exists():
            print(f"  ⚠️  {db_name}: symlink broken -> {target}")
            return {}
        db_path = target
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Get all tables (including views)
        cursor.execute("SELECT name, type FROM sqlite_master WHERE type IN ('table', 'view') ORDER BY name")
        objects = cursor.fetchall()
        
        if not objects:
            print(f"  ⚠️  {db_name}: no tables found")
            conn.close()
            return {}
        
        results = {}
        for obj_name, obj_type in objects:
            # Skip internal SQLite tables
            if obj_name.startswith('sqlite_'):
                continue
            
            output_path = EXPORT_DIR / db_name / f"{obj_name}.csv"
            try:
                row_count = export_table(conn, obj_name, output_path)
                results[obj_name] = row_count
                status = "✅" if row_count > 0 else "📭"
                print(f"  {status} {obj_name}: {row_count} rows -> {output_path.relative_to(ROOT)}")
            except Exception as e:
                print(f"  ❌ {obj_name}: ERROR - {e}")
                results[obj_name] = -1
        
        conn.close()
        return results
        
    except Exception as e:
        print(f"  ❌ {db_name}: failed to open - {e}")
        return {}

def main():
    print("=" * 60)
    print("DATABASE EXPORT TOOL")
    print(f"Time: {datetime.now().isoformat()}")
    print(f"Export dir: {EXPORT_DIR}")
    print("=" * 60)
    
    # Clean old exports
    if EXPORT_DIR.exists():
        import shutil
        for item in EXPORT_DIR.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
        print(f"\n🧹 Cleaned old exports from {EXPORT_DIR}")
    
    total_tables = 0
    total_rows = 0
    all_results = {}
    
    for db_name, db_path in DATABASES.items():
        print(f"\n📦 {db_name} ({db_path.name})")
        results = export_database(db_name, db_path)
        all_results[db_name] = results
        total_tables += len(results)
        total_rows += sum(v for v in results.values() if v > 0)
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total databases: {len(DATABASES)}")
    print(f"Total tables exported: {total_tables}")
    print(f"Total rows exported: {total_rows}")
    
    # List empty tables
    empty = []
    for db_name, results in all_results.items():
        for table, count in results.items():
            if count == 0:
                empty.append(f"  {db_name}.{table}")
    
    if empty:
        print(f"\n📭 Empty tables ({len(empty)}):")
        for e in empty:
            print(e)
    
    # List failed exports
    failed = []
    for db_name, results in all_results.items():
        for table, count in results.items():
            if count == -1:
                failed.append(f"  {db_name}.{table}")
    
    if failed:
        print(f"\n❌ Failed exports ({len(failed)}):")
        for f in failed:
            print(f)
    
    print(f"\n✅ Export complete at {datetime.now().isoformat()}")

if __name__ == "__main__":
    main()
