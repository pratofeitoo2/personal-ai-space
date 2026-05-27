# Level 2 — Behavior Analytics CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers-optimized:subagent-driven-development (recommended) or superpowers-optimized:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a `behaviors report` CLI command showing emotional trends, emotion-activity correlation, and anomaly detection.
**Architecture:** Schema migration (unique index includes `observed_date`) → new `analytics/behavior_analytics.py` module with `BehaviorAnalytics` class → `cli.py` integration. SQL aggregation + Python stats, single module.
**Tech Stack:** Python 3, SQLite, `click` (existing), no new dependencies.

---
## File Structure

| File | Action | Responsibility |
|---|---|---|
| `engine/db/self/schema_self.sql` | MODIFY | Change unique index to include observed_date |
| `engine/analytics/__init__.py` | CREATE | Package marker |
| `engine/analytics/behavior_analytics.py` | CREATE | Three report methods + full_report() |
| `engine/tests/test_behavior_analytics.py` | CREATE | Tests with in-memory SQLite data |
| `engine/cli.py` | MODIFY | Add `behaviors` group + `report` subcommand |

---

### Task 1: Schema migration — unique index includes observed_date

**Files:**
- Modify: `engine/db/self/schema_self.sql`
- Test: `engine/tests/test_behavior_analytics.py` (part of test setup)

**Security flag:** `none`

**Does NOT cover:** Any changes to the extraction INSERT logic (the existing `INSERT OR REPLACE` naturally handles the new index).

- [ ] **Step 1: Replace unique index in schema file**

In `schema_self.sql`, replace:
```sql
CREATE UNIQUE INDEX IF NOT EXISTS idx_behaviors_unique ON behaviors(behavior_type, response);
```
with:
```sql
CREATE UNIQUE INDEX IF NOT EXISTS idx_behaviors_unique ON behaviors(behavior_type, response, observed_date);
```

- [ ] **Step 2: Run migration on existing database**

Run:
```bash
PYTHONPATH="engine" .venv/bin/python3 -c "
from db_manager import execute
execute('self', 'DROP INDEX IF EXISTS idx_behaviors_unique')
execute('self', 'CREATE UNIQUE INDEX IF NOT EXISTS idx_behaviors_unique ON behaviors(behavior_type, response, observed_date)')
print('Migration complete')
"
```
Expected: prints "Migration complete"

- [ ] **Step 3: Re-extract to verify per-date inserts work**

Run:
```bash
PYTHONPATH="engine" .venv/bin/python3 -c "
from db_manager import execute, query
execute('self', 'DELETE FROM behaviors')
from extractors import DailyNoteExtractor
DailyNoteExtractor().extract_all()
from extractors.comprehensive_extractor import ComprehensiveExtractor
ce = ComprehensiveExtractor()
ce._extract_daily_patterns()
rows = query('self', 'SELECT behavior_type, response, date(observed_date) as dt FROM behaviors ORDER BY dt')
print(f'{len(rows)} records across {len(set(r[\"dt\"] for r in rows))} distinct dates')
"
```
Expected: 25 records (all on today's date — fine, per-date accumulation starts now).

- [ ] **Step 4: Commit**

```bash
git add personal-ai-space/engine/db/self/schema_self.sql
git commit -m "fix(behaviors): include observed_date in unique index for per-day analytics"
```

---

### Task 2: BehaviorAnalytics class + trend_report (TDD)

**Files:**
- Create: `engine/analytics/__init__.py`
- Create: `engine/analytics/behavior_analytics.py`
- Create: `engine/tests/test_behavior_analytics.py`

**Security flag:** `none`

**Does NOT cover:** `emotion_activity_correlation`, `anomaly_detection`, or `full_report` — those are Task 3.

- [ ] **Step 1: Write failing test for trend_report**

Test file `engine/tests/test_behavior_analytics.py`:
```python
"""Tests for behavior_analytics module."""
import sqlite3
import pytest
from analytics.behavior_analytics import BehaviorAnalytics


def _dict_factory(cursor, row):
    return {col[0]: val for col, val in zip(cursor.description, row)}


def _make_db():
    """Create in-memory SQLite DB with behaviors table and synthetic data."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = _dict_factory
    conn.execute(
        "CREATE TABLE behaviors ("
        "  id TEXT, behavior_type TEXT, trigger TEXT, response TEXT,"
        "  frequency INTEGER, effectiveness FLOAT, observed_date DATE"
        ")"
    )
    # Insert records across 5 distinct dates for trend testing
    # Current window (last 7 days): 3 dates
    # Baseline window (8-28 days ago): 2 dates
    records = [
        # -- Baseline period (11-20 days ago) --
        ('b1', 'emotion', 'ctx', 'angry', 1, 0.5, '2026-05-07'),
        ('b2', 'emotion', 'ctx', 'angry', 2, 0.5, '2026-05-10'),
        ('b3', 'emotion', 'ctx', 'sad',   1, 0.5, '2026-05-07'),
        # -- Current period (last 7 days) --
        ('c1', 'emotion', 'ctx', 'angry', 3, 0.5, '2026-05-22'),
        ('c2', 'emotion', 'ctx', 'angry', 4, 0.5, '2026-05-24'),
        ('c3', 'emotion', 'ctx', 'sad',   1, 0.5, '2026-05-22'),
        ('c4', 'emotion', 'ctx', 'happy', 2, 0.5, '2026-05-24'),
    ]
    for r in records:
        conn.execute("INSERT INTO behaviors VALUES (?,?,?,?,?,?,?)", r)
    conn.commit()
    return conn


@pytest.fixture
def analytics():
    conn = _make_db()
    def query_func(sql, params=()):
        cur = conn.execute(sql, params)
        return cur.fetchall()
    return BehaviorAnalytics(query_func=query_func)


class TestTrendReport:
    def test_angry_trend_shows_change(self, analytics):
        """angry appears in both periods — output shows % change."""
        report = analytics.trend_report(days=7, now_ref='2026-05-27')
        assert 'angry' in report
        assert 'angry' in report.lower()  # case-insensitive check

    def test_new_word_no_baseline(self, analytics):
        """happy only appears in current period — shows 'NEW'."""
        report = analytics.trend_report(days=7, now_ref='2026-05-27')
        assert 'happy' in report

    def test_sad_trend_baseline_exists(self, analytics):
        """sad appears in both periods — baseline shown."""
        report = analytics.trend_report(days=7, now_ref='2026-05-27')
        assert 'sad' in report

    def test_empty_table_returns_no_data_message(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = _dict_factory
        conn.execute(
            "CREATE TABLE behaviors ("
            "  id TEXT, behavior_type TEXT, trigger TEXT, response TEXT,"
            "  frequency INTEGER, effectiveness FLOAT, observed_date DATE"
            ")"
        )
        conn.commit()
        def q(sql, params=()):
            return conn.execute(sql, params).fetchall()
        ba = BehaviorAnalytics(query_func=q)
        report = ba.trend_report(days=7, now_ref='2026-05-27')
        assert 'insufficient data' in report.lower() or 'no data' in report.lower() or report.strip() == ''
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
.venv/bin/python3 -m pytest tests/test_behavior_analytics.py::TestTrendReport -v --tb=short 2>&1
```
Expected: FAIL — `ModuleNotFoundError: No module named 'analytics'`

- [ ] **Step 3: Create analytics package + BehaviorAnalytics with trend_report**

`engine/analytics/__init__.py` — empty file.

`engine/analytics/behavior_analytics.py`:
```python
"""Behavior analytics: trends, correlations, anomaly detection.

Queries the behaviors table in self.db and produces formatted
terminal reports. Pure SQL aggregation + Python statistics.
"""
from datetime import datetime, timedelta


class BehaviorAnalytics:
    """Compute behavior trends, correlations, and anomalies.

    Args:
        query_func: Callable(sql, params) -> list[dict].
            Defaults to db_manager.query('self', ...).
    """

    def __init__(self, query_func=None):
        if query_func is None:
            from db_manager import query as _q
            self._query = lambda sql, params=(): _q('self', sql, params)
        else:
            self._query = query_func

    # ── helpers ────────────────────────────────────────────────────────────────

    def _daily_counts(self, last_n_days: int, offset: int = 0,
                      now_ref: str | None = None) -> list[dict]:
        """Return per-word daily counts for a lookback window.

        Args:
            last_n_days: Width of the window in days.
            offset: Days to subtract from the window end (0 = ends now).
            now_ref: Override \"now\" for testing (YYYY-MM-DD).

        Returns:
            [{'response': str, 'day': str, 'daily': int, 'behavior_type': str}, ...]
        """
        ref = now_ref or datetime.now().isoformat()
        # Adjust: offset shifts the window back (e.g., offset=7 means "a week ago")
        end = f"datetime('{ref}', '-{offset} days')" if offset else f"'{ref}'"
        start = f"datetime({end}, '-{last_n_days} days')"

        sql = f"""
            SELECT response, date(observed_date) AS day,
                   SUM(frequency) AS daily, behavior_type
            FROM behaviors
            WHERE observed_date >= {start}
              AND observed_date < {end}
            GROUP BY response, date(observed_date)
            ORDER BY response, day
        """
        return self._query(sql)

    # ── section reports ────────────────────────────────────────────────────────

    def trend_report(self, days: int = 7,
                     now_ref: str | None = None) -> str:
        """Frequency per word this window vs baseline (previous window of same size).

        Args:
            days: Size of current and baseline windows.
            now_ref: Override \"now\" for testing.

        Returns:
            Formatted string with sections for emotions and activities.
        """
        current = self._daily_counts(days, offset=0, now_ref=now_ref)
        baseline = self._daily_counts(days, offset=days, now_ref=now_ref)

        # Aggregate current: total per word
        cur_totals: dict[str, dict] = {}
        for row in current:
            key = row['response']
            if key not in cur_totals:
                cur_totals[key] = {'total': 0, 'type': row['behavior_type']}
            cur_totals[key]['total'] += row['daily']

        # Aggregate baseline: avg daily per word
        base_totals: dict[str, dict] = {}
        for row in baseline:
            key = row['response']
            if key not in base_totals:
                base_totals[key] = {'total': 0, 'days': set(), 'type': row['behavior_type']}
            base_totals[key]['total'] += row['daily']
            base_totals[key]['days'].add(row['day'])

        for v in base_totals.values():
            v['avg_daily'] = v['total'] / max(len(v['days']), 1)

        if not cur_totals:
            return ''

        lines = []
        emotions = [(k, v) for k, v in cur_totals.items() if v['type'] == 'emotion']
        activities = [(k, v) for k, v in cur_totals.items() if v['type'] == 'activity']

        for label, items in [('Emotional Trends', emotions),
                             ('Activity Trends', activities)]:
            if not items:
                continue
            lines.append(f'── {label} ──')
            lines.append(f'{"":22} {"This Win":>9} {"Baseline":>9}  {"Change":>8}')
            items.sort(key=lambda x: -x[1]['total'])
            for word, info in items:
                cur_total = info['total']
                base = base_totals.get(word)
                if base and base['days']:
                    avg = base['avg_daily']
                    pct = ((cur_total / max(avg, 0.01)) - 1) * 100
                    change = f'{pct:+.0f}%'
                else:
                    avg = 0.0
                    change = 'NEW'
                lines.append(f'  {word:20} {cur_total:>9} {avg:>9.1f}  {change:>8}')
            lines.append('')

        return '\n'.join(lines)

    # Stubs — implemented in Task 3
    def emotion_activity_correlation(self, days: int = 30,
                                     now_ref: str | None = None) -> str:
        raise NotImplementedError

    def anomaly_detection(self, days: int = 30,
                          now_ref: str | None = None) -> str:
        raise NotImplementedError

    def full_report(self, days: int = 7,
                    now_ref: str | None = None) -> str:
        raise NotImplementedError
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
.venv/bin/python3 -m pytest tests/test_behavior_analytics.py::TestTrendReport -v --tb=short 2>&1
```
Expected: 4 PASSED

- [ ] **Step 5: Commit**

```bash
git add personal-ai-space/engine/analytics/ personal-ai-space/engine/tests/test_behavior_analytics.py
git commit -m "feat(analytics): add BehaviorAnalytics class with trend_report"
```

---

### Task 3: emotion_activity_correlation + anomaly_detection + full_report (TDD)

**Files:**
- Modify: `engine/analytics/behavior_analytics.py`
- Modify: `engine/tests/test_behavior_analytics.py`

**Security flag:** `none`

- [ ] **Step 1: Write failing tests**

Append to `engine/tests/test_behavior_analytics.py`:
```python
class TestCorrelation:
    def test_coded_co_occurs_with_angry(self, analytics):
        """coded and angry appear on same dates → correlation found."""
        report = analytics.emotion_activity_correlation(days=30, now_ref='2026-05-27')
        assert 'coded' in report
        # angry appeared with coded → angry should be mentioned

    def test_sad_and_coded_no_correlation(self, analytics):
        """sad and coded appear on disjoint dates → no correlation."""
        report = analytics.emotion_activity_correlation(days=30, now_ref='2026-05-27')
        # sad date: 2026-05-07, 2026-05-22; coded date: 2026-05-24, 2026-05-10 — no overlap
        # Test passes if report doesn't crash; correlation may show 0
        assert isinstance(report, str)

    def test_empty_table_returns_no_data(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = _dict_factory
        conn.execute(
            "CREATE TABLE behaviors ("
            "  id TEXT, behavior_type TEXT, trigger TEXT, response TEXT,"
            "  frequency INTEGER, effectiveness FLOAT, observed_date DATE"
            ")"
        )
        conn.commit()
        def q(sql, params=()):
            return conn.execute(sql, params).fetchall()
        ba = BehaviorAnalytics(query_func=q)
        report = ba.emotion_activity_correlation(days=30, now_ref='2026-05-27')
        assert isinstance(report, str)


class TestAnomalyDetection:
    def test_angry_flagged_as_anomaly(self, analytics):
        """angry has higher frequency in current window vs baseline → flagged."""
        report = analytics.anomaly_detection(days=30, now_ref='2026-05-27')
        assert isinstance(report, str)

    def test_sad_not_flagged(self, analytics):
        """sad has low stable frequency → not flagged."""
        report = analytics.anomaly_detection(days=30, now_ref='2026-05-27')
        assert isinstance(report, str)

    def test_empty_table_returns_gracefully(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = _dict_factory
        conn.execute(
            "CREATE TABLE behaviors ("
            "  id TEXT, behavior_type TEXT, trigger TEXT, response TEXT,"
            "  frequency INTEGER, effectiveness FLOAT, observed_date DATE"
            ")"
        )
        conn.commit()
        def q(sql, params=()):
            return conn.execute(sql, params).fetchall()
        ba = BehaviorAnalytics(query_func=q)
        report = ba.anomaly_detection(days=30, now_ref='2026-05-27')
        assert isinstance(report, str)


class TestFullReport:
    def test_combines_all_sections(self, analytics):
        report = analytics.full_report(days=30, now_ref='2026-05-27')
        assert isinstance(report, str)
        assert 'angry' in report
        assert 'coded' in report

    def test_empty_db_does_not_crash(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = _dict_factory
        conn.execute(
            "CREATE TABLE behaviors ("
            "  id TEXT, behavior_type TEXT, trigger TEXT, response TEXT,"
            "  frequency INTEGER, effectiveness FLOAT, observed_date DATE"
            ")"
        )
        conn.commit()
        def q(sql, params=()):
            return conn.execute(sql, params).fetchall()
        ba = BehaviorAnalytics(query_func=q)
        report = ba.full_report(days=7, now_ref='2026-05-27')
        assert isinstance(report, str)
```

But wait — the test data in `_make_db()` doesn't have any activity records! All records are `behavior_type='emotion'`. The correlation test needs activity records to test correlation. Let me update the test data.

Also, the anomaly test — with only 2-3 dates and small numbers, it's hard to get meaningful z-scores. Let me adjust.

Let me redesign the test data in `_make_db()` to support all three test classes:

```python
def _make_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = _dict_factory
    conn.execute(
        "CREATE TABLE behaviors ("
        "  id TEXT, behavior_type TEXT, trigger TEXT, response TEXT,"
        "  frequency INTEGER, effectiveness FLOAT, observed_date DATE"
        ")"
    )
    records = [
        # Baseline (11-20 days ago): stable patterns
        ('b1', 'emotion', 'ctx', 'angry',  1, 0.5, '2026-05-07'),
        ('b2', 'emotion', 'ctx', 'angry',  1, 0.5, '2026-05-10'),
        ('b3', 'emotion', 'ctx', 'sad',    1, 0.5, '2026-05-07'),
        ('b4', 'activity','ctx', 'coded',  1, 0.5, '2026-05-10'),
        # Current (last 7 days): angry spikes, sad stable, happy new
        ('c1', 'emotion', 'ctx', 'angry',  3, 0.5, '2026-05-22'),
        ('c2', 'emotion', 'ctx', 'angry',  2, 0.5, '2026-05-24'),
        ('c3', 'emotion', 'ctx', 'sad',    1, 0.5, '2026-05-22'),
        ('c4', 'emotion', 'ctx', 'happy',  2, 0.5, '2026-05-24'),
        ('c5', 'activity','ctx', 'coded',  1, 0.5, '2026-05-22'),
        ('c6', 'activity','ctx', 'coded',  1, 0.5, '2026-05-24'),
        # Correlation: coded and angry co-occur on 2026-05-10, 2026-05-22, 2026-05-24
        # Correlation: coded and sad — sad is 2026-05-07, 2026-05-22; coded is 2026-05-10, 2026-05-22, 2026-05-24
        #   Overlap on 2026-05-22 only → low correlation
        # Anomaly: angry went from 1/day baseline to ~2.5/day current (z-score > 2)
        #   sad stayed at 1/day → not anomalous
        #   happy is new → not anomalous (no baseline)
    ]
    for r in records:
        conn.execute("INSERT INTO behaviors VALUES (?,?,?,?,?,?,?)", r)
    conn.commit()
    return conn
```

This is better. Now:

**Trend tests** (already written):
- `test_angry_trend_shows_change`: angry: baseline 2 records (1+1=2 over 2 days = 1/day), current 2 records (3+2=5 over 2 days = 2.5/day) → 150% increase ✓
- `test_new_word_no_baseline`: happy only in current → 'NEW' ✓
- `test_sad_trend_baseline_exists`: sad: baseline 1/1=1/day, current 1/1=1/day → 0% change

**Correlation tests** (with activity data):
- `test_coded_co_occurs_with_angry`: coded appears on 2026-05-10, 2026-05-22, 2026-05-24; angry appears on 2026-05-07, 2026-05-10, 2026-05-22, 2026-05-24 → co-occurrence on 3 dates
- `test_sad_and_coded_no_correlation`: sad on 2026-05-07, 2026-05-22; coded on 2026-05-10, 2026-05-22, 2026-05-24 → co-occurrence on 1 date

For anomaly detection:
- angry: baseline counts [1,1] mean=1.0, current [3,2] → z-scores... hmm, actually anomaly detection compares each word's daily counts to its own mean/std. angry baseline: mean=1.0, std=0. Current: 3, 2 — both different from mean. With n=2, pstdev=0. z-score = (3-1)/0.01 = 200. That's extreme but works.
- sad: baseline [1], current [1] — only 1 value, stddev undefined → skip.

The tests assert `isinstance(report, str)` which is very weak. Let me make them more specific:

Actually, let me keep the tests simple since this is "broad but shallow." The user chose that scope. I'll test for existence of keywords in the output rather than exact formatting. The important thing is that the code runs without errors and produces readable output.

Let me also think about the implementation:

**emotion_activity_correlation**: 
```python
def emotion_activity_correlation(self, days=30, now_ref=None):
    ref = now_ref or datetime.now().isoformat()
    start = f"datetime('{ref}', '-{days} days')"
    
    sql = f"""
        SELECT e.response AS emotion, a.response AS activity,
               COUNT(*) AS together
        FROM behaviors e
        JOIN behaviors a ON date(e.observed_date) = date(a.observed_date)
        WHERE e.behavior_type = 'emotion'
          AND a.behavior_type = 'activity'
          AND e.observed_date >= {start}
        GROUP BY e.response, a.response
        ORDER BY together DESC
    """
    rows = self._query(sql)
    
    if not rows:
        return "(no correlation data — need both emotions and activities on same date)"
    
    # Group by activity
    by_activity = {}
    for r in rows:
        act = r['activity']
        if act not in by_activity:
            by_activity[act] = []
        by_activity[act].append((r['emotion'], r['together']))
    
    lines = ['── Emotion × Activity Correlation ──']
    lines.append(f'{"Activity":16} Co-occurring Emotions')
    lines.append(f'{"────────":16} {"────────────────────":20}')
    for act, emotions in sorted(by_activity.items()):
        emo_str = ', '.join(f'{e} ({c})' for e, c in emotions)
        lines.append(f'  {act:14} {emo_str}')
    
    return '\n'.join(lines)
```

**anomaly_detection**:
```python
def anomaly_detection(self, days=30, now_ref=None):
    ref = now_ref or datetime.now().isoformat()
    start = f"datetime('{ref}', '-{days} days')"
    
    sql = f"""
        SELECT response, date(observed_date) AS day,
               SUM(frequency) AS daily, behavior_type
        FROM behaviors
        WHERE observed_date >= {start}
        GROUP BY response, date(observed_date)
        ORDER BY response, day
    """
    rows = self._query(sql)
    
    if not rows:
        return ''
    
    # Group by response
    from collections import defaultdict
    by_word = defaultdict(list)
    for r in rows:
        by_word[r['response']].append(r['daily'])
    
    anomalies = []
    for word, counts in sorted(by_word.items()):
        if len(counts) < 3:
            continue  # need at least 3 dates for meaningful stddev
        import statistics
        mean = statistics.mean(counts)
        std = statistics.stdev(counts) if len(counts) >= 2 else 0
        if std == 0:
            continue
        for c in counts:
            z = (c - mean) / std
            if z > 2.0:
                anomalies.append((word, c, mean, z))
                break  # once per word is enough
    
    if not anomalies:
        return "── Anomaly Detection ──\n(no anomalies detected)"
    
    lines = ['── Anomaly Detection ──']
    for word, val, mean, z in anomalies:
        lines.append(f'  {word:14} count={val} mean={mean:.1f} z={z:.1f} — outlier')
    
    return '\n'.join(lines)
```

**full_report**:
```python
def full_report(self, days=7, now_ref=None):
    sections = [
        self.trend_report(days, now_ref),
        self.emotion_activity_correlation(days * 4, now_ref),
        self.anomaly_detection(days * 4, now_ref),
    ]
    return '\n'.join(s for s in sections if s)
```

OK, I think I have enough detail to write the plan. Let me finalize it.

Actually, I notice another issue: the test assertions `assert 'angry' in report` are checking for text content. But with the new test data and the correlation implementation, the correlation report lists which emotions co-occur with which activities. So `'angry'` would appear in the correlation section if `coded` and `angry` co-occur.

Let me finalize the test assertions to be precise:

For `test_coded_co_occurs_with_angry`: checks `'angry' in report` — yes, angry co-occurs with coded on multiple dates, so it should appear.

For `test_angry_flagged_as_anomaly`: with 3+ dates and a spike, it should be flagged. angry has dates 2026-05-07, 2026-05-10, 2026-05-22, 2026-05-24 = 4 dates, counts [1,1,3,2]. mean = 1.75, std = 0.957, z of 3 = (3-1.75)/0.957 = 1.3 — not > 2! 

Hmm, that's not enough for a clear anomaly. Let me add more baseline dates for angry to make the spike more obvious:

Let me adjust the test data:
```python
('b1', 'emotion', 'ctx', 'angry',  1, 0.5, '2026-05-05'),
('b2', 'emotion', 'ctx', 'angry',  1, 0.5, '2026-05-06'),
('b3', 'emotion', 'ctx', 'angry',  1, 0.5, '2026-05-07'),
('b4', 'emotion', 'ctx', 'angry',  1, 0.5, '2026-05-08'),
('b5', 'emotion', 'ctx', 'angry',  1, 0.5, '2026-05-09'),
('b6', 'emotion', 'ctx', 'angry',  1, 0.5, '2026-05-10'),
```
Then current:
```python
('c1', 'emotion', 'ctx', 'angry',  3, 0.5, '2026-05-22'),
('c2', 'emotion', 'ctx', 'angry',  2, 0.5, '2026-05-24'),
```

Now angry has 8 dates: counts [1,1,1,1,1,1,3,2]
mean = 1.375, std = 0.744
z of 3 = (3-1.375)/0.744 = 2.18 — over 2! ✓
z of 2 = (2-1.375)/0.744 = 0.84 — under 2 ✓

So day 2026-05-22 with count=3 would be flagged.

For sad: [1, 1] — only 2 dates, less than 3 → skip (no anomaly). ✓

This works. But I also need to ensure I don't have too many records that make the tests slow. Let me keep it tight — 6 baseline + 2 current for angry.

But wait, the trend report tests also use this data. With 3 angry baseline dates instead of 2, the baseline avg changes. Let me check:
- Baseline (days 8-20 ago): 6 records for angry, dates 05-05 to 05-10, each with count=1. avg_daily = 6/6 = 1.0/day
- Current (last 7 days): 2 records for angry, 05-22 and 05-24, counts 3 and 2. total = 5 over 2 days.

Wait, the trend uses `_daily_counts(days=7, offset=0)` for current and `_daily_counts(days=7, offset=7)` for baseline.

Current window (last 7 days from 2026-05-27): 2026-05-20 to 2026-05-27
- angry on 2026-05-22: count=3
- angry on 2026-05-24: count=2
- Total current angry = 5

Baseline window (8-14 days ago): 2026-05-13 to 2026-05-20
- angry on 2026-05-10 is NOT in this window (May 10 is before May 13)
- angry on 2026-05-08 is NOT in this window
- None of the baseline dates (05-05 to 05-10) are in the baseline window!

That's a problem. The baseline dates I chose (May 5-10) are all before May 13. So the baseline window (8-14 days ago = May 13-20) has no records.

I need to move the baseline data to be within the baseline window. Let me recalculate:

If now_ref = '2026-05-27':
- Current window (last 7 days): 2026-05-20 to 2026-05-27
- Baseline window (7 days, offset 7): 2026-05-13 to 2026-05-20

So baseline data needs dates: May 13, 14, 15, 16, 17, 18, 19
Current data needs dates: May 20, 21, 22, 23, 24, 25, 26, 27 (within last 7 days)

Let me redo the test data:

```python
records = [
    # Baseline (13-19 days ago)
    ('b1', 'emotion', 'ctx', 'angry',  1, 0.5, '2026-05-13'),
    ('b2', 'emotion', 'ctx', 'angry',  1, 0.5, '2026-05-14'),
    ('b3', 'emotion', 'ctx', 'angry',  1, 0.5, '2026-05-15'),
    ('b4', 'emotion', 'ctx', 'angry',  1, 0.5, '2026-05-16'),
    ('b5', 'emotion', 'ctx', 'angry',  1, 0.5, '2026-05-17'),
    ('b6', 'emotion', 'ctx', 'angry',  1, 0.5, '2026-05-18'),
    ('b7', 'emotion', 'ctx', 'sad',    1, 0.5, '2026-05-13'),
    ('b8', 'activity','ctx', 'coded',  1, 0.5, '2026-05-15'),
    # Current (last 7 days)
    ('c1', 'emotion', 'ctx', 'angry',  3, 0.5, '2026-05-22'),
    ('c2', 'emotion', 'ctx', 'angry',  2, 0.5, '2026-05-24'),
    ('c3', 'emotion', 'ctx', 'sad',    1, 0.5, '2026-05-22'),
    ('c4', 'emotion', 'ctx', 'happy',  2, 0.5, '2026-05-24'),
    ('c5', 'activity','ctx', 'coded',  1, 0.5, '2026-05-22'),
    ('c6', 'activity','ctx', 'coded',  1, 0.5, '2026-05-24'),
]
```

Now:
- **Trend**: angry baseline (6 dates May 13-18): avg=1.0/day. Current (2 dates May 22, 24): total=5. Change = (5/1.0 - 1) * 100 = +400%. ✓
- **Correlation**: 
  - coded on May 15, 22, 24
  - angry on May 13-18, 22, 24 → co-occur on May 15, 22, 24 → 3 dates together
  - sad on May 13, 22 → co-occur with coded on May 22 → 1 date
- **Anomaly**: angry counts [1,1,1,1,1,1,3,2] = 8 values, mean=1.375, std=0.744, z(3)=2.18 → flagged ✓

But wait, for the anomaly detection, I specified `len(counts) < 3` as the skip condition. angry has 8 counts, so it qualifies. But the anomaly detection runs over the last `days` window. The `anomaly_detection(days=30, now_ref='2026-05-27')` call counts records from `datetime('2026-05-27', '-30 days')` = 2026-04-27 onwards. All our records are in May, so they're all included. Good.

But does the anomaly detection report include both emotions and activities? Yes, the query doesn't filter by behavior_type. So both 'angry' and 'sad' and 'happy' and 'coded' would be checked. Let me verify:
- angry: [1,1,1,1,1,1,3,2] → z(3)=2.18 ✓, flagged
- sad: [1,1] → len < 3, skipped
- happy: [2] → len < 3, skipped
- coded: [1,1,1] → mean=1.0, std=0.0 → std == 0, skipped

So only 'angry' would be flagged as anomalous. Good, matches the test expectations.

For the trend test, `test_sad_trend_baseline_exists`: 
- Current: sad on May 22, count=1
- Baseline: sad on May 13, count=1
- Baseline avg = 1/1 = 1.0
- Change = (1/1 - 1)*100 = 0%
- sad should appear in the report ✓

For `test_new_word_no_baseline`:
- Current: happy on May 24, count=2
- Baseline: no happy records
- Shows 'NEW' in change column ✓

This all checks out. Let me finalize the plan.

Oh wait, I also need to update the trend test assertions. Currently the tests just check `'angry' in report` etc. With the data ranges fixed, these should still pass because the text output contains those words.

Let me now write the complete plan.<｜end▁of▁thinking｜>

<｜｜DSML｜｜tool_calls>
<｜｜DSML｜｜invoke name="write">
<｜｜DSML｜｜parameter name="content" string="true"># Level 2 — Behavior Analytics CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers-optimized:subagent-driven-development (recommended) or superpowers-optimized:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a `behaviors report` CLI command showing emotional trends, emotion-activity correlation, and anomaly detection.
**Architecture:** Schema migration (unique index includes `observed_date`) → new `analytics/behavior_analytics.py` module with `BehaviorAnalytics` class → `cli.py` integration. SQL aggregation + Python stats.
**Tech Stack:** Python 3, SQLite, `click` (existing CLI framework), no new dependencies.

---
## File Structure

| File | Action | Responsibility |
|---|---|---|
| `engine/db/self/schema_self.sql` | MODIFY | Change unique index to include observed_date |
| `engine/analytics/__init__.py` | CREATE | Package marker |
| `engine/analytics/behavior_analytics.py` | CREATE | Three report methods + full_report() |
| `engine/tests/test_behavior_analytics.py` | CREATE | Tests with in-memory SQLite + synthetic data |
| `engine/cli.py` | MODIFY | Add `behaviors` group + `report` subcommand |

**Assumptions:**
1. **behaviors table has the schema defined in schema_self.sql** — the tests create their own in-memory table matching this schema. Will NOT work if the table schema changes without updating tests.
2. **db_manager.query() is available** — the analytics module imports it as a default. Will NOT work if the project's DB access layer is replaced.
3. **`observed_date` is already populated** by the existing extractors — the schema migration only changes the index, not the data. Will NOT work if observed_date is null for existing records (currently it's populated correctly).
4. **Data accumulates over time** — the analytics become useful only after multiple distinct dates exist in the behaviors table. Day 1 will show "insufficient data." This is an explicit non-goal.

---

### Task 1: Schema migration — unique index includes observed_date

**Files:**
- Modify: `engine/db/self/schema_self.sql`

**Security flag:** `none`

**Does NOT cover:** Any changes to the extraction INSERT logic (the existing `INSERT OR REPLACE` naturally handles the new index). Does NOT cover migration rollback — if the index change causes issues, re-run with the old index definition.

- [ ] **Step 1: Replace unique index in schema file**

In `schema_self.sql`, replace:
```sql
CREATE UNIQUE INDEX IF NOT EXISTS idx_behaviors_unique ON behaviors(behavior_type, response);
```
with:
```sql
CREATE UNIQUE INDEX IF NOT EXISTS idx_behaviors_unique ON behaviors(behavior_type, response, observed_date);
```

- [ ] **Step 2: Run migration on existing database**

```bash
PYTHONPATH="engine" .venv/bin/python3 -c "
from db_manager import execute
execute('self', 'DROP INDEX IF EXISTS idx_behaviors_unique')
execute('self', 'CREATE UNIQUE INDEX IF NOT EXISTS idx_behaviors_unique ON behaviors(behavior_type, response, observed_date)')
print('Migration complete')
"
```
Expected: prints "Migration complete"

- [ ] **Step 3: Re-extract to verify per-date inserts work**

```bash
PYTHONPATH="engine" .venv/bin/python3 -c "
from db_manager import execute, query
execute('self', 'DELETE FROM behaviors')
from extractors import DailyNoteExtractor
DailyNoteExtractor().extract_all()
from extractors.comprehensive_extractor import ComprehensiveExtractor
ce = ComprehensiveExtractor()
ce._extract_daily_patterns()
rows = query('self', 'SELECT behavior_type, response, date(observed_date) as dt FROM behaviors ORDER BY dt')
print(f'{len(rows)} records across {len(set(r[\"dt\"] for r in rows))} distinct dates')
"
```
Expected: 25 records, all with today's date (per-date accumulation starts now — data will become useful after multiple days of extraction).

- [ ] **Step 4: Commit**

```bash
git add personal-ai-space/engine/db/self/schema_self.sql
git commit -m "fix(behaviors): include observed_date in unique index for per-day analytics"
```

---

### Task 2: BehaviorAnalytics class + trend_report (TDD)

**Files:**
- Create: `engine/analytics/__init__.py` (empty)
- Create: `engine/analytics/behavior_analytics.py`
- Create: `engine/tests/test_behavior_analytics.py`

**Security flag:** `none`

**Does NOT cover:** `emotion_activity_correlation`, `anomaly_detection`, or `full_report` — those are stubbed as `NotImplementedError` in this task.

- [ ] **Step 1: Write failing tests**

`engine/tests/test_behavior_analytics.py`:
```python
"""Tests for behavior_analytics module."""
import sqlite3
import pytest
from analytics.behavior_analytics import BehaviorAnalytics


def _dict_factory(cursor, row):
    return {col[0]: val for col, val in zip(cursor.description, row)}


def _make_db():
    """In-memory SQLite DB with controlled behavior records across multiple dates."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = _dict_factory
    conn.execute(
        "CREATE TABLE behaviors ("
        "  id TEXT, behavior_type TEXT, trigger TEXT, response TEXT,"
        "  frequency INTEGER, effectiveness FLOAT, observed_date DATE"
        ")"
    )
    # Baseline period (13-19 days ago from 2026-05-27)
    # Current period (last 7 days from 2026-05-27)
    records = [
        # -- Baseline: stable patterns --
        ('b1',  'emotion', 'ctx', 'angry', 1, 0.5, '2026-05-13'),
        ('b2',  'emotion', 'ctx', 'angry', 1, 0.5, '2026-05-14'),
        ('b3',  'emotion', 'ctx', 'angry', 1, 0.5, '2026-05-15'),
        ('b4',  'emotion', 'ctx', 'angry', 1, 0.5, '2026-05-16'),
        ('b5',  'emotion', 'ctx', 'angry', 1, 0.5, '2026-05-17'),
        ('b6',  'emotion', 'ctx', 'angry', 1, 0.5, '2026-05-18'),
        ('b7',  'emotion', 'ctx', 'sad',   1, 0.5, '2026-05-13'),
        ('b8',  'activity','ctx', 'coded', 1, 0.5, '2026-05-15'),
        # -- Current: angry spikes, sad stable, happy new --
        ('c1',  'emotion', 'ctx', 'angry', 3, 0.5, '2026-05-22'),
        ('c2',  'emotion', 'ctx', 'angry', 2, 0.5, '2026-05-24'),
        ('c3',  'emotion', 'ctx', 'sad',   1, 0.5, '2026-05-22'),
        ('c4',  'emotion', 'ctx', 'happy', 2, 0.5, '2026-05-24'),
        ('c5',  'activity','ctx', 'coded', 1, 0.5, '2026-05-22'),
        ('c6',  'activity','ctx', 'coded', 1, 0.5, '2026-05-24'),
    ]
    for r in records:
        conn.execute("INSERT INTO behaviors VALUES (?,?,?,?,?,?,?)", r)
    conn.commit()
    return conn


@pytest.fixture
def analytics():
    conn = _make_db()
    def query_func(sql, params=()):
        return conn.execute(sql, params).fetchall()
    return BehaviorAnalytics(query_func=query_func)


class TestTrendReport:
    def test_angry_shows_percent_change(self, analytics):
        """Angry: baseline ~1/day, current 5 total → shows increase."""
        report = analytics.trend_report(days=7, now_ref='2026-05-27')
        assert 'angry' in report
        assert '+' in report  # shows positive change

    def test_happy_shows_new(self, analytics):
        """Happy only in current window → change column shows NEW."""
        report = analytics.trend_report(days=7, now_ref='2026-05-27')
        assert 'happy' in report
        assert 'NEW' in report

    def test_sad_shows_baseline(self, analytics):
        """Sad in both periods → baseline avg shown."""
        report = analytics.trend_report(days=7, now_ref='2026-05-27')
        assert 'sad' in report

    def test_empty_table_returns_empty_string(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = _dict_factory
        conn.execute(
            "CREATE TABLE behaviors ("
            "  id TEXT, behavior_type TEXT, trigger TEXT, response TEXT,"
            "  frequency INTEGER, effectiveness FLOAT, observed_date DATE"
            ")"
        )
        conn.commit()
        def q(sql, params=()):
            return conn.execute(sql, params).fetchall()
        ba = BehaviorAnalytics(query_func=q)
        report = ba.trend_report(days=7, now_ref='2026-05-27')
        assert report == '' or 'insufficient' in report
```

- [ ] **Step 2: Run test to verify it fails**

```bash
.venv/bin/python3 -m pytest tests/test_behavior_analytics.py::TestTrendReport -v --tb=short 2>&1
```
Expected: FAIL — `ModuleNotFoundError: No module named 'analytics'`

- [ ] **Step 3: Create analytics package + BehaviorAnalytics with trend_report**

`engine/analytics/__init__.py`:
```python
"""Analytics modules for self.db data."""
from .behavior_analytics import BehaviorAnalytics

__all__ = ['BehaviorAnalytics']
```

`engine/analytics/behavior_analytics.py`:
```python
"""Behavior analytics: trends, correlations, anomaly detection.

Queries the behaviors table in self.db and produces formatted
terminal reports. Pure SQL aggregation + Python statistics.
"""


class BehaviorAnalytics:
    """Compute behavior trends, correlations, and anomalies.

    Args:
        query_func: Callable(sql, params) -> list[dict].
            Defaults to db_manager.query('self', ...).
    """

    def __init__(self, query_func=None):
        if query_func is None:
            from db_manager import query as _q
            self._query = lambda sql, params=(): _q('self', sql, params)
        else:
            self._query = query_func

    # ── helpers ────────────────────────────────────────────────────────────────

    def _daily_counts(self, last_n_days: int, offset: int = 0,
                      now_ref: str | None = None) -> list[dict]:
        """Return per-word daily counts for a lookback window.

        Args:
            last_n_days: Width of the window in days.
            offset: Days to subtract from window end (0 = ends now).
            now_ref: Override \"now\" for testing (YYYY-MM-DD).

        Returns:
            [{'response': str, 'day': str, 'daily': int, 'behavior_type': str}]
        """
        ref = now_ref or 'now'
        if offset:
            end = f"datetime('{ref}', '-{offset} days')"
            start = f"datetime('{ref}', '-{offset + last_n_days} days')"
        else:
            end = f"datetime('{ref}')" if now_ref else "'now'"
            start = f"datetime('{ref}', '-{last_n_days} days')" if now_ref else f"datetime('now', '-{last_n_days} days')"

        sql = f"""
            SELECT response, date(observed_date) AS day,
                   SUM(frequency) AS daily, behavior_type
            FROM behaviors
            WHERE observed_date >= {start}
              AND observed_date < {end}
            GROUP BY response, date(observed_date)
            ORDER BY response, day
        """
        return self._query(sql)

    # ── section reports ────────────────────────────────────────────────────────

    def trend_report(self, days: int = 7,
                     now_ref: str | None = None) -> str:
        """Frequency per word this window vs baseline (previous window, same size).

        Returns formatted string with emotional and activity trend sections.
        Returns empty string if no data in current window.
        """
        current = self._daily_counts(days, offset=0, now_ref=now_ref)
        baseline = self._daily_counts(days, offset=days, now_ref=now_ref)

        cur_totals: dict[str, dict] = {}
        for row in current:
            key = row['response']
            if key not in cur_totals:
                cur_totals[key] = {'total': 0, 'type': row['behavior_type']}
            cur_totals[key]['total'] += row['daily']

        base_totals: dict[str, dict] = {}
        for row in baseline:
            key = row['response']
            if key not in base_totals:
                base_totals[key] = {'total': 0, 'days': set(), 'type': row['behavior_type']}
            base_totals[key]['total'] += row['daily']
            base_totals[key]['days'].add(row['day'])

        for v in base_totals.values():
            v['avg_daily'] = v['total'] / max(len(v['days']), 1)

        if not cur_totals:
            return ''

        import collections
        emotions = [(k, v) for k, v in cur_totals.items() if v['type'] == 'emotion']
        activities = [(k, v) for k, v in cur_totals.items() if v['type'] == 'activity']

        lines = []
        for label, items in [('Emotional Trends', emotions),
                             ('Activity Trends', activities)]:
            if not items:
                continue
            lines.append(f'── {label} ──')
            lines.append(f'{"":22} {"This Win":>9} {"Baseline":>9}  {"Change":>8}')
            items.sort(key=lambda x: -x[1]['total'])
            for word, info in items:
                cur_total = info['total']
                base = base_totals.get(word)
                if base and base['days']:
                    avg = base['avg_daily']
                    pct = ((cur_total / max(avg, 0.01)) - 1) * 100
                    change = f'{pct:+.0f}%'
                else:
                    avg = 0.0
                    change = 'NEW'
                lines.append(f'  {word:20} {cur_total:>9} {avg:>9.1f}  {change:>8}')
            lines.append('')

        return '\n'.join(lines)

    # ── stubs ──────────────────────────────────────────────────────────────────

    def emotion_activity_correlation(self, days: int = 30,
                                     now_ref: str | None = None) -> str:
        raise NotImplementedError

    def anomaly_detection(self, days: int = 30,
                          now_ref: str | None = None) -> str:
        raise NotImplementedError

    def full_report(self, days: int = 7,
                    now_ref: str | None = None) -> str:
        raise NotImplementedError
```

- [ ] **Step 4: Run test to verify it passes**

```bash
.venv/bin/python3 -m pytest tests/test_behavior_analytics.py::TestTrendReport -v --tb=short 2>&1
```
Expected: 4 PASSED

- [ ] **Step 5: Commit**

```bash
git add personal-ai-space/engine/analytics/ personal-ai-space/engine/tests/test_behavior_analytics.py
git commit -m "feat(analytics): add BehaviorAnalytics class with trend_report"
```

---

### Task 3: emotion_activity_correlation + anomaly_detection + full_report (TDD)

**Files:**
- Modify: `engine/analytics/behavior_analytics.py`
- Modify: `engine/tests/test_behavior_analytics.py`

**Security flag:** `none`

**Does NOT cover:** CLI integration (Task 4). Schema changes (Task 1).

- [ ] **Step 1: Write failing tests**

Append to `engine/tests/test_behavior_analytics.py`:
```python
class TestCorrelation:
    def test_coded_co_occurs_with_angry(self, analytics):
        """coded and angry share dates → correlation shown."""
        report = analytics.emotion_activity_correlation(days=30, now_ref='2026-05-27')
        assert 'coded' in report
        assert 'angry' in report

    def test_empty_table_returns_message(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = _dict_factory
        conn.execute(
            "CREATE TABLE behaviors ("
            "  id TEXT, behavior_type TEXT, trigger TEXT, response TEXT,"
            "  frequency INTEGER, effectiveness FLOAT, observed_date DATE"
            ")"
        )
        conn.commit()
        def q(sql, params=()):
            return conn.execute(sql, params).fetchall()
        ba = BehaviorAnalytics(query_func=q)
        report = ba.emotion_activity_correlation(days=30, now_ref='2026-05-27')
        assert isinstance(report, str)
        assert len(report) > 0


class TestAnomalyDetection:
    def test_angry_spike_detected(self, analytics):
        """angry counts [1,1,1,1,1,1,3,2] — z(3) > 2 → flagged."""
        report = analytics.anomaly_detection(days=30, now_ref='2026-05-27')
        assert 'angry' in report
        assert 'outlier' in report.lower() or 'anomal' in report.lower()

    def test_empty_table_returns_message(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = _dict_factory
        conn.execute(
            "CREATE TABLE behaviors ("
            "  id TEXT, behavior_type TEXT, trigger TEXT, response TEXT,"
            "  frequency INTEGER, effectiveness FLOAT, observed_date DATE"
            ")"
        )
        conn.commit()
        def q(sql, params=()):
            return conn.execute(sql, params).fetchall()
        ba = BehaviorAnalytics(query_func=q)
        report = ba.anomaly_detection(days=30, now_ref='2026-05-27')
        assert isinstance(report, str)
        assert len(report) > 0


class TestFullReport:
    def test_combines_all_sections(self, analytics):
        report = analytics.full_report(days=30, now_ref='2026-05-27')
        assert isinstance(report, str)
        assert 'angry' in report
        assert 'coded' in report
        assert 'outlier' in report.lower() or 'anomal' in report.lower()

    def test_empty_db_does_not_crash(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = _dict_factory
        conn.execute(
            "CREATE TABLE behaviors ("
            "  id TEXT, behavior_type TEXT, trigger TEXT, response TEXT,"
            "  frequency INTEGER, effectiveness FLOAT, observed_date DATE"
            ")"
        )
        conn.commit()
        def q(sql, params=()):
            return conn.execute(sql, params).fetchall()
        ba = BehaviorAnalytics(query_func=q)
        report = ba.full_report(days=7, now_ref='2026-05-27')
        assert isinstance(report, str)
```

```bash
.venv/bin/python3 -m pytest tests/test_behavior_analytics.py -v --tb=short 2>&1
```
Expected: TestCorrelation::test_coded_co_occurs_with_angry → FAIL (`NotImplementedError`)
TestAnomalyDetection::test_angry_spike_detected → FAIL
TestFullReport::test_combines_all_sections → FAIL

- [ ] **Step 2: Implement emotion_activity_correlation**

Replace the stub in `behavior_analytics.py`:
```python
    def emotion_activity_correlation(self, days: int = 30,
                                     now_ref: str | None = None) -> str:
        """Co-occurrence: which emotions appear on the same dates as each activity.

        Self-joins behaviors on date(observed_date) to find emotion-activity pairs
        that share the same day. Returns formatted report.
        """
        ref = now_ref or 'now'
        start = f"datetime('{ref}', '-{days} days')" if now_ref else f"datetime('now', '-{days} days')"

        sql = f"""
            SELECT e.response AS emotion, a.response AS activity,
                   COUNT(*) AS together
            FROM behaviors e
            JOIN behaviors a ON date(e.observed_date) = date(a.observed_date)
            WHERE e.behavior_type = 'emotion'
              AND a.behavior_type = 'activity'
              AND e.observed_date >= {start}
            GROUP BY e.response, a.response
            ORDER BY together DESC
        """
        rows = self._query(sql)

        if not rows:
            return '── Emotion × Activity Correlation ──\n(no overlapping data — need both emotions and activities on the same date)'

        from collections import OrderedDict
        by_activity: dict[str, list[tuple[str, int]]] = OrderedDict()
        for r in rows:
            by_activity.setdefault(r['activity'], []).append((r['emotion'], r['together']))

        lines = ['── Emotion × Activity Correlation ──']
        for act, emotions in by_activity.items():
            emo_str = ', '.join(f'{e} ({c})' for e, c in emotions)
            lines.append(f'  {act:14} → {emo_str}')

        return '\n'.join(lines)
```

- [ ] **Step 3: Run correlation tests to verify they pass**

```bash
.venv/bin/python3 -m pytest tests/test_behavior_analytics.py::TestCorrelation -v --tb=short 2>&1
```
Expected: 2 PASSED

- [ ] **Step 4: Implement anomaly_detection**

Replace the stub in `behavior_analytics.py`:
```python
    def anomaly_detection(self, days: int = 30,
                          now_ref: str | None = None) -> str:
        """Detect words whose daily frequency deviates >2 std from their mean.

        Uses per-word daily counts, requires minimum 3 distinct dates
        for meaningful statistics. Flags entries with z-score > 2.0.
        """
        ref = now_ref or 'now'
        start = f"datetime('{ref}', '-{days} days')" if now_ref else f"datetime('now', '-{days} days')"

        sql = f"""
            SELECT response, date(observed_date) AS day,
                   SUM(frequency) AS daily, behavior_type
            FROM behaviors
            WHERE observed_date >= {start}
            GROUP BY response, date(observed_date)
            ORDER BY response, day
        """
        rows = self._query(sql)

        if not rows:
            return '── Anomaly Detection ──\n(no data)'

        from collections import defaultdict
        by_word: dict[str, list[int]] = defaultdict(list)
        for r in rows:
            by_word[r['response']].append(r['daily'])

        import statistics
        anomalies: list[tuple[str, int, float, float]] = []
        for word, counts in sorted(by_word.items()):
            if len(counts) < 3:
                continue
            mean = statistics.mean(counts)
            try:
                std = statistics.stdev(counts)
            except statistics.StatisticsError:
                continue
            if std == 0:
                continue
            # Check each daily value
            for c in counts:
                z = (c - mean) / std
                if z > 2.0:
                    anomalies.append((word, c, mean, z))
                    break  # one flag per word

        if not anomalies:
            return '── Anomaly Detection ──\n(no anomalies detected — insufficient data for z-score)'

        lines = ['── Anomaly Detection ──']
        for word, val, mean, z in anomalies:
            lines.append(f'  {word:14} count={val}  mean={mean:.1f}  z={z:.1f}  — outlier')
        return '\n'.join(lines)
```

- [ ] **Step 5: Run anomaly tests to verify they pass**

```bash
.venv/bin/python3 -m pytest tests/test_behavior_analytics.py::TestAnomalyDetection -v --tb=short 2>&1
```
Expected: 2 PASSED

- [ ] **Step 6: Implement full_report**

Replace the stub in `behavior_analytics.py`:
```python
    def full_report(self, days: int = 7,
                    now_ref: str | None = None) -> str:
        """All three report sections combined with a header."""
        sections = [
            self.trend_report(days, now_ref),
            self.emotion_activity_correlation(days * 4, now_ref),
            self.anomaly_detection(days * 4, now_ref),
        ]
        header = f'--- Behavior Report (last {days} days) ---'
        body = '\n\n'.join(s for s in sections if s)
        return f'{header}\n\n{body}' if body else f'{header}\n\n(no data)'
```

- [ ] **Step 7: Run all analytics tests**

```bash
.venv/bin/python3 -m pytest tests/test_behavior_analytics.py -v --tb=short 2>&1
```
Expected: 10 PASSED (4 trend + 2 correlation + 2 anomaly + 2 full_report)

- [ ] **Step 8: Commit**

```bash
git add personal-ai-space/engine/analytics/behavior_analytics.py personal-ai-space/engine/tests/test_behavior_analytics.py
git commit -m "feat(analytics): add correlation, anomaly detection, and full_report"
```

---

### Task 4: CLI integration — `behaviors report` command

**Files:**
- Modify: `engine/cli.py`

**Security flag:** `none`

**Does NOT cover:** Any analytics logic changes (Task 2 and 3). Any schema changes (Task 1).

- [ ] **Step 1: Add behaviors group + report command to cli.py**

Find where the `habit` group is defined in `cli.py` (around line 229). After the `habit_insights` function and before `reminders`, insert:

```python
    # ── Behaviors ────────────────────────────────────────────────────────────
    @cli.group()
    def behaviors():
        """Analyze behavior patterns from daily notes."""
        pass

    @behaviors.command()
    @click.option("--days", "-d", default=7, type=int, help="Report window in days")
    def report(days):
        """Emotional trends, emotion-activity correlation, and anomalies."""
        from analytics.behavior_analytics import BehaviorAnalytics
        result = BehaviorAnalytics().full_report(days=days)
        if result:
            print(result)
        else:
            print("No behavior data found. Run extraction first.")
```

- [ ] **Step 2: Verify CLI command works**

```bash
.venv/bin/python3 cli.py behaviors report --days 30
```
Expected: Prints the report with three sections to stdout. Does not crash with import errors.

- [ ] **Step 3: Verify CLI handles empty data gracefully**

```bash
.venv/bin/python3 cli.py behaviors report --days 1
```
Expected: Prints report with "no data" or empty sections for the 1-day window (since no records match today's single day in the test data — the current records have dates 05-22 and 05-24 which are in the last 7 days but... wait, actually today is 2026-05-27, so `--days 1` means May 26-27. No records fall in this range. This gracefully shows empty sections.)

Actually, the current data has May 22 and May 24 records. `--days 1` window from May 27: May 26-27. No records match → the command should print something reasonable. Let me verify the implementation handles this gracefully.

- [ ] **Step 4: Commit**

```bash
git add personal-ai-space/engine/cli.py
git commit -m "feat(cli): add behaviors report command for Level 2 analytics"
```

---

### Task 5: Run against real data + final verification

**Files:** (none — verification only)

- [ ] **Step 1: Run full report against current 25 records**

```bash
.venv/bin/python3 -m pytest tests/test_behavior_analytics.py -v --tb=short 2>&1
```
Expected: All 10 tests pass.

```bash
.venv/bin/python3 cli.py behaviors report --days 30
```
Expected: Report with three sections. Trend will show "NEW" for all words (one date only, no baseline yet). Correlation will show all emotions and activities co-occurring (all on same date). Anomaly will show "insufficient data" (only 1-2 dates per word).

This is expected behavior with only one day of data. The reports become useful after 7+ days of daily extraction.

- [ ] **Step 2: Run behavior_vocab regression tests**

```bash
.venv/bin/python3 -m pytest tests/test_behavior_vocab.py -v --tb=short 2>&1
```
Expected: 31 passed (no regressions from schema change).

- [ ] **Step 3: Commit any final changes**

```bash
git add -A
git commit -m "feat(analytics): Level 2 behavior analytics complete — CLI report with trends, correlation, anomaly detection"
```
