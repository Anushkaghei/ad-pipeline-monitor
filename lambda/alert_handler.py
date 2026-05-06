"""AWS Lambda handler for alert dispatch."""

import json
import logging
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):
    """
    Lambda handler for processing alert payloads.
    Can be triggered by SNS, SQS, or direct invocation.
    """
    from monitoring.alerting.dispatcher import AlertDispatcher
    from monitoring.models import Alert, CheckResult, CheckType, Severity
    from ingestion.loader import build_connection_string, get_engine

    logger.info("Alert Lambda triggered: %s", json.dumps(event))

    conn_str = build_connection_string(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        db=os.getenv("POSTGRES_DB", "ad_pipeline"),
        user=os.getenv("POSTGRES_USER", "pipeline_user"),
        password=os.getenv("POSTGRES_PASSWORD", "pipeline_pass"),
    )
    engine = get_engine(conn_str)

    try:
        # Parse alert payload from event
        body = event.get("body", event)
        if isinstance(body, str):
            body = json.loads(body)

        check_result = CheckResult(
            check_name=body.get("check_name", "manual_alert"),
            check_type=CheckType(body.get("check_type", "row_count")),
            table_name=body.get("table_name"),
            expected_value=body.get("expected_value"),
            actual_value=body.get("actual_value"),
            passed=body.get("passed", False),
            severity=Severity(body.get("severity", "warning")),
            details=body.get("details", {}),
        )

        alert = Alert(
            check_result=check_result,
            pipeline_name=body.get("pipeline_name", "lambda_alert"),
        )
        alert.message = alert.format_message()

        dispatcher = AlertDispatcher(engine)
        results = dispatcher.dispatch(alert)

        return {
            "statusCode": 200,
            "body": json.dumps({"dispatched": results}),
        }

    except Exception as e:
        logger.error("Alert dispatch failed: %s", e)
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
