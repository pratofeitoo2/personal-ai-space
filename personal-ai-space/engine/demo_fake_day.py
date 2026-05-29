#!/usr/bin/env python3
"""
Fake Day Demo — Extreme Volume Automation Simulation
=====================================================

Simulates 24 hours of Personal AI automations compressed into ~24 minutes
(1 cycle = 1 hour, 60s delay between cycles).

Seeds the database with massive data volume to stress-test the automation
runner across all delivery channels (WhatsApp, macOS Notification, Reminders).

Usage:
    cd personal-ai-space/engine
    .venv/bin/python demo_fake_day.py
"""
import os
import sys
import time
import sqlite3
import shutil
import json
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# ════════════════════════════════════════════════════════════════════════════
# Configuration
# ════════════════════════════════════════════════════════════════════════════

DEMO_DIR = Path("/tmp/personal_ai_demo")
CYCLE_DELAY = 60          # seconds between cycles (1 cycle = 1 simulated hour)
TOTAL_CYCLES = 24         # simulate a full day
START_HOUR = 6            # start at 06:00 so morning_brief fires at cycle 2

# ════════════════════════════════════════════════════════════════════════════
# Logging helper
# ════════════════════════════════════════════════════════════════════════════

DELIVERIES = []

def log_delivery(rule_id, rule_name, whatsapp_items, mac_preview, reminder_title):
    """Log a delivery event for summary display."""
    DELIVERIES.append({
        "rule_id": rule_id,
        "rule_name": rule_name,
        "whatsapp_items": whatsapp_items,
        "mac_preview": mac_preview,
        "reminder": reminder_title,
    })

# ════════════════════════════════════════════════════════════════════════════
# Database setup — temporary DBs matching runner's expected schema
# ════════════════════════════════════════════════════════════════════════════

TASKS_DB = DEMO_DIR / "tasks.db"
SELF_DB = DEMO_DIR / "self.db"
CALENDAR_DB = DEMO_DIR / "calendar.db"


def setup_databases():
    """Create temp DBs with schemas the runner's SQL queries expect."""
    DEMO_DIR.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(str(TASKS_DB)) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                project_id TEXT,
                parent_task_id TEXT,
                priority TEXT NOT NULL DEFAULT 'normal',
                status TEXT NOT NULL DEFAULT 'pending',
                progress_pct INTEGER DEFAULT 0,
                estimated_hours REAL,
                actual_hours REAL,
                sort_order INTEGER DEFAULT 0,
                assigned_to TEXT,
                tags TEXT,
                recurrence TEXT,
                category TEXT DEFAULT 'general',
                due_date DATE,
                completed_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS task_archive (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                project_id TEXT,
                parent_task_id TEXT,
                priority TEXT NOT NULL DEFAULT 'normal',
                status TEXT NOT NULL DEFAULT 'completed',
                progress_pct INTEGER DEFAULT 0,
                estimated_hours REAL,
                actual_hours REAL,
                sort_order INTEGER DEFAULT 0,
                assigned_to TEXT,
                tags TEXT,
                recurrence TEXT,
                category TEXT DEFAULT 'general',
                due_date DATE,
                completed_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                archived_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)

    with sqlite3.connect(str(SELF_DB)) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS habits (
                id TEXT PRIMARY KEY,
                habit_name TEXT,
                category TEXT,
                frequency TEXT,
                start_date DATE,
                current_streak INTEGER DEFAULT 0,
                total_completions INTEGER DEFAULT 0,
                last_completed DATETIME,
                target_streak INTEGER,
                status TEXT
            );
            CREATE TABLE IF NOT EXISTS habit_logs (
                id TEXT PRIMARY KEY,
                habit_id TEXT,
                completed_at DATETIME,
                notes TEXT,
                confidence_level FLOAT,
                FOREIGN KEY (habit_id) REFERENCES habits(id)
            );
            CREATE TABLE IF NOT EXISTS needs (
                id TEXT PRIMARY KEY,
                category TEXT,
                name TEXT,
                title TEXT,
                priority TEXT,
                status TEXT,
                description TEXT,
                deadline DATE,
                linked_tasks TEXT,
                created_at DATETIME
            );
        """)

    with sqlite3.connect(str(CALENDAR_DB)) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                start_time DATETIME NOT NULL,
                end_time DATETIME,
                category TEXT DEFAULT 'general',
                status TEXT DEFAULT 'scheduled',
                notes TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)


def seed_extreme_data():
    """Seed DBs with massive volume — the 'extreme day' scenario."""
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    two_days_ago = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    in_3_days = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
    in_5_days = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
    in_7_days = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

    # ── Tasks (45 active + 15 archived) ───────────────────────────────────
    tasks = []
    tid = 0

    # 10 OVERDUE from 2 days ago (critical + high priority)
    for i in range(10):
        tid += 1
        priority = "critical" if i < 3 else "high"
        tasks.append((f"t{tid}", f"URGENTE: Finalizar relatorio Q{i+1}", None, None, None,
                      priority, "in_progress", 30 + i * 5, None, None, None, "work,reports",
                      None, "general", two_days_ago, None,
                      f"{two_days_ago} 09:00:00", f"{two_days_ago} 09:00:00"))

    # 8 OVERDUE from yesterday (mixed priority)
    for i in range(8):
        tid += 1
        priority = "high" if i < 4 else "normal"
        tasks.append((f"t{tid}", f"Atrasada: Revisar PR #{100 + i} do repositorio", None, None, None,
                      priority, "pending", 0, None, None, None, "code,reviews",
                      None, "general", yesterday, None,
                      f"{yesterday} 10:00:00", f"{yesterday} 10:00:00"))

    # 12 DUE TODAY (spread across priority levels)
    today_tasks = [
        ("critical", "Deploy producao — feature auth"),
        ("critical", "Resolver bug critical #4521 — login loop"),
        ("high", "Code review — 3 PRs pendentes"),
        ("high", "Atualizar dependencias com CVEs"),
        ("high", "Escrever testes para modulo de pagamentos"),
        ("normal", "Atualizar documentacao da API v2"),
        ("normal", "Refatorar modulo de logging"),
        ("normal", "Criar dashboard de metricas"),
        ("normal", "Implementar cache Redis para queries"),
        ("normal", "Setup CI/CD para novo repositorio"),
        ("low", "Organizar tickets do Jira"),
        ("low", "Limpar branches antigas do git"),
    ]
    for i, (priority, title) in enumerate(today_tasks):
        tid += 1
        tasks.append((f"t{tid}", title, None, None, None,
                      priority, "in_progress" if i < 5 else "pending",
                      i * 8, None, None, None, "devops,code,docs",
                      None, "general", today, None,
                      f"{today} 08:00:00", f"{today} 08:00:00"))

    # 8 DUE TOMORROW
    for i in range(8):
        tid += 1
        priority = "high" if i < 3 else "normal"
        tasks.append((f"t{tid}", f"Planejar sprint proxima semana — item {i+1}", None, None, None,
                      priority, "pending", 0, None, None, None, "planning",
                      None, "general", tomorrow, None,
                      f"{today} 14:00:00", f"{today} 14:00:00"))

    # 7 DUE IN 3-5 DAYS (low priority backlog)
    for i in range(7):
        tid += 1
        due = in_3_days if i < 4 else in_5_days
        tasks.append((f"t{tid}", f"Backlog: Melhorar performance do hook {i+1}", None, None, None,
                      "low", "pending", 0, None, None, None, "performance",
                      None, "general", due, None,
                      f"{today} 11:00:00", f"{today} 11:00:00"))

    with sqlite3.connect(str(TASKS_DB)) as conn:
        conn.executemany("""
            INSERT INTO tasks (id, title, description, project_id, parent_task_id,
                priority, status, progress_pct, estimated_hours, actual_hours,
                sort_order, assigned_to, tags, recurrence, category,
                due_date, completed_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, tasks)

    # 15 completed tasks in archive
    archived = []
    for i in range(15):
        tid += 1
        completed = f"{today} {8 + i:02d}:30:00"
        due = (datetime.now() - timedelta(days=i + 1)).strftime("%Y-%m-%d")
        archived.append((f"t{tid}", f"Concluida: Tarefa {i+1} do sprint", None, None, None,
                         "normal" if i > 5 else "high", "completed",
                         100, None, float(i) * 0.5, None, None,
                         None, None, "general",
                         due, completed, completed, completed))

    with sqlite3.connect(str(TASKS_DB)) as conn:
        conn.executemany("""
            INSERT INTO task_archive (id, title, description, project_id, parent_task_id,
                priority, status, progress_pct, estimated_hours, actual_hours,
                sort_order, assigned_to, tags, recurrence, category,
                due_date, completed_at, created_at, archived_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, archived)

    # ── Habits (12 total: 8 active, 4 at risk) ────────────────────────────
    habits = [
        ("h01", "Meditar 10min",         "bem-estar",   "daily", "2026-03-01", 60, 52, f"{today} 06:30:00", "active"),
        ("h02", "Exercicio 30min",       "saude",       "daily", "2026-03-15", 45, 40, f"{today} 07:00:00", "active"),
        ("h03", "Leitura 20min",         "crescimento", "daily", "2026-04-01", 30, 25, f"{today} 22:00:00", "active"),
        ("h04", "Beber 2L agua",         "saude",       "daily", "2026-01-01", 90, 85, f"{today} 18:00:00", "active"),
        ("h05", "Estudar ingles 15min",  "educacao",    "daily", "2026-04-15", 20, 12, yesterday,            "active"),
        ("h06", "Journal 5min",          "bem-estar",   "daily", "2026-05-01", 15, 8,  two_days_ago,         "active"),
        ("h07", "Caminhar 20min",        "saude",       "daily", "2026-05-10", 10, 5,  two_days_ago,         "active"),
        ("h08", "Praticar violao 15min", "hobby",       "daily", "2026-04-20", 25, 18, yesterday,            "active"),
        # 4 at risk — haven't completed in 2+ days
        ("h09", "Yoga manha",            "bem-estar",   "daily", "2026-04-01", 30, 20, two_days_ago,         "active"),
        ("h10", "Coding challenge",      "educacao",    "daily", "2026-05-01", 14, 10, two_days_ago,         "active"),
        ("h11", "Plant water",           "casa",        "weekly","2026-03-01",  8,  6, two_days_ago,         "active"),
        ("h12", "Backup arquivos",       "tech",        "weekly","2026-04-01",  4,  3, two_days_ago,         "active"),
    ]
    with sqlite3.connect(str(SELF_DB)) as conn:
        conn.executemany("""
            INSERT INTO habits (id, habit_name, category, frequency,
                start_date, current_streak, total_completions,
                last_completed, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, habits)

    # Habit logs for today (5 completed)
    habit_logs = [
        (f"hl{i+1}", f"h0{i+1}" if i < 5 else f"h0{i-4}",
         f"{today} {6 + i:02d}:{30 + i * 5:02d}:00", None, 0.9)
        for i in range(5)
    ]
    with sqlite3.connect(str(SELF_DB)) as conn:
        conn.executemany("""
            INSERT INTO habit_logs (id, habit_id, completed_at, notes, confidence_level)
            VALUES (?, ?, ?, ?, ?)
        """, habit_logs)

    # ── Goals / Needs (8 active, 3 near deadline) ──────────────────────────
    goals = [
        (f"g{i+1}", cat, title, title, priority, "active", desc, deadline)
        for i, (cat, title, priority, desc, deadline) in enumerate([
            ("carreira",  "Promocao para Senior",          "high",
             "Completar 3 projetos criticos e receber feedback 360", in_5_days),
            ("saude",     "Perder 5kg",                    "high",
             "Meta: 70kg ate final do mes",                     in_7_days),
            ("educacao",  "Certificacao AWS Solutions",    "normal",
             "Estudar 2h/dia, prova em 3 semanas",              in_7_days),
            ("financeiro","Fundo de emergencia 6 meses",   "high",
             "Guardar 20% do salario mensal",                   in_7_days),
            ("projeto",   "Lancar SaaS MVP",               "critical",
             "Beta publico ate fim do mes",                     in_3_days),
            ("hobby",     "Album de fotos 2026",           "low",
             "Organizar e editar 500 fotos",                    in_7_days),
            ("social",    "Networking — 2 reunioes/semana","normal",
             "Agendar cafe com 2 contatos por semana",          in_7_days),
            ("casa",      "Reforma cozinha",               "normal",
             "Planejar e orcamento ate junho",                  in_7_days),
            # 3 near deadline (within 3 days)
            ("urgente",   "Entregar proposta comercial",   "critical",
             "Proposta para cliente X — valor R$50k",           today),
            ("urgente",   "Resposta juridica — contrato",  "critical",
             "Revisar clausulas com advogado",                  tomorrow),
            ("urgente",   "Relatorio financeiro Q1",       "high",
             "Consolidar dados e enviar para diretorio",        in_3_days),
        ])
    ]
    with sqlite3.connect(str(SELF_DB)) as conn:
        conn.executemany("""
            INSERT INTO needs (id, category, name, title, priority, status, description, deadline)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, goals)

    # ── Calendar Events (15 events throughout today) ───────────────────────
    events = [
        (f"ev{i+1}", title, f"{today} {hour:02d}:00:00", f"{today} {int(hour + duration):02d}:00:00",
         category, "scheduled")
        for i, (title, hour, duration, category) in enumerate([
            ("Standup equipe",                    9,  0.5, "meeting"),
            ("Review de sprint",                  10, 1.0, "meeting"),
            ("1:1 com manager",                   11, 0.5, "meeting"),
            ("Almoco com cliente",                12, 1.5, "social"),
            ("Workshop de arquitetura",           14, 2.0, "training"),
            ("Demo para stakeholder",             16, 1.0, "meeting"),
            ("Retrospectiva sprint",              17, 1.0, "meeting"),
            ("Call com fornecedor",               10, 0.5, "external"),
            ("Reuniao com RH",                    15, 0.5, "admin"),
            ("Pair programming session",          11, 1.5, "development"),
            ("Architecture decision record",      14, 1.0, "development"),
            ("Client onboarding call",            16, 0.5, "external"),
            ("Team building",                     18, 1.0, "social"),
            ("Code freeze review",                17, 0.5, "development"),
            ("Weekly sync — product",             9,  1.0, "meeting"),
        ])
    ]
    with sqlite3.connect(str(CALENDAR_DB)) as conn:
        conn.executemany("""
            INSERT INTO events (id, title, start_time, end_time, category, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, events)


def _evolve_data(cycle: int):
    """Mutate the database each cycle to trigger state changes in the runner.

    This simulates a real day where tasks get completed, new ones appear,
    habits get logged, and calendar events approach/pass.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:00")

    with sqlite3.connect(str(TASKS_DB)) as conn:
        # Complete 1-2 tasks each cycle
        conn.execute("""
            UPDATE tasks SET status='completed', completed_at=?, updated_at=?
            WHERE status IN ('pending','in_progress')
            AND id IN (SELECT id FROM tasks WHERE status IN ('pending','in_progress') LIMIT ?)
        """, (now_str, now_str, min(cycle, 5)))

        # Add new overdue tasks periodically
        if cycle % 4 == 0:
            for j in range(2):
                conn.execute("""
                    INSERT OR IGNORE INTO tasks (id, title, priority, status, due_date, created_at, updated_at)
                    VALUES (?, ?, 'high', 'pending', date('now','localtime','-1 day'), ?, ?)
                """, (f"demo_t{cycle}_{j}", f"Nova tarefa atrasada #{cycle}.{j}", now_str, now_str))

    with sqlite3.connect(str(SELF_DB)) as conn:
        # Complete some habits each cycle
        if cycle % 2 == 0:
            conn.execute("""
                INSERT OR IGNORE INTO habit_logs (id, habit_id, completed_at)
                VALUES (?, ?, ?)
            """, (f"hl_cycle_{cycle}", "h01", now_str))
            conn.execute("""
                UPDATE habits SET current_streak = current_streak + 1, last_completed = ?
                WHERE id = 'h01'
            """, (now_str,))

        # Put more habits at risk periodically
        if cycle % 6 == 0 and cycle > 0:
            conn.execute("""
                UPDATE habits SET last_completed = date('now','localtime','-3 days')
                WHERE id IN ('h05', 'h06', 'h07')
            """)

    with sqlite3.connect(str(CALENDAR_DB)) as conn:
        # Add new events approaching periodically
        if cycle % 5 == 0 and cycle > 0:
            h = START_HOUR + cycle + 1
            conn.execute("""
                INSERT OR IGNORE INTO events (id, title, start_time, end_time, category, status)
                VALUES (?, ?, ?, ?, 'meeting', 'scheduled')
            """, (f"ev_new_{cycle}", f"Evento urgente #{cycle}", f"{today} {h:02d}:15:00", f"{today} {h:02d}:45:00"))


# ════════════════════════════════════════════════════════════════════════════
# Delivery mock — captures what would be sent
# ════════════════════════════════════════════════════════════════════════════

def mock_deliver_all(message, rule_id, rule_name, recipient=""):
    """Mock deliver_all — logs to DELIVERIES, no actual sends."""
    first_line = (message.split("\n")[0] or message)[:100]
    from automations.delivery import _REMINDER_TITLES
    rem_title = _REMINDER_TITLES.get(rule_id)

    log_delivery(rule_id, rule_name, len(message.split("\n")), first_line, rem_title)

    # Print channel previews
    ch = []
    if recipient:
        ch.append(f"    📱 WhatsApp  → {len(message)} chars para {recipient}")
    ch.append(f"    🔔 macOS     → \"{first_line}\"")
    if rem_title:
        ch.append(f"    ✅ Reminder  → \"{rem_title}\"")
    print("\n".join(ch))


# ════════════════════════════════════════════════════════════════════════════
# Simulated time
# ════════════════════════════════════════════════════════════════════════════

_sim_hour = START_HOUR

class SimulatedDatetime:
    """Drop-in replacement for datetime — returns simulated time."""
    @classmethod
    def now(cls):
        return datetime(2026, 5, 29, _sim_hour, 0, 0)


# ════════════════════════════════════════════════════════════════════════════
# Main simulation loop
# ════════════════════════════════════════════════════════════════════════════

def main():
    global _sim_hour

    print("\n" + "═" * 70)
    print("  🧪  FAKE DAY DEMO — Extreme Volume Automation Simulation")
    print("═" * 70)
    print(f"  Simulating 24h in {TOTAL_CYCLES} cycles × {CYCLE_DELAY}s delay")
    print(f"  Start: {START_HOUR:02d}:00  |  Total: {TOTAL_CYCLES} cycles")
    print("═" * 70)

    # ── Phase 1: Setup databases ──────────────────────────────────────────
    print("\n📦 Phase 1: Setting up temporary databases...")
    setup_databases()
    print(f"   ✓ Created: {TASKS_DB}")
    print(f"   ✓ Created: {SELF_DB}")
    print(f"   ✓ Created: {CALENDAR_DB}")

    # ── Phase 2: Seed extreme data ────────────────────────────────────────
    print("\n🌱 Phase 2: Seeding extreme volume data...")
    seed_extreme_data()

    # Count seeded data
    with sqlite3.connect(str(TASKS_DB)) as conn:
        task_count = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        archive_count = conn.execute("SELECT COUNT(*) FROM task_archive").fetchone()[0]
    with sqlite3.connect(str(SELF_DB)) as conn:
        habit_count = conn.execute("SELECT COUNT(*) FROM habits").fetchone()[0]
        log_count = conn.execute("SELECT COUNT(*) FROM habit_logs").fetchone()[0]
        goal_count = conn.execute("SELECT COUNT(*) FROM needs").fetchone()[0]
    with sqlite3.connect(str(CALENDAR_DB)) as conn:
        event_count = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]

    print(f"   ✓ {task_count} active tasks (+ {archive_count} archived)")
    print(f"   ✓ {habit_count} habits (+ {log_count} habit logs)")
    print(f"   ✓ {goal_count} goals/needs")
    print(f"   ✓ {event_count} calendar events")
    print(f"   {'─' * 40}")
    print(f"   Total: {task_count + archive_count + habit_count + log_count + goal_count + event_count} records")

    # ── Phase 3: Patch db_manager paths ───────────────────────────────────
    print("\n⚙️  Phase 3: Configuring runner to use demo databases...")
    import db_manager as db
    db.DB_PATHS["tasks"] = TASKS_DB
    db.DB_PATHS["self"] = SELF_DB
    db.DB_PATHS["calendar"] = CALENDAR_DB

    # ── Phase 4: Import runner (after DB patch) ───────────────────────────
    from automations.runner import AutomationRunner
    from automations.delivery import _REMINDER_TITLES

    # Create runner with mock engine
    mock_engine = MagicMock()
    mock_engine._hub = MagicMock()

    # Clear any cached state
    state_file = Path.home() / ".local" / "share" / "personal-ai-space" / "automation_state.json"
    if state_file.exists():
        state_file.unlink()

    runner = AutomationRunner(mock_engine)

    print(f"   ✓ Loaded {len(runner._rules)} automation rules")
    for r in runner._rules:
        print(f"     • {r['id']}: {r.get('name', '?')}")

    # ── Phase 5: Run simulation ───────────────────────────────────────────
    print("\n" + "═" * 70)
    print("  🚀  SIMULATION STARTING")
    print("═" * 70)

    recipient = "+5521966394764"

    # Only mock the datetime for simulated time — real delivery is active
    with patch("automations.runner.generate_opener", return_value=None), \
         patch("automations.templates.datetime") as mock_dt:

        # Make generate_greeting use simulated hour
        mock_dt.now.return_value = datetime(2026, 5, 29, START_HOUR, 0, 0)

        for cycle in range(TOTAL_CYCLES):
            _sim_hour = START_HOUR + cycle
            now = datetime(2026, 5, 29, _sim_hour % 24, 0, 0)
            mock_dt.now.return_value = now

            # ── Mutate data each cycle to trigger state changes ────────────
            if cycle > 0:
                _evolve_data(cycle)

            fired_rules = []
            for rule in runner._rules:
                if runner._is_due(rule, now):
                    fired_rules.append(rule.get("id", "?"))

            print(f"\n{'─' * 70}")
            print(f"  ⏰ CYCLE {cycle + 1:2d}/{TOTAL_CYCLES}  —  Simulated time: {_sim_hour:02d}:00:00")
            print(f"{'─' * 70}")

            if fired_rules:
                print(f"  📋 Rules due: {', '.join(fired_rules)}")
            else:
                print(f"  ⏳ No rules due this cycle")

            # Run each due rule — real delivery functions are called
            for rule in runner._rules:
                if runner._is_due(rule, now):
                    rule_id = rule.get("id", "unknown")
                    rule_name = rule.get("name", "Automation")
                    try:
                        runner._run_rule(rule, now, recipient)
                    except Exception as e:
                        print(f"  ❌ Rule '{rule_id}' error: {e}")

            # Delay between cycles (skip on last cycle)
            if cycle < TOTAL_CYCLES - 1:
                print(f"\n  ⏳ Waiting {CYCLE_DELAY}s before next cycle...")
                time.sleep(CYCLE_DELAY)

    # ── Phase 6: Summary ──────────────────────────────────────────────────
    print("\n\n" + "═" * 70)
    print("  📊  DEMO SUMMARY")
    print("═" * 70)
    print(f"\n  Total cycles:  {TOTAL_CYCLES}")
    print(f"  Total deliveries: {len(DELIVERIES)}")

    # Count by rule
    rule_counts = {}
    for d in DELIVERIES:
        rid = d["rule_id"]
        rule_counts[rid] = rule_counts.get(rid, 0) + 1

    print(f"\n  Deliveries by rule:")
    for rid, count in sorted(rule_counts.items()):
        print(f"    • {rid}: {count}x")

    # Count reminders created
    reminders = [d for d in DELIVERIES if d["reminder"]]
    print(f"\n  Reminders created: {len(reminders)}")
    for r in reminders:
        print(f"    • {r['reminder']} ({r['rule_name']})")

    # Final DB state
    print(f"\n  Final database state:")
    with sqlite3.connect(str(TASKS_DB)) as conn:
        active = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        archived = conn.execute("SELECT COUNT(*) FROM task_archive").fetchone()[0]
    with sqlite3.connect(str(SELF_DB)) as conn:
        habits = conn.execute("SELECT COUNT(*) FROM habits").fetchone()[0]
        logs = conn.execute("SELECT COUNT(*) FROM habit_logs").fetchone()[0]
    print(f"    Tasks:      {active} active + {archived} archived")
    print(f"    Habits:     {habits} tracked + {logs} log entries")

    print(f"\n{'═' * 70}")
    print(f"  ✅  DEMO COMPLETE — All channels tested with extreme volume")
    print(f"{'═' * 70}\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  ⚡ Demo interrupted by user")
        sys.exit(0)
