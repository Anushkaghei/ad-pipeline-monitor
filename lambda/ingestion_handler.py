"""AWS Lambda handler for data ingestion."""

import json
import logging
import os
from datetime import date, timedelta

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):
    """
    Lambda handler for scheduled ingestion.
    Triggered by EventBridge on a cron schedule.
    """
    from ingestion.loader import build_connection_string, get_engine, load_result, record_pipeline_run
    from ingestion.mock_google import MockGoogleAdsAdapter
    from ingestion.mock_meta import MockMetaAdsAdapter
    from datetime import datetime, timezone

    logger.info("Ingestion Lambda triggered: %s", json.dumps(event))

    # Build DB connection
    conn_str = build_connection_string(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        db=os.getenv("POSTGRES_DB", "ad_pipeline"),
        user=os.getenv("POSTGRES_USER", "pipeline_user"),
        password=os.getenv("POSTGRES_PASSWORD", "pipeline_pass"),
    )
    engine = get_engine(conn_str)

    # Date range
    end_date = date.today()
    start_date = end_date - timedelta(days=1)
    started_at = datetime.now(timezone.utc)
    total_rows = 0

    try:
        # Meta ingestion
        meta = MockMetaAdsAdapter()
        for entity in ["campaigns", "adsets"]:
            fetch_fn = getattr(meta, f"fetch_{entity}")
            result = fetch_fn(start_date, end_date)
            rows = load_result(engine, result)
            total_rows += rows
            logger.info("Meta %s: %d rows", entity, rows)

        # Google ingestion
        google = MockGoogleAdsAdapter()
        for entity in ["campaigns", "keywords"]:
            fetch_fn = getattr(google, f"fetch_{entity}")
            result = fetch_fn(start_date, end_date)
            rows = load_result(engine, result)
            total_rows += rows
            logger.info("Google %s: %d rows", entity, rows)

        record_pipeline_run(engine, "lambda_ingestion", "success", total_rows, started_at)

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Ingestion complete", "rows": total_rows}),
        }

    except Exception as e:
        logger.error("Ingestion failed: %s", e)
        record_pipeline_run(engine, "lambda_ingestion", "failed", total_rows, started_at, str(e))
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
        }
