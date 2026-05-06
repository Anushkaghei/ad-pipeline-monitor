-- ======================================================================
-- Ad Pipeline Monitor — Dashboard Queries
-- 
-- Use these SQL queries in your BI tool (Grafana, Metabase, Preset)
-- to build out the observability dashboard.
-- ======================================================================

-- ──────────────────────────────────────────────────────────────────────
-- 1. Pipeline Health: Success Rate (Last 7 Days)
-- ──────────────────────────────────────────────────────────────────────
SELECT 
    pipeline_name,
    COUNT(*) AS total_runs,
    COUNT(*) FILTER (WHERE status = 'success') AS successful_runs,
    ROUND(
        COUNT(*) FILTER (WHERE status = 'success')::NUMERIC / COUNT(*) * 100, 
        2
    ) AS success_rate_pct
FROM monitoring.pipeline_runs
WHERE started_at >= NOW() - INTERVAL '7 days'
GROUP BY pipeline_name
ORDER BY success_rate_pct ASC;


-- ──────────────────────────────────────────────────────────────────────
-- 2. Anomaly Overview: Active Alerts by Severity
-- ──────────────────────────────────────────────────────────────────────
SELECT 
    severity,
    COUNT(*) AS active_anomalies
FROM monitoring.check_results
WHERE passed = FALSE
  AND checked_at >= NOW() - INTERVAL '24 hours'
GROUP BY severity
ORDER BY 
    CASE severity 
        WHEN 'critical' THEN 1 
        WHEN 'warning' THEN 2 
        ELSE 3 
    END;


-- ──────────────────────────────────────────────────────────────────────
-- 3. Row Count Drift: Actual vs 7-Day Average
-- ──────────────────────────────────────────────────────────────────────
WITH history AS (
    SELECT 
        table_name,
        AVG(actual_value) AS baseline_avg
    FROM monitoring.check_results
    WHERE check_type = 'row_count'
      AND checked_at >= NOW() - INTERVAL '7 days'
      AND checked_at < NOW() - INTERVAL '24 hours'
    GROUP BY table_name
),
current AS (
    SELECT DISTINCT ON (table_name)
        table_name,
        actual_value AS current_count,
        checked_at
    FROM monitoring.check_results
    WHERE check_type = 'row_count'
    ORDER BY table_name, checked_at DESC
)
SELECT 
    c.table_name,
    ROUND(h.baseline_avg, 0) AS baseline_7d_avg,
    c.current_count,
    ROUND(((c.current_count - h.baseline_avg) / h.baseline_avg) * 100, 2) AS deviation_pct
FROM current c
JOIN history h ON c.table_name = h.table_name;


-- ──────────────────────────────────────────────────────────────────────
-- 4. Freshness SLA Breaches
-- ──────────────────────────────────────────────────────────────────────
SELECT DISTINCT ON (table_name)
    table_name,
    actual_value AS hours_stale,
    expected_value AS sla_hours,
    checked_at
FROM monitoring.check_results
WHERE check_type = 'freshness'
  AND passed = FALSE
ORDER BY table_name, checked_at DESC;


-- ──────────────────────────────────────────────────────────────────────
-- 5. Business Metric: Daily Spend Anomalies
-- ──────────────────────────────────────────────────────────────────────
SELECT 
    report_date,
    platform,
    SUM(total_spend) AS daily_spend,
    LAG(SUM(total_spend)) OVER (PARTITION BY platform ORDER BY report_date) AS prev_day_spend,
    ROUND(
        (SUM(total_spend) - LAG(SUM(total_spend)) OVER (PARTITION BY platform ORDER BY report_date)) 
        / NULLIF(LAG(SUM(total_spend)) OVER (PARTITION BY platform ORDER BY report_date), 0) * 100,
        2
    ) AS dod_spend_change_pct
FROM marts.agg_daily_spend
GROUP BY report_date, platform
ORDER BY platform, report_date DESC;


-- ──────────────────────────────────────────────────────────────────────
-- 6. dbt Test Failure Log
-- ──────────────────────────────────────────────────────────────────────
SELECT 
    check_name AS test_name,
    severity,
    details->>'failure_count' AS failures,
    checked_at
FROM monitoring.check_results
WHERE check_type = 'dbt_test'
  AND passed = FALSE
ORDER BY checked_at DESC
LIMIT 50;
