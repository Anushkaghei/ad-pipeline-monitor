"""Mock Meta Ads adapter — generates realistic sample data."""

import random
from datetime import date, timedelta
from typing import Any

from ingestion.base import AdPlatformAdapter, IngestionResult

# ── Campaign templates ───────────────────────────────────────
_CAMPAIGNS = [
    {"campaign_id": "meta_camp_001", "campaign_name": "Summer Sale 2025 - Conversions", "status": "ACTIVE", "objective": "CONVERSIONS", "daily_budget": 150.00},
    {"campaign_id": "meta_camp_002", "campaign_name": "Brand Awareness Q2", "status": "ACTIVE", "objective": "BRAND_AWARENESS", "daily_budget": 200.00},
    {"campaign_id": "meta_camp_003", "campaign_name": "Retargeting - Cart Abandoners", "status": "ACTIVE", "objective": "CONVERSIONS", "daily_budget": 75.00},
    {"campaign_id": "meta_camp_004", "campaign_name": "App Install - iOS", "status": "PAUSED", "objective": "APP_INSTALLS", "daily_budget": 100.00},
    {"campaign_id": "meta_camp_005", "campaign_name": "Lead Gen - Webinar Signup", "status": "ACTIVE", "objective": "LEAD_GENERATION", "daily_budget": 60.00},
    {"campaign_id": "meta_camp_006", "campaign_name": "Holiday Promo - Black Friday", "status": "ACTIVE", "objective": "CONVERSIONS", "daily_budget": 300.00},
    {"campaign_id": "meta_camp_007", "campaign_name": "Video Views - Product Demo", "status": "ACTIVE", "objective": "VIDEO_VIEWS", "daily_budget": 50.00},
    {"campaign_id": "meta_camp_008", "campaign_name": "Traffic - Blog Posts", "status": "ACTIVE", "objective": "LINK_CLICKS", "daily_budget": 40.00},
]

_ADSETS = [
    {"adset_id": "meta_adset_001", "adset_name": "Interest - Fashion 25-44", "campaign_id": "meta_camp_001", "status": "ACTIVE", "daily_budget": 50.00, "targeting": {"age_min": 25, "age_max": 44, "interests": ["fashion"]}},
    {"adset_id": "meta_adset_002", "adset_name": "Lookalike - Purchasers 1%", "campaign_id": "meta_camp_001", "status": "ACTIVE", "daily_budget": 100.00, "targeting": {"custom_audiences": ["lookalike_1pct"]}},
    {"adset_id": "meta_adset_003", "adset_name": "Broad - US 18-65", "campaign_id": "meta_camp_002", "status": "ACTIVE", "daily_budget": 200.00, "targeting": {"age_min": 18, "age_max": 65, "countries": ["US"]}},
    {"adset_id": "meta_adset_004", "adset_name": "Cart Abandon - 7 Day", "campaign_id": "meta_camp_003", "status": "ACTIVE", "daily_budget": 75.00, "targeting": {"custom_audiences": ["cart_abandon_7d"]}},
    {"adset_id": "meta_adset_005", "adset_name": "App Users - Engaged", "campaign_id": "meta_camp_004", "status": "PAUSED", "daily_budget": 100.00, "targeting": {"custom_audiences": ["app_engaged"]}},
]

ACCOUNT_ID = "act_123456789"


def _generate_daily_metrics(
    budget: float, objective: str
) -> dict[str, Any]:
    """Generate realistic daily metrics based on budget & objective."""
    # Base impressions scale with budget
    base_impressions = int(budget * random.uniform(200, 500))

    # CTR varies by objective
    ctr_ranges = {
        "CONVERSIONS": (0.020, 0.045),
        "BRAND_AWARENESS": (0.015, 0.030),
        "APP_INSTALLS": (0.025, 0.050),
        "LEAD_GENERATION": (0.030, 0.060),
        "VIDEO_VIEWS": (0.010, 0.025),
        "LINK_CLICKS": (0.035, 0.070),
    }
    ctr_range = ctr_ranges.get(objective, (0.020, 0.040))
    ctr = random.uniform(*ctr_range)

    impressions = base_impressions + random.randint(-2000, 2000)
    impressions = max(impressions, 100)
    clicks = max(int(impressions * ctr), 1)
    spend = round(budget * random.uniform(0.85, 1.00), 4)
    cpc = round(spend / clicks, 4) if clicks > 0 else 0
    conversions = int(clicks * random.uniform(0.01, 0.06))

    return {
        "impressions": impressions,
        "clicks": clicks,
        "spend": spend,
        "conversions": conversions,
        "ctr": round(ctr, 6),
        "cpc": cpc,
    }


def _inject_anomalies(rows: list[dict], anomaly_rate: float = 0.08) -> list[dict]:
    """Inject realistic anomalies into generated data."""
    for row in rows:
        if random.random() < anomaly_rate:
            anomaly_type = random.choice(["null_spend", "zero_impressions", "spike"])
            if anomaly_type == "null_spend":
                row["spend"] = None
            elif anomaly_type == "zero_impressions":
                row["impressions"] = 0
                row["clicks"] = 0
            elif anomaly_type == "spike":
                row["impressions"] = row.get("impressions", 10000) * random.randint(5, 15)
                row["clicks"] = row.get("clicks", 100) * random.randint(3, 8)
    return rows


class MockMetaAdsAdapter(AdPlatformAdapter):
    """Generates realistic mock Meta Ads data with occasional anomalies."""

    @property
    def platform_name(self) -> str:
        return "meta"

    def fetch_campaigns(
        self, date_start: date, date_end: date
    ) -> IngestionResult:
        rows: list[dict[str, Any]] = []
        current = date_start
        while current <= date_end:
            for camp in _CAMPAIGNS:
                # Occasionally skip a day to simulate missing partitions
                if random.random() < 0.03:
                    continue

                metrics = _generate_daily_metrics(
                    camp["daily_budget"], camp["objective"]
                )
                rows.append(
                    {
                        "campaign_id": camp["campaign_id"],
                        "campaign_name": camp["campaign_name"],
                        "status": camp["status"],
                        "objective": camp["objective"],
                        "daily_budget": camp["daily_budget"],
                        "date_start": current.isoformat(),
                        "date_stop": current.isoformat(),
                        "account_id": ACCOUNT_ID,
                        **metrics,
                    }
                )
            current += timedelta(days=1)

        rows = _inject_anomalies(rows)

        return IngestionResult(
            platform="meta",
            entity_type="campaigns",
            rows_fetched=len(rows),
            date_range=(date_start, date_end),
            data=rows,
        )

    def fetch_adsets(
        self, date_start: date, date_end: date
    ) -> IngestionResult:
        rows: list[dict[str, Any]] = []
        current = date_start
        while current <= date_end:
            for adset in _ADSETS:
                metrics = _generate_daily_metrics(
                    adset["daily_budget"], "CONVERSIONS"
                )
                rows.append(
                    {
                        "adset_id": adset["adset_id"],
                        "adset_name": adset["adset_name"],
                        "campaign_id": adset["campaign_id"],
                        "status": adset["status"],
                        "targeting": adset["targeting"],
                        "daily_budget": adset["daily_budget"],
                        "date_start": current.isoformat(),
                        "date_stop": current.isoformat(),
                        **{k: v for k, v in metrics.items() if k != "conversions"},
                    }
                )
            current += timedelta(days=1)

        rows = _inject_anomalies(rows)

        return IngestionResult(
            platform="meta",
            entity_type="adsets",
            rows_fetched=len(rows),
            date_range=(date_start, date_end),
            data=rows,
        )

    def fetch_keywords(
        self, date_start: date, date_end: date
    ) -> IngestionResult:
        # Meta doesn't have keywords
        return IngestionResult(
            platform="meta",
            entity_type="keywords",
            rows_fetched=0,
            date_range=(date_start, date_end),
            data=[],
        )
