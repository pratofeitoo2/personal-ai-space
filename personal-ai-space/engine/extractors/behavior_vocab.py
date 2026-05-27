"""Shared vocabulary and extraction functions for behaviors table.

Provides curated emotion (8 categories) and activity dictionaries,
with regex-based extraction that uses whitelist filtering, negation
detection, and context window capture.
"""
import re

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

ALL_EMOTIONS = [word for words in EMOTION_WORDS.values() for word in words]

ACTIVITY_WORDS = [
    'studied', 'researched', 'worked', 'coded', 'designed', 'wrote',
    'met', 'called', 'emailed', 'read', 'exercised', 'meditated',
    'slept', 'planned', 'reviewed', 'analyzed', 'presented',
    'negotiated', 'coordinated', 'mentored', 'trained', 'learned',
]

_EMOTION_TRIGGERS = ['feel', 'feels', 'feeling', 'felt']

_ACTIVITY_TRIGGERS = [
    'did', 'doing', 'studied', 'worked', 'exercised',
    'read', 'wrote', 'coded', 'designed', 'met',
    'meditated', 'slept', 'planned', 'reviewed',
    'analyzed', 'presented', 'negotiated', 'coordinated',
    'mentored', 'trained', 'learned',
]


def _detect_negation(text: str, word_start: int, word: str) -> bool:
    """Check if word at word_start is negated within a 4-word window before it.

    Args:
        text: Full text being searched.
        word_start: Character index where the target word begins.
        word: The target word (used for position context).

    Returns:
        True if a negation word is found within the window.
    """
    before = text[:word_start]
    if not before.strip():
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
        Each emotion word appears at most once (deduplicated by word).
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
                results.append({
                    'word': candidate,
                    'category': _get_emotion_category(candidate),
                    'negated': _detect_negation(text, word_start, candidate),
                    'context': _capture_context(text, word_start),
                })

    # Method 2: Direct keyword search with word boundaries
    for word in ALL_EMOTIONS:
        pattern = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)
        for match in pattern.finditer(text):
            if word not in seen:
                seen.add(word)
                word_start = match.start()
                results.append({
                    'word': word,
                    'category': _get_emotion_category(word),
                    'negated': _detect_negation(text, word_start, word),
                    'context': _capture_context(text, word_start),
                })

    return results


def extract_activities(text: str) -> list[dict]:
    """Extract activity words from text using verb triggers + direct keyword matching.

    Args:
        text: Raw text to search.

    Returns:
        List of dicts with keys: word, context.
        Each activity word appears at most once (deduplicated by word).
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
                results.append({
                    'word': candidate,
                    'context': _capture_context(text, word_start),
                })

    # Method 2: Direct keyword search with word boundaries
    for word in ACTIVITY_WORDS:
        pattern = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)
        for match in pattern.finditer(text):
            if word not in seen:
                seen.add(word)
                word_start = match.start()
                results.append({
                    'word': word,
                    'context': _capture_context(text, word_start),
                })

    return results
