"""Tests for the alerting system."""

from monitoring.alerting.console import ConsoleAlertChannel
from monitoring.alerting.email import EmailAlertChannel
from monitoring.alerting.slack import SlackAlertChannel
from monitoring.models import Alert, CheckResult, CheckType, Severity


def _make_alert(passed: bool = False, severity: Severity = Severity.WARNING) -> Alert:
    """Helper to create a test alert."""
    check = CheckResult(
        check_name="test_alert_check",
        check_type=CheckType.ROW_COUNT,
        table_name="raw.meta_campaigns",
        expected_value=100.0,
        actual_value=50.0 if not passed else 98.0,
        passed=passed,
        severity=severity,
        details={"test": True},
    )
    alert = Alert(
        check_result=check,
        pipeline_name="test_pipeline",
    )
    alert.message = alert.format_message()
    return alert


class TestConsoleAlertChannel:
    """Tests for console alert channel."""

    def test_is_always_configured(self):
        channel = ConsoleAlertChannel()
        assert channel.is_configured is True
        assert channel.channel_name == "console"

    def test_send_succeeds(self):
        channel = ConsoleAlertChannel()
        alert = _make_alert()
        result = channel.send(alert)
        assert result is True

    def test_send_passing_alert(self):
        channel = ConsoleAlertChannel()
        alert = _make_alert(passed=True)
        result = channel.send(alert)
        assert result is True


class TestSlackAlertChannel:
    """Tests for Slack alert channel."""

    def test_not_configured_without_url(self):
        channel = SlackAlertChannel()
        # Unless SLACK_WEBHOOK_URL is set, should not be configured
        if not channel.webhook_url:
            assert channel.is_configured is False

    def test_channel_name(self):
        channel = SlackAlertChannel()
        assert channel.channel_name == "slack"

    def test_send_skips_when_unconfigured(self):
        channel = SlackAlertChannel()
        if not channel.is_configured:
            result = channel.send(_make_alert())
            assert result is False


class TestEmailAlertChannel:
    """Tests for email alert channel."""

    def test_not_configured_without_smtp(self):
        channel = EmailAlertChannel()
        if not channel.host:
            assert channel.is_configured is False

    def test_channel_name(self):
        channel = EmailAlertChannel()
        assert channel.channel_name == "email"

    def test_send_skips_when_unconfigured(self):
        channel = EmailAlertChannel()
        if not channel.is_configured:
            result = channel.send(_make_alert())
            assert result is False
