SELECT
    country,
    COUNT(*) AS total_users,
    AVG(age) AS avg_age,
    CURRENT_DATE AS snapshot_date
FROM {{ ref('silver_users') }}
GROUP BY country
