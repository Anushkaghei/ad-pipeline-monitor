"""Run the full pipeline: ingest → monitor → alert."""

import logging
import os
import sys

from dotenv import load_dotenv

# Load .env if present
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    logger.info("=" * 60)
    logger.info("Ad Pipeline Monitor — Full Pipeline Run")
    logger.info("=" * 60)

    mode = os.getenv("RUN_MODE", "once")  # "once" or "scheduled"

    if mode == "scheduled":
        logger.info("Starting in SCHEDULED mode...")
        from scripts.run_ingestion import run_ingestion
        from scripts.run_monitoring import run_monitoring
        from monitoring.scheduler import run_scheduled
        run_scheduled(run_ingestion, run_monitoring)
    else:
        logger.info("Starting in ONE-SHOT mode...")

        # Step 1: Ingestion
        logger.info("Step 1/3: Running ingestion...")
        from scripts.run_ingestion import run_ingestion
        try:
            run_ingestion()
        except Exception as e:
            logger.error("Ingestion failed: %s", e)

        # Step 2: Monitoring
        logger.info("Step 2/3: Running monitoring checks...")
        from scripts.run_monitoring import run_monitoring
        try:
            run_monitoring()
        except Exception as e:
            logger.error("Monitoring failed: %s", e)

        # Step 3: Summary
        logger.info("Step 3/3: Pipeline complete!")
        logger.info("=" * 60)
        logger.info("View results at http://localhost:8000/anomalies")
        logger.info("=" * 60)


if __name__ == "__main__":
    main()
