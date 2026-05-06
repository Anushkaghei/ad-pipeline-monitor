"""Tests for the monitoring engine and checks."""

from datetime import datetime

from monitoring.models import (
    Alert,
    AnomalyScore,
    CheckResult,
    CheckType,
    Severity,
)


class TestCheckResult:
    """Tests for CheckResult model."""

    def test_create_passing_check(self):
        result = CheckResult(
            check_name="test_check",
            check_type=CheckType.ROW_COUNT,
            table_name="raw.meta_campaigns",
            expected_value=100.0,
            actual_value=98.0,
            passed=True,
        )
        assert result.passed is True
        assert result.severity == Severity.WARNING  # default

    def test_create_failing_check(self):
        result = CheckResult(
            check_name="test_check",
            check_type=CheckType.NULL_THRESHOLD,
            table_name="raw.google_campaigns",
            expected_value=5.0,
            actual_value=15.0,
            passed=False,
            severity=Severity.CRITICAL,
        )
        assert result.passed is False
        assert result.severity == Severity.CRITICAL

    def test_details_dict(self):
        result = CheckResult(
            check_name="test",
            check_type=CheckType.FRESHNESS,
            passed=True,
            details={"hours_stale": 2.5, "sla": 6.0},
        )
        assert result.details["hours_stale"] == 2.5


class TestAlert:
    """Tests for Alert model."""

    def test_format_message(self):
        check = CheckResult(
            check_name="row_count_raw.meta_campaigns",
            check_type=CheckType.ROW_COUNT,
            table_name="raw.meta_campaigns",
            expected_value=100.0,
            actual_value=50.0,
            passed=False,
            severity=Severity.CRITICAL,
        )
        alert = Alert(
            check_result=check,
            pipeline_name="daily_ingestion",
        )
        msg = alert.format_message()

        assert "FAIL" in msg
        assert "ROW_COUNT" in msg
        assert "daily_ingestion" in msg
        assert "raw.meta_campaigns" in msg
        assert "100.0" in msg
        assert "50.0" in msg
        assert "CRITICAL" in msg

    def test_passing_alert_message(self):
        check = CheckResult(
            check_name="freshness_check",
            check_type=CheckType.FRESHNESS,
            passed=True,
        )
        alert = Alert(check_result=check, pipeline_name="test")
        msg = alert.format_message()
        assert "PASS" in msg


class TestAnomalyScore:
    """Tests for AnomalyScore model."""

    def test_anomaly_detected(self):
        score = AnomalyScore(
            metric_name="row_count",
            table_name="raw.meta_campaigns",
            current_value=10.0,
            baseline_mean=100.0,
            baseline_std=10.0,
            z_score=-9.0,
            is_anomaly=True,
            threshold=2.0,
        )
        assert score.is_anomaly is True
        assert abs(score.z_score) > score.threshold

    def test_normal_score(self):
        score = AnomalyScore(
            metric_name="row_count",
            table_name="raw.meta_campaigns",
            current_value=102.0,
            baseline_mean=100.0,
            baseline_std=10.0,
            z_score=0.2,
            is_anomaly=False,
            threshold=2.0,
        )
        assert score.is_anomaly is False
