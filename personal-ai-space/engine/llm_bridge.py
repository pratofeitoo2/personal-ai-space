"""
LLM Bridge — Lightweight natural language interface for the Personal AI Space.

Two services, both loaded on demand:

  IntentClassifier  — Embedding-based (via Ollama) + fuzzy-match fallback.
                      Classifies free text into known agent commands.
                      No persistent RAM use — loads embeddings per query.

  TextGenerator     — Ollama text generation via /api/generate.
                      Loads model on first call, keeps warm for subsequent calls.
                      Unloaded when not in use (Ollama's process stays, model paged).

Design principles:
  - Zero new Python dependencies (stdlib + requests already in requirements.txt)
  - Graceful degradation — if Ollama is unavailable, system continues as normal
  - Tiny memory footprint — no model loaded in this Python process
  - All heavy lifting delegated to Ollama subprocess
"""
import json
import time
import logging
import difflib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import requests

logger = logging.getLogger("engine.llm_bridge")

OLLAMA_BASE = "http://localhost:11434"
OLLAMA_TIMEOUT = 30  # seconds per request


# ── intent catalogue ──────────────────────────────────────────────────────────
# Each intent maps to one agent command + parameter extraction hints.
# The example_phrases are embedded at classification time for similarity search.

@dataclass
class IntentDef:
    agent: str
    command: str
    description: str
    example_phrases: list[str] = field(default_factory=list)
    params_hint: dict = field(default_factory=dict)  # how to extract params from text


INTENT_CATALOGUE: list[IntentDef] = [
    IntentDef("task-coordinator", "get_today",
              "What's on my plate today?",
              ["what should I do today", "what's on my plate", "today's tasks",
               "show me my tasks", "what do I need to do", "my tasks for today",
               "what's due today", "today's agenda"]),
    IntentDef("task-coordinator", "get_all_open",
              "Show all open tasks",
              ["show all tasks", "list everything", "all my tasks",
               "what are all my tasks", "show me everything"]),
    IntentDef("task-coordinator", "summary",
              "Task completion summary",
              ["task summary", "how many tasks done", "task stats",
               "completion rate", "how am I doing on tasks"]),
    IntentDef("task-coordinator", "create_task",
              "Add a new task",
              ["add a task", "create task", "new task", "I need to",
               "remind me to", "add to my list", "create a new task"]),
    IntentDef("insight-generator", "analyse_habits",
              "Show habit insights",
              ["how are my habits", "habit insights", "show habits",
               "how am I doing on habits", "habit report", "my habit streak"]),
    IntentDef("report-generator", "daily_digest",
              "Show the daily digest",
              ["daily digest", "show digest", "today's report",
               "what happened today", "day summary", "digest"]),
    IntentDef("report-generator", "weekly_review",
              "Show the weekly review",
              ["weekly review", "this week's report", "week summary",
               "how was my week", "weekly report"]),
    IntentDef("reminder-system", "snapshot",
              "Show reminders and overdue items",
              ["what's overdue", "my reminders", "remind me",
               "what's late", "overdue tasks", "due soon"]),
    IntentDef("context-manager", "get_context",
              "Show my profile and context",
              ["show my profile", "what do you know about me",
               "my context", "who am I", "tell me about myself", "profile"]),
    IntentDef("memory", "mcp_stats",
              "Show memory stats",
              ["memory stats", "how much memory", "facts and lessons",
               "memory status", "what do you remember"]),
    IntentDef("knowledge-indexer", "search",
              "Search the knowledge base",
              ["search notes", "find something", "look up",
               "I'm looking for", "search knowledge", "find notes about"]),
    IntentDef("learning", "infer",
              "Run pattern inference",
              ["learn about me", "find patterns", "infer patterns",
               "what patterns do you see", "analyze my behavior"]),
]


# ── results ──────────────────────────────────────────────────────────────────

@dataclass
class Classification:
    intent: Optional[IntentDef]
    confidence: float
    raw_text: str
    alternatives: list[tuple[str, float]] = field(default_factory=list)
    extracted_params: dict = field(default_factory=dict)


@dataclass
class GenerationResult:
    text: str
    model: str
    duration_ms: int
    success: bool = True
    error: str = ""


# ── intent classifier ────────────────────────────────────────────────────────

class IntentClassifier:
    """Classifies free text into agent commands.

    Two tiers:
      1. Embedding similarity via Ollama (if available) — best accuracy.
      2. Fuzzy keyword matching (stdlib only) — zero-dependency fallback.

    Usage:
        classifier = IntentClassifier()
        result = classifier.classify("what's on my plate today?")
        # result.intent.command == "get_today"
    """

    SIMILARITY_THRESHOLD = 0.55  # minimum cosine similarity to accept

    def __init__(self, embedding_model: str = ""):
        self._phrases: list[str] = []
        self._phrase_intents: list[IntentDef] = []
        self._embed_cache: Optional[list[list[float]]] = None
        self._ollama_available: Optional[bool] = None
        self._embedding_model = embedding_model or _detect_embedding_model()

        # Build flat phrase list from catalogue
        for intent in INTENT_CATALOGUE:
            for phrase in intent.example_phrases:
                self._phrases.append(phrase.lower())
                self._phrase_intents.append(intent)

        self._check_ollama()

    def _check_ollama(self) -> bool:
        if self._ollama_available is not None:
            return self._ollama_available
        try:
            r = requests.get(f"{OLLAMA_BASE}/api/tags", timeout=2)
            self._ollama_available = r.ok
        except requests.ConnectionError:
            self._ollama_available = False
        if not self._ollama_available:
            logger.info("Ollama not reachable — intent classifier using fuzzy matching only")
        return self._ollama_available

    def _cosine_sim(self, a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        na = sum(x * x for x in a) ** 0.5
        nb = sum(x * x for x in b) ** 0.5
        return dot / (na * nb) if na and nb else 0.0

    def _embed(self, text: str) -> Optional[list[float]]:
        """Get embedding from Ollama."""
        try:
            r = requests.post(
                f"{OLLAMA_BASE}/api/embeddings",
                json={"model": self._embedding_model, "prompt": text},
                timeout=10,
            )
            if r.ok:
                return r.json().get("embedding")
        except (requests.ConnectionError, requests.Timeout, json.JSONDecodeError) as e:
            logger.debug(f"Embedding failed: {e}")
        return None

    def _build_embed_cache(self):
        """Embed all example phrases once."""
        if self._embed_cache is not None:
            return
        logger.info(f"Building embedding cache ({len(self._phrases)} phrases)...")
        cache = []
        for phrase in self._phrases:
            emb = self._embed(phrase)
            cache.append(emb if emb else [])
        self._embed_cache = cache

    def _classify_embedding(self, text: str) -> Optional[Classification]:
        """Classify using embedding similarity."""
        if not self._ollama_available:
            return None
        try:
            self._build_embed_cache()
            query_emb = self._embed(text.lower())
            if not query_emb:
                return None

            best_score = -1.0
            best_idx = -1
            scores: list[tuple[int, float]] = []

            for i, cached in enumerate(self._embed_cache):
                if not cached:
                    continue
                sim = self._cosine_sim(query_emb, cached)
                scores.append((i, sim))
                if sim > best_score:
                    best_score = sim
                    best_idx = i

            if best_idx < 0:
                return None

            scores.sort(key=lambda x: x[1], reverse=True)
            alternatives = [
                (self._phrase_intents[i].description, round(s, 3))
                for i, s in scores[:3]
                if s > self.SIMILARITY_THRESHOLD * 0.8
            ]

            params = self._extract_params(text, self._phrase_intents[best_idx])

            return Classification(
                intent=self._phrase_intents[best_idx],
                confidence=round(best_score, 3),
                raw_text=text,
                alternatives=alternatives,
                extracted_params=params,
            )
        except Exception as e:
            logger.warning(f"Embedding classification failed: {e}")
            return None

    def _classify_fuzzy(self, text: str) -> Classification:
        """Fallback: fuzzy keyword matching using difflib."""
        text_lower = text.lower()
        scores = []
        for i, phrase in enumerate(self._phrases):
            ratio = difflib.SequenceMatcher(None, text_lower, phrase).ratio()
            text_words = set(text_lower.split())
            phrase_words = set(phrase.split())
            overlap = len(text_words & phrase_words)
            keyword_bonus = overlap / max(len(phrase_words), 1) * 0.3
            scores.append((i, min(1.0, ratio + keyword_bonus)))

        scores.sort(key=lambda x: x[1], reverse=True)
        best_idx, best_score = scores[0]

        alternatives = [
            (self._phrase_intents[i].description, round(s, 3))
            for i, s in scores[:3]
            if s > 0.2
        ]

        params = self._extract_params(text, self._phrase_intents[best_idx]) if best_score > 0.3 else {}

        return Classification(
            intent=self._phrase_intents[best_idx] if best_score > 0.35 else None,
            confidence=round(best_score, 3),
            raw_text=text,
            alternatives=alternatives,
            extracted_params=params,
        )

    def _extract_params(self, text: str, intent: IntentDef) -> dict:
        """Simple parameter extraction based on intent type."""
        params = {}
        if intent.command == "create_task":
            # Try to extract title: anything after "to" or "that" or quoted
            text_lower = text.lower()
            for prefix in ["to ", "that ", "called ", "named "]:
                if prefix in text_lower:
                    idx = text_lower.index(prefix) + len(prefix)
                    title = text[idx:].strip().rstrip(".!")
                    if title:
                        params["title"] = title
                        break
            if "priority" not in params:
                # Check for priority keywords
                if "critical" in text_lower or "urgent" in text_lower:
                    params["priority"] = "critical"
                elif "high" in text_lower:
                    params["priority"] = "high"
                elif "low" in text_lower:
                    params["priority"] = "low"
        elif intent.command == "search":
            # Extract search query
            text_lower = text.lower()
            for prefix in ["for ", "about ", "regarding ", "up "]:
                if prefix in text_lower:
                    idx = text_lower.index(prefix) + len(prefix)
                    query = text[idx:].strip().rstrip(".!")
                    if query:
                        params["query"] = query
                        break
        return params

    def classify(self, text: str) -> Classification:
        """Classify text. Tries embedding first, falls back to fuzzy matching."""
        if not text or not text.strip():
            return Classification(intent=None, confidence=0.0, raw_text=text)

        result = self._classify_embedding(text)
        if result:
            return result

        return self._classify_fuzzy(text)


# ── text generator ───────────────────────────────────────────────────────────

class TextGenerator:
    """Generates text via Ollama. Loaded on demand, kept warm for the session.

    Usage:
        gen = TextGenerator(model="smollm2:1.7b-instruct-q4_K_M")
        result = gen.generate("Summarize: ...")
        print(result.text)
    """

    def __init__(self, model: str = ""):
        self.model = model or _detect_best_model()
        self._warm = False
        logger.info(f"TextGenerator initialized (model={self.model})")

    def warm(self) -> bool:
        """Pre-load model into Ollama's memory. Optional — happens on first generate anyway."""
        if self._warm:
            return True
        try:
            r = requests.post(
                f"{OLLAMA_BASE}/api/generate",
                json={"model": self.model, "prompt": "", "keep_alive": "5m"},
                timeout=5,
            )
            self._warm = r.ok
            return self._warm
        except requests.ConnectionError:
            logger.warning("Ollama not reachable — text generation unavailable")
            return False

    def generate(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.7,
        max_tokens: int = 256,
    ) -> GenerationResult:
        """Generate text. Returns result object (never raises on network error)."""
        start = time.monotonic()
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "system": system,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": False,
                "keep_alive": "5m",
            }
            r = requests.post(
                f"{OLLAMA_BASE}/api/generate",
                json=payload,
                timeout=OLLAMA_TIMEOUT,
            )
            elapsed = int((time.monotonic() - start) * 1000)
            if r.ok:
                data = r.json()
                text = data.get("response", "").strip()
                return GenerationResult(
                    text=text,
                    model=self.model,
                    duration_ms=elapsed,
                )
            return GenerationResult(
                text="",
                model=self.model,
                duration_ms=elapsed,
                success=False,
                error=f"Ollama returned {r.status_code}: {r.text[:200]}",
            )
        except requests.ConnectionError:
            elapsed = int((time.monotonic() - start) * 1000)
            return GenerationResult(
                text="",
                model=self.model,
                duration_ms=elapsed,
                success=False,
                error="Ollama not reachable at localhost:11434",
            )
        except Exception as e:
            elapsed = int((time.monotonic() - start) * 1000)
            return GenerationResult(
                text="",
                model=self.model,
                duration_ms=elapsed,
                success=False,
                error=str(e),
            )

    def chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 256,
    ) -> GenerationResult:
        """Chat completion via Ollama /api/chat."""
        start = time.monotonic()
        try:
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": False,
                "keep_alive": "5m",
            }
            r = requests.post(
                f"{OLLAMA_BASE}/api/chat",
                json=payload,
                timeout=OLLAMA_TIMEOUT,
            )
            elapsed = int((time.monotonic() - start) * 1000)
            if r.ok:
                data = r.json()
                text = data.get("message", {}).get("content", "").strip()
                return GenerationResult(text=text, model=self.model, duration_ms=elapsed)
            return GenerationResult(
                text="", model=self.model, duration_ms=elapsed,
                success=False, error=f"Ollama returned {r.status_code}",
            )
        except requests.ConnectionError:
            elapsed = int((time.monotonic() - start) * 1000)
            return GenerationResult(
                text="", model=self.model, duration_ms=elapsed,
                success=False, error="Ollama not reachable",
            )
        except Exception as e:
            elapsed = int((time.monotonic() - start) * 1000)
            return GenerationResult(
                text="", model=self.model, duration_ms=elapsed,
                success=False, error=str(e),
            )


# ── helpers ───────────────────────────────────────────────────────────────────

def _detect_embedding_model() -> str:
    """Auto-detect the best embedding model available in Ollama."""
    try:
        r = requests.get(f"{OLLAMA_BASE}/api/tags", timeout=3)
        if r.ok:
            names = [m["name"] for m in r.json().get("models", [])]
            for preferred in [
                "nomic-embed-text",
                "all-minilm:33m-l12-v2-fp16",
                "all-minilm:22m",
                "granite-embedding:30m",
            ]:
                for n in names:
                    if n.startswith(preferred):
                        return n
    except (requests.ConnectionError, json.JSONDecodeError):
        pass
    return "nomic-embed-text"


def _detect_best_model() -> str:
    """Auto-detect the best available model in Ollama."""
    try:
        r = requests.get(f"{OLLAMA_BASE}/api/tags", timeout=3)
        if r.ok:
            models = r.json().get("models", [])
            names = [m["name"] for m in models]
            # Prefer smallest capable model
            for preferred in [
                "smollm2:1.7b-instruct-q4_K_M",
                "smollm2:1.7b",
                "llama3.2:3b",
                "qwen2.5:3b",
                "phi4-mini:3.8b",
            ]:
                for n in names:
                    if n.startswith(preferred) or n == preferred.replace(":", ":"):
                        return n
            # Fall back to first available instruct model
            instruct_models = [n for n in names if "instruct" in n or "chat" in n]
            if instruct_models:
                return instruct_models[0]
            if names:
                return names[0]
    except (requests.ConnectionError, json.JSONDecodeError):
        pass
    return "smollm2:1.7b"  # fallback default


# ── enrichment prompts ───────────────────────────────────────────────────────

HABIT_INSIGHTS_SYSTEM = """You are a personal insight assistant. You are given structured data about someone's habits and you summarize it in 2-3 natural sentences.

Rules:
- Be concise and warm
- Mention the top habit and its completion rate
- Call out any habits at risk
- Do NOT use markdown or bullet points
- Never mention "based on the data" or "the data shows"
- Write as if you're their thoughtful assistant talking to them"""

HABIT_INSIGHTS_PROMPT = """Here is the structured habit data:

{data}

Write a 2-3 sentence natural overview of how things are going with these habits."""

DIGEST_OPENER_SYSTEM = """You are a personal assistant writing a short daily digest opener. Given structured data about tasks and habits, write 1-2 sentences that summarize the day.

Rules:
- Warm, direct, conversational
- Start with "Good morning" or similar
- Mention the most important thing to know today
- Never use markdown
- Keep it to 1-2 sentences"""

DIGEST_OPENER_PROMPT = """Today's data:
- Tasks due: {due_today}
- Overdue tasks: {overdue}
- Habits at risk: {at_risk_habits}
- Habits analyzed: {habit_count}

Write a 1-2 sentence opener for today's digest."""


def enrich_habit_insights(structured_data: dict, generator: Optional[TextGenerator] = None) -> Optional[str]:
    """Turn structured habit data into a natural language summary.

    Returns None if the LLM is unavailable (rule-based output still shows).
    """
    close = False
    if generator is None:
        gen = TextGenerator()
        close = True
    else:
        gen = generator

    data_str = json.dumps(structured_data, indent=2, ensure_ascii=False)
    prompt = HABIT_INSIGHTS_PROMPT.replace("{data}", data_str[:800])
    result = gen.generate(prompt, system=HABIT_INSIGHTS_SYSTEM, temperature=0.5, max_tokens=200)

    if close:
        pass  # let GC handle it

    return result.text if result.success else None


def enrich_digest_opener(
    due_today: int,
    overdue: int,
    at_risk_habits: int,
    habit_count: int,
    generator: Optional[TextGenerator] = None,
) -> Optional[str]:
    """Generate a narrative opener for the daily digest."""
    close = False
    if generator is None:
        gen = TextGenerator()
        close = True
    else:
        gen = generator

    prompt = DIGEST_OPENER_PROMPT.format(
        due_today=due_today, overdue=overdue,
        at_risk_habits=at_risk_habits, habit_count=habit_count,
    )
    result = gen.generate(prompt, system=DIGEST_OPENER_SYSTEM, temperature=0.5, max_tokens=150)

    if close:
        pass

    return result.text if result.success else None


def check_ollama() -> dict:
    """Health check — is Ollama running and what models are available?"""
    try:
        r = requests.get(f"{OLLAMA_BASE}/api/tags", timeout=3)
        if r.ok:
            models = r.json().get("models", [])
            return {
                "available": True,
                "models": [m["name"] for m in models],
                "error": "",
            }
        return {"available": False, "models": [], "error": f"HTTP {r.status_code}"}
    except requests.ConnectionError as e:
        return {"available": False, "models": [], "error": str(e)}
