"""Anomaly monitoring endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.engine import Engine

from api.schemas import AnomalyListResponse, AnomalyResponse, AnomalySummaryResponse

router = APIRouter(tags=["anomalies"])


def get_engine():
    from api.main import get_db_engine
    return get_db_engine()


@router.get("/anomalies", response_model=AnomalyListResponse)
def list_anomalies(
    check_type: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    failed_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
    engine: Engine = Depends(get_engine),
):
    """List recent anomaly check results with optional filters."""
    conditions = []
    params: dict = {"limit": limit}

    if check_type:
        conditions.append("check_type = :check_type")
        params["check_type"] = check_type
    if severity:
        conditions.append("severity = :severity")
        params["severity"] = severity
    if failed_only:
        conditions.append("passed = FALSE")

    where = "WHERE " + " AND ".join(conditions) if conditions else ""

    with engine.connect() as conn:
        rows = conn.execute(text(f"""
            SELECT id, check_name, check_type, table_name,
                   expected_value, actual_value, passed, severity,
                   details, checked_at
            FROM monitoring.check_results
            {where}
            ORDER BY checked_at DESC
            LIMIT :limit
        """), params).fetchall()

    anomalies = [
        AnomalyResponse(
            id=r.id, check_name=r.check_name, check_type=r.check_type,
            table_name=r.table_name, expected_value=r.expected_value,
            actual_value=r.actual_value, passed=r.passed,
            severity=r.severity, details=r.details, checked_at=r.checked_at,
        )
        for r in rows
    ]
    return AnomalyListResponse(
        anomalies=anomalies,
        total=len(anomalies),
        failed=sum(1 for a in anomalies if not a.passed),
        passed=sum(1 for a in anomalies if a.passed),
    )


@router.get("/anomalies/summary", response_model=AnomalySummaryResponse)
def anomaly_summary(engine: Engine = Depends(get_engine)):
    """Aggregated anomaly statistics from the last 24 hours."""
    with engine.connect() as conn:
        # By type
        type_rows = conn.execute(text("""
            SELECT check_type,
                   COUNT(*) AS total,
                   COUNT(*) FILTER (WHERE passed = FALSE) AS failures
            FROM monitoring.check_results
            WHERE checked_at >= NOW() - INTERVAL '24 hours'
            GROUP BY check_type
        """)).fetchall()

        # By severity
        sev_rows = conn.execute(text("""
            SELECT severity, COUNT(*) AS cnt
            FROM monitoring.check_results
            WHERE checked_at >= NOW() - INTERVAL '24 hours'
              AND passed = FALSE
            GROUP BY severity
        """)).fetchall()

        # Last check
        last = conn.execute(text("""
            SELECT MAX(checked_at) AS ts FROM monitoring.check_results
        """)).scalar()

    by_type = {
        r.check_type: {"total": r.total, "failures": r.failures}
        for r in type_rows
    }
    by_severity = {r.severity: r.cnt for r in sev_rows}
    total = sum(v["total"] for v in by_type.values())
    failures = sum(v["failures"] for v in by_type.values())

    return AnomalySummaryResponse(
        total_checks=total,
        total_failures=failures,
        by_type=by_type,
        by_severity=by_severity,
        last_check=last.isoformat() if last else None,
    )
