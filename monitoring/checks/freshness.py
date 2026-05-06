"""Freshness monitoring.

Detects stale tables where the last update exceeds the SLA threshold.
"""

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

from monitoring.models import CheckResult, CheckType, Severity

logger = logging.getLogger(__name__)

# Default freshness SLAs: table -> max_hours
DEFAULT_SLAS: dict[str, float] = {
    "raw.meta_campaigns": 6.0,
    "raw.google_campaigns": 6.0,
    "raw.meta_adsets": 6.0,
    "raw.google_keywords": 6.0,
}


def check_freshness(
    engine: Engine,
    sla_hours: dict[str, float] | None = None,
) -> list[CheckResult]:
    """
    Check table freshness against SLA thresholds.

    For each monitored table, check if the most recent
    ingestion_timestamp is within the SLA window.
    """
    slas = sla_hours or DEFAULT_SLAS
    results = []

    with engine.connect() as conn:
        for table, max_hours in slas.items():
            try:
                row = conn.execute(text(f"""
                    SELECT
                        MAX(ingestion_timestamp) AS last_updated,
                        EXTRACT(EPOCH FROM (NOW() - MAX(ingestion_timestamp))) / 3600
                            AS hours_since_update
                    FROM {table}
                """)).fetchone()

                if row is None or row.last_updated is None:
                    results.append(CheckResult(
                        check_name=f"freshness_{table}",
                        check_type=CheckType.FRESHNESS,
                        table_name=table,
                        passed=False,
                        severity=Severity.CRITICAL,
                        details={"reason": "Table is empty — no data ingested"},
                    ))
                    continue

                hours_stale = round(row.hours_since_update, 2)
                passed = hours_stale <= max_hours

                severity = Severity.INFO
                if not passed and hours_stale > max_hours * 2:
                    severity = Severity.CRITICAL
                elif not passed:
                    severity = Severity.WARNING

                results.append(CheckResult(
                    check_name=f"freshness_{table}",
                    check_type=CheckType.FRESHNESS,
                    table_name=table,
                    expected_value=max_hours,
                    actual_value=hours_stale,
                    passed=passed,
                    severity=severity,
                    details={
                        "last_updated": row.last_updated.isoformat(),
                        "hours_since_update": hours_stale,
                        "sla_hours": max_hours,
                    },
                ))

            except Exception as e:
                logger.error("Freshness check failed for %s: %s", table, e)
                results.append(CheckResult(
                    check_name=f"freshness_{table}",
                    check_type=CheckType.FRESHNESS,
                    table_name=table,
                    passed=False,
                    severity=Severity.CRITICAL,
                    details={"error": str(e)},
                ))

    return results
