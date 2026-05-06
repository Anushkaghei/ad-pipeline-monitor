"""Health check endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.engine import Engine

from api.schemas import HealthResponse

router = APIRouter(tags=["health"])


def get_engine():
    """Dependency — injected by main.py."""
    from api.main import get_db_engine
    return get_db_engine()


@router.get("/health", response_model=HealthResponse)
def health_check(engine: Engine = Depends(get_engine)):
    """Service health check including database connectivity."""
    db_status = "disconnected"
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            db_status = "connected"
    except Exception:
        db_status = "error"

    from datetime import datetime, timezone
    return HealthResponse(
        status="healthy" if db_status == "connected" else "degraded",
        database=db_status,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
