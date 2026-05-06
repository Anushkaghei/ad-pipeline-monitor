-- fct_ad_performance.sql
-- Unified fact table: all platforms, daily campaign-level metrics

{{ config(
    materialized='table',
    schema='marts'
) }}

WITH meta AS (
    SELECT
        campaign_id,
        campaign_name,
        campaign_status,
        campaign_objective                      AS campaign_type,
        daily_budget,
        impressions,
        clicks,
        spend,
        conversions,
        ctr,
        cpc,
        report_date,
        account_id,
        platform,
        ingestion_timestamp
    FROM {{ ref('stg_meta_campaigns') }}
),

google AS (
    SELECT
        campaign_id,
        campaign_name,
        campaign_status,
        campaign_type,
        daily_budget,
        impressions,
        clicks,
        spend,
        conversions,
        ctr,
        cpc,
        report_date,
        account_id,
        platform,
        ingestion_timestamp
    FROM {{ ref('stg_google_campaigns') }}
),

unioned AS (
    SELECT * FROM meta
    UNION ALL
    SELECT * FROM google
)

SELECT
    {{ dbt_utils.generate_surrogate_key(['platform', 'campaign_id', 'report_date']) }}
                                                AS performance_id,
    campaign_id,
    campaign_name,
    campaign_status,
    campaign_type,
    daily_budget,
    impressions,
    clicks,
    spend,
    conversions,
    ctr,
    cpc,
    CASE
        WHEN conversions > 0 THEN ROUND(spend / conversions, 2)
        ELSE NULL
    END                                         AS cost_per_conversion,
    CASE
        WHEN impressions > 0 THEN ROUND(conversions::NUMERIC / impressions * 1000, 4)
        ELSE 0
    END                                         AS conversion_rate_per_mille,
    report_date,
    account_id,
    platform,
    ingestion_timestamp

FROM unioned
