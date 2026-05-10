#!/usr/bin/env python3
"""
Initialize all databases from schema files and seed starter data.
Run once before first engine start.
"""
import sys
import json
import uuid
from pathlib import Path
from datetime import datetime, date

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

import db_manager as db
from log_manager import setup_logging, get_logger

setup_logging("INFO")
logger = get_logger("init")

SELF_PROFILE_PATH = ROOT.parent / "self" / "profile.json"


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

    starter_habits = [
        ("morning_standup",  "Morning standup",      "productivity", "daily",   0, 0, 30),
        ("deep_work",        "Deep work block",       "productivity", "daily",   0, 0, 30),
        ("reading",          "Read technical articles","learning",    "3x_week", 0, 0, 20),
        ("exercise",         "Exercise",              "health",       "4x_week", 0, 0, 20),
        ("weekly_review",    "Weekly review",         "meta",         "weekly",  0, 0, 12),
    ]
    for h in starter_habits:
        db.execute(
            "self",
            "INSERT OR IGNORE INTO habits "
            "(id, habit_name, category, frequency, current_streak, total_completions, "
            "start_date, target_streak, status) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (uuid.uuid4().hex, h[1], h[2], h[3], h[4], h[5], date.today().isoformat(), h[6], "active")
        )
    print(f"  ✓ {len(starter_habits)} habits seeded")


def seed_needs():
    print("Seeding active needs…")
    rows = db.query("self", "SELECT count(*) as n FROM needs")
    if rows and rows[0]["n"] > 0:
        print("  Needs already exist — skipping")
        return

    needs = [
        ("professional", "Functional AI system",    "critical", "in_progress", "Build personal AI space"),
        ("personal",     "Time clarity",            "high",     "active",      "Better time tracking"),
        ("professional", "Knowledge management",    "high",     "active",      "Systematic knowledge org"),
        ("health",       "Consistent routines",     "medium",   "active",      "Daily habits"),
    ]
    for n in needs:
        db.execute(
            "self",
            "INSERT OR IGNORE INTO needs (id, category, name, priority, status, description, created_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (uuid.uuid4().hex, n[0], n[1], n[2], n[3], n[4], datetime.now().isoformat())
        )
    print(f"  ✓ {len(needs)} needs seeded")


def seed_tasks():
    print("Seeding starter tasks…")
    rows = db.query("tasks", "SELECT count(*) as n FROM tasks")
    if rows and rows[0]["n"] > 0:
        print("  Tasks already exist — skipping")
        return

    tasks = [
        ("task_001", "Initialize engine databases",       "personal-ai", "critical", "completed"),
        ("task_002", "Design agent communication protocol","personal-ai", "high",     "pending"),
        ("task_003", "Build habit tracking system",       "personal-ai", "high",     "pending"),
        ("task_004", "Connect first integration",         "personal-ai", "medium",   "pending"),
        ("task_005", "Review and curate knowledge base",  "knowledge",   "medium",   "pending"),
    ]
    for t in tasks:
        db.execute(
            "tasks",
            "INSERT OR IGNORE INTO tasks (id, title, project_id, priority, status, created_at) "
            "VALUES (?,?,?,?,?,?)",
            (t[0], t[1], t[2], t[3], t[4], datetime.now().isoformat())
        )
    print(f"  ✓ {len(tasks)} tasks seeded")


def seed_projects():
    print("Seeding starter projects…")
    rows = db.query("tasks", "SELECT count(*) as n FROM projects")
    if rows and rows[0]["n"] > 0:
        print("  Projects already exist — skipping")
        return

    db.execute(
        "tasks",
        "INSERT OR IGNORE INTO projects (id, name, description, status, start_date, created_at) "
        "VALUES (?,?,?,?,?,?)",
        (
            "personal-ai",
            "Personal AI Powerhouse",
            "Build the personal agentic AI system",
            "active",
            date.today().isoformat(),
            datetime.now().isoformat(),
        )
    )
    print("  ✓ 1 project seeded")


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
