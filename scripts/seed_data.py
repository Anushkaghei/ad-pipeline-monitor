"""Seed database with sample data for development."""

import logging
import os
from datetime import date, timedelta

from ingestion.loader import build_connection_string, get_engine, load_result
from ingestion.mock_google import MockGoogleAdsAdapter
from ingestion.mock_meta import MockMetaAdsAdapter

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def main():
    conn_str = build_connection_string(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        db=os.getenv("POSTGRES_DB", "ad_pipeline"),
        user=os.getenv("POSTGRES_USER", "pipeline_user"),
        password=os.getenv("POSTGRES_PASSWORD", "pipeline_pass"),
    )
    engine = get_engine(conn_str)

    # Generate 14 days of historical data
    end_date = date.today()
    start_date = end_date - timedelta(days=14)

    logger.info("Seeding data from %s to %s...", start_date, end_date)

    meta = MockMetaAdsAdapter()
    google = MockGoogleAdsAdapter()

    total = 0

    # Meta campaigns
    result = meta.fetch_campaigns(start_date, end_date)
    rows = load_result(engine, result)
    total += rows
    logger.info("Meta campaigns: %d rows", rows)

    # Meta adsets
    result = meta.fetch_adsets(start_date, end_date)
    rows = load_result(engine, result)
    total += rows
    logger.info("Meta adsets: %d rows", rows)

    # Google campaigns
    result = google.fetch_campaigns(start_date, end_date)
    rows = load_result(engine, result)
    total += rows
    logger.info("Google campaigns: %d rows", rows)

    # Google keywords
    result = google.fetch_keywords(start_date, end_date)
    rows = load_result(engine, result)
    total += rows
    logger.info("Google keywords: %d rows", rows)

    logger.info("Seeding complete! Total rows: %d", total)


if __name__ == "__main__":
    main()
