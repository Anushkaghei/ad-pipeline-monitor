"""Monitoring engine — orchestrates all observability checks."""

import logging
import os
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.engine import Engine

from monitoring.checks.dbt_tests import parse_dbt_results
from monitoring.checks.freshness import check_freshness
from monitoring.checks.null_threshold import check_null_thresholds
from monitoring.checks.row_count import check_row_counts
from monitoring.checks.silent_failure import check_silent_failures
from monitoring.models import Alert, CheckResult

logger = logging.getLogger(__name__)


class MonitoringEngine:
    """
    Orchestrates all monitoring checks, stores results,
    and dispatches alerts for failures.
    """

    def __init__(self, engine: Engine) -> None:
        self.engine = engine
        self.deviation_threshold = float(os.getenv("ROW_COUNT_DEVIATION_THRESHOLD", "0.30"))
        self.null_threshold = float(os.getenv("NULL_THRESHOLD_PERCENT", "5.0"))
        self.freshness_sla = float(os.getenv("FRESHNESS_SLA_HOURS", "6"))
        self.lookback_days = int(os.getenv("ANOMALY_LOOKBACK_DAYS", "7"))

    def run_all_checks(self) -> list[CheckResult]:
        """Run every monitoring check and return aggregated results."""
        logger.info("=" * 60)
        logger.info("Starting monitoring run at %s", datetime.now(timezone.utc).isoformat())
        logger.info("=" * 60)

        all_results: list[CheckResult] = []

        # 1. Row count anomalies
        logger.info("Running row count checks...")
        rc_results = check_row_counts(
            self.engine, deviation_threshold=self.deviation_threshold,
            lookback_days=self.lookback_days,
        )
        all_results.extend(rc_results)
        logger.info("  → %d checks, %d passed", len(rc_results), sum(r.passed for r in rc_results))

        # 2. Null threshold monitoring
        logger.info("Running null threshold checks...")
        null_results = check_null_thresholds(self.engine)
        all_results.extend(null_results)
        logger.info("  → %d checks, %d passed", len(null_results), sum(r.passed for r in null_results))

        # 3. Freshness monitoring
        logger.info("Running freshness checks...")
        fresh_results = check_freshness(self.engine)
        all_results.extend(fresh_results)
        logger.info("  → %d checks, %d passed", len(fresh_results), sum(r.passed for r in fresh_results))

        # 4. Silent failure detection
        logger.info("Running silent failure checks...")
        sf_results = check_silent_failures(self.engine, lookback_days=self.lookback_days)
        all_results.extend(sf_results)
        logger.info("  → %d checks, %d passed", len(sf_results), sum(r.passed for r in sf_results))

        # 5. dbt test results
        logger.info("Parsing dbt test results...")
        dbt_results = parse_dbt_results()
        all_results.extend(dbt_results)
        logger.info("  → %d checks, %d passed", len(dbt_results), sum(r.passed for r in dbt_results))

        # Store results
        self._store_results(all_results)

        # Summary
        total = len(all_results)
        passed = sum(r.passed for r in all_results)
        failed = total - passed
        logger.info("=" * 60)
        logger.info("Monitoring complete: %d total, %d passed, %d failed", total, passed, failed)
        logger.info("=" * 60)

        return all_results

    def get_failed_checks(self, results: list[CheckResult]) -> list[CheckResult]:
        """Filter to only failed checks."""
        return [r for r in results if not r.passed]

    def generate_alerts(
        self, results: list[CheckResult], pipeline_name: str = "ad_pipeline"
    ) -> list[Alert]:
        """Generate Alert objects for failed checks."""
        alerts = []
        for result in results:
            if not result.passed:
                alert = Alert(
                    check_result=result,
                    pipeline_name=pipeline_name,
                )
                alert.message = alert.format_message()
                alerts.append(alert)
        return alerts

    def _store_results(self, results: list[CheckResult]) -> None:
        """Persist check results to the monitoring schema."""
        try:
            with self.engine.begin() as conn:
                for r in results:
                    conn.execute(
                        text("""
                            INSERT INTO monitoring.check_results
                                (check_name, check_type, table_name,
                                 expected_value, actual_value, passed,
                                 severity, details, checked_at)
                            VALUES
                                (:check_name, :check_type, :table_name,
                                 :expected_value, :actual_value, :passed,
                                 :severity, :details::jsonb, :checked_at)
                        """),
                        {
                            "check_name": r.check_name,
                            "check_type": r.check_type.value,
                            "table_name": r.table_name,
                            "expected_value": r.expected_value,
                            "actual_value": r.actual_value,
                            "passed": r.passed,
                            "severity": r.severity.value,
                            "details": r.details if isinstance(r.details, str) else __import__("json").dumps(r.details),
                            "checked_at": r.checked_at,
                        },
                    )
            logger.info("Stored %d check results", len(results))
        except Exception as e:
            logger.error("Failed to store check results: %s", e)
