-- stg_google_campaigns.sql
-- Clean and standardize raw Google campaign data

{{ config(
    materialized='view',
    schema='staging'
) }}

SELECT
    campaign_id,
    TRIM(campaign_name)                         AS campaign_name,
    UPPER(TRIM(status))                         AS campaign_status,
    UPPER(TRIM(campaign_type))                  AS campaign_type,
    COALESCE(budget_amount, 0)::NUMERIC(12,2)   AS daily_budget,
    COALESCE(impressions, 0)                    AS impressions,
    COALESCE(clicks, 0)                         AS clicks,
    COALESCE(cost, 0)::NUMERIC(12,4)            AS spend,
    COALESCE(conversions, 0)                    AS conversions,
    CASE
        WHEN COALESCE(impressions, 0) > 0
        THEN ROUND(COALESCE(clicks, 0)::NUMERIC / impressions, 6)
        ELSE 0
    END                                         AS ctr,
    CASE
        WHEN COALESCE(clicks, 0) > 0
        THEN ROUND(COALESCE(cost, 0)::NUMERIC / clicks, 4)
        ELSE 0
    END                                         AS cpc,
    date::DATE                                  AS report_date,
    date::DATE                                  AS report_date_end,
    customer_id                                 AS account_id,
    'google'                                    AS platform,
    ingestion_timestamp

FROM {{ source('raw', 'google_campaigns') }}

WHERE date IS NOT NULL
