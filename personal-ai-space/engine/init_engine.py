#!/usr/bin/env python3
"""
Initialize all databases from schema files and seed starter data.
Run once before first engine start.
"""
import sys
import json
import json5
import uuid
from pathlib import Path
from datetime import datetime, date

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

import db_manager as db
from log_manager import setup_logging, get_logger
from synthesis import propagator

setup_logging("INFO")
logger = get_logger("init")

SELF_PROFILE_PATH = ROOT.parent / "self" / "profile.json"
SEEDS_CONFIG_PATH = ROOT / "config" / "seeds.json5"


def _load_seeds():
    if SEEDS_CONFIG_PATH.exists():
        with open(SEEDS_CONFIG_PATH) as f:
            return json5.load(f)
    print(f"  ⚠ Seeds config not found at {SEEDS_CONFIG_PATH}")
    return {}


def init_databases():
    print("Initializing databases…")
    db.init_all()
    health = db.health_check()
    for name, result in health.items():
        icon = "✓" if result["ok"] else "✗"
        print(f"  {icon} {name}.db ({result.get('tables', '?')} tables)")
    print()


def seed_profile():
    print("Seeding user profile…")
    rows = db.query("self", "SELECT id FROM profile LIMIT 1")
    if rows:
        print("  Profile already exists — skipping")
        return

    profile = {}
    if SELF_PROFILE_PATH.exists():
        with open(SELF_PROFILE_PATH) as f:
            profile = json.load(f)

    db.execute(
        "self",
        "INSERT OR IGNORE INTO profile "
        "(id, name, age, timezone, work_style, energy_peak_hours, "
        "communication_preference, decision_style) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (
            profile.get("id", "self_001"),
            profile.get("name", "User"),
            profile.get("age"),
            profile.get("timezone", "America/Sao_Paulo"),
            profile.get("work_style", "deep_work_preferred"),
            json.dumps(profile.get("energy_peak_hours", [])),
            profile.get("preferences", {}).get("communication"),
            profile.get("preferences", {}).get("decision_making"),
        )
    )
    print("  ✓ Profile seeded from self/profile.json")


def seed_habits():
    print("Seeding starter habits…")
    rows = db.query("self", "SELECT count(*) as n FROM habits")
    if rows and rows[0]["n"] > 0:
        print("  Habits already exist — skipping")
        return

    seeds = _load_seeds()
    habits = seeds.get("habits", [])
    for h in habits:
        db.execute(
            "self",
            "INSERT OR IGNORE INTO habits "
            "(id, habit_name, category, frequency, current_streak, total_completions, "
            "start_date, target_streak, status) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (uuid.uuid4().hex, h["name"], h["category"], h["frequency"],
             0, 0, date.today().isoformat(), h.get("target_streak", 30), "active")
        )
    print(f"  ✓ {len(habits)} habits seeded")


def seed_needs():
    print("Seeding active needs…")
    rows = db.query("self", "SELECT count(*) as n FROM needs")
    if rows and rows[0]["n"] > 0:
        print("  Needs already exist — skipping")
        return

    seeds = _load_seeds()
    needs = seeds.get("needs", [])
    for n in needs:
        db.execute(
            "self",
            "INSERT OR IGNORE INTO needs (id, category, name, priority, status, description, created_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (uuid.uuid4().hex, n["category"], n["name"], n["priority"],
             n["status"], n["description"], datetime.now().isoformat())
        )
    print(f"  ✓ {len(needs)} needs seeded")


def seed_tasks():
    print("Seeding starter tasks…")
    rows = db.query("tasks", "SELECT count(*) as n FROM tasks")
    if rows and rows[0]["n"] > 0:
        print("  Tasks already exist — skipping")
        return

    seeds = _load_seeds()
    tasks = seeds.get("tasks", [])
    now = datetime.now().isoformat()
    for t in tasks:
        tid = t["id"]
        db.execute(
            "tasks",
            "INSERT OR IGNORE INTO tasks "
            "(id, title, description, project_id, priority, status, created_at, estimated_hours, category) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (tid, t["title"], t["description"], t["project_id"],
             t["priority"], t["status"], now, t.get("estimated_hours"), t.get("category", "general"))
        )
        propagator.on_task_created(tid)
    print(f"  ✓ {len(tasks)} tasks seeded")


def seed_projects():
    print("Seeding starter projects…")
    rows = db.query("tasks", "SELECT count(*) as n FROM projects")
    if rows and rows[0]["n"] > 0:
        print("  Projects already exist — skipping")
        return

    seeds = _load_seeds()
    projects = seeds.get("projects", [])
    now = datetime.now().isoformat()
    for p in projects:
        db.execute(
            "tasks",
            "INSERT OR IGNORE INTO projects "
            "(id, name, description, status, start_date, total_tasks, completed_tasks, created_at) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (
                p["id"],
                p["name"],
                p["description"],
                p["status"],
                date.today().isoformat(),
                0, 0,
                now,
            )
        )
    print(f"  ✓ {len(projects)} projects seeded")


def ensure_dirs():
    for sub in ["logs", "memory", "db"]:
        (ROOT / sub).mkdir(exist_ok=True)
    print("  ✓ Directories ready")


def main():
    print("\n" + "=" * 50)
    print("  Personal AI Space — Database Initialization")
    print("=" * 50 + "\n")

    ensure_dirs()
    print()
    init_databases()
    seed_profile()
    print()
    seed_habits()
    seed_needs()
    seed_tasks()
    seed_projects()

    print("\n" + "=" * 50)
    print("  Initialization complete ✓")
    print("  Run:  python engine/cli.py health")
    print("  Then: python engine/cli.py digest")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    main()
