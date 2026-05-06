# Monitoring Strategy

This document outlines the observability philosophy and the specific checks implemented in the Ad Pipeline Monitor.

## The Problem with Traditional ELT Monitoring

In typical ELT pipelines, teams rely on job schedulers (like Airflow) to tell them if a task succeeded or failed. This approach only catches **Hard Failures** (e.g., Python exceptions, database connection drops). 

However, data pipelines frequently suffer from **Silent Failures** — the job succeeds, but the data is wrong. 

## Our Multi-Layered Observability Approach

This platform implements a 5-pillar monitoring strategy to catch both hard and silent failures.

### Pillar 1: Row Count Anomaly Detection
**The Risk**: An API schema changes, causing the adapter to drop 90% of the campaigns, but it doesn't crash.
**The Solution**: We calculate a 7-day rolling average of ingestion volume. Using standard deviation, we calculate a Z-score for today's ingestion.
- **Warning**: Deviation > 30%
- **Critical**: Deviation > 50%

### Pillar 2: Null Threshold Monitoring
**The Risk**: The platform stops sending the `spend` metric, but the schema remains the same, so rows still load.
**The Solution**: We define acceptable null limits per column.
- Campaign ID: 0% tolerance
- Spend/Cost: 5% tolerance
- If nulls exceed the threshold, an alert fires indicating data degradation.

### Pillar 3: Table Freshness SLAs
**The Risk**: A cron job silently hangs, or an upstream dependency is delayed.
**The Solution**: We define SLAs indicating the maximum acceptable age of data in a table.
- Default SLA: 6 hours.
- If `MAX(ingestion_timestamp)` is older than the SLA, the table is flagged as stale.

### Pillar 4: Silent Failure Detection
**The Risk**: The API successfully returns an empty list `[]`. The job logs say `Success: 0 rows processed`. This is often a sign of token expiration or sudden account suspension. Another risk is missing specific date partitions (e.g., data arrived for Monday and Wednesday, but not Tuesday).
**The Solution**: 
- We explicitly flag successful jobs that process 0 rows.
- We check for gaps in sequential date columns.
- We verify that downstream marts are newer than their upstream staging tables (preventing materialized views from becoming silently stale).

### Pillar 5: dbt Test Integration
**The Risk**: Data violates business logic (e.g., negative spend, CTR > 1.0, duplicate IDs).
**The Solution**: We leverage dbt's native testing framework. Our Python engine parses dbt's `target/run_results.json` artifact, elevating SQL test failures into the same alerting ecosystem as our Python checks.

## Alerting Escalation Path

Not all issues require waking someone up. 

1. **Info**: Logged to the database for historical tracking, but no notification is sent. (e.g., "Row count dipped 10%, within normal variance").
2. **Warning**: Sent to the Slack `#data-alerts` channel. Needs review during business hours. (e.g., "Null threshold on Spend reached 6%").
3. **Critical**: Sent to Slack with `@here` and emailed to the on-call engineer. (e.g., "0 rows ingested for Google Ads").
