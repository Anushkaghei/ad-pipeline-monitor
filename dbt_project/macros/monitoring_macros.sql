-- monitoring_macros.sql
-- Custom macros for monitoring and data quality checks

{% macro assert_row_count(model, min_rows) %}
    {#
        Assert that a model has at least `min_rows` rows.
        Usage: {{ assert_row_count(ref('stg_meta_campaigns'), 1) }}
    #}
    SELECT
        CASE
            WHEN COUNT(*) < {{ min_rows }}
            THEN 'FAIL: ' || '{{ model }}' || ' has ' || COUNT(*)::TEXT || ' rows, expected >= ' || '{{ min_rows }}'
            ELSE 'PASS'
        END AS result
    FROM {{ model }}
{% endmacro %}


{% macro check_freshness_hours(model, timestamp_col, max_hours) %}
    {#
        Check if a table has been updated within max_hours.
        Returns FAIL if the most recent timestamp is older than max_hours.
    #}
    SELECT
        CASE
            WHEN EXTRACT(EPOCH FROM (NOW() - MAX({{ timestamp_col }}))) / 3600 > {{ max_hours }}
            THEN 'FAIL: ' || '{{ model }}' || ' is stale — last update was ' ||
                 ROUND(EXTRACT(EPOCH FROM (NOW() - MAX({{ timestamp_col }}))) / 3600, 1)::TEXT || ' hours ago'
            ELSE 'PASS'
        END AS result
    FROM {{ model }}
{% endmacro %}


{% macro null_percentage(model, column_name, max_pct) %}
    {#
        Check if null percentage for a column exceeds threshold.
    #}
    SELECT
        CASE
            WHEN COUNT(*) = 0 THEN 'PASS'
            WHEN (COUNT(*) FILTER (WHERE {{ column_name }} IS NULL))::NUMERIC / COUNT(*) * 100 > {{ max_pct }}
            THEN 'FAIL: ' || '{{ column_name }}' || ' in {{ model }} has ' ||
                 ROUND((COUNT(*) FILTER (WHERE {{ column_name }} IS NULL))::NUMERIC / COUNT(*) * 100, 2)::TEXT ||
                 '% nulls (threshold: {{ max_pct }}%)'
            ELSE 'PASS'
        END AS result
    FROM {{ model }}
{% endmacro %}
