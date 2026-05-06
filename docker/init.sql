-- ============================================================
-- Ad Pipeline Monitor — Database Initialization
-- ============================================================
-- This script runs automatically when the Postgres container
-- starts for the first time.

-- ── Schemas ─────────────────────────────────────────────────
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS marts;
CREATE SCHEMA IF NOT EXISTS monitoring;

-- ============================================================
-- RAW LAYER
-- ============================================================

CREATE TABLE IF NOT EXISTS raw.meta_campaigns (
    id                  BIGSERIAL PRIMARY KEY,
    campaign_id         VARCHAR(64) NOT NULL,
    campaign_name       VARCHAR(256),
    status              VARCHAR(32),
    objective           VARCHAR(64),
    daily_budget        NUMERIC(12,2),
    impressions         BIGINT DEFAULT 0,
    clicks              BIGINT DEFAULT 0,
    spend               NUMERIC(12,4) DEFAULT 0,
    conversions         INTEGER DEFAULT 0,
    ctr                 NUMERIC(8,6),
    cpc                 NUMERIC(10,4),
    date_start          DATE NOT NULL,
    date_stop           DATE,
    account_id          VARCHAR(64),
    ingestion_timestamp TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS raw.google_campaigns (
    id                  BIGSERIAL PRIMARY KEY,
    campaign_id         VARCHAR(64) NOT NULL,
    campaign_name       VARCHAR(256),
    status              VARCHAR(32),
    campaign_type       VARCHAR(64),
    budget_amount       NUMERIC(12,2),
    impressions         BIGINT DEFAULT 0,
    clicks              BIGINT DEFAULT 0,
    cost                NUMERIC(12,4) DEFAULT 0,
    conversions         INTEGER DEFAULT 0,
    ctr                 NUMERIC(8,6),
    cpc                 NUMERIC(10,4),
    date                DATE NOT NULL,
    customer_id         VARCHAR(64),
    ingestion_timestamp TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS raw.meta_adsets (
    id                  BIGSERIAL PRIMARY KEY,
    adset_id            VARCHAR(64) NOT NULL,
    adset_name          VARCHAR(256),
    campaign_id         VARCHAR(64) NOT NULL,
    status              VARCHAR(32),
    targeting           JSONB,
    daily_budget        NUMERIC(12,2),
    impressions         BIGINT DEFAULT 0,
    clicks              BIGINT DEFAULT 0,
    spend               NUMERIC(12,4) DEFAULT 0,
    date_start          DATE NOT NULL,
    date_stop           DATE,
    ingestion_timestamp TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS raw.google_keywords (
    id                  BIGSERIAL PRIMARY KEY,
    keyword_id          VARCHAR(64) NOT NULL,
    keyword_text        VARCHAR(256),
    campaign_id         VARCHAR(64) NOT NULL,
    ad_group_id         VARCHAR(64),
    match_type          VARCHAR(32),
    impressions         BIGINT DEFAULT 0,
    clicks              BIGINT DEFAULT 0,
    cost                NUMERIC(12,4) DEFAULT 0,
    quality_score       INTEGER,
    date                DATE NOT NULL,
    ingestion_timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- ── Indexes on raw tables ───────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_raw_meta_camp_date
    ON raw.meta_campaigns (date_start, campaign_id);

CREATE INDEX IF NOT EXISTS idx_raw_google_camp_date
    ON raw.google_campaigns (date, campaign_id);

CREATE INDEX IF NOT EXISTS idx_raw_meta_adsets_date
    ON raw.meta_adsets (date_start, campaign_id);

CREATE INDEX IF NOT EXISTS idx_raw_google_kw_date
    ON raw.google_keywords (date, campaign_id);

-- ============================================================
-- MONITORING LAYER
-- ============================================================

CREATE TABLE IF NOT EXISTS monitoring.pipeline_runs (
    id              BIGSERIAL PRIMARY KEY,
    pipeline_name   VARCHAR(128) NOT NULL,
    status          VARCHAR(32) NOT NULL DEFAULT 'running',
    rows_ingested   INTEGER DEFAULT 0,
    started_at      TIMESTAMPTZ DEFAULT NOW(),
    completed_at    TIMESTAMPTZ,
    error_message   TEXT
);

CREATE TABLE IF NOT EXISTS monitoring.check_results (
    id              BIGSERIAL PRIMARY KEY,
    check_name      VARCHAR(128) NOT NULL,
    check_type      VARCHAR(64) NOT NULL,
    table_name      VARCHAR(128),
    expected_value  NUMERIC,
    actual_value    NUMERIC,
    passed          BOOLEAN NOT NULL,
    severity        VARCHAR(16) DEFAULT 'warning',
    details         JSONB,
    checked_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS monitoring.alert_history (
    id              BIGSERIAL PRIMARY KEY,
    check_result_id BIGINT REFERENCES monitoring.check_results(id),
    channel         VARCHAR(32) NOT NULL,
    sent_at         TIMESTAMPTZ DEFAULT NOW(),
    payload         JSONB,
    success         BOOLEAN DEFAULT TRUE
);

-- ── Indexes on monitoring tables ────────────────────────────
CREATE INDEX IF NOT EXISTS idx_check_results_time
    ON monitoring.check_results (checked_at DESC);

CREATE INDEX IF NOT EXISTS idx_check_results_type
    ON monitoring.check_results (check_type, passed);

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_name
    ON monitoring.pipeline_runs (pipeline_name, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_alert_history_time
    ON monitoring.alert_history (sent_at DESC);
