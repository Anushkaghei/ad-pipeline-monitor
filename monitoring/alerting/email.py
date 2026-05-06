"""Email alert channel via SMTP (compatible with AWS SES)."""

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from monitoring.alerting.base import AlertChannel
from monitoring.models import Alert, Severity

logger = logging.getLogger(__name__)

SEVERITY_COLORS = {
    Severity.INFO: "#3498db",
    Severity.WARNING: "#f39c12",
    Severity.CRITICAL: "#e74c3c",
}


class EmailAlertChannel(AlertChannel):
    """Send alerts via SMTP email (works with SES or any SMTP server)."""

    def __init__(self) -> None:
        self.host = os.getenv("SMTP_HOST", "")
        self.port = int(os.getenv("SMTP_PORT", "587"))
        self.user = os.getenv("SMTP_USER", "")
        self.password = os.getenv("SMTP_PASSWORD", "")
        self.from_addr = os.getenv("ALERT_EMAIL_FROM", "alerts@example.com")
        self.to_addr = os.getenv("ALERT_EMAIL_TO", "team@example.com")

    @property
    def channel_name(self) -> str:
        return "email"

    @property
    def is_configured(self) -> bool:
        return bool(self.host and self.user and self.password)

    def send(self, alert: Alert) -> bool:
        if not self.is_configured:
            logger.warning("Email SMTP not configured — skipping")
            return False

        cr = alert.check_result
        color = SEVERITY_COLORS.get(cr.severity, "#95a5a6")

        subject = f"[{cr.severity.value.upper()}] Ad Pipeline Alert — {cr.check_name}"

        html = f"""
        <html><body style="font-family: Arial, sans-serif; max-width: 600px;">
        <div style="border-left: 4px solid {color}; padding: 12px 16px; margin: 16px 0; background: #f9f9f9;">
            <h2 style="color: {color}; margin: 0 0 8px;">
                {'✅' if cr.passed else '❌'} {cr.check_name}
            </h2>
            <table style="border-collapse: collapse; width: 100%;">
                <tr><td style="padding: 4px 8px; font-weight: bold;">Pipeline</td>
                    <td style="padding: 4px 8px;">{alert.pipeline_name}</td></tr>
                <tr><td style="padding: 4px 8px; font-weight: bold;">Severity</td>
                    <td style="padding: 4px 8px;">{cr.severity.value.upper()}</td></tr>
                {"<tr><td style='padding: 4px 8px; font-weight: bold;'>Table</td><td style='padding: 4px 8px;'>" + cr.table_name + "</td></tr>" if cr.table_name else ""}
                {"<tr><td style='padding: 4px 8px; font-weight: bold;'>Expected</td><td style='padding: 4px 8px;'>" + str(cr.expected_value) + "</td></tr>" if cr.expected_value is not None else ""}
                {"<tr><td style='padding: 4px 8px; font-weight: bold;'>Actual</td><td style='padding: 4px 8px;'>" + str(cr.actual_value) + "</td></tr>" if cr.actual_value is not None else ""}
                <tr><td style="padding: 4px 8px; font-weight: bold;">Time</td>
                    <td style="padding: 4px 8px;">{cr.checked_at.isoformat()}</td></tr>
            </table>
            {"<pre style='background: #eee; padding: 8px; font-size: 12px;'>" + str(cr.details) + "</pre>" if cr.details else ""}
        </div>
        </body></html>
        """

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.from_addr
        msg["To"] = self.to_addr
        msg.attach(MIMEText(alert.format_message(), "plain"))
        msg.attach(MIMEText(html, "html"))

        try:
            with smtplib.SMTP(self.host, self.port) as server:
                server.starttls()
                server.login(self.user, self.password)
                server.send_message(msg)
            logger.info("Email alert sent for %s", cr.check_name)
            return True
        except Exception as e:
            logger.error("Failed to send email alert: %s", e)
            return False
