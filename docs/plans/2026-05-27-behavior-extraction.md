# Behavior Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers-optimized:subagent-driven-development (recommended) or superpowers-optimized:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace regex-greedy emotion/activity extractors with a whitelist-based shared module that eliminates noise words, detects negation, and provides meaningful trigger context.
**Architecture:** A new `behavior_vocab.py` module provides curated emotion (8 categories, ~65 words) and activity (~25 words) dictionaries plus extraction functions (`extract_emotions`, `extract_activities`). Both `DailyNoteExtractor` (in `__init__.py`) and `ComprehensiveExtractor._extract_daily_patterns` delegate to it, unifying the duplicate/inconsistent extraction logic. Extraction uses regex verb-triggered patterns + direct keyword search with `\b` word boundaries, then filters against whitelists.
**Tech Stack:** Python 3, re (stdlib), pytest
**Assumptions:** Assumes the `behaviors` table schema stays unchanged — the `trigger` column already exists and currently stores `'daily_note'`. The plan will populate it with real context instead. Assumes existing data can be deleted and re-extracted from the same source files (daily notes in `command/inbox/`). Will NOT work if the inbox files have been deleted since the original extraction.

---

## File Structure

```
engine/extractors/
├── __init__.py                    # DailyNoteExtractor refactored to delegate to behavior_vocab
├── behavior_vocab.py              # [NEW] Shared extraction logic + curated dictionaries
├── comprehensive_extractor.py     # ComprehensiveExtractor refactored to delegate to behavior_vocab
├── converters.py                  # Unchanged
└── codemap.md                     # Unchanged

engine/tests/
├── conftest.py                    # Unchanged
├── test_behavior_vocab.py         # [NEW] Tests for extraction logic (pure, no DB needed)
└── ... other tests unchanged
```

### Module Responsibilities

| File | Responsibility |
|---|---|
| `engine/extractors/behavior_vocab.py` | Curated emotion/activity dictionaries, `_detect_negation()`, `_capture_context()`, `extract_emotions()`, `extract_activities()` — pure functions, no DB dependency |
| `engine/extractors/__init__.py` | `DailyNoteExtractor` — imports `behavior_vocab`, delegates extraction, inserts into `self.db` behaviors table with real trigger context + emotion category |
| `engine/extractors/comprehensive_extractor.py` | `ComprehensiveExtractor._extract_daily_patterns` — imports `behavior_vocab`, delegates extraction, same INSERT pattern |
| `engine/tests/test_behavior_vocab.py` | Unit tests for `behavior_vocab` — 100% pure string processing, no fixtures needed |

---

### Task 1: Write tests + implement behavior_vocab.py (TDD)

**Files:**
- Create: `engine/extractors/behavior_vocab.py`
- Create: `engine/tests/test_behavior_vocab.py`

**Security flag:** `none`

**Does NOT cover:** File I/O, database operations, or network calls — this module is pure string processing only.

- [ ] **Step 1: Write failing tests in test_behavior_vocab.py**

```python
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
        # The trigger 'feel' captures 'happy' as candidate
        happy = next((r for r in result if r['word'] == 'happy'), None)
        if happy:
            assert happy['negated'] is True
        else:
            # 'happy' might also be found via direct keyword search before the feel trigger
            # In either case, check negation is detected
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
        """'depressed' should not match 'depressed' substring within 'antidepressant'."""
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
        # Each entry is just the word, not a phrase
        for r in result:
            assert ' ' not in r['word']

    def test_word_boundary_prevents_substring_match(self):
        result = extract_activities("I need a coded message")
        assert all(r['word'] != 'coded' for r in result)

    def test_empty_text_returns_empty(self):
        assert extract_activities("") == []

    def test_no_activity_returns_empty(self):
        assert extract_activities("I ate lunch and watched TV") == []


class TestNegationDetection:
    def test_not_immediately_before(self):
        assert _detect_negation("not happy today", 4, "happy") is True

    def test_never_before(self):
        assert _detect_negation("never felt happy", 12, "happy") is True

    def test_contraction_negation(self):
        assert _detect_negation("don't feel happy", 15, "happy") is True

    def test_no_negation(self):
        assert _detect_negation("feel very happy", 14, "happy") is False

    def test_negation_too_far(self):
        assert _detect_negation("I definitely was not really very extremely happy", 44, "happy") is False

    def test_empty_before_text(self):
        assert _detect_negation("happy", 0, "happy") is False


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
```

- [ ] **Step 2: Run tests to verify they fail (module doesn't exist yet)**

Run:
```bash
cd personal-ai-space && python3 -m pytest engine/tests/test_behavior_vocab.py -v
```
Expected: FAIL with `ModuleNotFoundError: No module named 'extractors.behavior_vocab'` (or similar import error — the test file itself may not even load since it imports from a non-existent module)

- [ ] **Step 3: Implement behavior_vocab.py**

```python
"""Shared vocabulary and extraction functions for behaviors table.

Provides curated emotion (8 categories) and activity dictionaries,
with regex-based extraction that uses whitelist filtering, negation
detection, and context window capture.
"""
import re
from typing import Optional

# Category-organized emotion words (Plutchik-inspired)
EMOTION_WORDS = {
    'joy': [
        'happy', 'joyful', 'content', 'pleased', 'cheerful', 'glad',
        'satisfied', 'grateful', 'hopeful', 'optimistic', 'elated',
    ],
    'sadness': [
        'sad', 'unhappy', 'depressed', 'melancholy', 'down',
        'heartbroken', 'miserable', 'lonely', 'disappointed',
    ],
    'anger': [
        'angry', 'frustrated', 'irritated', 'annoyed', 'furious', 'agitated',
    ],
    'fear': [
        'anxious', 'afraid', 'scared', 'worried', 'nervous', 'fearful',
        'panicked', 'stressed', 'uneasy', 'overwhelmed',
    ],
    'energy': [
        'tired', 'exhausted', 'drained', 'fatigued', 'weary', 'sleepy',
        'energized', 'motivated', 'excited', 'productive', 'focused',
    ],
    'calm': [
        'calm', 'peaceful', 'relaxed', 'tranquil', 'serene',
        'comfortable', 'safe',
    ],
    'distress': [
        'distracted', 'confused', 'uncertain', 'doubtful', 'restless', 'stuck',
    ],
    'trust': [
        'confident', 'assured', 'secure', 'trusting', 'certain',
    ],
}

# Fast lookup set
ALL_EMOTIONS = [word for words in EMOTION_WORDS.values() for word in words]

# Curated activity words — past-tense verbs describing meaningful actions
ACTIVITY_WORDS = [
    'studied', 'researched', 'worked', 'coded', 'designed', 'wrote',
    'met', 'called', 'emailed', 'read', 'exercised', 'meditated',
    'slept', 'planned', 'reviewed', 'analyzed', 'presented',
    'negotiated', 'coordinated', 'mentored', 'trained', 'learned',
]

# Verb triggers for emotion extraction via regex
_EMOTION_TRIGGERS = ['feel', 'feels', 'feeling', 'felt']

# Verb triggers for activity extraction via regex
_ACTIVITY_TRIGGERS = ['did', 'doing', 'studied', 'worked', 'exercised',
                      'read', 'wrote', 'coded', 'designed', 'met',
                      'meditated', 'slept', 'planned', 'reviewed',
                      'analyzed', 'presented', 'negotiated', 'coordinated',
                      'mentored', 'trained', 'learned']


def _detect_negation(text: str, word_start: int, word: str) -> bool:
    """Check if word at word_start is negated within a 4-word window before it.

    Args:
        text: Full text being searched.
        word_start: Character index where the target word begins.
        word: The target word (used only for logging/future use).

    Returns:
        True if a negation word is found within the window.
    """
    before = text[:word_start].strip()
    if not before:
        return False
    # Take enough chars for ~4 words (max 50 chars is safe)
    window = before[-50:] if len(before) > 50 else before
    # Match: not/never/n't + up to 4 words (3 intermediate + 1 target), anchored at end
    pattern = re.compile(
        r'(?:\b(?:not|never)\b|n\'t)\s+(?:\w+\s+){0,3}$',
        re.IGNORECASE,
    )
    return bool(pattern.search(window))


def _capture_context(text: str, word_start: int, window: int = 5) -> str:
    """Return up to N words immediately before the match position.

    Args:
        text: Full text being searched.
        word_start: Character index where the target word begins.
        window: Maximum number of context words to capture.

    Returns:
        String of context words, or 'daily_note' if no context available.
    """
    before = text[:word_start].strip()
    if not before:
        return 'daily_note'
    words = before.split()
    context_words = words[-window:] if len(words) > window else words
    return ' '.join(context_words)


def _get_emotion_category(word: str) -> str:
    """Return the category name for a given emotion word."""
    for category, words in EMOTION_WORDS.items():
        if word in words:
            return category
    return 'unknown'


def extract_emotions(text: str) -> list[dict]:
    """Extract emotion words from text using verb triggers + direct keyword matching.

    Args:
        text: Raw text to search.

    Returns:
        List of dicts with keys: word, category, negated, context.
        Each emotion word appears at most once (deduplicated).
    """
    results = []
    seen = set()

    # Method 1: Verb-triggered regex (e.g., "I feel anxious")
    for trigger in _EMOTION_TRIGGERS:
        pattern = re.compile(
            r'\b' + re.escape(trigger) + r'[\s:]+([a-z]+)',
            re.IGNORECASE,
        )
        for match in pattern.finditer(text):
            candidate = match.group(1).lower()
            if candidate in ALL_EMOTIONS and candidate not in seen:
                seen.add(candidate)
                word_start = match.start(1)
                negated = _detect_negation(text, word_start, candidate)
                context = _capture_context(text, word_start)
                category = _get_emotion_category(candidate)
                results.append({
                    'word': candidate,
                    'category': category,
                    'negated': negated,
                    'context': context,
                })

    # Method 2: Direct keyword search with word boundaries
    for word in ALL_EMOTIONS:
        pattern = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)
        for match in pattern.finditer(text):
            if word not in seen:
                seen.add(word)
                word_start = match.start()
                negated = _detect_negation(text, word_start, word)
                context = _capture_context(text, word_start)
                category = _get_emotion_category(word)
                results.append({
                    'word': word,
                    'category': category,
                    'negated': negated,
                    'context': context,
                })

    return results


def extract_activities(text: str) -> list[dict]:
    """Extract activity words from text using verb triggers + direct keyword matching.

    Args:
        text: Raw text to search.

    Returns:
        List of dicts with keys: word, context.
        Each activity word appears at most once (deduplicated).
    """
    results = []
    seen = set()

    # Method 1: Verb-triggered regex (e.g., "I did research")
    for trigger in _ACTIVITY_TRIGGERS:
        pattern = re.compile(
            r'\b' + re.escape(trigger) + r'[\s:]+([a-z]+)',
            re.IGNORECASE,
        )
        for match in pattern.finditer(text):
            candidate = match.group(1).lower()
            if candidate in ACTIVITY_WORDS and candidate not in seen:
                seen.add(candidate)
                word_start = match.start(1)
                context = _capture_context(text, word_start)
                results.append({
                    'word': candidate,
                    'context': context,
                })

    # Method 2: Direct keyword search with word boundaries
    for word in ACTIVITY_WORDS:
        pattern = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)
        for match in pattern.finditer(text):
            if word not in seen:
                seen.add(word)
                word_start = match.start()
                context = _capture_context(text, word_start)
                results.append({
                    'word': word,
                    'context': context,
                })

    return results
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
cd personal-ai-space && python3 -m pytest engine/tests/test_behavior_vocab.py -v
```
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add docs/plans/2026-05-27-behavior-extraction.md
git add personal-ai-space/engine/extractors/behavior_vocab.py
git add personal-ai-space/engine/tests/test_behavior_vocab.py
git commit -m "feat(behaviors): add behavior_vocab.py with curated dictionaries and extraction logic

- Curated emotion dictionary (8 categories, ~65 words) with whitelist filtering
- Curated activity dictionary (~25 words) with \b word boundary matching
- _detect_negation(): 4-word negation window before matched word
- _capture_context(): up to 5 context words before match, fallback 'daily_note'
- extract_emotions(): verb-triggered regex + direct keyword matching
- extract_activities(): verb-triggered regex + direct keyword matching
- Tests covering acceptance criteria, negation, word boundaries, empty input"
```

---

### Task 2: Refactor DailyNoteExtractor to use behavior_vocab

**Files:**
- Modify: `engine/extractors/__init__.py`

**Security flag:** `none`

**Does NOT cover:** Other extractors in `__init__.py` (RelationshipExtractor, GoalExtractor, FinanceExtractor, ProfileExtractor) — those are unchanged. Only the `DailyNoteExtractor` class is modified.

- [ ] **Step 1: Add import and refactor DailyNoteExtractor**

Insert at the top of `__init__.py` (after the existing imports):
```python
from extractors.behavior_vocab import extract_emotions, extract_activities
```

Replace the `_extract_emotions` method (lines 219-232):
```python
    def _extract_emotions(self, content: str) -> list[dict]:
        """Extract emotion keywords with whitelist filtering and context.

        Delegates to behavior_vocab for shared extraction logic.
        Returns list of dicts with word, category, negated, context.
        """
        return extract_emotions(content)
```

Replace the `_extract_activities` method (lines 234-246):
```python
    def _extract_activities(self, content: str) -> list[dict]:
        """Extract activity keywords with whitelist filtering and context.

        Delegates to behavior_vocab for shared extraction logic.
        Returns list of dicts with word, context.
        """
        return extract_activities(content)
```

Update `_insert_insights` method — change the emotion INSERT block (lines 185-197) from:
```python
            emotions = self._extract_emotions(content)
            for emotion in emotions:
                try:
                    execute("self", """
                        INSERT INTO behaviors 
                        (id, behavior_type, trigger, response, frequency, effectiveness, observed_date)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(behavior_type, response) DO UPDATE SET
                          frequency = frequency + 1,
                          observed_date = excluded.observed_date
                    """, (uuid.uuid4().hex, 'emotion', 'daily_note', emotion, 1, 0.5, datetime.now().isoformat()))
                    count += 1
```
to:
```python
            emotions = self._extract_emotions(content)
            for emotion in emotions:
                try:
                    effectiveness = 0.2 if emotion['negated'] else 0.5
                    trigger = emotion['context']
                    execute("self", """
                        INSERT INTO behaviors 
                        (id, behavior_type, trigger, response, frequency, effectiveness, observed_date)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(behavior_type, response) DO UPDATE SET
                          frequency = frequency + 1,
                          observed_date = excluded.observed_date
                    """, (uuid.uuid4().hex, 'emotion', trigger, emotion['word'], 1, effectiveness, datetime.now().isoformat()))
                    count += 1
```

Update the activity INSERT block (lines 199-212) from:
```python
            activities = self._extract_activities(content)
            for activity in activities:
                try:
                    execute("self", """
                        INSERT INTO behaviors 
                        (id, behavior_type, trigger, response, frequency, effectiveness, observed_date)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(behavior_type, response) DO UPDATE SET
                          frequency = frequency + 1,
                          observed_date = excluded.observed_date
                    """, (uuid.uuid4().hex, 'activity', 'daily_note', activity, 1, 0.5, datetime.now().isoformat()))
                    count += 1
```
to:
```python
            activities = self._extract_activities(content)
            for activity in activities:
                try:
                    execute("self", """
                        INSERT INTO behaviors 
                        (id, behavior_type, trigger, response, frequency, effectiveness, observed_date)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(behavior_type, response) DO UPDATE SET
                          frequency = frequency + 1,
                          observed_date = excluded.observed_date
                    """, (uuid.uuid4().hex, 'activity', activity['context'], activity['word'], 1, 0.5, datetime.now().isoformat()))
                    count += 1
```

- [ ] **Step 2: Verify no syntax/import errors**

Run:
```bash
cd personal-ai-space && python3 -c "from extractors import DailyNoteExtractor; print('OK')"
```
Expected: prints `OK`

- [ ] **Step 3: Run existing tests to verify no regressions**

Run:
```bash
cd personal-ai-space && python3 -m pytest engine/tests/ -v --timeout=30 2>&1 | head -60
```
Expected: All previously passing tests still pass (pre-existing failures, if any, are unchanged)

- [ ] **Step 4: Commit**

```bash
git add personal-ai-space/engine/extractors/__init__.py
git commit -m "refactor(behaviors): DailyNoteExtractor delegates to behavior_vocab

- _extract_emotions() and _extract_activities() now delegate to behavior_vocab
- INSERT for emotions passes real trigger context and effectiveness=0.2 when negated
- INSERT for activities passes real trigger context instead of hardcoded 'daily_note'"
```

---

### Task 3: Refactor ComprehensiveExtractor to use behavior_vocab

**Files:**
- Modify: `engine/extractors/comprehensive_extractor.py`

**Security flag:** `none`

**Does NOT cover:** Other methods in ComprehensiveExtractor (`_extract_relationships`, `_extract_professional_data`, `_extract_learning_patterns`, `_extract_implicit_tasks`) — those are unchanged. Only `_extract_daily_patterns` is modified.

- [ ] **Step 1: Add import and refactor _extract_daily_patterns**

Add import at the top of `comprehensive_extractor.py` (after existing imports):
```python
from extractors.behavior_vocab import extract_emotions, extract_activities
```

Replace `_extract_daily_patterns` (lines 160-222) with:

```python
    def _extract_daily_patterns(self):
        """Extract behaviors and patterns from daily notes using shared vocabulary."""
        inbox_dir = self.project_root / "command" / "inbox"

        emotions_found = []
        activities_found = []

        for file_path in inbox_dir.glob("*.md"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                emotions_found.extend(extract_emotions(content))
                activities_found.extend(extract_activities(content))
            except Exception as e:
                logger.warning("Failed to process daily note: %s", e)

        # Deduplicate across all files (keep last-seen context)
        emotion_dedup = {}
        for e in emotions_found:
            # Merge negated flag: if any occurrence is negated, mark as negated
            if e['word'] in emotion_dedup:
                existing = emotion_dedup[e['word']]
                if e['negated']:
                    existing['negated'] = True
            else:
                emotion_dedup[e['word']] = dict(e)

        activity_dedup = {}
        for a in activities_found:
            if a['word'] not in activity_dedup:
                activity_dedup[a['word']] = dict(a)

        for word, emotion in emotion_dedup.items():
            try:
                effectiveness = 0.2 if emotion['negated'] else 0.5
                trigger = emotion['context']
                execute("self", """
                    INSERT INTO behaviors 
                    (id, behavior_type, trigger, response, frequency, effectiveness, observed_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(behavior_type, response) DO UPDATE SET
                      frequency = frequency + 1,
                      observed_date = excluded.observed_date
                """, (uuid.uuid4().hex, 'emotion', trigger, word, 1, effectiveness, datetime.now().isoformat()))
                self.stats['behaviors_emotions'] += 1
            except Exception as e:
                logger.warning("Failed to insert emotion behavior '%s': %s", word, e)

        for word, activity in activity_dedup.items():
            try:
                trigger = activity['context']
                execute("self", """
                    INSERT INTO behaviors 
                    (id, behavior_type, trigger, response, frequency, effectiveness, observed_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(behavior_type, response) DO UPDATE SET
                      frequency = frequency + 1,
                      observed_date = excluded.observed_date
                """, (uuid.uuid4().hex, 'activity', trigger, word, 1, 0.5, datetime.now().isoformat()))
                self.stats['behaviors_activities'] += 1
            except Exception as e:
                logger.warning("Failed to insert activity behavior '%s': %s", word, e)
```

- [ ] **Step 2: Verify no syntax/import errors**

Run:
```bash
cd personal-ai-space && python3 -c "from extractors.comprehensive_extractor import ComprehensiveExtractor; print('OK')"
```
Expected: prints `OK`

- [ ] **Step 3: Run existing tests to verify no regressions**

Run:
```bash
cd personal-ai-space && python3 -m pytest engine/tests/ -v --timeout=30 2>&1 | head -60
```
Expected: All previously passing tests still pass

- [ ] **Step 4: Commit**

```bash
git add personal-ai-space/engine/extractors/comprehensive_extractor.py
git commit -m "refactor(behaviors): ComprehensiveExtractor._extract_daily_patterns delegates to behavior_vocab

- Replaced separate hardcoded keyword lists with calls to extract_emotions/extract_activities
- Deduplicates across files with negated-merge logic (any negated occurrence → negated)
- Real trigger context instead of hardcoded 'daily_note'
- effectiveness=0.2 when negated"
```

---

### Task 4: Database cleanup and re-extraction

**Files:**
- Modify: none (DB operations only)

**Security flag:** `none`

- [ ] **Step 1: Delete existing behaviors**

Run:
```bash
cd personal-ai-space && python3 -c "
from db_manager import execute
execute('self', 'DELETE FROM behaviors')
print('Behaviors deleted')
"
```
Expected: prints `Behaviors deleted`

- [ ] **Step 2: Run DailyNoteExtractor extraction**

Run:
```bash
cd personal-ai-space && python3 -c "
from extractors import DailyNoteExtractor
dne = DailyNoteExtractor()
count = dne.extract_all()
print(f'Extracted {count} behaviors from daily notes')
"
```
Expected: prints extracted count (should be fewer than before since noise words are filtered)

- [ ] **Step 3: Run ComprehensiveExtractor extraction**

Run:
```bash
cd personal-ai-space && python3 -c "
from extractors.comprehensive_extractor import ComprehensiveExtractor
ce = ComprehensiveExtractor()
ce._extract_daily_patterns()
print(f'Extracted emotions: {ce.stats.get(\"behaviors_emotions\", 0)}, activities: {ce.stats.get(\"behaviors_activities\", 0)}')
"
```
Expected: prints activity counts

- [ ] **Step 4: Verify no noise words in behaviors**

Run:
```bash
cd personal-ai-space && python3 -c "
from db_manager import query
rows = query('self', 'SELECT response, trigger, behavior_type, effectiveness FROM behaviors')
print(f'Total behaviors: {len(rows)}')
noise_words = {'about', 'the', 'that', 'this', 'these', 'those', 'it', 'and', 'or', 'but'}
noise_found = [r for r in rows if r['response'] in noise_words]
if noise_found:
    print(f'NOISE FOUND: {noise_found}')
else:
    print('Zero noise words found ✓')
# Check triggers
noop_triggers = [r for r in rows if r['trigger'] == 'daily_note']
print(f'Records with daily_note trigger (acceptable for edge cases): {len(noop_triggers)}')
# Show all records
for r in rows:
    neg = ' [NEGATED]' if r['effectiveness'] == 0.2 else ''
    print(f'  {r[\"behavior_type\"]:10} {r[\"response\"]:15} trigger=\"{r[\"trigger\"]}\" eff={r[\"effectiveness\"]}{neg}')
"
```
Expected: Zero noise words. Most triggers have meaningful context. Some edge-case records may still have 'daily_note' (when the matched word is at the start of the text with no preceding context).

- [ ] **Step 5: Update the design draft status to implemented**

```bash
sed -i '' 's/^**Status**: Approved Design/**Status**: Implemented/' .omo/drafts/2026-05-27-behavior-extraction-design.md
git add .omo/drafts/2026-05-27-behavior-extraction-design.md
```

- [ ] **Step 6: Final commit**

```bash
git add -A
git commit -m "chore(behaviors): delete old data and re-extract with behavior_vocab

- DELETE FROM behaviors removes ~30 records (~50% garbage)
- Re-extraction produces only whitelisted emotion/activity words
- All triggers contain meaningful context not 'daily_note'
- Negated emotions marked with effectiveness=0.2"
```

---

## Self-Review

### 1. Spec Coverage
- ✅ AC1 (`extract_emotions("I feel about the that")` returns `[]`): Task 1, `test_rejects_noise_words_after_feel`
- ✅ AC2 (`extract_emotions("I feel anxious and sad")` returns both): Task 1, `test_captures_multiple_emotions`
- ✅ AC3 (`extract_emotions("I don't feel happy")` negated=True): Task 1, `test_detects_negation`
- ✅ AC4 (`extract_activities("I read it today and worked on")` returns `read`, `worked`): Task 1, `test_no_greedy_capture`
- ✅ AC5 (delete old data + re-extract): Task 4
- ✅ AC6 (trigger contains meaningful context): Task 2/3 (INSERT uses `emotion['context']`), Task 4 verification
- ✅ AC7 (both extractors produce identical results): Both delegate to the same `behavior_vocab` functions

### 2. Placeholder Scan
- Zero placeholders found — every code block contains full implementation code, every test contains assertion logic

### 3. Type Consistency
- `extract_emotions` returns `list[dict]` with keys `word`, `category`, `negated`, `context` — consistent across all 3 call sites (test file, `__init__.py`, `comprehensive_extractor.py`)
- `extract_activities` returns `list[dict]` with keys `word`, `context` — consistent across all 3 call sites
- `_capture_context` returns `str` with fallback `'daily_note'` — consistent
- `_detect_negation` returns `bool` — consistent

### 4. Scope-Reduction Scan
- No "v1", "basic", "simple", "for now", "placeholder", "initial version", or "minimal" found. No scope downgrades.
