"""PostgreSQL data loader — loads ingestion results into raw tables."""

import json
import logging
from datetime import datetime, timezone

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from ingestion.base import IngestionResult

logger = logging.getLogger(__name__)

# ── Table mapping ────────────────────────────────────────────
TABLE_MAP = {
    ("meta", "campaigns"): "raw.meta_campaigns",
    ("meta", "adsets"): "raw.meta_adsets",
    ("google", "campaigns"): "raw.google_campaigns",
    ("google", "keywords"): "raw.google_keywords",
}

# Columns per table (excluding auto-generated id and ingestion_timestamp)
COLUMNS = {
    "raw.meta_campaigns": [
        "campaign_id", "campaign_name", "status", "objective",
        "daily_budget", "impressions", "clicks", "spend", "conversions",
        "ctr", "cpc", "date_start", "date_stop", "account_id",
    ],
    "raw.meta_adsets": [
        "adset_id", "adset_name", "campaign_id", "status", "targeting",
        "daily_budget", "impressions", "clicks", "spend",
        "date_start", "date_stop",
    ],
    "raw.google_campaigns": [
        "campaign_id", "campaign_name", "status", "campaign_type",
        "budget_amount", "impressions", "clicks", "cost", "conversions",
        "ctr", "cpc", "date", "customer_id",
    ],
    "raw.google_keywords": [
        "keyword_id", "keyword_text", "campaign_id", "ad_group_id",
        "match_type", "impressions", "clicks", "cost", "quality_score",
        "date",
    ],
}


def get_engine(connection_string: str) -> Engine:
    """Create a SQLAlchemy engine."""
    return create_engine(connection_string, pool_pre_ping=True)


def build_connection_string(
    host: str = "localhost",
    port: int = 5432,
    db: str = "ad_pipeline",
    user: str = "pipeline_user",
    password: str = "pipeline_pass",
) -> str:
    """Build a PostgreSQL connection string."""
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


def load_result(engine: Engine, result: IngestionResult, batch_size: int = 500) -> int:
    """
    Load an IngestionResult into the appropriate raw table.

    Returns the number of rows inserted.
    """
    if not result.data:
        logger.info(
            "No data to load for %s/%s", result.platform, result.entity_type
        )
        return 0

    table_key = (result.platform, result.entity_type)
    table_name = TABLE_MAP.get(table_key)
    if not table_name:
        logger.error("No table mapping for %s", table_key)
        return 0

    columns = COLUMNS[table_name]
    now = datetime.now(timezone.utc)
    total_inserted = 0

    with engine.begin() as conn:
        for i in range(0, len(result.data), batch_size):
            batch = result.data[i : i + batch_size]
            values_list = []

            for row in batch:
                vals = {}
                for col in columns:
                    val = row.get(col)
                    # Serialize dicts/lists to JSON string for JSONB columns
                    if isinstance(val, (dict, list)):
                        val = json.dumps(val)
                    vals[col] = val
                vals["ingestion_timestamp"] = now
                values_list.append(vals)

            all_cols = columns + ["ingestion_timestamp"]
            col_str = ", ".join(all_cols)
            param_str = ", ".join(f":{c}" for c in all_cols)
            sql = text(f"INSERT INTO {table_name} ({col_str}) VALUES ({param_str})")

            conn.execute(sql, values_list)
            total_inserted += len(batch)

    logger.info(
        "Loaded %d rows into %s", total_inserted, table_name
    )
    return total_inserted


def record_pipeline_run(
    engine: Engine,
    pipeline_name: str,
    status: str,
    rows_ingested: int,
    started_at: datetime,
    error_message: str | None = None,
) -> int:
    """Record a pipeline run in the monitoring schema."""
    with engine.begin() as conn:
        result = conn.execute(
            text("""
                INSERT INTO monitoring.pipeline_runs
                    (pipeline_name, status, rows_ingested, started_at, completed_at, error_message)
                VALUES
                    (:pipeline_name, :status, :rows_ingested, :started_at, NOW(), :error_message)
                RETURNING id
            """),
            {
                "pipeline_name": pipeline_name,
                "status": status,
                "rows_ingested": rows_ingested,
                "started_at": started_at,
                "error_message": error_message,
            },
        )
        run_id = result.scalar()
        logger.info("Recorded pipeline run %s (id=%s, status=%s)", pipeline_name, run_id, status)
        return run_id
