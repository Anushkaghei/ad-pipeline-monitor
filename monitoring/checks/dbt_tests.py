"""dbt test artifact parser.

Parses dbt's run_results.json to extract test failures
and convert them into monitoring CheckResults.
"""

import json
import logging
from pathlib import Path

from monitoring.models import CheckResult, CheckType, Severity

logger = logging.getLogger(__name__)

DEFAULT_ARTIFACT_PATH = Path("dbt_project/target/run_results.json")


def parse_dbt_results(
    artifact_path: Path | str | None = None,
) -> list[CheckResult]:
    """
    Parse dbt run_results.json and return CheckResults for test nodes.

    Looks for test results (nodes starting with 'test.') and converts
    pass/fail/error status into CheckResult objects.
    """
    path = Path(artifact_path) if artifact_path else DEFAULT_ARTIFACT_PATH
    results = []

    if not path.exists():
        logger.warning("dbt artifacts not found at %s", path)
        results.append(CheckResult(
            check_name="dbt_artifacts_missing",
            check_type=CheckType.DBT_TEST,
            passed=True,
            severity=Severity.INFO,
            details={"reason": f"No dbt artifacts at {path}"},
        ))
        return results

    try:
        with open(path) as f:
            run_results = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.error("Failed to parse dbt artifacts: %s", e)
        results.append(CheckResult(
            check_name="dbt_artifact_parse_error",
            check_type=CheckType.DBT_TEST,
            passed=False,
            severity=Severity.CRITICAL,
            details={"error": str(e)},
        ))
        return results

    for result in run_results.get("results", []):
        unique_id = result.get("unique_id", "")

        # Only process test nodes
        if not unique_id.startswith("test."):
            continue

        status = result.get("status", "unknown")
        passed = status == "pass"
        test_name = unique_id.split(".")[-1] if "." in unique_id else unique_id

        # Determine severity from test type
        severity = Severity.WARNING
        if "not_null" in test_name or "unique" in test_name:
            severity = Severity.CRITICAL if not passed else Severity.INFO
        elif not passed:
            severity = Severity.WARNING

        # Extract failure details
        details: dict = {
            "unique_id": unique_id,
            "status": status,
            "execution_time": result.get("execution_time"),
        }
        if result.get("message"):
            details["message"] = result["message"]
        if result.get("failures"):
            details["failure_count"] = result["failures"]

        results.append(CheckResult(
            check_name=f"dbt_{test_name}",
            check_type=CheckType.DBT_TEST,
            passed=passed,
            severity=severity if not passed else Severity.INFO,
            details=details,
        ))

    logger.info(
        "Parsed %d dbt test results: %d passed, %d failed",
        len(results),
        sum(1 for r in results if r.passed),
        sum(1 for r in results if not r.passed),
    )
    return results
