# Level 2 — Behavior Analytics CLI

**Date**: 2026-05-27
**Status**: Draft Design
**Author**: Sisyphus

---

## TL;DR

Add a `behaviors report` CLI command that reads the `behaviors` table and produces a formatted terminal report with three sections: emotional trends (current vs baseline), emotion-activity co-occurrence, and anomaly detection (statistical outliers). Single new module `engine/analytics/behavior_analytics.py`, no new tables, no new dependencies.

---

## Problem

The `behaviors` table in `self.db` accumulates 25+ structured records from daily note extraction, but the data is invisible — no user-facing output exists. The user cannot currently answer:

- "How many times did I mention 'angry' this week?"
- "What emotions co-occur with 'coded'?"
- "Was yesterday unusual compared to my baseline?"

---

## Scope

### In scope
- Single-file analytics module: `engine/analytics/behavior_analytics.py`
- CLI integration: `behaviors report [--days N]` subcommand in existing `cli.py`
- Three report sections in one command
- Statistical computation in Python (SQLite has no built-in stddev)
- Graceful handling of insufficient data (first few days after launch)

### Non-goals
- No new tables or schema migrations
- No UI, dashboard, or visualization
- No real-time alerts or push notifications
- No cross-table correlation (observations, relationships — deferred)
- No persistence of computed analytics (everything computed on-demand)
- No changes to the extraction pipeline or behaviors schema

---

## Architecture

```
┌─────────────┐     ┌─────────────────────────┐     ┌──────────┐
│  cli.py      │────▶│  behavior_analytics.py  │────▶│ self.db  │
│ (click cmd)  │     │  ── trend_report()      │     │ behaviors│
│              │     │  ── emotion_activity()  │     │ table    │
│              │     │  ── anomaly_detection() │     └──────────┘
│              │     │  ── full_report()       │
└──────┬───────┘     └─────────────────────────┘
       │
       ▼
  stdout (formatted text)
```

Data flow:
1. `cli.py` parses `behaviors report [--days 7]`
2. Instantiates `BehaviorAnalytics(db_manager)`
3. Calls `full_report(days=7)` which runs three internal methods
4. Each method queries `self.db` via `db_manager.query()`, computes stats in Python
5. Returns formatted string; `cli.py` prints to stdout

---

## Module Structure

### `engine/analytics/__init__.py`
Empty init (package marker).

### `engine/analytics/behavior_analytics.py`

```python
class BehaviorAnalytics:
    def __init__(self, db=None):
        # Accept optional db_manager override for testing
        self.db = db or default_db_manager

    def full_report(self, days: int = 7) -> str:
        """Combined report: trends + correlation + anomalies."""

    def trend_report(self, days: int = 7) -> str:
        """Frequency per emotion/activity this period vs baseline."""

    def emotion_activity_correlation(self, days: int = 30) -> str:
        """Co-occurrence matrix: on days activity X appears, which emotions co-occur?"""

    def anomaly_detection(self, days: int = 30) -> str:
        """Flag words with frequency > 2 std from mean (z-score)."""
```

### Statistical approach (Python)

```
For each unique behavior word:
  - daily_counts = [sum(frequency) per distinct observed_date in window]
  - mean = avg(daily_counts)
  - std  = population std(daily_counts)  (statistics.stdev with fallback)
  - z-score = (current_period_count - mean) / max(std, 0.01)
  - anomaly if z-score > 2.0
```

Edge cases:
- 0 distinct dates → skip word entirely
- 1 distinct date → stddev is undefined, skip anomaly for that word
- 2 distinct dates → use population stddev (`statistics.pstdev`), anomaly flag if both values differ by >2×
- 3+ distinct dates → sample stddev (`statistics.stdev`), z-score > 2.0 flags anomaly

### SQL queries

**Trend (current vs baseline):**
```sql
-- Current period: counts per word
SELECT response, behavior_type, SUM(frequency) as total
FROM behaviors
WHERE observed_date >= datetime('now', '-N days')
GROUP BY response

-- Baseline: avg daily count per word (previous N days, offset by N)
SELECT response, AVG(daily) as avg_daily, COUNT(DISTINCT date(observed_date)) as days_with_data
FROM (
  SELECT response, date(observed_date) as d, SUM(frequency) as daily
  FROM behaviors
  WHERE observed_date >= datetime('now', ?)
    AND observed_date < datetime('now', ?)
  GROUP BY response, date(observed_date)
) GROUP BY response
```

**Emotion-Activity co-occurrence:**
```sql
SELECT e.response as emotion, a.response as activity, COUNT(*) as together
FROM behaviors e
JOIN behaviors a ON date(e.observed_date) = date(a.observed_date)
WHERE e.behavior_type = 'emotion'
  AND a.behavior_type = 'activity'
GROUP BY e.response, a.response
ORDER BY together DESC
```

**Daily counts for anomaly:**
```sql
SELECT response, date(observed_date) as day, SUM(frequency) as daily
FROM behaviors
WHERE observed_date >= datetime('now', '-N days')
GROUP BY response, date(observed_date)
ORDER BY response, day
```

---

## CLI Interface

```bash
python cli.py behaviors report --days 7
```

Integration: add a `behaviors` click group to `cli.py` with a `report` subcommand.

---

## Output Format

```
╔══════════════════════════════════════════════════════════════╗
║           Behavior Report — Last 7 Days                      ║
╚══════════════════════════════════════════════════════════════╝

── Emotional Trends ──
                         This Window    Baseline      Change
angry                            4         1.0        +300%
anxious                          3         1.5        +100%
worried                          6         0.0         NEW
sad                              5         0.0         NEW
happy                            1         2.0         -50%
...                                          ...        ...

── Activity Trends ──
                         This Window    Baseline      Change
coded                            2         0.5        +300%
learned                          2         0.0         NEW

── Emotion × Activity Correlation (last 30 days) ──
Activity    Co-occurring Emotions (with co-occurrence count)
─────────   ─────────────────────────────────────────────────
coded        focused (1), angry (1), anxious (1)
learned      sad (1)

── Anomaly Detection ──
(no anomalies detected — needs at least 3 distinct dates per word)
```

If insufficient data, sections show a message instead of a table:
```
── Emotional Trends ──
(insufficient data — need at least 2 distinct days to compute trends)
```

---

## Error Handling

| Condition | Behavior |
|---|---|
| behaviors table empty | Each section shows "no data" message |
| Only 1 distinct date in window | Trends: "insufficient data" |
| Only 1-2 distinct dates for a word | Anomaly: skip that word |
| DB connection fails | `db_manager` raises; CLI shows error |
| No CLI args | Default to `--days 7` |

---

## Testing Strategy

**Unit tests** in `engine/tests/test_behavior_analytics.py`:
1. Insert synthetic behavior records across multiple dates via `db_manager`
2. Verify trend_report returns expected numbers
3. Verify emotion_activity_correlation returns correct co-occurrences
4. Verify anomaly_detection flags known outliers
5. Verify graceful handling of empty table
6. Verify graceful handling of single-date data

Test data pattern:
```python
test_db = sqlite3.connect(":memory:")  # or use db_manager with test schema
# Insert records for "angry" on 5 different days with varying frequency
# Insert records for "coded" + "angry" on same date → verify co-occurrence
```

---

## File Changes

| File | Action |
|---|---|
| `engine/analytics/__init__.py` | CREATE (empty) |
| `engine/analytics/behavior_analytics.py` | CREATE (~200 lines) |
| `engine/tests/test_behavior_analytics.py` | CREATE |
| `engine/cli.py` | MODIFY — add `behaviors` group + `report` command |

---

## Rollout

1. Create module + tests (TDD)
2. Run tests to verify
3. Add CLI command
4. Run `behaviors report --days 30` to verify against real data
5. Commit
