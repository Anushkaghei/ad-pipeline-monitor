# Ad Pipeline Monitor — ELT Observability Platform

A production-grade data engineering observability system designed to catch "silent failures" in advertising pipelines (Meta Ads, Google Ads). 

Built entirely with free and open-source tools: **Python 3.11, PostgreSQL, dbt, FastAPI, and AWS SAM (Serverless)**.

## The Problem This Solves

Traditional job orchestrators (like Airflow) tell you if code successfully ran without crashing. They **do not** tell you if the data is actually correct.

This platform implements a **5-Pillar Observability Engine** that catches issues *before* they hit the executive dashboard:
1. **Row Count Drift**: Z-score anomaly detection against a 7-day rolling average.
2. **Null Thresholds**: Configurable strictness for critical columns (e.g., `spend` cannot have >5% nulls).
3. **Freshness SLAs**: Detects stale tables when upstream processes hang silently.
4. **Silent Failures**: Flags successful API calls that returned 0 rows or missed date partitions.
5. **dbt Testing**: Elevates native dbt SQL tests into real-time Slack/Email alerts.

## Architecture

![Architecture](docs/architecture.md)

- **Ingestion**: Python adapters for Meta Graph API and Google Ads API (includes highly realistic Mock adapters for testing without credentials).
- **Storage**: PostgreSQL (Raw → Staging → Marts → Monitoring schemas).
- **Transformation**: dbt models with native tests and custom observability macros.
- **Monitoring Engine**: Python orchestrator executing statistical analysis and SQL assertions.
- **Alerting**: Multi-channel dispatcher (Slack Webhooks, SMTP/SES Emails, Rich Console).
- **Serving**: FastAPI REST endpoints for dashboard integration.

## Local Development (Docker)

You can run the entire platform locally without any cloud dependencies.

### 1. Setup

```bash
# Clone the repository
git clone https://github.com/Anushkaghei/ad-pipeline-monitor.git
cd ad-pipeline-monitor

# Configure environment variables
cp .env.example .env
# Edit .env to add Slack Webhook URL (optional)

# Start the infrastructure (Postgres, API, dbt, Scheduler)
make up
```

### 2. Initialize and Seed

Because real Meta/Google Ads credentials are hard to share, the system includes realistic mock adapters that generate historical data and intentionally inject anomalies (spikes, nulls).

```bash
# Initialize DB schemas and tables
make setup

# Seed 14 days of historical data
make seed
```

### 3. Run the Pipeline

```bash
# Run the ingestion layer (fetches yesterday's data)
make ingest

# Run dbt transformations
make dbt-run

# Run observability checks and dispatch alerts
make monitor
```

Or run everything automatically via the local cron scheduler:
```bash
docker-compose logs -f app
```

## FastAPI Monitoring Dashboard

The platform includes a REST API to query the health of the system.

1. Navigate to: [http://localhost:8000/docs](http://localhost:8000/docs)
2. **GET `/health`**: Database connectivity status.
3. **GET `/pipeline-status`**: Status of recent ingestion runs.
4. **GET `/anomalies`**: Filterable list of all detected data anomalies.

## ☁️ AWS Serverless Deployment

For production, the system is designed to deploy to AWS using SAM (Serverless Application Model). It uses EventBridge to trigger Lambda functions on a cron schedule, keeping costs near $0.

```bash
# Build the Lambda packages
sam build

# Deploy to AWS (interactive prompt)
sam deploy --guided
```

## Testing

The project includes a comprehensive pytest suite covering the mock adapters, anomaly detection algorithms, API endpoints, and alerting logic.

```bash
# Run the test suite
make test
```

## Documentation Directory

Deep dive into the technical decisions:
- [Architecture Details](docs/architecture.md)
- [Monitoring Strategy](docs/monitoring_strategy.md)
- [Scalability & Future Evolution](docs/scalability.md)
- [Interview Talking Points](docs/interview_talking_points.md)
- [Grafana/BI SQL Queries](docs/dashboard_queries.sql)
