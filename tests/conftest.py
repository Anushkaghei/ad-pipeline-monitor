"""Shared pytest fixtures."""

import os
import pytest
from datetime import date, timedelta
from unittest.mock import MagicMock

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


@pytest.fixture(scope="session")
def db_engine() -> Engine:
    """
    Create a test database engine.
    Uses env vars if available, otherwise creates a mock.
    """
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "ad_pipeline_test")
    user = os.getenv("POSTGRES_USER", "pipeline_user")
    password = os.getenv("POSTGRES_PASSWORD", "pipeline_pass")

    conn_str = f"postgresql://{user}:{password}@{host}:{port}/{db}"

    try:
        engine = create_engine(conn_str, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return engine
    except Exception:
        pytest.skip("PostgreSQL not available — skipping DB tests")


@pytest.fixture
def mock_engine() -> MagicMock:
    """Create a mock database engine for unit tests."""
    return MagicMock(spec=Engine)


@pytest.fixture
def date_range() -> tuple[date, date]:
    """Standard test date range: last 7 days."""
    end = date.today()
    start = end - timedelta(days=7)
    return start, end


@pytest.fixture
def sample_date() -> date:
    """A single test date."""
    return date.today() - timedelta(days=1)
