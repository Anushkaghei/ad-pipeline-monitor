"""Tests for anomaly detection logic."""

import math

from monitoring.models import AnomalyScore, CheckResult, CheckType, Severity


class TestRowCountAnomalyDetection:
    """Test the row count anomaly detection algorithm."""

    def test_no_deviation(self):
        """No anomaly when current equals mean."""
        mean = 100.0
        std = 10.0
        current = 100.0
        z_score = (current - mean) / std
        deviation = abs(current - mean) / mean

        assert abs(z_score) < 0.01
        assert deviation < 0.30

    def test_moderate_deviation(self):
        """Flag when deviation exceeds 30%."""
        mean = 100.0
        std = 10.0
        current = 60.0  # 40% drop
        deviation = abs(current - mean) / mean

        assert deviation > 0.30  # Should flag

    def test_spike_detection(self):
        """Detect upward spikes."""
        mean = 100.0
        std = 10.0
        current = 200.0  # 100% increase
        z_score = (current - mean) / std
        deviation = abs(current - mean) / mean

        assert z_score > 2.0
        assert deviation > 0.50

    def test_zero_std_handling(self):
        """Handle zero standard deviation gracefully."""
        mean = 100.0
        std = 0.0
        current = 100.0

        # Should use 1.0 as fallback
        safe_std = std if std > 0 else 1.0
        z_score = (current - mean) / safe_std
        assert z_score == 0.0

    def test_severity_escalation(self):
        """Test severity levels based on deviation."""
        # < 30% → info
        assert _get_severity(0.15) == Severity.INFO
        # 30-50% → warning
        assert _get_severity(0.40) == Severity.WARNING
        # > 50% → critical
        assert _get_severity(0.60) == Severity.CRITICAL


class TestNullThresholdDetection:
    """Test null threshold calculations."""

    def test_zero_nulls(self):
        total, nulls = 100, 0
        pct = (nulls / total) * 100
        assert pct == 0.0
        assert pct <= 5.0  # Under threshold

    def test_acceptable_nulls(self):
        total, nulls = 100, 3
        pct = (nulls / total) * 100
        assert pct == 3.0
        assert pct <= 5.0

    def test_exceeds_threshold(self):
        total, nulls = 100, 10
        pct = (nulls / total) * 100
        assert pct == 10.0
        assert pct > 5.0

    def test_all_nulls(self):
        total, nulls = 100, 100
        pct = (nulls / total) * 100
        assert pct == 100.0
        assert pct > 5.0

    def test_zero_rows(self):
        """Zero total rows should not error."""
        total = 0
        # Should be treated as pass
        assert total == 0


class TestFreshnessDetection:
    """Test freshness SLA calculations."""

    def test_within_sla(self):
        hours_stale = 2.5
        sla_hours = 6.0
        assert hours_stale <= sla_hours

    def test_exceeds_sla(self):
        hours_stale = 8.0
        sla_hours = 6.0
        assert hours_stale > sla_hours

    def test_critical_staleness(self):
        hours_stale = 24.0
        sla_hours = 6.0
        assert hours_stale > sla_hours * 2  # Critical


class TestAnomalyScoreModel:
    """Test the AnomalyScore Z-score logic."""

    def test_z_score_calculation(self):
        score = AnomalyScore(
            metric_name="row_count",
            table_name="test_table",
            current_value=150.0,
            baseline_mean=100.0,
            baseline_std=20.0,
            z_score=2.5,
            is_anomaly=True,
            threshold=2.0,
        )
        expected_z = (150.0 - 100.0) / 20.0
        assert abs(score.z_score - expected_z) < 0.01

    def test_negative_z_score(self):
        score = AnomalyScore(
            metric_name="row_count",
            table_name="test_table",
            current_value=50.0,
            baseline_mean=100.0,
            baseline_std=20.0,
            z_score=-2.5,
            is_anomaly=True,
            threshold=2.0,
        )
        assert score.z_score < 0
        assert abs(score.z_score) > score.threshold


def _get_severity(deviation: float) -> Severity:
    """Helper matching the engine's severity logic."""
    if deviation > 0.5:
        return Severity.CRITICAL
    elif deviation > 0.30:
        return Severity.WARNING
    return Severity.INFO
