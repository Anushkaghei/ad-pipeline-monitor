"""Mock Google Ads adapter — generates realistic sample data."""

import random
from datetime import date, timedelta
from typing import Any

from ingestion.base import AdPlatformAdapter, IngestionResult

# ── Campaign templates ───────────────────────────────────────
_CAMPAIGNS = [
    {"campaign_id": "goog_camp_001", "campaign_name": "Search - Brand Terms", "status": "ENABLED", "campaign_type": "SEARCH", "budget_amount": 120.00},
    {"campaign_id": "goog_camp_002", "campaign_name": "Search - Competitor Terms", "status": "ENABLED", "campaign_type": "SEARCH", "budget_amount": 200.00},
    {"campaign_id": "goog_camp_003", "campaign_name": "Display - Remarketing", "status": "ENABLED", "campaign_type": "DISPLAY", "budget_amount": 80.00},
    {"campaign_id": "goog_camp_004", "campaign_name": "Shopping - All Products", "status": "ENABLED", "campaign_type": "SHOPPING", "budget_amount": 250.00},
    {"campaign_id": "goog_camp_005", "campaign_name": "YouTube - Pre-Roll Ads", "status": "PAUSED", "campaign_type": "VIDEO", "budget_amount": 100.00},
    {"campaign_id": "goog_camp_006", "campaign_name": "Performance Max - eComm", "status": "ENABLED", "campaign_type": "PERFORMANCE_MAX", "budget_amount": 180.00},
    {"campaign_id": "goog_camp_007", "campaign_name": "Search - Non-Brand Generic", "status": "ENABLED", "campaign_type": "SEARCH", "budget_amount": 300.00},
]

_KEYWORDS = [
    {"keyword_id": "goog_kw_001", "keyword_text": "buy shoes online", "campaign_id": "goog_camp_001", "ad_group_id": "ag_001", "match_type": "EXACT"},
    {"keyword_id": "goog_kw_002", "keyword_text": "running shoes sale", "campaign_id": "goog_camp_001", "ad_group_id": "ag_001", "match_type": "PHRASE"},
    {"keyword_id": "goog_kw_003", "keyword_text": "nike competitor brand", "campaign_id": "goog_camp_002", "ad_group_id": "ag_002", "match_type": "BROAD"},
    {"keyword_id": "goog_kw_004", "keyword_text": "best running shoes 2025", "campaign_id": "goog_camp_007", "ad_group_id": "ag_003", "match_type": "PHRASE"},
    {"keyword_id": "goog_kw_005", "keyword_text": "athletic footwear", "campaign_id": "goog_camp_007", "ad_group_id": "ag_003", "match_type": "BROAD"},
    {"keyword_id": "goog_kw_006", "keyword_text": "trail running shoes", "campaign_id": "goog_camp_001", "ad_group_id": "ag_004", "match_type": "EXACT"},
]

CUSTOMER_ID = "cust_987654321"


def _generate_campaign_metrics(
    budget: float, campaign_type: str
) -> dict[str, Any]:
    """Generate realistic metrics based on campaign type."""
    type_params = {
        "SEARCH":          {"imp_mult": (150, 300), "ctr": (0.08, 0.18), "conv_rate": (0.02, 0.08)},
        "DISPLAY":         {"imp_mult": (1000, 3000), "ctr": (0.003, 0.008), "conv_rate": (0.005, 0.02)},
        "SHOPPING":        {"imp_mult": (200, 600), "ctr": (0.04, 0.10), "conv_rate": (0.015, 0.05)},
        "VIDEO":           {"imp_mult": (500, 1500), "ctr": (0.01, 0.03), "conv_rate": (0.003, 0.01)},
        "PERFORMANCE_MAX": {"imp_mult": (300, 800), "ctr": (0.05, 0.12), "conv_rate": (0.02, 0.06)},
    }
    params = type_params.get(campaign_type, type_params["SEARCH"])

    impressions = int(budget * random.uniform(*params["imp_mult"]))
    ctr = random.uniform(*params["ctr"])
    clicks = max(int(impressions * ctr), 1)
    cost = round(budget * random.uniform(0.88, 1.00), 4)
    cpc = round(cost / clicks, 4) if clicks > 0 else 0
    conversions = int(clicks * random.uniform(*params["conv_rate"]))

    return {
        "impressions": impressions,
        "clicks": clicks,
        "cost": cost,
        "conversions": conversions,
        "ctr": round(ctr, 6),
        "cpc": cpc,
    }


def _generate_keyword_metrics(match_type: str) -> dict[str, Any]:
    """Generate keyword-level metrics."""
    match_params = {
        "EXACT":  {"imp": (3000, 10000), "ctr": (0.10, 0.20), "qs": (7, 10)},
        "PHRASE": {"imp": (5000, 15000), "ctr": (0.06, 0.14), "qs": (5, 9)},
        "BROAD":  {"imp": (8000, 25000), "ctr": (0.03, 0.08), "qs": (3, 7)},
    }
    params = match_params.get(match_type, match_params["BROAD"])

    impressions = random.randint(*params["imp"])
    ctr = random.uniform(*params["ctr"])
    clicks = max(int(impressions * ctr), 1)
    cost = round(clicks * random.uniform(0.50, 3.50), 4)
    quality_score = random.randint(*params["qs"])

    return {
        "impressions": impressions,
        "clicks": clicks,
        "cost": cost,
        "quality_score": quality_score,
    }


def _inject_anomalies(rows: list[dict], anomaly_rate: float = 0.06) -> list[dict]:
    """Inject anomalies for testing monitoring checks."""
    for row in rows:
        if random.random() < anomaly_rate:
            anomaly = random.choice(["null_cost", "zero_clicks", "spike"])
            if anomaly == "null_cost":
                row["cost"] = None
            elif anomaly == "zero_clicks":
                row["impressions"] = 0
                row["clicks"] = 0
            elif anomaly == "spike":
                row["impressions"] = row.get("impressions", 5000) * random.randint(5, 12)
    return rows


class MockGoogleAdsAdapter(AdPlatformAdapter):
    """Generates realistic mock Google Ads data with occasional anomalies."""

    @property
    def platform_name(self) -> str:
        return "google"

    def fetch_campaigns(
        self, date_start: date, date_end: date
    ) -> IngestionResult:
        rows: list[dict[str, Any]] = []
        current = date_start
        while current <= date_end:
            for camp in _CAMPAIGNS:
                if random.random() < 0.02:
                    continue

                metrics = _generate_campaign_metrics(
                    camp["budget_amount"], camp["campaign_type"]
                )
                rows.append(
                    {
                        "campaign_id": camp["campaign_id"],
                        "campaign_name": camp["campaign_name"],
                        "status": camp["status"],
                        "campaign_type": camp["campaign_type"],
                        "budget_amount": camp["budget_amount"],
                        "date": current.isoformat(),
                        "customer_id": CUSTOMER_ID,
                        **metrics,
                    }
                )
            current += timedelta(days=1)

        rows = _inject_anomalies(rows)

        return IngestionResult(
            platform="google",
            entity_type="campaigns",
            rows_fetched=len(rows),
            date_range=(date_start, date_end),
            data=rows,
        )

    def fetch_adsets(
        self, date_start: date, date_end: date
    ) -> IngestionResult:
        # Google calls these "ad groups" — not implemented in mock
        return IngestionResult(
            platform="google",
            entity_type="adsets",
            rows_fetched=0,
            date_range=(date_start, date_end),
            data=[],
        )

    def fetch_keywords(
        self, date_start: date, date_end: date
    ) -> IngestionResult:
        rows: list[dict[str, Any]] = []
        current = date_start
        while current <= date_end:
            for kw in _KEYWORDS:
                metrics = _generate_keyword_metrics(kw["match_type"])
                rows.append(
                    {
                        "keyword_id": kw["keyword_id"],
                        "keyword_text": kw["keyword_text"],
                        "campaign_id": kw["campaign_id"],
                        "ad_group_id": kw["ad_group_id"],
                        "match_type": kw["match_type"],
                        "date": current.isoformat(),
                        **metrics,
                    }
                )
            current += timedelta(days=1)

        rows = _inject_anomalies(rows)

        return IngestionResult(
            platform="google",
            entity_type="keywords",
            rows_fetched=len(rows),
            date_range=(date_start, date_end),
            data=rows,
        )
