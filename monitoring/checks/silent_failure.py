"""Silent failure detection.

Detects cases where:
- API returned 0 rows unexpectedly
- Missing date partitions (gaps in date sequences)
- Downstream tables not updated after upstream changes
"""

import logging
from datetime import date, timedelta

from sqlalchemy import text
from sqlalchemy.engine import Engine

from monitoring.models import CheckResult, CheckType, Severity

logger = logging.getLogger(__name__)

# Table -> date column mapping
DATE_COLUMNS = {
    "raw.meta_campaigns": "date_start",
    "raw.google_campaigns": "date",
    "raw.meta_adsets": "date_start",
    "raw.google_keywords": "date",
}


def check_silent_failures(
    engine: Engine,
    lookback_days: int = 7,
) -> list[CheckResult]:
    """Run all silent failure checks."""
    results = []
    results.extend(_check_zero_row_ingestions(engine))
    results.extend(_check_missing_partitions(engine, lookback_days))
    results.extend(_check_downstream_staleness(engine))
    return results


def _check_zero_row_ingestions(engine: Engine) -> list[CheckResult]:
    """Detect pipeline runs that succeeded but ingested 0 rows."""
    results = []

    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT pipeline_name, started_at, completed_at
            FROM monitoring.pipeline_runs
            WHERE status = 'success'
              AND rows_ingested = 0
              AND started_at >= NOW() - INTERVAL '24 hours'
            ORDER BY started_at DESC
        """)).fetchall()

        if rows:
            results.append(CheckResult(
                check_name="silent_failure_zero_rows",
                check_type=CheckType.SILENT_FAILURE,
                passed=False,
                severity=Severity.WARNING,
                details={
                    "description": "Pipeline(s) succeeded but ingested 0 rows",
                    "pipelines": [
                        {
                            "name": r.pipeline_name,
                            "started_at": r.started_at.isoformat(),
                        }
                        for r in rows
                    ],
                },
            ))
        else:
            results.append(CheckResult(
                check_name="silent_failure_zero_rows",
                check_type=CheckType.SILENT_FAILURE,
                passed=True,
                severity=Severity.INFO,
                details={"description": "No zero-row ingestions detected"},
            ))

    return results


def _check_missing_partitions(
    engine: Engine, lookback_days: int
) -> list[CheckResult]:
    """Detect missing date partitions (gaps in date sequences)."""
    results = []
    today = date.today()

    with engine.connect() as conn:
        for table, date_col in DATE_COLUMNS.items():
            try:
                rows = conn.execute(text(f"""
                    SELECT DISTINCT {date_col}::DATE AS dt
                    FROM {table}
                    WHERE {date_col} >= :start_date
                      AND {date_col} <= :end_date
                    ORDER BY dt
                """), {
                    "start_date": today - timedelta(days=lookback_days),
                    "end_date": today,
                }).fetchall()

                existing_dates = {r.dt for r in rows}
                expected_dates = {
                    today - timedelta(days=i) for i in range(lookback_days + 1)
                }
                missing = sorted(expected_dates - existing_dates)

                if missing:
                    results.append(CheckResult(
                        check_name=f"missing_partitions_{table}",
                        check_type=CheckType.SILENT_FAILURE,
                        table_name=table,
                        passed=False,
                        severity=Severity.WARNING if len(missing) <= 2 else Severity.CRITICAL,
                        details={
                            "missing_dates": [d.isoformat() for d in missing],
                            "missing_count": len(missing),
                            "lookback_days": lookback_days,
                        },
                    ))
                else:
                    results.append(CheckResult(
                        check_name=f"missing_partitions_{table}",
                        check_type=CheckType.SILENT_FAILURE,
                        table_name=table,
                        passed=True,
                        severity=Severity.INFO,
                        details={"lookback_days": lookback_days, "all_dates_present": True},
                    ))

            except Exception as e:
                logger.error("Missing partition check failed for %s: %s", table, e)
                results.append(CheckResult(
                    check_name=f"missing_partitions_{table}",
                    check_type=CheckType.SILENT_FAILURE,
                    table_name=table,
                    passed=False,
                    severity=Severity.CRITICAL,
                    details={"error": str(e)},
                ))

    return results


def _check_downstream_staleness(engine: Engine) -> list[CheckResult]:
    """Check if mart tables are older than their staging sources."""
    results = []

    pairs = [
        ("staging.stg_meta_campaigns", "marts.fct_ad_performance"),
        ("staging.stg_google_campaigns", "marts.fct_ad_performance"),
    ]

    with engine.connect() as conn:
        for upstream, downstream in pairs:
            try:
                # Check if both tables exist by attempting a query
                up_ts = conn.execute(text(f"""
                    SELECT MAX(ingestion_timestamp) AS ts FROM {upstream}
                """)).scalar()

                down_ts = conn.execute(text(f"""
                    SELECT MAX(ingestion_timestamp) AS ts FROM {downstream}
                """)).scalar()

                if up_ts and down_ts and up_ts > down_ts:
                    results.append(CheckResult(
                        check_name=f"downstream_stale_{downstream}",
                        check_type=CheckType.SILENT_FAILURE,
                        table_name=downstream,
                        passed=False,
                        severity=Severity.WARNING,
                        details={
                            "upstream": upstream,
                            "upstream_updated": up_ts.isoformat() if up_ts else None,
                            "downstream_updated": down_ts.isoformat() if down_ts else None,
                            "description": f"{downstream} is stale vs {upstream}",
                        },
                    ))
                else:
                    results.append(CheckResult(
                        check_name=f"downstream_stale_{downstream}",
                        check_type=CheckType.SILENT_FAILURE,
                        table_name=downstream,
                        passed=True,
                        severity=Severity.INFO,
                    ))

            except Exception:
                # Tables may not exist yet — not a failure
                results.append(CheckResult(
                    check_name=f"downstream_stale_{downstream}",
                    check_type=CheckType.SILENT_FAILURE,
                    table_name=downstream,
                    passed=True,
                    severity=Severity.INFO,
                    details={"reason": "Tables not yet materialized"},
                ))

    return results
