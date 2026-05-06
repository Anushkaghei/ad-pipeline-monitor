"""Tests for the ingestion layer."""

from datetime import date, timedelta

import pytest

from ingestion.base import IngestionResult
from ingestion.mock_google import MockGoogleAdsAdapter
from ingestion.mock_meta import MockMetaAdsAdapter


class TestMockMetaAdapter:
    """Tests for the mock Meta Ads adapter."""

    def setup_method(self):
        self.adapter = MockMetaAdsAdapter()

    def test_platform_name(self):
        assert self.adapter.platform_name == "meta"

    def test_fetch_campaigns_returns_data(self, date_range):
        start, end = date_range
        result = self.adapter.fetch_campaigns(start, end)

        assert isinstance(result, IngestionResult)
        assert result.platform == "meta"
        assert result.entity_type == "campaigns"
        assert result.rows_fetched > 0
        assert len(result.data) == result.rows_fetched
        assert result.success is True

    def test_fetch_campaigns_has_required_fields(self, sample_date):
        result = self.adapter.fetch_campaigns(sample_date, sample_date)

        required_fields = {
            "campaign_id", "campaign_name", "status", "objective",
            "daily_budget", "impressions", "clicks", "spend",
            "date_start", "account_id",
        }
        for row in result.data:
            assert required_fields.issubset(row.keys()), \
                f"Missing fields: {required_fields - row.keys()}"

    def test_fetch_campaigns_realistic_values(self, sample_date):
        result = self.adapter.fetch_campaigns(sample_date, sample_date)

        for row in result.data:
            if row.get("impressions") is not None and row["impressions"] > 0:
                assert row["impressions"] >= 0
            if row.get("clicks") is not None:
                assert row["clicks"] >= 0
            if row.get("spend") is not None:
                assert row["spend"] >= 0 or row["spend"] is None

    def test_fetch_adsets_returns_data(self, date_range):
        start, end = date_range
        result = self.adapter.fetch_adsets(start, end)

        assert result.platform == "meta"
        assert result.entity_type == "adsets"
        assert result.rows_fetched > 0

    def test_fetch_keywords_returns_empty(self, date_range):
        start, end = date_range
        result = self.adapter.fetch_keywords(start, end)

        assert result.rows_fetched == 0
        assert result.data == []

    def test_date_range_coverage(self):
        start = date.today() - timedelta(days=3)
        end = date.today()
        result = self.adapter.fetch_campaigns(start, end)

        dates_in_data = {row["date_start"] for row in result.data}
        # Should have data for multiple days
        assert len(dates_in_data) >= 2


class TestMockGoogleAdapter:
    """Tests for the mock Google Ads adapter."""

    def setup_method(self):
        self.adapter = MockGoogleAdsAdapter()

    def test_platform_name(self):
        assert self.adapter.platform_name == "google"

    def test_fetch_campaigns_returns_data(self, date_range):
        start, end = date_range
        result = self.adapter.fetch_campaigns(start, end)

        assert result.platform == "google"
        assert result.entity_type == "campaigns"
        assert result.rows_fetched > 0

    def test_fetch_campaigns_has_required_fields(self, sample_date):
        result = self.adapter.fetch_campaigns(sample_date, sample_date)

        required_fields = {
            "campaign_id", "campaign_name", "status", "campaign_type",
            "budget_amount", "impressions", "clicks", "cost",
            "date", "customer_id",
        }
        for row in result.data:
            assert required_fields.issubset(row.keys())

    def test_fetch_keywords_returns_data(self, date_range):
        start, end = date_range
        result = self.adapter.fetch_keywords(start, end)

        assert result.platform == "google"
        assert result.entity_type == "keywords"
        assert result.rows_fetched > 0

    def test_fetch_keywords_has_required_fields(self, sample_date):
        result = self.adapter.fetch_keywords(sample_date, sample_date)

        required_fields = {
            "keyword_id", "keyword_text", "campaign_id",
            "match_type", "impressions", "clicks",
        }
        for row in result.data:
            assert required_fields.issubset(row.keys())

    def test_fetch_adsets_returns_empty(self, date_range):
        start, end = date_range
        result = self.adapter.fetch_adsets(start, end)
        assert result.rows_fetched == 0


class TestIngestionResult:
    """Tests for the IngestionResult data class."""

    def test_default_values(self):
        result = IngestionResult(
            platform="test", entity_type="campaigns", rows_fetched=0
        )
        assert result.success is True
        assert result.data == []
        assert result.errors == []

    def test_error_result(self):
        result = IngestionResult(
            platform="test", entity_type="campaigns",
            rows_fetched=0, success=False, errors=["API timeout"],
        )
        assert result.success is False
        assert "API timeout" in result.errors
