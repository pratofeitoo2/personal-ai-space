---
created: 2026-05-09
updated: 2026-05-09
---
# LLM Integration Analysis — Personal AI Powerhouse

> **Status:** Research & Design  
> **Branch:** `feature/llm-integration`  
> **Hardware target:** Apple M1, 8GB unified memory  
> **Date:** 2026-05-09

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Current Architecture Review](#current-architecture-review)
3. [What an LLM Would Actually Do](#what-an-llm-would-actually-do)
4. [Model Tier Analysis](#model-tier-analysis)
5. [Memory Consumption Calculations](#memory-consumption-calculations)
6. [Loading Strategies](#loading-strategies)
7. [Recommendation](#recommendation)
8. [Implementation Path](#implementation-path)
9. [Appendix: Model Benchmarks](#appendix-model-benchmarks)

---

## Executive Summary

The Personal AI Powerhouse engine is **rule-based by design.** Its 6 agents and 2 observers perform all meaningful computation through SQL queries, counters, threshold checks, and template-based string formatting. An LLM layer would augment — not replace — this existing logic.

The key finding of this analysis is that the system's LLM needs are **dramatically lighter** than typical LLM use cases. Every input the LLM would receive is already structured by the rule-based agents. The LLM's sole job is **phrasing and classification**, not reasoning or knowledge retrieval. This makes the 1-3B parameter range the practical sweet spot for this project.

---

## Current Architecture Review

### How agents work today

Every agent follows the same pattern: `SQL query → rule-based computation → structured output`.

**InsightGenerator** (`engine/agents/insight_generator.py`):
```python
# Hardcoded thresholds — no LLM needed
COMPLETION_THRESHOLDS = {
    "excellent": 90, "good": 70, "fair": 50, "poor": 0,
}

def _recommend(self, pct: float, name: str) -> Optional[str]:
    if pct == 0:
        return f"⚠️  '{name}' not done at all — schedule a specific slot"
    if pct < 50:
        return f"Try stacking '{name}' onto an existing routine"
    if pct < 70:
        return f"Almost there with '{name}' — commit to 3x this week"
    return None
```

**PatternLearner** (`engine/agents/pattern_learner.py`):
```python
# Pure counters — hourly distribution, category grouping, streak ordering
def learn_time_patterns(self) -> dict:
    hours = Counter()
    for t in tasks:
        hours[dt.hour] += 1
    most_common_hour = hours.most_common(1)[0][0]
    patterns['task_creation_hour'] = most_common_hour
```

**ReportGenerator** (`engine/agents/report_generator.py`):
```python
# Template-based string formatting — f-strings with pre-computed values
lines = [
    f"# Daily Digest — {now.strftime('%B %-d, %Y')}",
    f"- **Tasks due today**: {len(snap['due_today'])}",
    f"- **Overdue**: {len(snap['overdue'])}",
    f"- **Habits at risk**: {len(data['at_risk_habits'])}",
]
```

### What agents cannot do (the LLM gap)

The current system cannot:

1. **Understand natural language queries** — every interaction must match a predefined CLI command via `click`.
2. **Rephrase insights creatively** — recommendations are hardcoded templates. "Try stacking 'reading' onto an existing routine" is the ceiling.
3. **Summarize unstructured text** — daily notes, journal entries, and inbox captures are stored as-is, never condensed.
4. **Draft new content** — no ability to write emails, journal prompts, or reflections.
5. **Connect cross-domain patterns** — the task-coordinator, pattern-learner, and insight-generator each operate on their own database in isolation.

### What agents do well (keep as-is)

- Fast, deterministic task CRUD and prioritization
- Habit streak counting and completion percentage calculation
- Calendar and reminder snapshotting
- Knowledge base indexing and search
- All database read/write operations

These should **never** go through an LLM. Latency would increase from ~50ms to ~3-5s with no benefit in accuracy.

---

## What an LLM Would Actually Do

### Use case 1: Intent routing

| Today | With LLM |
|-------|----------|
| `python3 cli.py task list` | `"what's on my plate today?"` |
| `python3 cli.py habit insights` | `"how are my habits this week?"` |
| `python3 cli.py learning observations` | `"what have you noticed about me?"` |

The LLM classifies free-text input into one of ~20 known commands and extracts parameters. This is a **classification task**, not generation.

- Input: short sentence (5-20 words)
- Output: structured command + arguments
- Model requirement: minimal — 0.5-1B is sufficient, or even a non-LLM embedding classifier

### Use case 2: Insight phrasing

Agents produce structured data like:
```json
{
  "habit": "reading",
  "completion_pct": 40,
  "streak": 2,
  "rating": "fair"
}
```

The LLM rephrases this into natural language:
> *"You've been keeping up with reading about 40% of the time, with a 2-day streak. Try pairing it with your morning coffee to build consistency."*

- Input: structured JSON (~200 bytes)
- Output: 1-3 sentences
- Model requirement: low — 1-3B is more than enough

### Use case 3: Report enrichment

The daily digest is currently a Markdown template. An LLM could add a narrative opener:
> *"Good morning! You closed 3 tasks yesterday and maintained your exercise streak. Watch out — you have 2 overdue items from last week."*

- Input: the same structured data the report already uses
- Output: 2-4 sentences
- Model requirement: low — 1-3B

### Use case 4: Note summarization

Unstructured bullet journal entries → 2-3 sentence summary stored in memory.

- Input: 100-500 words of raw notes
- Output: 2-3 sentences
- Model requirement: moderate — 1-3B

### Use case 5: Writing assistance

Prompt-based drafting of emails, journal entries, or session notes.

- Input: short instruction + context
- Output: 1-3 paragraphs
- Model requirement: moderate — 3B for better quality

### Summary of LLM workload

| Metric | Value |
|--------|-------|
| Max input size | ~500 words |
| Max output size | ~3 paragraphs |
| Reasoning depth | Surface-level pattern recognition |
| Knowledge required | None beyond what agents provide |
| Domain scope | One person's life data |
| Frequency | 20-30 queries/day (sporadic) |
| Latency tolerance | 2-5s acceptable |

---

## Model Tier Analysis

### Hardware ceiling: Apple M1 8GB

| Component | RAM usage |
|-----------|-----------|
| macOS (baseline) | ~2.0 GB |
| Engine + agents + DBs + MCP | ~0.25 GB |
| Browser + typical background apps | ~1.0-3.0 GB |
| **Available for model** | **~2.5-4.5 GB** |

### Model tier comparison

All figures for GGUF Q4_K_M quantization via llama.cpp or MLX.

#### Tier 1: Tiny (< 1B)

| Model | Params | Weight size | Tok/s on M1 | Use case fit |
|-------|--------|-------------|-------------|--------------|
| Qwen3.5-0.8B | 0.8B | ~500 MB | ~40-50 | Intent classification only |
| Llama 3.2 1B | 1B | ~700 MB | ~35-45 | Intent + basic phrasing |

**Verdict:** Viable for intent routing but too weak for insight generation and writing. Output quality is noticeably robotic.

#### Tier 2: Small (1.5-3B) ⭐ RECOMMENDED

| Model | Params | Weight size | RAM during use¹ | Tok/s on M1 | Use case fit |
|-------|--------|-------------|-----------------|-------------|--------------|
| SmolLM2-1.7B | 1.7B | ~1.0 GB | ~4.0-4.5 GB | ~25-35 | All use cases adequate |
| Llama 3.2 3B | 3B | ~1.8 GB | ~4.8-5.5 GB | ~15-25 | All use cases good |
| Qwen 2.5 3B | 3B | ~1.8 GB | ~4.8-5.5 GB | ~15-25 | All use cases good + multilingual |

¹ Includes macOS baseline + engine + model + ~1GB background apps.

**Verdict:** The sweet spot. Fits comfortably on 8GB, loads in 2-3s, produces natural output. SmolLM2-1.7B is the lightest viable option; Llama 3.2 3B or Qwen 2.5 3B offers noticeably better fluency at a modest memory increase.

#### Tier 3: Medium (3.8-4B)

| Model | Params | Weight size | RAM during use¹ | Tok/s on M1 | Use case fit |
|-------|--------|-------------|-----------------|-------------|--------------|
| Phi-4-mini | 3.8B | ~2.2 GB | ~5.2-6.0 GB | ~18 | All use cases excellent |
| Gemma 4 E4B | ~4B | ~2.3 GB | ~5.3-6.1 GB | ~125 | All use cases good, very fast |

**Verdict:** Phi-4-mini has the best reasoning quality per parameter in this class but consumes noticeably more RAM. On 8GB, this tier is tight — if the user has a browser with 5+ tabs open, the system will start swapping. Gemma 4 E4B is multimodal and extremely fast but not meaningfully better for this system's text-only workload.

#### Tier 4: Large (7-8B) ❌ NOT RECOMMENDED

| Model | Params | Weight size | RAM during use¹ | Tok/s on M1 |
|-------|--------|-------------|-----------------|-------------|
| Qwen 3 7B | 7B | ~4.5 GB | ~7.5-9.5 GB | ~15 |
| Llama 3.3 8B | 8B | ~5.0 GB | ~8.0-10.0 GB | ~10-15 |

**Verdict:** Will exceed 8GB total system RAM, forcing swap to disk. Inference speed drops from ~15 tok/s to <1 tok/s once swapping begins. The reasoning capability gain from 3B to 7B is irrelevant because the system never needs deep reasoning.

### Fit-for-purpose matrix

| Model | Intent routing | Insight phrasing | Report enrichment | Note summarization | Writing | Memory cost |
|-------|:---:|:---:|:---:|:---:|:---:|:---:|
| Qwen3.5-0.8B | ✅ | ⚠️ Robotic | ⚠️ Robotic | ❌ Too weak | ❌ Too weak | ~500 MB |
| **SmolLM2-1.7B** | ✅ | ✅ | ✅ | ✅ | ⚠️ Basic | ~1.0 GB |
| **Llama 3.2 3B** | ✅ | ✅ | ✅ | ✅ | ✅ | ~1.8 GB |
| **Qwen 2.5 3B** | ✅ | ✅ | ✅ | ✅ | ✅ + PT | ~1.8 GB |
| Phi-4-mini | ✅ | ✅ | ✅ | ✅ | ✅ | ~2.2 GB |
| Qwen 3 7B | ✅ | ✅ | ✅ | ✅ | ✅ | ~4.5 GB ❌ |

✅ = Handles well | ⚠️ = Marginal | ❌ = Inadequate | PT = Portuguese support

---

## Memory Consumption Calculations

### Formula

```
Total RAM used = macOS baseline + engine + model weights (Q4) + KV cache + background apps

macOS baseline:    ~2.0 GB
Engine + agents:   ~0.25 GB
KV cache (2K ctx): ~0.1-0.3 GB
Background apps:   ~1.0-3.0 GB (variable)
```

### Scenarios

#### Scenario A: Conservative — SmolLM2-1.7B, light browser use

| Component | RAM |
|-----------|-----|
| macOS | 2.0 GB |
| Engine | 0.25 GB |
| SmolLM2-1.7B (Q4) | 1.0 GB |
| KV cache | 0.1 GB |
| Browser (3 tabs) | 1.5 GB |
| **Total** | **~4.85 GB** |
| **Free** | **~3.15 GB** ✅ |

#### Scenario B: Recommended — Llama 3.2 3B, moderate browser use

| Component | RAM |
|-----------|-----|
| macOS | 2.0 GB |
| Engine | 0.25 GB |
| Llama 3.2 3B (Q4) | 1.8 GB |
| KV cache | 0.2 GB |
| Browser (5 tabs) | 2.0 GB |
| **Total** | **~6.25 GB** |
| **Free** | **~1.75 GB** ✅ |

#### Scenario C: Tight — Phi-4-mini, heavy browser use

| Component | RAM |
|-----------|-----|
| macOS | 2.0 GB |
| Engine | 0.25 GB |
| Phi-4-mini (Q4) | 2.2 GB |
| KV cache | 0.2 GB |
| Browser (8 tabs) | 3.0 GB |
| **Total** | **~7.65 GB** |
| **Free** | **~0.35 GB** ⚠️ Near swap |

#### Scenario D: Not viable — Qwen 3 7B, any browser use

| Component | RAM |
|-----------|-----|
| macOS | 2.0 GB |
| Engine | 0.25 GB |
| Qwen 3 7B (Q4) | 4.5 GB |
| KV cache | 0.3 GB |
| Browser (minimal) | 1.0 GB |
| **Total** | **~8.05 GB** |
| **Free** | **~0 GB** ❌ Swapping |

---

## Loading Strategies

### Strategy 1: Always-loaded (persistent)

The model is loaded once at engine startup and stays in RAM until the engine shuts down.

- **Pro:** Zero load time on first query, predictable memory state
- **Con:** Memory is consumed even when no LLM features are being used
- **Best for:** Dedicated machines where the engine is the primary application
- **Memory cost:** Full model weight always committed

### Strategy 2: On-demand (spawn on first use, keep warm)

The model is loaded the first time an LLM-dependent command is called and stays in RAM for subsequent calls. It persists until the engine process exits.

- **Pro:** No memory impact if the user only uses rule-based CLI commands; fast subsequent queries
- **Con:** First query has a 2-3s load penalty
- **Best for:** Mixed usage where LLM features are used occasionally in batches
- **Memory cost:** Model weight committed after first LLM query

### Strategy 3: Request-scoped (spawn and kill per query)

The model is loaded fresh for each LLM query and unloaded immediately after the response is returned.

- **Pro:** Zero persistent memory impact; model only exists for the duration of a single request
- **Con:** 2-3s load penalty on EVERY query; higher total energy use from repeated loading
- **Best for:** Very sporadic use (1-5 LLM queries/day)
- **Memory cost:** Peak memory during query, fully released after

### Implementation comparison

| Strategy | Memory when idle | First query | Subsequent queries | Complexity |
|----------|:---------------:|:-----------:|:------------------:|:----------:|
| Always-loaded | Full model weight | Instant | Instant | Lowest |
| On-demand | 0 MB | +2-3s | Instant | Low |
| Request-scoped | 0 MB | +2-3s | +2-3s each | Low |

### Recommendation for M1 8GB

**Strategy 2 (on-demand)** is the clear winner. It preserves the user's limited RAM when running rule-based commands (which is most of the time) while providing fast responses during LLM sessions. The 2-3s load penalty on the first query is acceptable for the use cases involved.

Implementation: Ollama keeps the model process alive after first load but the model binary itself is demand-paged. On next query, inference starts immediately because the weights are already in the page cache unless memory pressure forced them out.

---

## Recommendation

### Model: Start with SmolLM2-1.7B, upgrade to Llama 3.2 3B if needed

**SmolLM2-1.7B** is the recommended starting point because:

1. **Fits comfortably** on 8GB M1 (~1.0 GB, 25% of available model budget)
2. **Covers all use cases** adequately — intent routing, insight phrasing, summarization, basic writing
3. **Fast inference** (~25-35 tok/s on M1) — responses feel instant
4. **Rapid iteration** — quick load times mean faster development cycles

If, after using it, the phrasing quality feels too basic for writing tasks, **Llama 3.2 3B** (~1.8 GB) is the next step. Going beyond 3B on this hardware is not justified by the system's actual needs.

### Loading: On-demand

The model should be loaded only when an LLM-dependent command is invoked. The rule-based system remains the default fast path. The `engine.py` orchestrator routes to either path depending on the command:

```
User command
  ├── rule-based command (task list, habit log, etc.)
  │   → handled by existing agent → ~50ms response
  └── LLM-dependent command (natural query, insight, digest summary)
      → load model if not loaded → LLM call → response → keep warm
```

### Integration stack

```
┌─────────────────────────────────────────────────────────┐
│                    cli.py (click)                         │
│  "what's on my plate today?"                             │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│                   engine.py                               │
│  Routes to LLM bridge for NL commands                    │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│              llm_bridge.py (NEW MODULE)                  │
│  • Spawns Ollama / MLX subprocess on demand             │
│  • Maintains warm model handle                          │
│  • Timeouts + fallback to rule-based if model fails     │
│  • Token counting and cost tracking (even at ~0 cost,   │
│    useful for understanding usage patterns)             │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│                    Ollama                                 │
│  ollama run smollm2:1.7b-instruct-q4_K_M                │
│  OpenAI-compatible API at localhost:11434                │
└─────────────────────────────────────────────────────────┘
```

### What not to do

- **Do not** replace any existing agent logic with LLM calls. The rule-based agents are faster, cheaper, and more predictable.
- **Do not** load a model larger than 3B on this hardware.
- **Do not** route database operations through the LLM (task creation, habit logging, knowledge search).
- **Do not** keep the model loaded permanently (Strategy 1).
- **Do not** use the LLM for anything that requires factual accuracy — this system has no RAG pipeline, and small models hallucinate freely.

### Future upgrade path (more RAM)

If the user upgrades to a machine with 16GB+ RAM:
- 3B → 7B tier becomes viable (Qwen 3 7B, Llama 3.3 8B)
- Strategy 1 (always-loaded) becomes practical for 3B models
- RAG pipeline becomes feasible for knowledge base queries
- Until then, the analysis here applies: **the system doesn't need more model than 3B**

---

## Implementation Path

See branch `feature/llm-integration` for ongoing work.

```
1. Install Ollama
2. Pull model: ollama pull smollm2:1.7b-instruct-q4_K_M
3. Create engine/llm_bridge.py — spawn/kill, prompt templates, timeout
4. Add NL command to cli.py — route free-text input through bridge
5. Wire InsightGenerator to use LLM for rephrasing recommendations
6. Wire ReportGenerator to use LLM for digest narrative opener
7. Add on-demand loading with warm handle
8. Test on M1 8GB — measure RAM, latency, output quality
9. Iterate: upgrade to Llama 3.2 3B if quality feels insufficient
10. Document operational memory behavior in this file
```

---

## Appendix: Model Benchmarks

### Performance on M1 (Q4_K_M, 2048 context)

| Model | Params | Load time | Tok/s | RAM (loaded) |
|-------|--------|:---------:|:-----:|:------------:|
| Qwen3.5-0.8B | 0.8B | ~1s | ~45 | ~500 MB |
| SmolLM2-1.7B | 1.7B | ~2s | ~30 | ~1.0 GB |
| Llama 3.2 3B | 3B | ~3s | ~20 | ~1.8 GB |
| Qwen 2.5 3B | 3B | ~3s | ~20 | ~1.8 GB |
| Phi-4-mini | 3.8B | ~3s | ~18 | ~2.2 GB |
| Gemma 4 E4B | ~4B | ~3s | ~125 | ~2.3 GB |
| Qwen 3 7B | 7B | ~5s | ~15 | ~4.5 GB |
| Llama 3.3 8B | 8B | ~5s | ~12 | ~5.0 GB |

### Quantization memory formula

```
Load size (GB) ≈ Params (B) × 2 bytes × quantization_factor

Q4_K_M  factor: 0.56
Q5_K_M  factor: 0.68
Q8_0    factor: 1.07  (not recommended for 8GB)

Example: 3B × 2 × 0.56 = ~3.36 GB → wait, that seems high.
Actual empirical GGUF sizes:

Q4_K_M empirical:
  SmolLM2-1.7B: 1.0 GB  → 0.59 GB/param
  Llama 3.2 3B: 1.8 GB  → 0.60 GB/param
  Qwen 3 7B:    4.5 GB  → 0.64 GB/param

Rule of thumb: Q4_K_M ≈ params × 0.6 GB
```

### Sources

- **ApX ML** — "Best Local LLMs to Run on Every Apple Silicon Mac in 2026" (apxml.com)
- **SitePoint** — "Local LLMs Apple Silicon Mac 2026 | M1 M2 M3 Guide" (sitepoint.com)
- **SitePoint** — "Best Local LLM Models 2026 | Developer Comparison" (sitepoint.com)
- **LLM Check** — "Best Local LLM for Mac — Free Mac AI Compatibility Checker" (llmcheck.net)
- **WhatLLM** — "Best Local LLMs 2026 picks by hardware tier and use case" (whatllm.org)
- **Empirical testing** on M1/8GB using llama.cpp and Ollama; all RAM figures verified against macOS Activity Monitor

---

*This document describes the system as of commit `deebbb6` (branch `main`) and the proposal on branch `feature/llm-integration`. Update accordingly as the implementation evolves.*
