# Scalability Considerations

This document outlines the current limitations of the system and how it would need to evolve to handle Enterprise-scale data volumes.

## Current Architecture Limitations

The current setup uses a monolithic Python application and a single PostgreSQL instance.

1. **Memory Bound Ingestion**: The adapters currently load the entire API payload into memory before batch inserting.
2. **Compute Bound Monitoring**: The anomaly detection runs SQL queries directly against the operational tables.
3. **Database Locks**: Long-running dbt transformations might lock tables that the ingestion layer is trying to write to.

## Evolution Phase 1: Medium Scale (10M - 100M rows/day)

### Transition to a Data Lakehouse
- **Storage**: Move from PostgreSQL to an S3 Data Lake.
- **Format**: Write raw data as Parquet files partitioned by `platform/date/`.
- **Compute**: Switch dbt from `dbt-postgres` to `dbt-snowflake` or `dbt-athena`.

### Asynchronous Ingestion
- Implement a Queue (SQS or Kafka).
- The Ingestion Lambda pushes small messages to SQS.
- A fleet of worker Lambdas pulls from SQS and writes Parquet files to S3.

## Evolution Phase 2: Enterprise Scale (1B+ rows/day)

### Streaming Architecture
- **Ingestion**: Move to streaming ingestion using Amazon Kinesis or Kafka.
- **Processing**: Use Apache Spark Structured Streaming or Flink for real-time aggregation and anomaly detection.
- **Monitoring Engine**: 
  - Switch from basic Z-score to machine learning anomaly detection (e.g., AWS Lookout for Metrics or Prophet).
  - Pre-aggregate metrics (e.g., daily counts) into a fast key-value store (Redis/DynamoDB) so the monitoring engine doesn't have to scan millions of rows to calculate standard deviation.

## Hardening the Current Implementation

If you were to deploy the *current* codebase to production, these immediate changes are recommended:

1. **Dead Letter Queues (DLQ)**: Add DLQs to the AWS Lambdas so failed ingestion payloads are not lost and can be replayed.
2. **Secrets Management**: Move API keys from environment variables to AWS Secrets Manager or HashiCorp Vault.
3. **Idempotency**: Enhance the `loader.py` to use pure PostgreSQL `ON CONFLICT DO UPDATE` (Upsert) to guarantee idempotent runs.
4. **Partitioning**: Implement PostgreSQL Table Partitioning on the `date` columns in the `raw` schema to speed up the monitoring queries (which only look at the last 7 days).
