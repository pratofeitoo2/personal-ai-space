"""BehaviorAnalytics — trend reports, emotion-activity correlation, anomaly detection.

Queries the behaviors table via an injected query_func callable.
Tests pass an in-memory SQLite wrapper; production uses db_manager.
"""
import statistics
from collections import defaultdict
from datetime import date


def _default_query(sql: str, params: tuple = ()):
    """Default query function using db_manager."""
    from db_manager import query
    return query("self", sql, params)


class BehaviorAnalytics:
    """Analytics engine for the behaviors table.

    Args:
        query_func: Optional callable(sql, params) → list of rows.
                     Defaults to db_manager.query('self', ...).
    """

    def __init__(self, query_func=None):
        self._query = query_func or _default_query

    @staticmethod
    def _tuples(rows):
        """Normalize rows to tuples (handles both dict and tuple rows)."""
        if not rows:
            return []
        if isinstance(rows[0], dict):
            keys = list(rows[0].keys())
            return [tuple(r[k] for k in keys) for r in rows]
        return rows

    # ── Trend Report ──────────────────────────────────────────────────

    def trend_report(self) -> dict:
        """Current vs baseline behavior frequencies.

        Returns:
            dict with:
                current_date: str — most recent observed_date (or empty)
                current: list[dict] — behaviors on the most recent date
                baseline: list[dict] — behaviors on all older dates
            Each entry: {behavior_type, response, total_frequency, pct_of_type}
        """
        rows = self._tuples(self._query(
            "SELECT behavior_type, response, SUM(frequency), observed_date "
            "FROM behaviors GROUP BY behavior_type, response, observed_date "
            "ORDER BY observed_date DESC"
        ))

        if not rows:
            return {"current_date": "", "current": [], "baseline": []}

        # Determine most recent date
        dates = sorted(set(r[3] for r in rows), reverse=True)
        latest = dates[0]
        older = set(dates[1:])

        current_rows = [r for r in rows if r[3] == latest]
        baseline_rows = [r for r in rows if r[3] in older]

        def _build(entries) -> list:
            """Aggregate entries by (behavior_type, response) and add pct."""
            agg = defaultdict(int)
            btypes = {}
            for bt, resp, freq, _ in entries:
                agg[(bt, resp)] += freq
                btypes[(bt, resp)] = bt
            # Total per type for percentages
            type_totals = defaultdict(int)
            for (bt, _), freq in agg.items():
                type_totals[bt] += freq
            result = []
            for (bt, resp), freq in sorted(agg.items(), key=lambda x: x[1], reverse=True):
                total = type_totals.get(bt, 1) or 1
                result.append({
                    "behavior_type": bt,
                    "response": resp,
                    "total_frequency": freq,
                    "pct_of_type": round(freq / total * 100, 1),
                })
            return result

        return {
            "current_date": latest,
            "current": _build(current_rows),
            "baseline": _build(baseline_rows),
        }

    # ── Emotion-Activity Correlation ─────────────────────────────────

    def emotion_activity_correlation(self) -> list[dict]:
        """Co-occurrence of emotions and activities on the same day.

        Returns:
            List of dicts: {emotion, activity, cooccurrences, observed_dates}
            Sorted by cooccurrences descending.
        """
        rows = self._tuples(self._query(
            "SELECT b1.response, b2.response, b1.observed_date "
            "FROM behaviors b1 "
            "JOIN behaviors b2 ON b1.observed_date = b2.observed_date "
            "AND b1.rowid <> b2.rowid "
            "WHERE b1.behavior_type = 'emotion' "
            "AND b2.behavior_type = 'activity' "
            "ORDER BY b1.observed_date"
        ))

        pairs = defaultdict(int)
        dates_per_pair = defaultdict(set)
        for emotion, activity, obs_date in rows:
            key = (emotion, activity)
            pairs[key] += 1
            dates_per_pair[key].add(obs_date)

        result = sorted(
            [
                {
                    "emotion": emotion,
                    "activity": activity,
                    "cooccurrences": count,
                    "observed_dates": sorted(dates_per_pair[(emotion, activity)]),
                }
                for (emotion, activity), count in pairs.items()
            ],
            key=lambda r: r["cooccurrences"],
            reverse=True,
        )
        return result

    # ── Anomaly Detection ────────────────────────────────────────────

    def anomaly_detection(self, z_threshold: float = 2.0,
                          min_dates: int = 3) -> list[dict]:
        """Detect statistical outliers in behavior frequency over time.

        Uses z-score per (behavior_type, response) across distinct dates.
        Only words with >= min_dates distinct dates are evaluated.

        Args:
            z_threshold: Z-score above which a word is flagged (default 2.0).
            min_dates: Minimum distinct dates required (default 3).

        Returns:
            List of dicts: {behavior_type, response, dates, frequencies,
                            mean, stddev, latest_zscore, is_anomaly}
            Sorted by |z-score| descending, only includes evaluated words.
        """
        rows = self._tuples(self._query(
            "SELECT behavior_type, response, SUM(frequency), observed_date "
            "FROM behaviors GROUP BY behavior_type, response, observed_date "
            "ORDER BY behavior_type, response, observed_date"
        ))

        # Group by (behavior_type, response)
        series = defaultdict(list)
        for bt, resp, freq, obs_date in rows:
            series[(bt, resp)].append((obs_date, freq))

        result = []
        for (bt, resp), points in series.items():
            if len(points) < min_dates:
                continue
            dates_list = [p[0] for p in points]
            freqs = [p[1] for p in points]

            mean = statistics.mean(freqs)
            stdev = statistics.stdev(freqs) if len(freqs) > 1 else 0.0

            if stdev == 0:
                continue  # Skip uniform series

            latest_freq = freqs[-1]
            zscore = (latest_freq - mean) / stdev
            is_anomaly = abs(zscore) > z_threshold

            result.append({
                "behavior_type": bt,
                "response": resp,
                "dates": dates_list,
                "frequencies": freqs,
                "mean": round(mean, 2),
                "stddev": round(stdev, 2),
                "latest_zscore": round(zscore, 2),
                "is_anomaly": is_anomaly,
            })

        result.sort(key=lambda r: abs(r["latest_zscore"]), reverse=True)
        return result

    # ── Full Report ──────────────────────────────────────────────────

    def full_report(self) -> dict:
        """Combine all analytics into a single report dict.

        Returns:
            dict with keys: trends, correlations, anomalies
        """
        return {
            "trends": self.trend_report(),
            "correlations": self.emotion_activity_correlation(),
            "anomalies": self.anomaly_detection(),
        }

    def __str__(self) -> str:
        """Human-readable multi-line string of the full report."""
        report = self.full_report()
        lines = ["╔══════════════════════════════════════════╗"]
        lines.append("║        Behavior Analytics Report       ║")
        lines.append("╚══════════════════════════════════════════╝")
        lines.append("")

        # Trends
        trends = report["trends"]
        lines.append("── Emotional Trends ──")
        if trends["current_date"]:
            lines.append(f"  Current: {trends['current_date']}")
        else:
            lines.append("  (no data)")

        for label, entries in [("Current", trends["current"]),
                                ("Baseline", trends["baseline"])]:
            if not entries:
                continue
            lines.append(f"  {label}:")
            for e in entries:
                lines.append(
                    f"    {e['response']:20s} "
                    f"{e['total_frequency']:3d}  "
                    f"({e['pct_of_type']:5.1f}%)"
                )

        # Correlations
        lines.append("")
        lines.append("── Emotion-Activity Correlations ──")
        corr = report["correlations"]
        if corr:
            for c in corr[:8]:  # Top 8
                lines.append(
                    f"  {c['emotion']:12s} + {c['activity']:12s}  "
                    f"×{c['cooccurrences']}"
                )
        else:
            lines.append("  (none)")

        # Anomalies
        lines.append("")
        lines.append("── Anomaly Detection ──")
        anom = [a for a in report["anomalies"] if a["is_anomaly"]]
        if anom:
            for a in anom[:5]:
                lines.append(
                    f"  ⚠ {a['response']:20s} "
                    f"z={a['latest_zscore']:+.2f}  "
                    f"(μ={a['mean']}, σ={a['stddev']})"
                )
        else:
            lines.append("  (no anomalies detected — need ≥3 dates per word)")

        return "\n".join(lines)
