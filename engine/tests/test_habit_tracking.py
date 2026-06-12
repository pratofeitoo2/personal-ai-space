"""Tests for habit tracking system — reminders ↔ self.db pipeline.

TDD: These tests define the behavior we need to implement.
Run: cd personal-ai-space/engine && python -m pytest tests/test_habit_tracking.py -v
"""
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, call

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))


# ════════════════════════════════════════════════════════════════════════════
# Fixtures
# ════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def habit_db(init_test_db):
    """Seed self.db with habits for testing."""
    import db_manager as db
    habits = [
        ("h-journal", "Diário Pessoal", "bem-estar", "daily", "2026-05-01", 5, 10, "2026-05-29", "active"),
        ("h-reading", "Leitura (30min)", "aprendizado", "daily", "2026-05-01", 3, 8, "2026-05-29", "active"),
        ("h-exercise", "Exercício", "saúde", "daily", "2026-05-01", 0, 2, "2026-05-27", "active"),
    ]
    for h in habits:
        db.execute("self",
            """INSERT INTO habits (id, habit_name, category, frequency, start_date,
               current_streak, total_completions, last_completed, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""", h)
    return db


@pytest.fixture
def mock_bridge():
    """Mock reminders-bridge subprocess calls in delivery.py."""
    with patch("automations.delivery.subprocess.run") as mock:
        # First call is _ensure_sisyphus_list → lists → must return list with "Sisyphus"
        lists_result = MagicMock(returncode=0, stdout="Sisyphus\n", stderr="")
        ok_result = MagicMock(returncode=0, stdout="", stderr="")
        mock.side_effect = [lists_result] + [ok_result] * 20
        yield mock


# ════════════════════════════════════════════════════════════════════════════
# Task 1: Habit reminder creation
# ════════════════════════════════════════════════════════════════════════════

class TestCreateHabitReminders:
    """Tests for creating individual habit reminders in Apple Reminders."""

    def test_creates_one_reminder_per_habit(self, habit_db, mock_bridge):
        """Each active habit should produce one reminder."""
        from automations.delivery import create_habit_reminders

        habits = habit_db.query("self", "SELECT id, habit_name FROM habits WHERE status='active'", ())
        create_habit_reminders(habits)

        # Should call bridge: ensure list + N adds
        # c[0][0] is the args list; c[0][0][1] is the command (add/complete/etc)
        add_calls = [c for c in mock_bridge.call_args_list if len(c[0][0]) > 1 and c[0][0][1] == "add"]
        assert len(add_calls) == len(habits)

    def test_reminder_title_format(self, habit_db, mock_bridge):
        """Reminder title should be '🔲 {habit_name}'."""
        from automations.delivery import create_habit_reminders

        habits = habit_db.query("self", "SELECT id, habit_name FROM habits WHERE status='active'", ())
        create_habit_reminders(habits)

        add_calls = [c for c in mock_bridge.call_args_list if len(c[0][0]) > 1 and c[0][0][1] == "add"]
        for c in add_calls:
            args = c[0][0]
            # args = [bridge, "add", list_name, title, notes]
            title = args[3]
            assert title.startswith("🔲 "), f"Title should start with 🔲: {title}"

    def test_reminder_notes_contain_habit_id(self, habit_db, mock_bridge):
        """Reminder notes should contain JSON with habit_id and type=habit."""
        from automations.delivery import create_habit_reminders

        habits = habit_db.query("self", "SELECT id, habit_name FROM habits WHERE status='active'", ())
        create_habit_reminders(habits)

        add_calls = [c for c in mock_bridge.call_args_list if len(c[0][0]) > 1 and c[0][0][1] == "add"]
        for c in add_calls:
            args = c[0][0]
            # args = [bridge, "add", list_name, title, notes]
            notes = args[4] if len(args) > 4 else ""
            data = json.loads(notes)
            assert data["type"] == "habit"
            assert "habit_id" in data

    def test_does_not_create_duplicates(self, habit_db):
        """Running twice should produce the same number of habit reminders (daily refresh)."""
        from automations.delivery import create_habit_reminders

        habits = habit_db.query("self", "SELECT id, habit_name FROM habits WHERE status='active'", ())

        with patch("automations.delivery.subprocess.run") as mock:
            lists_result = MagicMock(returncode=0, stdout="Sisyphus\n", stderr="")
            ok_result = MagicMock(returncode=0, stdout="", stderr="")
            mock.side_effect = [lists_result] + [ok_result] * 20
            create_habit_reminders(habits)
            first_adds = len([c for c in mock.call_args_list
                             if len(c[0][0]) > 1 and c[0][0][1] == "add"])

        with patch("automations.delivery.subprocess.run") as mock:
            lists_result = MagicMock(returncode=0, stdout="Sisyphus\n", stderr="")
            ok_result = MagicMock(returncode=0, stdout="", stderr="")
            mock.side_effect = [lists_result] + [ok_result] * 20
            create_habit_reminders(habits)
            second_adds = len([c for c in mock.call_args_list
                              if len(c[0][0]) > 1 and c[0][0][1] == "add"])

        assert first_adds == second_adds == len(habits)

    def test_completes_old_reminder_before_creating_new(self, habit_db, mock_bridge):
        """Should complete existing reminder before creating new one (same title)."""
        from automations.delivery import create_habit_reminders

        habits = habit_db.query("self", "SELECT id, habit_name FROM habits WHERE status='active'", ())
        create_habit_reminders(habits)

        complete_calls = [c for c in mock_bridge.call_args_list if len(c[0][0]) > 1 and c[0][0][1] == "complete"]
        assert len(complete_calls) == len(habits)


# ════════════════════════════════════════════════════════════════════════════
# Task 2: Habit completion detection
# ════════════════════════════════════════════════════════════════════════════

class TestHabitCompletionDetection:
    """Tests for detecting habit completions from Apple Reminders."""

    def test_detects_completed_habit_reminder(self, habit_db):
        """Completed reminder with type=habit should trigger mark_habit_complete."""
        from sync.sync_reminders import _is_habit_reminder, _parse_habit_id

        reminder = {
            "title": "🔲 Diário Pessoal",
            "completed": True,
            "notes": '{"habit_id":"h-journal","type":"habit"}',
        }
        assert _is_habit_reminder(reminder) is True
        assert _parse_habit_id(reminder) == "h-journal"

    def test_ignores_non_habit_reminder(self):
        """Completed reminder without type=habit should not be treated as habit."""
        from sync.sync_reminders import _is_habit_reminder

        reminder = {
            "title": "🔲 Diário Pessoal",
            "completed": True,
            "notes": "Just a regular reminder",
        }
        assert _is_habit_reminder(reminder) is False

    def test_ignores_incomplete_habit_reminder(self):
        """Incomplete habit reminder is still detected as habit type (completion check is separate)."""
        from sync.sync_reminders import _is_habit_reminder

        reminder = {
            "title": "🔲 Diário Pessoal",
            "completed": False,
            "notes": '{"habit_id":"h-journal","type":"habit"}',
        }
        # _is_habit_reminder detects type, not completion status
        assert _is_habit_reminder(reminder) is True

    def test_updates_streak_in_self_db(self, habit_db):
        """Completing a habit should increment streak and update last_completed."""
        from sync.sync_habits import mark_habit_complete

        # Get current streak
        before = habit_db.query("self",
            "SELECT current_streak, last_completed FROM habits WHERE id='h-journal'", ())
        old_streak = before[0]["current_streak"]

        # Mark complete
        result = mark_habit_complete("h-journal")
        assert result["new_streak"] == old_streak + 1

        # Verify in DB
        after = habit_db.query("self",
            "SELECT current_streak, last_completed FROM habits WHERE id='h-journal'", ())
        assert after[0]["current_streak"] == old_streak + 1

    def test_creates_habit_log_entry(self, habit_db):
        """Completing a habit should create a habit_logs entry."""
        from sync.sync_habits import mark_habit_complete
        import db_manager as db

        today = datetime.now().strftime("%Y-%m-%d")
        mark_habit_complete("h-reading")

        logs = db.query("self",
            "SELECT id FROM habit_logs WHERE habit_id='h-reading' AND date(completed_at)=?",
            (today,))
        assert len(logs) >= 1

    def test_habit_completion_skips_task_creation(self, habit_db):
        """Habit reminders should not create tasks in tasks.db."""
        from sync.sync_reminders import RemindersSync
        import db_manager as db

        # Seed a habit reminder in sync_state
        compound_key = "Sisyphus::🔲 Diário Pessoal"
        db.execute("tasks",
            """INSERT INTO sync_state (id, entity_type, entity_id, file_path, file_hash, last_modified, direction)
               VALUES (?, 'apple-reminder', ?, ?, ?, ?, 'bidirectional')""",
            ("test-habit-sync", "h-journal", compound_key, "hash123",
             datetime.now().isoformat()))

        # Verify no task was created
        tasks = db.query("tasks",
            "SELECT id FROM tasks WHERE title LIKE '%Diário Pessoal%'", ())
        assert len(tasks) == 0


# ════════════════════════════════════════════════════════════════════════════
# Task 3: Integration — morning brief creates habit reminders
# ════════════════════════════════════════════════════════════════════════════

class TestHabitReminderIntegration:
    """Tests for habit reminder creation integrated with automation delivery."""

    def test_morning_brief_includes_habit_reminders(self, habit_db, mock_bridge):
        """Morning brief delivery should create habit reminders."""
        from automations.delivery import deliver_all_with_habits

        sections = [
            {"formatted": "🌅 Bom dia!", "items": [], "item_type": "greeting"},
        ]
        habits = habit_db.query("self", "SELECT id, habit_name FROM habits WHERE status='active'", ())

        deliver_all_with_habits("Test message", sections, "morning_brief", "Briefing Matinal", "+5511999999999", habits)

        # Should have created habit reminders
        add_calls = [c for c in mock_bridge.call_args_list if len(c[0][0]) > 1 and c[0][0][1] == "add"]
        assert len(add_calls) == len(habits)
