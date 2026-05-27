"""Tests for behavior_vocab extraction module."""
import pytest
from extractors.behavior_vocab import (
    extract_emotions, extract_activities,
    _detect_negation, _capture_context,
    ALL_EMOTIONS, EMOTION_WORDS, ACTIVITY_WORDS,
)


class TestExtractEmotions:
    def test_rejects_noise_words_after_feel(self):
        """Stops noise words like 'about', 'the', 'that' from being captured."""
        result = extract_emotions("I feel about the that")
        assert result == []

    def test_captures_valid_emotion_after_feel(self):
        result = extract_emotions("I feel anxious")
        assert len(result) == 1
        assert result[0]['word'] == 'anxious'
        assert result[0]['category'] == 'fear'
        assert result[0]['negated'] is False
        assert result[0]['context'] == 'I feel'

    def test_captures_multiple_emotions(self):
        result = extract_emotions("I feel anxious and sad")
        words = [r['word'] for r in result]
        assert 'anxious' in words
        assert 'sad' in words

    def test_detects_negation(self):
        """I don't feel happy marks happy as negated."""
        result = extract_emotions("I don't feel happy")
        happy = next((r for r in result if r['word'] == 'happy'), None)
        if happy:
            assert happy['negated'] is True
        else:
            for r in result:
                if r['word'] == 'happy':
                    assert r['negated'] is True
                    break

    def test_direct_keyword_match(self):
        result = extract_emotions("I'm very tired today")
        tired = next((r for r in result if r['word'] == 'tired'), None)
        assert tired is not None
        assert tired['category'] == 'energy'

    def test_word_boundary_prevents_false_match(self):
        result = extract_emotions("I take antidepressant medication")
        assert all(r['word'] != 'depressed' for r in result)

    def test_empty_text_returns_empty_list(self):
        assert extract_emotions("") == []

    def test_no_emotion_in_text_returns_empty(self):
        assert extract_emotions("I went to the store and bought milk") == []

    def test_context_captures_trigger_words(self):
        result = extract_emotions("Today I feel happy about the news")
        happy = next(r for r in result if r['word'] == 'happy')
        assert 'feel' in happy['context']

    def test_fallback_trigger_when_no_context(self):
        result = extract_emotions("Happy today")
        happy = next(r for r in result if r['word'] == 'happy')
        assert happy['context'] != ''


class TestExtractActivities:
    def test_captures_activity_words(self):
        result = extract_activities("I studied yesterday and worked today")
        words = [r['word'] for r in result]
        assert 'studied' in words
        assert 'worked' in words

    def test_no_greedy_capture(self):
        """'read' alone, not 'read it today and worked on'."""
        result = extract_activities("I read it today and worked on")
        words = [r['word'] for r in result]
        assert 'read' in words
        assert 'worked' in words
        for r in result:
            assert ' ' not in r['word']

    def test_word_boundary_prevents_substring_match(self):
        """'coded' inside 'encoded' should not match due to \\b boundaries."""
        result = extract_activities("I encoded the data")
        assert all(r['word'] != 'coded' for r in result)

    def test_empty_text_returns_empty(self):
        assert extract_activities("") == []

    def test_no_activity_returns_empty(self):
        assert extract_activities("I ate lunch and watched TV") == []

    def test_activity_returns_dicts_with_context(self):
        result = extract_activities("Yesterday I studied for the exam")
        studied = next((r for r in result if r['word'] == 'studied'), None)
        assert studied is not None
        assert 'context' in studied
        assert studied['context'] != ''


class TestNegationDetection:
    def test_not_immediately_before(self):
        assert _detect_negation("not happy today", 4, "happy") is True

    def test_never_before(self):
        assert _detect_negation("never felt happy", 11, "happy") is True

    def test_contraction_negation(self):
        assert _detect_negation("don't feel happy", 11, "happy") is True

    def test_no_negation(self):
        assert _detect_negation("feel very happy", 10, "happy") is False

    def test_negation_within_window(self):
        """3 intermediate words between 'not' and 'happy' is within 4-word window."""
        assert _detect_negation("I definitely was not really very extremely happy", 43, "happy") is True

    def test_negation_too_far(self):
        """4 intermediate words between 'not' and 'happy' exceeds 4-word window."""
        assert _detect_negation("I was not really very extremely unbelievably happy", 45, "happy") is False

    def test_empty_before_text(self):
        assert _detect_negation("happy", 0, "happy") is False

    def test_wasnt_contraction(self):
        assert _detect_negation("I wasn't happy at all", 9, "happy") is True


class TestContextCapture:
    def test_full_context_window(self):
        result = _capture_context("Today I was feeling happy", 21, 5)
        words = result.split()
        assert len(words) <= 5

    def test_no_context_returns_daily_note(self):
        assert _capture_context("", 0, 5) == 'daily_note'

    def test_single_word_context(self):
        result = _capture_context("really happy", 7, 5)
        assert result == 'really'


class TestVocabIntegrity:
    def test_all_emotions_have_categories(self):
        for word in ALL_EMOTIONS:
            found = False
            for cat, words in EMOTION_WORDS.items():
                if word in words:
                    found = True
                    break
            assert found, f"{word} has no category"

    def test_no_duplicate_emotions(self):
        all_words = []
        for words in EMOTION_WORDS.values():
            all_words.extend(words)
        assert len(all_words) == len(set(all_words)), "Duplicate emotion words found"

    def test_no_duplicate_activities(self):
        assert len(ACTIVITY_WORDS) == len(set(ACTIVITY_WORDS)), "Duplicate activity words found"
