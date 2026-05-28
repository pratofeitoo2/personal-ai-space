"""
Scheduler — Periodic job runner for engine daemon.

Reads schedule definitions from engine.config.json5 and system.config.json5.
Runs jobs at configured times on a background thread alongside the HTTP daemon.
"""
import sys
import time
import threading
import json5
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

from log_manager import get_logger

logger = get_logger("engine.scheduler")


class Scheduler:
    """Lightweight scheduler for periodic engine jobs.

    Loads job definitions from config files and runs matching handlers
    on configurable schedules: interval (minutes), daily at time, weekly on day+time.
    Runs as a daemon thread alongside the engine HTTP server.
    """

    def __init__(self, engine):
        self._engine = engine
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._jobs: list[dict] = []
        self._last_run: dict[str, datetime] = {}
        self._config_dir = Path(__file__).resolve().parent.parent / "config"
        self._load_jobs()

    # ── Job loading ───────────────────────────────────────────────────

    def _load_jobs(self):
        """Load job definitions from engine.config.json5 and system.config.json5."""
        cfg_path = self._config_dir / "engine.config.json5"
        if cfg_path.exists():
            try:
                with open(cfg_path) as f:
                    cfg = json5.load(f)
                for key, sched in cfg.get("update_cycle", {}).items():
                    job = self._parse_schedule(key, sched)
                    if job:
                        self._jobs.append(job)
            except Exception as e:
                logger.warning("Failed to load engine.config.json5: %s", e)

        sys_path = self._config_dir / "system.config.json5"
        if sys_path.exists():
            try:
                with open(sys_path) as f:
                    cfg = json5.load(f)
                reporting = cfg.get("data_flows", {}).get("reporting", {})
                for key in ("daily_digest", "weekly_review", "monthly_analysis"):
                    if key in reporting:
                        job = self._parse_schedule(key, reporting[key])
                        if job:
                            self._jobs.append(job)
            except Exception as e:
                logger.warning("Failed to load system.config.json5: %s", e)

        self._jobs.append({
            "name": "pattern_inference",
            "handler": self._run_pattern_inference,
            "type": "interval",
            "interval_minutes": 240,
        })
        self._jobs.append({
            "name": "apple_calendar_poll",
            "handler": self._run_apple_calendar_poll,
            "type": "interval",
            "interval_minutes": 30,
        })
        self._jobs.append({
            "name": "apple_reminders_sync",
            "handler": self._run_apple_reminders_poll,
            "type": "interval",
            "interval_minutes": 1,
        })
        self._jobs.append({
            "name": "self_sync",
            "handler": self._run_self_sync,
            "type": "interval",
            "interval_minutes": 60,
        })
        self._jobs.append({
            "name": "knowledge_sync",
            "handler": self._run_knowledge_sync,
            "type": "interval",
            "interval_minutes": 60,
        })
        self._jobs.append({
            "name": "archive_tasks",
            "handler": self._run_task_archiver,
            "type": "interval",
            "interval_minutes": 5,
        })

        logger.info("Scheduler: %d jobs loaded", len(self._jobs))

    def _parse_schedule(self, name: str, raw: str) -> Optional[dict]:
        """Parse a schedule string into a job definition.

        Recognises formats: 'hourly', 'daily_08:00', 'friday_18:00',
        'weekly_monday_09:00', 'first_monday_09:00'.
        """
        s = str(raw).lower().strip() if not isinstance(raw, str) else raw.lower().strip()
        if not s:
            return None

        if s == "hourly":
            return {"name": name, "handler": self._resolve_handler(name),
                    "type": "interval", "interval_minutes": 60}

        if s.startswith("daily_"):
            t = s.split("_", 1)[1] if "_" in s else "08:00"
            return {"name": name, "handler": self._resolve_handler(name),
                    "type": "daily", "time": t}

        if s.startswith("first_monday_"):
            t = s.split("_", 2)[2] if "_" in s else "09:00"
            return {"name": name, "handler": self._resolve_handler(name),
                    "type": "first_monday", "time": t}

        if s.startswith("weekly_"):
            parts = s.split("_")
            day = parts[1] if len(parts) > 1 else "monday"
            t = parts[2] if len(parts) > 2 else "09:00"
            return {"name": name, "handler": self._resolve_handler(name),
                    "type": "weekly", "day": day, "time": t}

        if "_" in s:
            parts = s.split("_")
            if len(parts) == 2 and parts[1].count(":") == 1:
                return {"name": name, "handler": self._resolve_handler(name),
                        "type": "weekly", "day": parts[0], "time": parts[1]}

        return None

    def _resolve_handler(self, name: str):
        mapping = {
            "insight_generation": self._run_insight_generation,
            "habit_sync": self._run_habit_sync,
            "self_analysis": self._run_self_analysis,
            "daily_digest": self._run_daily_digest,
            "weekly_review": self._run_weekly_review,
            "monthly_analysis": self._run_monthly_analysis,
        }
        return mapping.get(name, self._run_generic)

    # ── Scheduling logic ──────────────────────────────────────────────

    def _should_run(self, job: dict) -> bool:
        now = datetime.now()
        last = self._last_run.get(job["name"])

        if job["type"] == "interval":
            if last is None:
                return True
            elapsed = (now - last).total_seconds() / 60
            return elapsed >= job["interval_minutes"]

        if job["type"] == "daily":
            if last is not None and last.date() == now.date():
                return False
            want_h, want_m = job["time"].split(":")
            return now.hour == int(want_h) and now.minute == int(want_m)

        if job["type"] == "weekly":
            days = ["monday", "tuesday", "wednesday", "thursday",
                    "friday", "saturday", "sunday"]
            if now.strftime("%A").lower() != job["day"].lower():
                return False
            if last is not None and last.date() == now.date():
                return False
            want_h, want_m = job["time"].split(":")
            return now.hour == int(want_h) and now.minute == int(want_m)

        if job["type"] == "first_monday":
            if now.day > 7 or now.strftime("%A").lower() != "monday":
                return False
            if last is not None and last.month == now.month:
                return False
            want_h, want_m = job["time"].split(":")
            return now.hour == int(want_h) and now.minute == int(want_m)

        return False

    def _run_job(self, job: dict):
        try:
            logger.info("Scheduler: running '%s'", job["name"])
            job["handler"]()
            self._last_run[job["name"]] = datetime.now()
            logger.info("Scheduler: '%s' done", job["name"])
        except Exception as e:
            logger.error("Scheduler: '%s' failed: %s", job["name"], e)

    # ── Job handlers ──────────────────────────────────────────────────

    def _run_daily_digest(self):
        eng = self._engine
        if hasattr(eng, "daily_digest"):
            eng.daily_digest()

    def _run_weekly_review(self):
        eng = self._engine
        if hasattr(eng, "weekly_review"):
            eng.weekly_review()

    def _run_insight_generation(self):
        eng = self._engine
        if hasattr(eng, "send"):
            eng.send("insight-generator", "analyse_habits", {"days": 7})

    def _run_self_analysis(self):
        eng = self._engine
        if hasattr(eng, "pattern_infer"):
            eng.pattern_infer()

    def _run_pattern_inference(self):
        eng = self._engine
        if hasattr(eng, "pattern_infer"):
            eng.pattern_infer()

    def _run_habit_sync(self):
        logger.debug("Habit sync check completed")

    def _run_self_sync(self):
        """Sync self/ directory files into self.db (profile, habits, goals, etc.)."""
        try:
            from sync.sync_self import sync_all
            result = sync_all()
            logger.info(
                "self_sync done — profile:%s habits:%s goals:%s rel:%s traits:%s needs:%s docs:%s",
                result.get("profile", "?"),
                result.get("habits", "?"),
                result.get("goals", "?"),
                result.get("relationships", "?"),
                result.get("traits", "?"),
                result.get("needs", "?"),
                result.get("documents", "?"),
            )
        except ImportError:
            logger.warning("sync_self module not available, skipping")
        except Exception as e:
            logger.warning("self_sync failed: %s", e)

    def _run_task_archiver(self):
        """Move completed/cancelled tasks from tasks → task_archive every 5 minutes."""
        try:
            from db.tasks.migrate_schema_v3 import archive_completed_tasks
            moved = archive_completed_tasks()
            if moved:
                logger.info("task_archiver: archived %d completed task(s)", moved)
        except Exception as e:
            logger.warning("task_archiver failed: %s", e)

    def _run_knowledge_sync(self):
        """Sync knowledge/ directory files into knowledge.db."""
        try:
            from sync.sync_knowledge import sync_all
            result = sync_all()
            logger.info(
                "knowledge_sync done — articles:%s notes:%s",
                result.get("articles", "?"),
                result.get("notes", "?"),
            )
        except ImportError:
            logger.warning("sync_knowledge module not available, skipping")
        except Exception as e:
            logger.warning("knowledge_sync failed: %s", e)

    def _run_monthly_analysis(self):
        logger.info("Monthly analysis triggered (placeholder)")

    def _run_generic(self):
        logger.debug("Generic job handler called (no specific handler)")

    def _poll_apple_bridge(self, bridge_name: str, args: list,
                           obs_type: str) -> None:
        """Call an apple-bridge CLI tool and store output as observations."""
        bridge = Path.home() / ".claude" / bridge_name
        if not bridge.exists():
            logger.debug("%s not found, skipping poll", bridge_name)
            return
        try:
            import subprocess as _sp
            result = _sp.run(
                [str(bridge)] + args, capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0 or not result.stdout.strip():
                return
            for line in result.stdout.strip().split("\n"):
                line = line.strip()
                if not line:
                    continue
                eng = self._engine
                if hasattr(eng, "_hub"):
                    eng._hub.store_observation(
                        obs_type, {"raw": line, "bridge": bridge_name},
                        source="apple_bridge",
                    )
            logger.debug("%s: %d lines observed", bridge_name,
                         len(result.stdout.strip().split("\n")))
        except FileNotFoundError:
            logger.debug("%s not installed", bridge_name)
        except Exception as e:
            logger.warning("%s poll failed: %s", bridge_name, e)

    def _run_apple_calendar_poll(self):
        """Sync Apple Calendar events into calendar.db via sync_calendar.py."""
        import subprocess as _sp
        sync_script = Path(__file__).resolve().parent.parent / "sync" / "sync_calendar.py"
        if not sync_script.exists():
            logger.warning("sync_calendar.py not found at %s", sync_script)
            return
        try:
            result = _sp.run(
                [sys.executable, str(sync_script), "--quick"],
                capture_output=True, text=True, timeout=60,
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    if line.strip():
                        logger.info("[sync_calendar] %s", line.strip())
                logger.info("Apple Calendar sync completed")
            else:
                logger.warning("Apple Calendar sync failed (rc=%d): %s",
                               result.returncode, result.stderr.strip()[:300])
        except Exception as e:
            logger.warning("Apple Calendar sync error: %s", e)

    def _run_apple_reminders_poll(self):
        """Run full bidirectional sync between Apple Reminders and tasks.db."""
        import subprocess as _sp
        sync_script = Path(__file__).resolve().parent.parent / "sync" / "sync_reminders.py"
        if not sync_script.exists():
            logger.warning("sync_reminders.py not found at %s", sync_script)
            return
        try:
            result = _sp.run(
                [sys.executable, str(sync_script)],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    if line.strip():
                        logger.info("[sync_reminders] %s", line.strip())
                logger.info("Apple Reminders sync completed")
            else:
                logger.warning("Apple Reminders sync failed (rc=%d): %s",
                               result.returncode, result.stderr.strip()[:300])
        except Exception as e:
            logger.warning("Apple Reminders sync error: %s", e)

    # ── Lifecycle ─────────────────────────────────────────────────────

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True,
                                        name="engine-scheduler")
        self._thread.start()
        logger.info("Scheduler started")

    def stop(self):
        self._running = False
        logger.info("Scheduler stopping")

    def _loop(self):
        logger.info("Scheduler loop started (tick: 30s)")
        while self._running:
            try:
                for job in self._jobs:
                    if self._should_run(job):
                        self._run_job(job)
                time.sleep(30)
            except Exception as e:
                logger.error("Scheduler loop error: %s", e)
                time.sleep(30)

    def get_status(self) -> dict:
        return {
            "running": self._running,
            "jobs_loaded": len(self._jobs),
            "jobs": [
                {
                    "name": j["name"],
                    "type": j.get("type", "?"),
                    "last_run": str(self._last_run.get(j["name"], "")),
                }
                for j in self._jobs
            ],
        }
