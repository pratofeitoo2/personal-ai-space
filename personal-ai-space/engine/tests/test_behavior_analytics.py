"""Tests for BehaviorAnalytics — trend reports, correlations, anomaly detection.

Uses in-memory SQLite with the same schema pattern as self.db.
BehaviorAnalytics accepts an optional query_func for dependency injection.
"""
import sqlite3
from datetime import date

import pytest
from analytics.behavior_analytics import BehaviorAnalytics


# ── Helpers ──────────────────────────────────────────────────────────

EMPTY_QUERY = lambda sql, params=(): []  # noqa: E731


def _memory_db():
    """Return an in-memory SQLite connection with the behaviors table."""
    conn = sqlite3.connect(":memory:")
    conn.execute("""
        CREATE TABLE behaviors (
            id TEXT PRIMARY KEY,
            behavior_type TEXT,
            trigger TEXT,
            response TEXT,
            frequency INTEGER DEFAULT 1,
            effectiveness FLOAT DEFAULT 0.5,
            observed_date DATE
        )
    """)
    conn.execute("""
        CREATE UNIQUE INDEX idx_behaviors_unique
        ON behaviors(behavior_type, response, observed_date)
    """)
    return conn


def _make_query(conn):
    """Wrap a connection's execute → fetchall as a query_func."""
    def query(sql, params=()):
        return conn.execute(sql, params).fetchall()
    return query


def _seed(conn, rows: list[dict]):
    """Insert rows into behaviors table."""
    for r in rows:
        conn.execute(
            """INSERT OR IGNORE INTO behaviors
               (id, behavior_type, trigger, response, frequency, effectiveness, observed_date)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                r.get("id", r["response"] + "_" + str(r.get("observed_date", "2026-01-01"))),
                r["behavior_type"],
                r.get("trigger", ""),
                r["response"],
                r.get("frequency", 1),
                r.get("effectiveness", 0.5),
                r.get("observed_date", "2026-01-01"),
            ),
        )
    conn.commit()


# ── Trend Report Tests ──────────────────────────────────────────────


class TestTrendReport:
    def test_empty_db_returns_empty_report(self):
        """No behaviors → trend_report returns empty sections."""
        ba = BehaviorAnalytics(query_func=_make_query(_memory_db()))
        report = ba.trend_report()
        assert report["current"] == []
        assert report["baseline"] == []

    def test_single_emotion_appears_in_current(self):
        """Single emotion record appears in current (most recent date)."""
        conn = _memory_db()
        _seed(conn, [
            {"behavior_type": "emotion", "response": "happy",
             "frequency": 3, "observed_date": "2026-05-27"},
        ])
        ba = BehaviorAnalytics(query_func=_make_query(conn))
        report = ba.trend_report()
        emotions = [r for r in report["current"] if r["behavior_type"] == "emotion"]
        assert any(r["response"] == "happy" for r in emotions)
        happy = next(r for r in emotions if r["response"] == "happy")
        assert happy["total_frequency"] == 3

    def test_baseline_uses_older_data(self):
        """Baseline is computed from data older than the most recent date."""
        conn = _memory_db()
        _seed(conn, [
            {"behavior_type": "emotion", "response": "sad",
             "frequency": 5, "observed_date": "2026-05-20"},
            {"behavior_type": "emotion", "response": "sad",
             "frequency": 2, "observed_date": "2026-05-27"},
        ])
        ba = BehaviorAnalytics(query_func=_make_query(conn))
        report = ba.trend_report()
        current_emotions = [r for r in report["current"] if r["behavior_type"] == "emotion"]
        baseline_emotions = [r for r in report["baseline"] if r["behavior_type"] == "emotion"]
        current_sad = next(r for r in current_emotions if r["response"] == "sad")
        base_sad = next(r for r in baseline_emotions if r["response"] == "sad")
        assert current_sad["total_frequency"] == 2
        assert base_sad["total_frequency"] == 5

    def test_current_computes_percentages(self):
        """Current section includes percentage of total for each record."""
        conn = _memory_db()
        _seed(conn, [
            {"behavior_type": "emotion", "response": "happy",
             "frequency": 3, "observed_date": "2026-05-27"},
            {"behavior_type": "emotion", "response": "sad",
             "frequency": 1, "observed_date": "2026-05-27"},
        ])
        ba = BehaviorAnalytics(query_func=_make_query(conn))
        report = ba.trend_report()
        totals = {r["response"]: r["pct_of_type"] for r in report["current"]
                  if r["behavior_type"] == "emotion"}
        assert totals["happy"] == 75.0
        assert totals["sad"] == 25.0

    def test_activities_and_emotions_separate_types(self):
        """Behavior type is preserved in report entries."""
        conn = _memory_db()
        _seed(conn, [
            {"behavior_type": "emotion", "response": "happy",
             "frequency": 2, "observed_date": "2026-05-27"},
            {"behavior_type": "activity", "response": "coded",
             "frequency": 1, "observed_date": "2026-05-27"},
        ])
        ba = BehaviorAnalytics(query_func=_make_query(conn))
        report = ba.trend_report()
        types = {r["behavior_type"] for r in report["current"]}
        assert types == {"emotion", "activity"}

    def test_current_shows_latest_date(self):
        """current_date reflects the most recent observed_date."""
        conn = _memory_db()
        _seed(conn, [
            {"behavior_type": "emotion", "response": "calm",
             "frequency": 1, "observed_date": "2026-05-27"},
        ])
        ba = BehaviorAnalytics(query_func=_make_query(conn))
        report = ba.trend_report()
        assert report["current_date"] == "2026-05-27"


# ── Correlation Tests ───────────────────────────────────────────────


class TestEmotionActivityCorrelation:
    def test_empty_db_returns_empty_correlations(self):
        ba = BehaviorAnalytics(query_func=_make_query(_memory_db()))
        result = ba.emotion_activity_correlation()
        assert result == []

    def test_same_date_emotion_and_activity_correlate(self):
        """Co-occurring emotions and activities on the same date appear."""
        conn = _memory_db()
        _seed(conn, [
            {"behavior_type": "emotion", "response": "happy",
             "frequency": 1, "observed_date": "2026-05-27"},
            {"behavior_type": "activity", "response": "coded",
             "frequency": 1, "observed_date": "2026-05-27"},
        ])
        ba = BehaviorAnalytics(query_func=_make_query(conn))
        result = ba.emotion_activity_correlation()
        assert len(result) >= 1
        assert any(r["emotion"] == "happy" and r["activity"] == "coded" for r in result)

    def test_different_dates_no_correlation(self):
        """Emotions and activities on different dates should not correlate."""
        conn = _memory_db()
        _seed(conn, [
            {"behavior_type": "emotion", "response": "happy",
             "frequency": 1, "observed_date": "2026-05-26"},
            {"behavior_type": "activity", "response": "coded",
             "frequency": 1, "observed_date": "2026-05-27"},
        ])
        ba = BehaviorAnalytics(query_func=_make_query(conn))
        result = ba.emotion_activity_correlation()
        # No same-date co-occurrence → no correlation
        all_empty = all(r["cooccurrences"] == 0 for r in result) if result else True
        assert all_empty


# ── Anomaly Tests ───────────────────────────────────────────────────


class TestAnomalyDetection:
    def test_insufficient_data_returns_empty(self):
        """Fewer than 3 distinct dates returns empty anomaly list."""
        conn = _memory_db()
        _seed(conn, [
            {"behavior_type": "emotion", "response": "happy",
             "frequency": 1, "observed_date": "2026-05-27"},
        ])
        ba = BehaviorAnalytics(query_func=_make_query(conn))
        result = ba.anomaly_detection()
        assert result == []

    def test_requires_min_dates(self):
        """At least min_dates parameter distinct dates required."""
        conn = _memory_db()
        # 2 dates only
        for d in ["2026-05-26", "2026-05-27"]:
            _seed(conn, [
                {"behavior_type": "emotion", "response": "happy",
                 "frequency": 1, "observed_date": d},
            ])
        ba = BehaviorAnalytics(query_func=_make_query(conn))
        result = ba.anomaly_detection(min_dates=3)
        assert result == []

    def test_high_zscore_flagged(self):
        """A word with a z-score above threshold is flagged."""
        conn = _memory_db()
        # 5 dates: stable at 1-2, then spike to 50
        dates = ["2026-05-23", "2026-05-24", "2026-05-25", "2026-05-26", "2026-05-27"]
        for i, d in enumerate(dates):
            freq = 50 if d == "2026-05-27" else 1
            _seed(conn, [
                {"behavior_type": "emotion", "response": "stressed",
                 "frequency": freq, "observed_date": d},
            ])
        ba = BehaviorAnalytics(query_func=_make_query(conn))
        result = ba.anomaly_detection(z_threshold=1.5)
        assert any(r["response"] == "stressed" and r["is_anomaly"] for r in result)

    def test_stable_word_not_anomalous(self):
        """A word with stable frequency across dates is not flagged."""
        conn = _memory_db()
        for d in ["2026-05-25", "2026-05-26", "2026-05-27"]:
            _seed(conn, [
                {"behavior_type": "emotion", "response": "calm",
                 "frequency": 2, "observed_date": d},
            ])
        ba = BehaviorAnalytics(query_func=_make_query(conn))
        result = ba.anomaly_detection(z_threshold=2.0)
        anomalous = [r for r in result if r["is_anomaly"]]
        assert len(anomalous) == 0

    def test_stddev_zero_skipped(self):
        """Word with same frequency every date (stddev=0) is skipped, not errored."""
        conn = _memory_db()
        for d in ["2026-05-25", "2026-05-26", "2026-05-27"]:
            _seed(conn, [
                {"behavior_type": "emotion", "response": "peaceful",
                 "frequency": 1, "observed_date": d},
            ])
        ba = BehaviorAnalytics(query_func=_make_query(conn))
        result = ba.anomaly_detection()
        # peaceful has stddev=0, should be skipped gracefully
        peaceful = [r for r in result if r["response"] == "peaceful"]
        assert len(peaceful) == 0 or not peaceful[0]["is_anomaly"]


# ── Full Report Tests ───────────────────────────────────────────────


class TestFullReport:
    def test_full_report_includes_all_sections(self):
        conn = _memory_db()
        _seed(conn, [
            {"behavior_type": "emotion", "response": "happy",
             "frequency": 1, "observed_date": "2026-05-27"},
            {"behavior_type": "activity", "response": "coded",
             "frequency": 1, "observed_date": "2026-05-27"},
        ])
        ba = BehaviorAnalytics(query_func=_make_query(conn))
        report = ba.full_report()
        assert "trends" in report
        assert "correlations" in report
        assert "anomalies" in report

    def test_full_report_with_no_data(self):
        ba = BehaviorAnalytics(query_func=EMPTY_QUERY)
        report = ba.full_report()
        assert report["trends"]["current"] == []
        assert report["correlations"] == []
        assert report["anomalies"] == []

    def test_str_has_readable_output(self):
        ba = BehaviorAnalytics(query_func=EMPTY_QUERY)
        text = str(ba)
        assert "Behavior Analytics Report" in text
