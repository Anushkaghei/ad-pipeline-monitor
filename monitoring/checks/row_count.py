"""Row count anomaly detection.

Compares current ingestion row count against a 7-day rolling average
and flags deviations above a configurable threshold.
"""

import logging
import math

from sqlalchemy import text
from sqlalchemy.engine import Engine

from monitoring.models import AnomalyScore, CheckResult, CheckType, Severity

logger = logging.getLogger(__name__)

# Tables to monitor
MONITORED_TABLES = [
    "raw.meta_campaigns",
    "raw.google_campaigns",
    "raw.meta_adsets",
    "raw.google_keywords",
]


def check_row_counts(
    engine: Engine,
    deviation_threshold: float = 0.30,
    lookback_days: int = 7,
) -> list[CheckResult]:
    """
    Run row count checks on all monitored tables.

    For each table:
    1. Get today's ingested row count
    2. Get the average daily row count over the past `lookback_days`
    3. Compute z-score if enough history exists
    4. Flag as anomaly if deviation exceeds threshold
    """
    results = []

    with engine.connect() as conn:
        for table in MONITORED_TABLES:
            try:
                # Current count (last 24 hours)
                current = conn.execute(text(f"""
                    SELECT COUNT(*) FROM {table}
                    WHERE ingestion_timestamp >= NOW() - INTERVAL '24 hours'
                """)).scalar() or 0

                # Historical daily counts
                history = conn.execute(text(f"""
                    SELECT
                        ingestion_timestamp::DATE AS day,
                        COUNT(*) AS cnt
                    FROM {table}
                    WHERE ingestion_timestamp >= NOW() - INTERVAL '{lookback_days} days'
                      AND ingestion_timestamp < NOW() - INTERVAL '24 hours'
                    GROUP BY day
                    ORDER BY day
                """)).fetchall()

                if len(history) < 2:
                    # Not enough history to judge
                    results.append(CheckResult(
                        check_name=f"row_count_{table}",
                        check_type=CheckType.ROW_COUNT,
                        table_name=table,
                        expected_value=None,
                        actual_value=float(current),
                        passed=True,
                        severity=Severity.INFO,
                        details={"reason": "Insufficient history", "history_days": len(history)},
                    ))
                    continue

                counts = [row.cnt for row in history]
                mean = sum(counts) / len(counts)
                variance = sum((c - mean) ** 2 for c in counts) / len(counts)
                std = math.sqrt(variance) if variance > 0 else 1.0

                z_score = (current - mean) / std if std > 0 else 0
                deviation = abs(current - mean) / mean if mean > 0 else 0
                is_anomaly = deviation > deviation_threshold

                severity = Severity.INFO
                if is_anomaly and deviation > 0.5:
                    severity = Severity.CRITICAL
                elif is_anomaly:
                    severity = Severity.WARNING

                results.append(CheckResult(
                    check_name=f"row_count_{table}",
                    check_type=CheckType.ROW_COUNT,
                    table_name=table,
                    expected_value=round(mean, 2),
                    actual_value=float(current),
                    passed=not is_anomaly,
                    severity=severity,
                    details={
                        "mean": round(mean, 2),
                        "std": round(std, 2),
                        "z_score": round(z_score, 2),
                        "deviation_pct": round(deviation * 100, 2),
                        "threshold_pct": deviation_threshold * 100,
                        "history_days": len(history),
                    },
                ))

            except Exception as e:
                logger.error("Row count check failed for %s: %s", table, e)
                results.append(CheckResult(
                    check_name=f"row_count_{table}",
                    check_type=CheckType.ROW_COUNT,
                    table_name=table,
                    passed=False,
                    severity=Severity.CRITICAL,
                    details={"error": str(e)},
                ))

    return results


def compute_anomaly_score(
    engine: Engine,
    table: str,
    lookback_days: int = 7,
    threshold: float = 2.0,
) -> AnomalyScore | None:
    """Compute a z-score-based anomaly score for a table's row count."""
    with engine.connect() as conn:
        current = conn.execute(text(f"""
            SELECT COUNT(*) FROM {table}
            WHERE ingestion_timestamp >= NOW() - INTERVAL '24 hours'
        """)).scalar() or 0

        history = conn.execute(text(f"""
            SELECT
                ingestion_timestamp::DATE AS day,
                COUNT(*) AS cnt
            FROM {table}
            WHERE ingestion_timestamp >= NOW() - INTERVAL '{lookback_days} days'
              AND ingestion_timestamp < NOW() - INTERVAL '24 hours'
            GROUP BY day
        """)).fetchall()

        if len(history) < 2:
            return None

        counts = [row.cnt for row in history]
        mean = sum(counts) / len(counts)
        variance = sum((c - mean) ** 2 for c in counts) / len(counts)
        std = math.sqrt(variance) if variance > 0 else 1.0
        z_score = (current - mean) / std

        return AnomalyScore(
            metric_name="row_count",
            table_name=table,
            current_value=float(current),
            baseline_mean=round(mean, 2),
            baseline_std=round(std, 2),
            z_score=round(z_score, 2),
            is_anomaly=abs(z_score) > threshold,
            threshold=threshold,
        )
