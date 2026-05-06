"""
Real Google Ads API adapter.
Falls back to MockGoogleAdsAdapter when credentials are not configured.
"""

import logging
import os
from datetime import date

from ingestion.base import AdPlatformAdapter, IngestionResult

logger = logging.getLogger(__name__)


class GoogleAdsAdapter(AdPlatformAdapter):
    """Fetch data from the Google Ads API using REST."""

    def __init__(self) -> None:
        self.developer_token = os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN", "")
        self.customer_id = os.getenv("GOOGLE_ADS_CUSTOMER_ID", "")
        self.client_id = os.getenv("GOOGLE_ADS_CLIENT_ID", "")
        self.client_secret = os.getenv("GOOGLE_ADS_CLIENT_SECRET", "")
        self.refresh_token = os.getenv("GOOGLE_ADS_REFRESH_TOKEN", "")
        if not all([self.developer_token, self.customer_id]):
            logger.warning("Google Ads credentials missing — use MockGoogleAdsAdapter.")

    @property
    def platform_name(self) -> str:
        return "google"

    @property
    def _configured(self) -> bool:
        return bool(self.developer_token and self.customer_id)

    def _query(self, gaql: str) -> list[dict]:
        """Execute a GAQL query via the Google Ads REST API."""
        import requests

        # Get OAuth2 token
        token_resp = requests.post("https://oauth2.googleapis.com/token", data={
            "client_id": self.client_id, "client_secret": self.client_secret,
            "refresh_token": self.refresh_token, "grant_type": "refresh_token",
        }, timeout=15)
        token_resp.raise_for_status()
        access_token = token_resp.json()["access_token"]

        cid = self.customer_id.replace("-", "")
        url = f"https://googleads.googleapis.com/v16/customers/{cid}/googleAds:searchStream"
        resp = requests.post(url, json={"query": gaql}, headers={
            "Authorization": f"Bearer {access_token}",
            "developer-token": self.developer_token,
        }, timeout=60)
        resp.raise_for_status()
        results = []
        for batch in resp.json():
            results.extend(batch.get("results", []))
        return results

    def fetch_campaigns(self, date_start: date, date_end: date) -> IngestionResult:
        if not self._configured:
            return IngestionResult(platform="google", entity_type="campaigns",
                                   rows_fetched=0, errors=["Not configured"], success=False)
        try:
            gaql = (
                "SELECT campaign.id, campaign.name, campaign.status, "
                "campaign.advertising_channel_type, campaign_budget.amount_micros, "
                "metrics.impressions, metrics.clicks, metrics.cost_micros, "
                "metrics.conversions, metrics.ctr, metrics.average_cpc, "
                "segments.date "
                f"FROM campaign WHERE segments.date BETWEEN '{date_start}' AND '{date_end}'"
            )
            results = self._query(gaql)
            rows = []
            for r in results:
                c, m, s = r.get("campaign", {}), r.get("metrics", {}), r.get("segments", {})
                b = r.get("campaignBudget", {})
                rows.append({
                    "campaign_id": str(c.get("id")), "campaign_name": c.get("name"),
                    "status": c.get("status"), "campaign_type": c.get("advertisingChannelType"),
                    "budget_amount": int(b.get("amountMicros", 0)) / 1_000_000,
                    "impressions": int(m.get("impressions", 0)),
                    "clicks": int(m.get("clicks", 0)),
                    "cost": int(m.get("costMicros", 0)) / 1_000_000,
                    "conversions": int(float(m.get("conversions", 0))),
                    "ctr": float(m.get("ctr", 0)), "cpc": int(m.get("averageCpc", 0)) / 1_000_000,
                    "date": s.get("date"), "customer_id": self.customer_id,
                })
            return IngestionResult(platform="google", entity_type="campaigns",
                                   rows_fetched=len(rows), date_range=(date_start, date_end), data=rows)
        except Exception as e:
            logger.error("Google Ads API error: %s", e)
            return IngestionResult(platform="google", entity_type="campaigns",
                                   rows_fetched=0, errors=[str(e)], success=False)

    def fetch_adsets(self, date_start: date, date_end: date) -> IngestionResult:
        return IngestionResult(platform="google", entity_type="adsets", rows_fetched=0, data=[])

    def fetch_keywords(self, date_start: date, date_end: date) -> IngestionResult:
        if not self._configured:
            return IngestionResult(platform="google", entity_type="keywords",
                                   rows_fetched=0, errors=["Not configured"], success=False)
        try:
            gaql = (
                "SELECT ad_group_criterion.keyword.text, ad_group_criterion.criterion_id, "
                "ad_group_criterion.keyword.match_type, ad_group.id, campaign.id, "
                "metrics.impressions, metrics.clicks, metrics.cost_micros, "
                "metrics.historical_quality_score, segments.date "
                f"FROM keyword_view WHERE segments.date BETWEEN '{date_start}' AND '{date_end}'"
            )
            results = self._query(gaql)
            rows = []
            for r in results:
                agc = r.get("adGroupCriterion", {})
                kw = agc.get("keyword", {})
                m, s = r.get("metrics", {}), r.get("segments", {})
                rows.append({
                    "keyword_id": str(agc.get("criterionId")),
                    "keyword_text": kw.get("text"),
                    "campaign_id": str(r.get("campaign", {}).get("id")),
                    "ad_group_id": str(r.get("adGroup", {}).get("id")),
                    "match_type": kw.get("matchType"),
                    "impressions": int(m.get("impressions", 0)),
                    "clicks": int(m.get("clicks", 0)),
                    "cost": int(m.get("costMicros", 0)) / 1_000_000,
                    "quality_score": int(m.get("historicalQualityScore", 0)),
                    "date": s.get("date"),
                })
            return IngestionResult(platform="google", entity_type="keywords",
                                   rows_fetched=len(rows), date_range=(date_start, date_end), data=rows)
        except Exception as e:
            logger.error("Google Ads keywords error: %s", e)
            return IngestionResult(platform="google", entity_type="keywords",
                                   rows_fetched=0, errors=[str(e)], success=False)
