"""FastAPI application — Ad Pipeline Monitor REST API."""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from api.routes import anomalies, health, pipelines

logger = logging.getLogger(__name__)

# ── Database engine (module-level singleton) ─────────────────
_engine: Engine | None = None


def get_db_engine() -> Engine:
    """Return the shared database engine."""
    global _engine
    if _engine is None:
        conn_str = (
            f"postgresql://"
            f"{os.getenv('POSTGRES_USER', 'pipeline_user')}:"
            f"{os.getenv('POSTGRES_PASSWORD', 'pipeline_pass')}@"
            f"{os.getenv('POSTGRES_HOST', 'localhost')}:"
            f"{os.getenv('POSTGRES_PORT', '5432')}/"
            f"{os.getenv('POSTGRES_DB', 'ad_pipeline')}"
        )
        _engine = create_engine(conn_str, pool_pre_ping=True)
    return _engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    logger.info("Starting Ad Pipeline Monitor API...")
    get_db_engine()  # Warm up connection
    yield
    logger.info("Shutting down API...")
    if _engine:
        _engine.dispose()


# ── App ──────────────────────────────────────────────────────
app = FastAPI(
    title="Ad Pipeline Monitor API",
    description="ELT Observability Platform for Advertising Pipelines",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ───────────────────────────────────────────────────
app.include_router(health.router)
app.include_router(pipelines.router)
app.include_router(anomalies.router)


@app.get("/")
def root():
    """API root — redirect to docs."""
    return {
        "service": "Ad Pipeline Monitor",
        "docs": "/docs",
        "health": "/health",
    }
