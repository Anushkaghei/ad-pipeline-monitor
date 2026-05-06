"""Console alert channel — always available fallback."""

import logging

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from monitoring.alerting.base import AlertChannel
from monitoring.models import Alert, Severity

logger = logging.getLogger(__name__)
console = Console()

SEVERITY_STYLES = {
    Severity.INFO: ("blue", "ℹ️"),
    Severity.WARNING: ("yellow", "⚠️"),
    Severity.CRITICAL: ("red bold", "🚨"),
}


class ConsoleAlertChannel(AlertChannel):
    """Print alerts to the console with rich formatting."""

    @property
    def channel_name(self) -> str:
        return "console"

    @property
    def is_configured(self) -> bool:
        return True  # Always available

    def send(self, alert: Alert) -> bool:
        cr = alert.check_result
        style, icon = SEVERITY_STYLES.get(cr.severity, ("white", "•"))

        title = f"{icon} {cr.severity.value.upper()} — {cr.check_name}"

        body = Text()
        body.append(f"Pipeline: {alert.pipeline_name}\n")
        if cr.table_name:
            body.append(f"Table: {cr.table_name}\n")
        body.append(f"Status: {'PASS ✅' if cr.passed else 'FAIL ❌'}\n")
        if cr.expected_value is not None:
            body.append(f"Expected: {cr.expected_value}\n")
        if cr.actual_value is not None:
            body.append(f"Actual: {cr.actual_value}\n")
        body.append(f"Time: {cr.checked_at.isoformat()}\n")
        if cr.details:
            body.append(f"Details: {cr.details}")

        console.print(Panel(body, title=title, border_style=style, expand=False))
        return True
