"""Alert dispatcher — routes alerts to configured channels."""

import json
import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

from monitoring.alerting.base import AlertChannel
from monitoring.alerting.console import ConsoleAlertChannel
from monitoring.alerting.email import EmailAlertChannel
from monitoring.alerting.slack import SlackAlertChannel
from monitoring.models import Alert

logger = logging.getLogger(__name__)


class AlertDispatcher:
    """
    Routes alerts to all configured channels.
    Falls back to console if no other channels are configured.
    """

    def __init__(self, engine: Engine | None = None) -> None:
        self.engine = engine
        self.channels: list[AlertChannel] = []

        # Register channels
        slack = SlackAlertChannel()
        if slack.is_configured:
            self.channels.append(slack)
            logger.info("Slack alerting enabled")

        email = EmailAlertChannel()
        if email.is_configured:
            self.channels.append(email)
            logger.info("Email alerting enabled")

        # Console is always available
        self.console = ConsoleAlertChannel()
        self.channels.append(self.console)

        if len(self.channels) == 1:
            logger.info(
                "No external alert channels configured — using console only. "
                "Set SLACK_WEBHOOK_URL or SMTP_HOST to enable external alerts."
            )

    def dispatch(self, alert: Alert) -> dict[str, bool]:
        """
        Send an alert through all configured channels.
        Returns a dict of {channel_name: success}.
        """
        results = {}

        for channel in self.channels:
            try:
                success = channel.send(alert)
                results[channel.channel_name] = success
            except Exception as e:
                logger.error(
                    "Alert channel %s failed: %s", channel.channel_name, e
                )
                results[channel.channel_name] = False

        # Record in alert history
        if self.engine:
            self._record_alert(alert, results)

        return results

    def dispatch_all(self, alerts: list[Alert]) -> list[dict[str, bool]]:
        """Dispatch multiple alerts."""
        all_results = []
        for alert in alerts:
            result = self.dispatch(alert)
            all_results.append(result)

        # Summary
        total = len(alerts)
        if total > 0:
            logger.info(
                "Dispatched %d alerts across %d channels",
                total, len(self.channels),
            )

        return all_results

    def _record_alert(self, alert: Alert, results: dict[str, bool]) -> None:
        """Store alert dispatch history."""
        try:
            with self.engine.begin() as conn:
                for channel_name, success in results.items():
                    conn.execute(
                        text("""
                            INSERT INTO monitoring.alert_history
                                (channel, payload, success)
                            VALUES (:channel, :payload::jsonb, :success)
                        """),
                        {
                            "channel": channel_name,
                            "payload": json.dumps({
                                "check_name": alert.check_result.check_name,
                                "severity": alert.check_result.severity.value,
                                "message": alert.message[:500],
                            }),
                            "success": success,
                        },
                    )
        except Exception as e:
            logger.error("Failed to record alert history: %s", e)
