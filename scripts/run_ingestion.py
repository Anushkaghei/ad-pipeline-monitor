"""Run a single ingestion cycle."""

import logging
import os
from datetime import date, datetime, timedelta, timezone

from ingestion.loader import build_connection_string, get_engine, load_result, record_pipeline_run
from ingestion.mock_google import MockGoogleAdsAdapter
from ingestion.mock_meta import MockMetaAdsAdapter

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def run_ingestion():
    conn_str = build_connection_string(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        db=os.getenv("POSTGRES_DB", "ad_pipeline"),
        user=os.getenv("POSTGRES_USER", "pipeline_user"),
        password=os.getenv("POSTGRES_PASSWORD", "pipeline_pass"),
    )
    engine = get_engine(conn_str)

    end_date = date.today()
    start_date = end_date - timedelta(days=1)
    started_at = datetime.now(timezone.utc)
    total = 0

    logger.info("Starting ingestion for %s to %s", start_date, end_date)

    try:
        # Meta
        meta = MockMetaAdsAdapter()
        for entity in ["campaigns", "adsets"]:
            result = getattr(meta, f"fetch_{entity}")(start_date, end_date)
            rows = load_result(engine, result)
            total += rows
            logger.info("Meta %s: %d rows", entity, rows)

        # Google
        google = MockGoogleAdsAdapter()
        for entity in ["campaigns", "keywords"]:
            result = getattr(google, f"fetch_{entity}")(start_date, end_date)
            rows = load_result(engine, result)
            total += rows
            logger.info("Google %s: %d rows", entity, rows)

        record_pipeline_run(engine, "daily_ingestion", "success", total, started_at)
        logger.info("Ingestion complete: %d total rows", total)

    except Exception as e:
        logger.error("Ingestion failed: %s", e)
        record_pipeline_run(engine, "daily_ingestion", "failed", total, started_at, str(e))
        raise


def main():
    run_ingestion()


if __name__ == "__main__":
    main()
