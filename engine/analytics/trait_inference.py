"""Infer objective traits from session data using keyword/pattern matching.

Follows the injectable-query pattern from behavior_analytics.py and the
INSERT OR REPLACE pattern from sync_traits() in sync_self.py.
"""
import json
import logging
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("engine.analytics.trait_inference")

INFERRED_FROM = "session_analysis"
CONFIDENCE = 0.80
OPENCODE_DB = Path.home() / ".local/share/opencode/opencode.db"


def _default_query(sql: str, params: tuple = ()):
    from db_manager import query

    return query("self", sql, params)


def _default_execute(sql: str, params: tuple = ()):
    from db_manager import execute

    return execute("self", sql, params)


class TraitInferrer:
    """Infer observable traits from session_metadata and session_signals.

    Args:
        query_func: Callable(sql, params) → list[dict] for self.db SELECT.
        execute_func: Callable(sql, params) → int for self.db INSERT/UPDATE.
    """

    def __init__(self, query_func=None, execute_func=None):
        self._query = query_func or _default_query
        self._execute = execute_func or _default_execute

    def infer_all(self) -> dict:
        """Run all trait inferences and return per-group row counts."""
        now = datetime.now(timezone.utc)
        today = now.strftime("%Y-%m-%d")
        iso = now.isoformat()

        # Wipe old session_analysis traits before re-inferring
        self._execute(
            "DELETE FROM traits WHERE inferred_from = ?",
            (INFERRED_FROM,),
        )

        all_rows: list[tuple] = []
        stats: dict[str, int] = {}

        stats["working_hours"] = self._infer_working_hours(all_rows, today, iso)
        stats["session_depth"] = self._infer_session_depth(all_rows, today, iso)
        stats["model_preference"] = self._infer_model_preference(all_rows, today, iso)
        stats["agent_preference"] = self._infer_agent_preference(all_rows, today, iso)
        stats["task_volume"] = self._infer_task_volume(all_rows, today, iso)

        count = 0
        for row in all_rows:
            self._execute(
                """INSERT OR REPLACE INTO traits
                   (id, trait_name, category, confidence_score,
                    inferred_from, discovered_date, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                row,
            )
            count += 1

        stats["total"] = count
        logger.info("TraitInferrer: %d trait(s) inferred", count)
        return stats

    # ── Helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def _safe_id(label: str, max_len: int = 60) -> str:
        """Lowercase alphanumeric + underscores, truncated."""
        safe = "".join(c if c.isalnum() or c in ("_", "-") else "_" for c in label.lower())
        return safe[:max_len].rstrip("_")

    @staticmethod
    def _parse_model(raw: str) -> str:
        """Extract model id from JSON string or return raw string."""
        try:
            data = json.loads(raw)
            return data.get("id", raw)
        except (json.JSONDecodeError, TypeError):
            return raw

    @staticmethod
    def _model_family(model_id: str) -> str:
        """Derive a broad family name from a model id (e.g. claude-opus-4-7 → claude)."""
        if not model_id:
            return "unknown"
        return model_id.split("-")[0].split("/")[-1]

    # ── Inference methods ───────────────────────────────────────────────

    def _infer_working_hours(self, rows: list, today: str, iso: str) -> int:
        """Read time_created from OpenCode DB and classify peak working period."""
        if not OPENCODE_DB.exists():
            logger.warning("OpenCode DB not found at %s", OPENCODE_DB)
            return 0

        conn = sqlite3.connect(str(OPENCODE_DB))
        try:
            raw = [
                row[0]
                for row in conn.execute(
                    "SELECT time_created FROM session WHERE time_created IS NOT NULL"
                ).fetchall()
            ]
        finally:
            conn.close()

        if not raw:
            return 0

        # Epoch milliseconds → hour-of-day
        hours: list[int] = []
        for ts in raw:
            try:
                ts_sec = ts / 1000 if ts > 1e12 else ts  # millis → seconds
                hours.append(datetime.fromtimestamp(ts_sec, tz=timezone.utc).hour)
            except (OSError, ValueError):
                continue

        if not hours:
            return 0

        total = len(hours)
        periods = {
            "morning": sum(1 for h in hours if 5 <= h < 12),
            "afternoon": sum(1 for h in hours if 12 <= h < 18),
            "evening": sum(1 for h in hours if 18 <= h < 22),
            "night": sum(1 for h in hours if h >= 22 or h < 5),
        }
        peak_label, peak_count = max(periods.items(), key=lambda x: x[1])
        peak_pct = peak_count / total

        rows.append((
            "session_peak_hours",
            f"Peak Hours: {peak_label} ({peak_count}/{total}, {peak_pct:.0%})",
            "session_inferred", CONFIDENCE, INFERRED_FROM, today, iso,
        ))

        if peak_pct > 0.50:
            rows.append((
                "session_primary_window",
                f"Primary Window: {peak_label} ({peak_count}/{total} sessions)",
                "session_inferred", CONFIDENCE, INFERRED_FROM, today, iso,
            ))

        # Secondary peak if ≥ 25%
        secondary = sorted(periods.items(), key=lambda x: -x[1])
        if len(secondary) > 1 and secondary[1][1] / total >= 0.25:
            rows.append((
                "session_secondary_window",
                f"Secondary Window: {secondary[1][0]} ({secondary[1][1]}/{total})",
                "session_inferred", CONFIDENCE - 0.05, INFERRED_FROM, today, iso,
            ))

        return len(rows)

    def _infer_session_depth(self, rows: list, today: str, iso: str) -> int:
        """Classify typical session depth by average duration + volume."""
        sessions = self._query(
            "SELECT duration_seconds, message_count FROM session_metadata"
        )
        if not sessions:
            return 0

        durations = [s["duration_seconds"] or 0 for s in sessions]
        msg_counts = [s["message_count"] or 0 for s in sessions]
        n = len(durations)
        avg_dur = sum(durations) / n
        avg_msgs = sum(msg_counts) / n

        if avg_dur > 1800:  # > 30 min
            depth = "extended_deep_work"
        elif avg_dur > 600:  # > 10 min
            depth = "deep_work"
        elif avg_dur > 180:  # > 3 min
            depth = "moderate_focus"
        else:
            depth = "quick_task"

        rows.append((
            "session_depth",
            f"Session Depth: {depth} ({avg_dur:.0f}s avg, {avg_msgs:.1f} msgs avg, n={n})",
            "session_inferred", CONFIDENCE, INFERRED_FROM, today, iso,
        ))

        # Also emit the raw average duration as a separate metric trait
        rows.append((
            "session_avg_duration_seconds",
            f"Avg Duration: {avg_dur:.0f}s",
            "session_inferred", CONFIDENCE, INFERRED_FROM, today, iso,
        ))

        rows.append((
            "session_avg_messages_per_session",
            f"Avg Messages: {avg_msgs:.1f}",
            "session_inferred", 0.85, INFERRED_FROM, today, iso,
        ))

        return 3

    def _infer_model_preference(self, rows: list, today: str, iso: str) -> int:
        """Most-used model families from session_metadata."""
        raw = self._query(
            "SELECT model FROM session_metadata "
            "WHERE model IS NOT NULL AND model != ''"
        )
        if not raw:
            return 0

        families: Counter[str] = Counter()
        for r in raw:
            model_id = self._parse_model(r["model"])
            families[self._model_family(model_id)] += 1

        total = sum(families.values())
        top = families.most_common(5)

        inserted = 0
        for i, (fam, count) in enumerate(top):
            pct = count / total * 100
            confidence = max(0.5, CONFIDENCE - i * 0.08)
            role = "primary" if i == 0 else ("secondary" if i < 3 else "minor")
            safe = self._safe_id(f"session_model_{role}_{fam}")

            rows.append((
                safe,
                f"Model {role.replace('_', ' ').title()}: {fam} ({count}/{total}, {pct:.0f}%)",
                "session_inferred", confidence, INFERRED_FROM, today, iso,
            ))
            inserted += 1

        return inserted

    def _infer_agent_preference(self, rows: list, today: str, iso: str) -> int:
        """Most-used agent types from session_metadata."""
        raw = self._query(
            "SELECT agent FROM session_metadata "
            "WHERE agent IS NOT NULL AND agent != ''"
        )
        if not raw:
            return 0

        agents: Counter[str] = Counter(r["agent"] for r in raw)
        total = sum(agents.values())
        top = agents.most_common(5)

        inserted = 0
        for i, (agent, count) in enumerate(top):
            pct = count / total * 100
            confidence = max(0.5, CONFIDENCE - i * 0.08)
            role = "primary" if i == 0 else ("secondary" if i < 3 else "minor")
            safe = self._safe_id(f"session_agent_{role}_{agent}")

            rows.append((
                safe,
                f"Agent {role.replace('_', ' ').title()}: {agent} ({count}/{total}, {pct:.0f}%)",
                "session_inferred", confidence, INFERRED_FROM, today, iso,
            ))
            inserted += 1

        return inserted

    def _infer_task_volume(self, rows: list, today: str, iso: str) -> int:
        """Sessions-per-day frequency and density categorisation."""
        raw = self._query(
            "SELECT date, message_count, duration_seconds "
            "FROM session_metadata ORDER BY date"
        )
        if not raw:
            return 0

        dates = Counter(r["date"] for r in raw)
        msg_counts = [r["message_count"] or 0 for r in raw]
        durations = [r["duration_seconds"] or 0 for r in raw]

        n_days = len(dates)
        total_sessions = sum(dates.values())
        avg_per_day = total_sessions / n_days if n_days else 0
        peak_date, peak_count = dates.most_common(1)[0]
        avg_msgs = sum(msg_counts) / len(msg_counts)
        avg_dur = sum(durations) / len(durations)

        rows.append((
            "session_volume_daily",
            f"Daily Volume: {avg_per_day:.1f} sessions avg across {n_days} day(s)",
            "session_inferred", CONFIDENCE, INFERRED_FROM, today, iso,
        ))

        rows.append((
            "session_peak_day",
            f"Peak Day: {peak_date} ({peak_count} sessions)",
            "session_inferred", 0.85, INFERRED_FROM, today, iso,
        ))

        # Volume level classification
        if avg_per_day > 5:
            level = "high (heavy user)"
        elif avg_per_day > 2:
            level = "moderate (regular user)"
        else:
            level = "light (occasional user)"

        rows.append((
            "session_volume_level",
            f"Volume Level: {level}",
            "session_inferred", CONFIDENCE, INFERRED_FROM, today, iso,
        ))

        # Density classification — complex vs focused vs brief interactions
        if avg_msgs > 20:
            density = "high (complex interactions)"
        elif avg_msgs > 8:
            density = "moderate (balanced interactions)"
        else:
            density = "low (quick interactions)"

        rows.append((
            "session_density",
            f"Session Density: {density} ({avg_msgs:.1f} msgs, {avg_dur:.0f}s avg)",
            "session_inferred", CONFIDENCE, INFERRED_FROM, today, iso,
        ))

        return 4
