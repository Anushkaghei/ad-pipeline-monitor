-- custom_tests.sql
-- Custom data quality tests

-- Test: no negative spend values
{% test positive_spend(model, column_name) %}
    SELECT *
    FROM {{ model }}
    WHERE {{ column_name }} < 0
{% endtest %}

-- Test: CTR should be between 0 and 1
{% test valid_ctr(model, column_name) %}
    SELECT *
    FROM {{ model }}
    WHERE {{ column_name }} < 0 OR {{ column_name }} > 1
{% endtest %}

-- Test: report dates should not be in the future
{% test no_future_dates(model, column_name) %}
    SELECT *
    FROM {{ model }}
    WHERE {{ column_name }} > CURRENT_DATE
{% endtest %}
