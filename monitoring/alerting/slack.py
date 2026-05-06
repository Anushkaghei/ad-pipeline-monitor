"""Slack webhook alert channel."""

import json
import logging
import os

import requests

from monitoring.alerting.base import AlertChannel
from monitoring.models import Alert, Severity

logger = logging.getLogger(__name__)

SEVERITY_EMOJI = {
    Severity.INFO: ":information_source:",
    Severity.WARNING: ":warning:",
    Severity.CRITICAL: ":rotating_light:",
}


class SlackAlertChannel(AlertChannel):
    """Send alerts to Slack via incoming webhook."""

    def __init__(self) -> None:
        self.webhook_url = os.getenv("SLACK_WEBHOOK_URL", "")

    @property
    def channel_name(self) -> str:
        return "slack"

    @property
    def is_configured(self) -> bool:
        return bool(self.webhook_url)

    def send(self, alert: Alert) -> bool:
        if not self.is_configured:
            logger.warning("Slack webhook not configured — skipping")
            return False

        cr = alert.check_result
        emoji = SEVERITY_EMOJI.get(cr.severity, ":grey_question:")

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji} Ad Pipeline Alert — {cr.severity.value.upper()}",
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Check:*\n{cr.check_name}"},
                    {"type": "mrkdwn", "text": f"*Pipeline:*\n{alert.pipeline_name}"},
                    {"type": "mrkdwn", "text": f"*Status:*\n{'✅ Pass' if cr.passed else '❌ Fail'}"},
                    {"type": "mrkdwn", "text": f"*Severity:*\n{cr.severity.value.upper()}"},
                ],
            },
        ]

        if cr.table_name:
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Table:* `{cr.table_name}`"},
            })

        if cr.expected_value is not None or cr.actual_value is not None:
            fields = []
            if cr.expected_value is not None:
                fields.append({"type": "mrkdwn", "text": f"*Expected:*\n{cr.expected_value}"})
            if cr.actual_value is not None:
                fields.append({"type": "mrkdwn", "text": f"*Actual:*\n{cr.actual_value}"})
            blocks.append({"type": "section", "fields": fields})

        if cr.details:
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"```{json.dumps(cr.details, indent=2)}```"},
            })

        blocks.append({
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": f"_Checked at {cr.checked_at.isoformat()}_"}],
        })

        try:
            resp = requests.post(
                self.webhook_url,
                json={"blocks": blocks},
                timeout=10,
            )
            resp.raise_for_status()
            logger.info("Slack alert sent for %s", cr.check_name)
            return True
        except requests.RequestException as e:
            logger.error("Failed to send Slack alert: %s", e)
            return False
