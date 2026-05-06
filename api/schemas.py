"""Pydantic response schemas for the monitoring API."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    database: str
    timestamp: str
    version: str = "1.0.0"


class PipelineRunResponse(BaseModel):
    id: int
    pipeline_name: str
    status: str
    rows_ingested: int
    started_at: datetime
    completed_at: datetime | None
    error_message: str | None


class PipelineStatusResponse(BaseModel):
    pipelines: list[PipelineRunResponse]
    total: int


class AnomalyResponse(BaseModel):
    id: int
    check_name: str
    check_type: str
    table_name: str | None
    expected_value: float | None
    actual_value: float | None
    passed: bool
    severity: str
    details: dict[str, Any] | None
    checked_at: datetime


class AnomalyListResponse(BaseModel):
    anomalies: list[AnomalyResponse]
    total: int
    failed: int
    passed: int


class AnomalySummaryResponse(BaseModel):
    total_checks: int
    total_failures: int
    by_type: dict[str, dict[str, int]]
    by_severity: dict[str, int]
    last_check: str | None
