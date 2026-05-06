"""Local cron scheduler using APScheduler."""

import logging
import os

from apscheduler.schedulers.blocking import BlockingScheduler

logger = logging.getLogger(__name__)


def create_scheduler(
    ingestion_fn: callable,
    monitoring_fn: callable,
    ingestion_interval_minutes: int = 60,
    monitoring_interval_minutes: int = 30,
) -> BlockingScheduler:
    """
    Create a local scheduler that runs ingestion and monitoring
    on configurable intervals.
    """
    scheduler = BlockingScheduler()

    scheduler.add_job(
        ingestion_fn,
        "interval",
        minutes=ingestion_interval_minutes,
        id="ingestion_job",
        name="Ad Platform Ingestion",
        max_instances=1,
    )

    scheduler.add_job(
        monitoring_fn,
        "interval",
        minutes=monitoring_interval_minutes,
        id="monitoring_job",
        name="Monitoring Checks",
        max_instances=1,
    )

    logger.info(
        "Scheduler configured: ingestion every %dm, monitoring every %dm",
        ingestion_interval_minutes,
        monitoring_interval_minutes,
    )
    return scheduler


def run_scheduled(ingestion_fn: callable, monitoring_fn: callable) -> None:
    """Start the scheduler (blocking)."""
    interval_ingest = int(os.getenv("INGESTION_INTERVAL_MINUTES", "60"))
    interval_monitor = int(os.getenv("MONITORING_INTERVAL_MINUTES", "30"))

    scheduler = create_scheduler(
        ingestion_fn, monitoring_fn,
        ingestion_interval_minutes=interval_ingest,
        monitoring_interval_minutes=interval_monitor,
    )

    logger.info("Starting scheduler...")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")
