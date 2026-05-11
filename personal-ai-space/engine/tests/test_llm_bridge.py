import pytest


class TestIntentClassifierFuzzy:
    """Test fuzzy-matching fallback (no Ollama needed)."""

    def make_classifier(self):
        from llm_bridge import IntentClassifier
        c = IntentClassifier()
        c._ollama_available = False
        return c

    def test_classify_digest(self):
        c = self.make_classifier()
        r = c.classify("show me the daily digest")
        assert r.intent is not None
        assert r.intent.command == "daily_digest"
        assert r.confidence > 0.3

    def test_classify_today_tasks(self):
        c = self.make_classifier()
        r = c.classify("what should I do today")
        assert r.intent is not None
        assert r.intent.command == "get_today"
        assert r.confidence > 0.3

    def test_classify_create_task(self):
        c = self.make_classifier()
        r = c.classify("remind me to buy groceries")
        assert r.intent is not None
        assert r.intent.command == "create_task"
        assert r.confidence > 0.3

    def test_classify_search(self):
        c = self.make_classifier()
        r = c.classify("find notes about python")
        assert r.intent is not None
        assert r.intent.command == "search"
        assert r.confidence > 0.3

    def test_classify_habit_insights(self):
        c = self.make_classifier()
        r = c.classify("how are my habits")
        assert r.intent is not None
        assert r.intent.command == "analyse_habits"

    def test_classify_weekly_review(self):
        c = self.make_classifier()
        r = c.classify("how was my week")
        assert r.intent is not None
        assert r.intent.command == "weekly_review"

    def test_classify_mcp_tools(self):
        c = self.make_classifier()
        r = c.classify("what can you do")
        assert r.intent is not None
        assert r.intent.command == "mcp_tools"

    def test_empty_text_returns_none(self):
        c = self.make_classifier()
        r = c.classify("")
        assert r.intent is None
        assert r.confidence == 0.0

    def test_gibberish_low_confidence(self):
        c = self.make_classifier()
        r = c.classify("asdfzxcv qwerty 12345")
        assert r.confidence < 0.4

    def test_alternatives_populated(self):
        c = self.make_classifier()
        r = c.classify("show my tasks")
        assert r.intent is not None
        assert len(r.alternatives) > 0

    def test_extract_params_task_title_with_to(self):
        c = self.make_classifier()
        r = c.classify("remind me to submit the report")
        if r.intent and r.intent.command == "create_task":
            params = r.extracted_params
            if "title" in params:
                assert "submit the report" in params["title"]

    def test_extract_params_task_title_with_that(self):
        c = self.make_classifier()
        r = c.classify("add a task that I need to call dentist")
        if r.intent and r.intent.command == "create_task":
            params = r.extracted_params
            if "title" in params:
                assert "call dentist" in params["title"]

    def test_extract_priority_urgent(self):
        c = self.make_classifier()
        r = c.classify("add urgent task to fix bug")
        if r.intent and r.intent.command == "create_task":
            assert r.extracted_params.get("priority") == "critical"

    def test_extract_search_query(self):
        c = self.make_classifier()
        r = c.classify("search for machine learning papers")
        if r.intent and r.intent.command == "search":
            assert "machine learning" in r.extracted_params.get("query", "")

    def test_intent_catalogue_has_all_fields(self):
        from llm_bridge import INTENT_CATALOGUE
        for intent in INTENT_CATALOGUE:
            assert intent.agent, f"Missing agent in {intent.description}"
            assert intent.command, f"Missing command in {intent.description}"
            assert intent.description, f"Missing description"
            assert len(intent.example_phrases) > 0, f"No examples for {intent.description}"


class TestTextGenerator:
    def test_unavailable_model_returns_error(self):
        from llm_bridge import TextGenerator
        gen = TextGenerator(model="nonexistent-model-xyz")
        result = gen.generate("test prompt", max_tokens=10)
        assert result.success is False


class TestCheckOllama:
    def test_returns_expected_structure(self):
        from llm_bridge import check_ollama
        status = check_ollama()
        assert "available" in status
        assert "models" in status
        assert isinstance(status["models"], list)
