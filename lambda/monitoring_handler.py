"""AWS Lambda handler for monitoring checks."""

import json
import logging
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):
    """
    Lambda handler for scheduled monitoring.
    Runs all observability checks and dispatches alerts.
    """
    from ingestion.loader import build_connection_string, get_engine
    from monitoring.alerting.dispatcher import AlertDispatcher
    from monitoring.engine import MonitoringEngine

    logger.info("Monitoring Lambda triggered: %s", json.dumps(event))

    conn_str = build_connection_string(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        db=os.getenv("POSTGRES_DB", "ad_pipeline"),
        user=os.getenv("POSTGRES_USER", "pipeline_user"),
        password=os.getenv("POSTGRES_PASSWORD", "pipeline_pass"),
    )
    engine = get_engine(conn_str)

    try:
        monitor = MonitoringEngine(engine)
        results = monitor.run_all_checks()
        alerts = monitor.generate_alerts(results, pipeline_name="lambda_pipeline")

        if alerts:
            dispatcher = AlertDispatcher(engine)
            dispatcher.dispatch_all(alerts)

        failed = sum(1 for r in results if not r.passed)
        return {
            "statusCode": 200,
            "body": json.dumps({
                "total_checks": len(results),
                "passed": len(results) - failed,
                "failed": failed,
                "alerts_sent": len(alerts),
            }),
        }

    except Exception as e:
        logger.error("Monitoring failed: %s", e)
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
