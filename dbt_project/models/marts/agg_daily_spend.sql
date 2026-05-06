-- agg_daily_spend.sql
-- Daily aggregated spend by platform and campaign

{{ config(
    materialized='table',
    schema='marts'
) }}

SELECT
    report_date,
    platform,
    campaign_id,
    campaign_name,

    SUM(impressions)                            AS total_impressions,
    SUM(clicks)                                 AS total_clicks,
    SUM(spend)                                  AS total_spend,
    SUM(conversions)                            AS total_conversions,

    CASE
        WHEN SUM(impressions) > 0
        THEN ROUND(SUM(clicks)::NUMERIC / SUM(impressions), 6)
        ELSE 0
    END                                         AS avg_ctr,

    CASE
        WHEN SUM(clicks) > 0
        THEN ROUND(SUM(spend) / SUM(clicks), 4)
        ELSE 0
    END                                         AS avg_cpc,

    CASE
        WHEN SUM(conversions) > 0
        THEN ROUND(SUM(spend) / SUM(conversions), 2)
        ELSE NULL
    END                                         AS avg_cost_per_conversion,

    COUNT(*)                                    AS record_count,
    MAX(ingestion_timestamp)                    AS last_ingested_at

FROM {{ ref('fct_ad_performance') }}

GROUP BY
    report_date,
    platform,
    campaign_id,
    campaign_name

ORDER BY report_date DESC, total_spend DESC
