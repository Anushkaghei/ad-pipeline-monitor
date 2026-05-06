"""Database setup script — initializes schemas and tables."""

import logging
import os
import sys
from pathlib import Path

from sqlalchemy import text

from ingestion.loader import build_connection_string, get_engine

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

    init_sql = Path(__file__).parent.parent / "docker" / "init.sql"
    if not init_sql.exists():
        logger.error("init.sql not found at %s", init_sql)
        sys.exit(1)

    logger.info("Running database initialization from %s...", init_sql)
    sql = init_sql.read_text()

    with engine.begin() as conn:
        # Execute statements one at a time
        for statement in sql.split(";"):
            stmt = statement.strip()
            if stmt and not stmt.startswith("--"):
                conn.execute(text(stmt))

    logger.info("Database setup complete!")


if __name__ == "__main__":
    main()
