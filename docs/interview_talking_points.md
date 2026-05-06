# Interview Talking Points

If you are using this project as a portfolio piece or discussing it in a data engineering interview, these talking points highlight the architectural decisions, trade-offs, and advanced concepts demonstrated in the code.

## 1. Why decouple Monitoring from the Scheduler?

**The Question:** "Why did you build a custom monitoring engine instead of just using Airflow alerts or dbt Cloud?"

**The Answer:**
*   **Separation of Concerns:** Job orchestration (Airflow/Prefect) is great at telling you *if code ran*. It is not inherently good at telling you *if the data is correct*. 
*   **Cross-System Visibility:** By having a dedicated engine, we can correlate metadata from the Python ingestion layer (rows fetched) with artifacts from the transformation layer (dbt tests).
*   **Statistical Analysis:** It's difficult to do complex rolling-window Z-score calculations purely in Airflow. Python allows us to leverage math libraries and custom logic.
*   **Cost:** Enterprise observability tools (Datadog, Monte Carlo, dbt Cloud) are incredibly expensive. This open-source approach delivers 80% of the value for $0.

## 2. Handling Missing Data vs Erroneous Data

**The Question:** "How do you handle API failures vs Data anomalies?"

**The Answer:**
*   **API Failures (Hard Failures):** Handled via standard try/except blocks and retries in the adapter. If the API goes down, the pipeline run is marked as `failed`, and we alert immediately.
*   **Data Anomalies (Silent Failures):** Handled via our 5-pillar strategy. We specifically look for "successful" API calls that return 0 rows, gaps in date partitions, and unexpected spikes/drops in volume using standard deviation boundaries.

## 3. Dealing with API Rate Limits and Pagination

**The Question:** "How does your ingestion layer handle large accounts and API limits?"

**The Answer:**
*   *Note: In the mock adapter, this is simulated, but the real adapters show the pattern.*
*   We use pagination (e.g., cursors in Meta Ads).
*   We ingest data in chunks and use SQLAlchemy `batch inserts` (`executemany`) rather than inserting row-by-row.
*   We use an **Upsert** strategy. If the pipeline runs twice for the same date, it updates the existing rows rather than creating duplicates, ensuring idempotency.

## 4. Why dbt for Transformations?

**The Question:** "Why didn't you just use Python/Pandas to clean the data before inserting it into Postgres?"

**The Answer:**
*   **ELT vs ETL:** The modern data stack prefers ELT. We load the raw JSON/data into the warehouse as quickly as possible.
*   **Auditability:** By keeping the `raw` schema untouched, if there's ever a bug in our transformation logic, we don't have to re-ping the APIs. We just rebuild the dbt models.
*   **SQL Accessibility:** Analytics Engineers and Data Analysts can easily read and modify the dbt models, whereas Python transformations create a bottleneck on Data Engineers.

## 5. Deployment Trade-offs: Docker vs Serverless

**The Question:** "Why did you provide both Docker and AWS SAM deployments?"

**The Answer:**
*   **Docker** is perfect for local development and testing. It allows any engineer to clone the repo, run `docker-compose up`, and instantly have a working PostgreSQL instance and Python environment.
*   **AWS Serverless (Lambda + EventBridge)** is chosen for production because ELT workloads for advertising are highly bursty. You run them once an hour or once a day. Paying for an always-on EC2 instance is wasteful. Lambda scales to zero and costs practically nothing on the free tier.

## 6. The Mock Data Generator

**The Question:** "Why go through the trouble of building complex mock adapters?"

**The Answer:**
*   It proves the pipeline works end-to-end without requiring sensitive API credentials from the interviewer or user.
*   More importantly, the mock adapter intentionally injects **deterministic anomalies** (nulls, spikes, zero-rows). This allows us to write reliable Unit Tests for our monitoring engine to prove that it successfully catches those exact anomalies.
