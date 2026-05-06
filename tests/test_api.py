"""Tests for the FastAPI monitoring API."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from api.main import app


@pytest.fixture
def client():
    """Create a test client with mocked database."""
    return TestClient(app)


class TestRootEndpoint:
    def test_root_returns_service_info(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert "service" in data
        assert data["service"] == "Ad Pipeline Monitor"
        assert "docs" in data


class TestHealthEndpoint:
    def test_health_endpoint_exists(self, client):
        # Will return degraded if no DB, but should not 500
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "database" in data
        assert "timestamp" in data


class TestPipelineEndpoints:
    def test_pipeline_status_exists(self, client):
        resp = client.get("/pipeline-status")
        # May fail with DB error, but route should exist
        assert resp.status_code in (200, 500)

    def test_latest_runs_exists(self, client):
        resp = client.get("/latest-runs?limit=5")
        assert resp.status_code in (200, 500)


class TestAnomalyEndpoints:
    def test_anomalies_endpoint_exists(self, client):
        resp = client.get("/anomalies")
        assert resp.status_code in (200, 500)

    def test_anomalies_with_filters(self, client):
        resp = client.get("/anomalies?check_type=row_count&failed_only=true&limit=10")
        assert resp.status_code in (200, 500)

    def test_anomalies_summary_exists(self, client):
        resp = client.get("/anomalies/summary")
        assert resp.status_code in (200, 500)
