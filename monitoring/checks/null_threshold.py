"""Null threshold monitoring.

Checks critical columns for null percentages exceeding configurable limits.
"""

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

from monitoring.models import CheckResult, CheckType, Severity

logger = logging.getLogger(__name__)

# Columns to monitor: table -> [(column, max_null_pct)]
COLUMN_THRESHOLDS: dict[str, list[tuple[str, float]]] = {
    "raw.meta_campaigns": [
        ("campaign_id", 0.0),
        ("spend", 5.0),
        ("impressions", 5.0),
        ("date_start", 0.0),
    ],
    "raw.google_campaigns": [
        ("campaign_id", 0.0),
        ("cost", 5.0),
        ("impressions", 5.0),
        ("date", 0.0),
    ],
    "raw.meta_adsets": [
        ("adset_id", 0.0),
        ("campaign_id", 0.0),
        ("spend", 5.0),
    ],
    "raw.google_keywords": [
        ("keyword_id", 0.0),
        ("campaign_id", 0.0),
        ("cost", 5.0),
    ],
}


def check_null_thresholds(
    engine: Engine,
    custom_thresholds: dict[str, list[tuple[str, float]]] | None = None,
) -> list[CheckResult]:
    """
    Check null percentages for critical columns across monitored tables.

    Returns a CheckResult for each column that exceeds its threshold.
    """
    thresholds = custom_thresholds or COLUMN_THRESHOLDS
    results = []

    with engine.connect() as conn:
        for table, columns in thresholds.items():
            for column, max_pct in columns:
                try:
                    row = conn.execute(text(f"""
                        SELECT
                            COUNT(*) AS total,
                            COUNT(*) FILTER (WHERE {column} IS NULL) AS nulls
                        FROM {table}
                        WHERE ingestion_timestamp >= NOW() - INTERVAL '24 hours'
                    """)).fetchone()

                    total = row.total if row else 0
                    nulls = row.nulls if row else 0

                    if total == 0:
                        results.append(CheckResult(
                            check_name=f"null_{table}.{column}",
                            check_type=CheckType.NULL_THRESHOLD,
                            table_name=table,
                            passed=True,
                            severity=Severity.INFO,
                            details={"reason": "No recent data", "column": column},
                        ))
                        continue

                    null_pct = (nulls / total) * 100
                    passed = null_pct <= max_pct

                    severity = Severity.INFO
                    if not passed and null_pct > 20:
                        severity = Severity.CRITICAL
                    elif not passed:
                        severity = Severity.WARNING

                    results.append(CheckResult(
                        check_name=f"null_{table}.{column}",
                        check_type=CheckType.NULL_THRESHOLD,
                        table_name=table,
                        expected_value=max_pct,
                        actual_value=round(null_pct, 2),
                        passed=passed,
                        severity=severity,
                        details={
                            "column": column,
                            "total_rows": total,
                            "null_rows": nulls,
                            "null_pct": round(null_pct, 2),
                            "threshold_pct": max_pct,
                        },
                    ))

                except Exception as e:
                    logger.error("Null check failed for %s.%s: %s", table, column, e)
                    results.append(CheckResult(
                        check_name=f"null_{table}.{column}",
                        check_type=CheckType.NULL_THRESHOLD,
                        table_name=table,
                        passed=False,
                        severity=Severity.CRITICAL,
                        details={"error": str(e), "column": column},
                    ))

    return results
