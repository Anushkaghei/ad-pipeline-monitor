-- dim_campaign.sql
-- Campaign dimension with latest attributes (SCD Type 1)

{{ config(
    materialized='table',
    schema='marts'
) }}

WITH latest_meta AS (
    SELECT DISTINCT ON (campaign_id)
        campaign_id,
        campaign_name,
        campaign_status,
        campaign_objective                  AS campaign_type,
        daily_budget,
        account_id,
        'meta'                              AS platform,
        ingestion_timestamp                 AS last_seen_at
    FROM {{ ref('stg_meta_campaigns') }}
    ORDER BY campaign_id, ingestion_timestamp DESC
),

latest_google AS (
    SELECT DISTINCT ON (campaign_id)
        campaign_id,
        campaign_name,
        campaign_status,
        campaign_type,
        daily_budget,
        account_id,
        'google'                            AS platform,
        ingestion_timestamp                 AS last_seen_at
    FROM {{ ref('stg_google_campaigns') }}
    ORDER BY campaign_id, ingestion_timestamp DESC
),

unioned AS (
    SELECT * FROM latest_meta
    UNION ALL
    SELECT * FROM latest_google
)

SELECT
    {{ dbt_utils.generate_surrogate_key(['platform', 'campaign_id']) }}
                                            AS campaign_key,
    campaign_id,
    campaign_name,
    campaign_status,
    campaign_type,
    daily_budget,
    account_id,
    platform,
    last_seen_at

FROM unioned
