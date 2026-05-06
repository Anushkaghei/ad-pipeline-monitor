"""
Real Meta Ads API adapter.
Falls back to MockMetaAdsAdapter when credentials are not configured.
"""

import logging
import os
from datetime import date

import requests

from ingestion.base import AdPlatformAdapter, IngestionResult

logger = logging.getLogger(__name__)
BASE_URL = "https://graph.facebook.com/v19.0"


class MetaAdsAdapter(AdPlatformAdapter):
    """Fetch data from the Meta (Facebook) Ads API."""

    def __init__(self) -> None:
        self.access_token = os.getenv("META_ACCESS_TOKEN", "")
        self.ad_account_id = os.getenv("META_AD_ACCOUNT_ID", "")
        if not self.access_token or not self.ad_account_id:
            logger.warning("Meta Ads credentials missing — use MockMetaAdsAdapter.")

    @property
    def platform_name(self) -> str:
        return "meta"

    @property
    def _configured(self) -> bool:
        return bool(self.access_token and self.ad_account_id)

    def _get(self, endpoint: str, params: dict) -> dict:
        params["access_token"] = self.access_token
        r = requests.get(f"{BASE_URL}/{endpoint}", params=params, timeout=30)
        r.raise_for_status()
        return r.json()

    def fetch_campaigns(self, date_start: date, date_end: date) -> IngestionResult:
        if not self._configured:
            return IngestionResult(platform="meta", entity_type="campaigns",
                                   rows_fetched=0, errors=["Not configured"], success=False)
        try:
            camps = self._get(f"{self.ad_account_id}/campaigns",
                              {"fields": "id,name,status,objective,daily_budget", "limit": 500}).get("data", [])
            rows = []
            for c in camps:
                insights = self._get(f"{c['id']}/insights", {
                    "time_range": {"since": str(date_start), "until": str(date_end)},
                    "fields": "impressions,clicks,spend,actions,ctr,cpc", "time_increment": 1
                }).get("data", [])
                for i in insights:
                    conv = sum(int(a.get("value", 0)) for a in i.get("actions", [])
                               if a.get("action_type") == "offsite_conversion")
                    rows.append({"campaign_id": c["id"], "campaign_name": c.get("name"),
                                 "status": c.get("status"), "objective": c.get("objective"),
                                 "daily_budget": float(c.get("daily_budget", 0)) / 100,
                                 "impressions": int(i.get("impressions", 0)),
                                 "clicks": int(i.get("clicks", 0)),
                                 "spend": float(i.get("spend", 0)), "conversions": conv,
                                 "ctr": float(i.get("ctr", 0)), "cpc": float(i.get("cpc", 0)),
                                 "date_start": i.get("date_start"), "date_stop": i.get("date_stop"),
                                 "account_id": self.ad_account_id})
            return IngestionResult(platform="meta", entity_type="campaigns",
                                   rows_fetched=len(rows), date_range=(date_start, date_end), data=rows)
        except requests.RequestException as e:
            logger.error("Meta API error: %s", e)
            return IngestionResult(platform="meta", entity_type="campaigns",
                                   rows_fetched=0, errors=[str(e)], success=False)

    def fetch_adsets(self, date_start: date, date_end: date) -> IngestionResult:
        if not self._configured:
            return IngestionResult(platform="meta", entity_type="adsets",
                                   rows_fetched=0, errors=["Not configured"], success=False)
        try:
            adsets = self._get(f"{self.ad_account_id}/adsets",
                               {"fields": "id,name,campaign_id,status,targeting,daily_budget", "limit": 500}).get("data", [])
            rows = []
            for a in adsets:
                insights = self._get(f"{a['id']}/insights", {
                    "time_range": {"since": str(date_start), "until": str(date_end)},
                    "fields": "impressions,clicks,spend", "time_increment": 1
                }).get("data", [])
                for i in insights:
                    rows.append({"adset_id": a["id"], "adset_name": a.get("name"),
                                 "campaign_id": a.get("campaign_id"), "status": a.get("status"),
                                 "targeting": a.get("targeting"),
                                 "daily_budget": float(a.get("daily_budget", 0)) / 100,
                                 "impressions": int(i.get("impressions", 0)),
                                 "clicks": int(i.get("clicks", 0)),
                                 "spend": float(i.get("spend", 0)),
                                 "date_start": i.get("date_start"), "date_stop": i.get("date_stop")})
            return IngestionResult(platform="meta", entity_type="adsets",
                                   rows_fetched=len(rows), date_range=(date_start, date_end), data=rows)
        except requests.RequestException as e:
            logger.error("Meta adsets error: %s", e)
            return IngestionResult(platform="meta", entity_type="adsets",
                                   rows_fetched=0, errors=[str(e)], success=False)

    def fetch_keywords(self, date_start: date, date_end: date) -> IngestionResult:
        return IngestionResult(platform="meta", entity_type="keywords", rows_fetched=0, data=[])
