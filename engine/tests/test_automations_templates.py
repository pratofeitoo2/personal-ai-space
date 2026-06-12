"""Tests for automations/templates.py"""
from datetime import datetime
from unittest.mock import patch
import pytest

from automations.templates import (
    format_section, build_brief_message, generate_greeting, generate_opener,
)


class TestFormatSection:
    def test_returns_formatted_with_items(self):
        result = format_section(["item 1", "item 2"], "📋 Lista")
        assert result is not None
        assert "📋 Lista" in result
        assert "• item 1" in result
        assert "• item 2" in result

    def test_returns_empty_msg_when_no_items(self):
        result = format_section([], "📋 Lista", empty_msg="Nada aqui")
        assert result == "Nada aqui"

    def test_returns_none_when_no_items_and_no_empty_msg(self):
        result = format_section([], "📋 Lista")
        assert result is None

    def test_formats_single_item(self):
        result = format_section(["only one"], "📋 Lista")
        assert "• only one" in result


class TestBuildBriefMessage:
    def test_joins_sections_with_double_newline(self):
        sections = [
            {"formatted": "Section 1", "items": []},
            {"formatted": "Section 2", "items": ["a"]},
        ]
        result = build_brief_message(sections)
        assert result == "Section 1\n\nSection 2"

    def test_skips_empty_formatted(self):
        sections = [
            {"formatted": "", "items": []},
            {"formatted": "Only this", "items": ["x"]},
        ]
        result = build_brief_message(sections)
        assert result == "Only this"

    def test_returns_empty_string_for_no_sections(self):
        assert build_brief_message([]) == ""

    def test_returns_empty_string_if_all_empty(self):
        sections = [{"formatted": "", "items": []}, {"formatted": "", "items": []}]
        assert build_brief_message(sections) == ""


class TestGenerateGreeting:
    def test_morning_before_12(self):
        with patch("automations.templates.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 5, 29, 7, 0, 0)
            assert "Bom dia" in generate_greeting()

    def test_afternoon_12_to_18(self):
        with patch("automations.templates.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 5, 29, 14, 0, 0)
            assert "Boa tarde" in generate_greeting()

    def test_night_after_18(self):
        with patch("automations.templates.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 5, 29, 20, 0, 0)
            assert "Boa noite" in generate_greeting()


class TestGenerateOpener:
    def test_returns_text_when_bridge_available(self):
        with patch("automations.templates.enrich_digest_opener") as mock_bridge:
            mock_bridge.return_value = "Bom dia! Você tem 3 tarefas hoje."
            result = generate_opener(3, 1, 2, 5)
            assert result == "Bom dia! Você tem 3 tarefas hoje."
            mock_bridge.assert_called_once_with(3, 1, 2, 5)

    def test_returns_none_when_bridge_offline(self):
        with patch("automations.templates.enrich_digest_opener") as mock_bridge:
            mock_bridge.return_value = None
            result = generate_opener(0, 0, 0, 0)
            assert result is None

    def test_handles_exception_gracefully(self):
        with patch("automations.templates.enrich_digest_opener") as mock_bridge:
            mock_bridge.side_effect = RuntimeError("Ollama not responding")
            result = generate_opener(0, 0, 0, 0)
            assert result is None
