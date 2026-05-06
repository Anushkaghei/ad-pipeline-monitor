-- stg_meta_campaigns.sql
-- Clean and standardize raw Meta campaign data

{{ config(
    materialized='view',
    schema='staging'
) }}

SELECT
    campaign_id,
    TRIM(campaign_name)                         AS campaign_name,
    UPPER(TRIM(status))                         AS campaign_status,
    UPPER(TRIM(objective))                      AS campaign_objective,
    COALESCE(daily_budget, 0)::NUMERIC(12,2)    AS daily_budget,
    COALESCE(impressions, 0)                    AS impressions,
    COALESCE(clicks, 0)                         AS clicks,
    COALESCE(spend, 0)::NUMERIC(12,4)           AS spend,
    COALESCE(conversions, 0)                    AS conversions,
    CASE
        WHEN COALESCE(impressions, 0) > 0
        THEN ROUND(COALESCE(clicks, 0)::NUMERIC / impressions, 6)
        ELSE 0
    END                                         AS ctr,
    CASE
        WHEN COALESCE(clicks, 0) > 0
        THEN ROUND(COALESCE(spend, 0)::NUMERIC / clicks, 4)
        ELSE 0
    END                                         AS cpc,
    date_start::DATE                            AS report_date,
    date_stop::DATE                             AS report_date_end,
    account_id,
    'meta'                                      AS platform,
    ingestion_timestamp

FROM {{ source('raw', 'meta_campaigns') }}

WHERE date_start IS NOT NULL
