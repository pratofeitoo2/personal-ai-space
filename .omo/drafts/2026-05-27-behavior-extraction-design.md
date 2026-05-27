# Behavior Extraction Redesign

**Date**: 2026-05-27
**Status**: Approved Design
**Author**: Prometheus

---

## TL;DR

Rewrite the two extractors that populate the `behaviors` table to eliminate noise words ("about", "the", "that", etc.) and produce meaningful emotion/activity data with contextual triggers, using a curated whitelist approach with negation detection and context window extraction.

---

## Problem Statement

The `behaviors` table in `self.db` contains ~30 records, ~50% of which are garbage:

| Problema | Causa | Exemplo |
|---|---|---|
| Non-emotions stored as emotions | Regex captures any word after "feel/feeling/felt" | `response='about'`, `response='the'` |
| Whole sentences stored as activities | Regex has no length/word limit | `response='some research to understand sexuality as a field for...'` |
| Substring matching | `if keyword in content` without word boundary | Potential false matches |
| No negation handling | "not happy" stores `happy` with effectiveness=0.5 | False positive |
| Static trigger | `trigger='daily_note'` always | Useless for analysis |
| Duplicate logic | Two extractors do similar things differently | Inconsistent data, maintenance burden |

## Root Causes

1. **`DailyNoteExtractor._extract_emotions`** (lines 219-232 of `extractors/__init__.py`): Regex patterns `r'feel(?:ing)?[\s:]+([a-z]+)'` capture the immediate next word regardless of whether it is a known emotion word. No whitelist filter exists.

2. **`DailyNoteExtractor._extract_activities`** (lines 234-246 of `extractors/__init__.py`): Regex pattern `r'(?:did|doing|studied|worked|exercised|read|wrote)\s+([a-z\s]+)'` uses `[a-z\s]+` which greedily captures everything until a non-alpha character, producing long meaningless strings.

3. **`ComprehensiveExtractor._extract_daily_patterns`** (lines 160-222 of `comprehensive_extractor.py`): Uses `if emotion in content` for substring matching without word boundaries, and maintains a separate keyword list that overlaps inconsistently with the other extractor.

## Design Decisions

### Approach: Hybrid (Whitelist + Context Trigger)

Chosen over:
- **Pure whitelist (A)**: Clean but doesn't populate `trigger` meaningfully
- **NLP (B)**: Too heavyweight, adds dependencies, hard to debug
- **Combined (A+B)**: Unnecessary scope for the problem

### User Decisions

| Decision | Choice |
|---|---|
| Extraction approach | C — Hybrid (whitelist + context trigger) |
| Existing data | Delete and re-extract |
| Extractor consolidation | Yes, unify into shared logic |

---

## Architecture

### New Module: `engine/extractors/behavior_vocab.py`

Shared curated dictionaries + extraction functions.

```
engine/extractors/
├── __init__.py                    # Existing — DailyNoteExtractor refactored
├── comprehensive_extractor.py      # Existing — calls shared extraction
├── behavior_vocab.py              # [NEW] Shared extraction logic
└── ...
```

### Curated Emotion Dictionary

Organized by category (Plutchik-inspired) with ~80 words total:

| Category | Words |
|---|---|
| `joy` | happy, joyful, content, pleased, cheerful, glad, satisfied, grateful, hopeful, optimistic, elated |
| `sadness` | sad, unhappy, depressed, melancholy, down, heartbroken, miserable, lonely, disappointed |
| `anger` | angry, frustrated, irritated, annoyed, furious, agitated |
| `fear` | anxious, afraid, scared, worried, nervous, fearful, panicked, stressed, uneasy, overwhelmed |
| `energy` | tired, exhausted, drained, fatigued, weary, sleepy, energized, motivated, excited, productive, focused |
| `calm` | calm, peaceful, relaxed, tranquil, serene, comfortable, safe |
| `distress` | distracted, confused, uncertain, doubtful, restless, stuck |
| `trust` | confident, assured, secure, trusting, certain |

### Curated Activity Dictionary

~25 words focused on meaningful actions:

studied, researched, worked, coded, designed, wrote, met, called, emailed, read, exercised, meditated, slept, planned, reviewed, analyzed, presented, negotiated, coordinated, mentored, trained, learned

### Extraction Algorithm

```
Input: raw text
Output: list of {word, category, negated, trigger_context}

1. Lowercase text
2. Apply verb-triggered regex (feel|felt|feeling|did|doing|studied|etc.)
3. For each capture group match:
   a. Check if captured word ∈ ALLOWED_EMOTIONS or ALLOWED_ACTIVITIES
   b. If yes: check negation within 4-word window before match
   c. Extract trigger context (up to 5 words before match)
   d. Add to results
4. Apply direct keyword search with \b word boundaries (for comprehensive coverage)
5. Repeat step 3 for direct keyword matches
6. Deduplicate results
7. Return list
```

### Negation Detection

Pattern: `\b(?:not|n't|never)\s+(?:\w+\s+){0,3}?` + `\b(word)\b`

Max window: 4 words between negation and target word.

If negated:
- `frequency` tracks as normal (it was observed)
- `effectiveness = 0.2` (low effectiveness — the negation indicates it's not a productive pattern)
- Metadata in JSON notes: `{"negated": true}`

### Trigger Context

Capture the 3-5 words immediately before the matched emotion/activity:

| Text | Match | Trigger |
|---|---|---|
| "I feel anxious about..." | anxious | "I feel" |
| "I'm tired today because..." | tired | "I'm" |
| "Worked on the presentation all day" | worked | "Worked" (verb itself when standalone) |

If no preceding context available (word at start of text), fall back to `'daily_note'`.

---

## File Changes

### 1. Create: `engine/extractors/behavior_vocab.py`

```python
# Shared vocabulary and extraction functions

# Category-organized emotion words
EMOTION_WORDS = { ... }
ALL_EMOTIONS = [word for words in EMOTION_WORDS.values() for word in words]
ACTIVITY_WORDS = [ ... ]

def extract_emotions(text: str) -> list[dict]:
    """Return [{word, category, negated, context}, ...]"""

def extract_activities(text: str) -> list[dict]:
    """Return [{word, context}, ...]"""

def _detect_negation(text: str, match_pos: int, word: str) -> bool:
    """Check if word is negated within 4-word window before it."""

def _capture_context(text: str, match_pos: int, window: int = 5) -> str:
    """Return up to N words before the match position."""
```

### 2. Refactor: `engine/extractors/__init__.py`

Changes:
- Import `behavior_vocab`
- Replace `_extract_emotions()` → call `behavior_vocab.extract_emotions()`
- Replace `_extract_activities()` → call `behavior_vocab.extract_activities()`
- Update INSERT to pass real trigger context from extraction result
- Remove old regex methods

### 3. Refactor: `engine/extractors/comprehensive_extractor.py`

Changes:
- Import `behavior_vocab`
- Replace `_extract_daily_patterns()` keyword loop → call `behavior_vocab.extract_emotions()` + `extract_activities()`
- Same INSERT update for trigger

### 4. Database: Cleanup + Re-extraction

- `DELETE FROM behaviors`
- Run consolidated extraction
- Verify: zero noise words, all triggers meaningful

---

## Acceptance Criteria

1. `behavior_vocab.extract_emotions("I feel about the that")` returns empty list
2. `behavior_vocab.extract_emotions("I feel anxious and sad")` returns `[{word:'anxious', negated:false}, {word:'sad', negated:false}]`
3. `behavior_vocab.extract_emotions("I don't feel happy")` returns `[{word:'happy', negated:true}]`
4. `behavior_vocab.extract_activities("I read it today and worked on")` returns `[{word:'read'}, {word:'worked'}]` (not "it today and worked on")
5. Existing 30 noise records deleted, re-extraction produces only valid words
6. `trigger` field contains meaningful context (not 'daily_note' where context exists)
7. Both extractors produce identical results when run on the same text
