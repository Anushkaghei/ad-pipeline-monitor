"""Pipeline status endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.engine import Engine

from api.schemas import PipelineRunResponse, PipelineStatusResponse

router = APIRouter(tags=["pipelines"])


def get_engine():
    from api.main import get_db_engine
    return get_db_engine()


@router.get("/pipeline-status", response_model=PipelineStatusResponse)
def pipeline_status(engine: Engine = Depends(get_engine)):
    """Get the latest status of each pipeline."""
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT DISTINCT ON (pipeline_name)
                id, pipeline_name, status, rows_ingested,
                started_at, completed_at, error_message
            FROM monitoring.pipeline_runs
            ORDER BY pipeline_name, started_at DESC
        """)).fetchall()

    pipelines = [
        PipelineRunResponse(
            id=r.id, pipeline_name=r.pipeline_name, status=r.status,
            rows_ingested=r.rows_ingested, started_at=r.started_at,
            completed_at=r.completed_at, error_message=r.error_message,
        )
        for r in rows
    ]
    return PipelineStatusResponse(pipelines=pipelines, total=len(pipelines))


@router.get("/latest-runs", response_model=PipelineStatusResponse)
def latest_runs(
    limit: int = Query(default=20, ge=1, le=100),
    engine: Engine = Depends(get_engine),
):
    """Get paginated pipeline run history."""
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT id, pipeline_name, status, rows_ingested,
                   started_at, completed_at, error_message
            FROM monitoring.pipeline_runs
            ORDER BY started_at DESC
            LIMIT :limit
        """), {"limit": limit}).fetchall()

    pipelines = [
        PipelineRunResponse(
            id=r.id, pipeline_name=r.pipeline_name, status=r.status,
            rows_ingested=r.rows_ingested, started_at=r.started_at,
            completed_at=r.completed_at, error_message=r.error_message,
        )
        for r in rows
    ]
    return PipelineStatusResponse(pipelines=pipelines, total=len(pipelines))
