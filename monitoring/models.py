"""Pydantic models for monitoring domain objects."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class CheckType(str, Enum):
    ROW_COUNT = "row_count"
    NULL_THRESHOLD = "null_threshold"
    FRESHNESS = "freshness"
    SILENT_FAILURE = "silent_failure"
    DBT_TEST = "dbt_test"


class CheckResult(BaseModel):
    """Result of a single monitoring check."""

    check_name: str
    check_type: CheckType
    table_name: str | None = None
    expected_value: float | None = None
    actual_value: float | None = None
    passed: bool
    severity: Severity = Severity.WARNING
    details: dict[str, Any] = Field(default_factory=dict)
    checked_at: datetime = Field(default_factory=datetime.utcnow)


class PipelineRun(BaseModel):
    """Record of a pipeline execution."""

    id: int | None = None
    pipeline_name: str
    status: str = "running"
    rows_ingested: int = 0
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    error_message: str | None = None


class Alert(BaseModel):
    """An alert to be dispatched via one or more channels."""

    check_result: CheckResult
    pipeline_name: str = "unknown"
    message: str = ""
    channels: list[str] = Field(default_factory=lambda: ["console"])

    def format_message(self) -> str:
        """Format a human-readable alert message."""
        cr = self.check_result
        status = "✅ PASS" if cr.passed else "🚨 FAIL"
        lines = [
            f"{status} | {cr.check_type.value.upper()}",
            f"Check: {cr.check_name}",
            f"Pipeline: {self.pipeline_name}",
        ]
        if cr.table_name:
            lines.append(f"Table: {cr.table_name}")
        if cr.expected_value is not None:
            lines.append(f"Expected: {cr.expected_value}")
        if cr.actual_value is not None:
            lines.append(f"Actual: {cr.actual_value}")
        lines.append(f"Severity: {cr.severity.value.upper()}")
        lines.append(f"Time: {cr.checked_at.isoformat()}")
        if cr.details:
            lines.append(f"Details: {cr.details}")
        return "\n".join(lines)


class AnomalyScore(BaseModel):
    """Anomaly scoring for a metric."""

    metric_name: str
    table_name: str
    current_value: float
    baseline_mean: float
    baseline_std: float
    z_score: float
    is_anomaly: bool
    threshold: float
