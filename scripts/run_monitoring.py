"""Run monitoring checks and dispatch alerts."""

import logging
import os

from ingestion.loader import build_connection_string, get_engine
from monitoring.alerting.dispatcher import AlertDispatcher
from monitoring.engine import MonitoringEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def run_monitoring():
    conn_str = build_connection_string(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        db=os.getenv("POSTGRES_DB", "ad_pipeline"),
        user=os.getenv("POSTGRES_USER", "pipeline_user"),
        password=os.getenv("POSTGRES_PASSWORD", "pipeline_pass"),
    )
    engine = get_engine(conn_str)

    # Run all checks
    monitor = MonitoringEngine(engine)
    results = monitor.run_all_checks()

    # Generate and dispatch alerts for failures
    alerts = monitor.generate_alerts(results, pipeline_name="ad_pipeline")

    if alerts:
        dispatcher = AlertDispatcher(engine)
        dispatcher.dispatch_all(alerts)
        logger.info("Dispatched %d alerts", len(alerts))
    else:
        logger.info("All checks passed — no alerts needed")

    return results


def main():
    run_monitoring()


if __name__ == "__main__":
    main()
