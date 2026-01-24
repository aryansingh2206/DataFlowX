SELECT
    user_id,
    name,
    country,
    age,
    created_at::DATE AS signup_date
FROM read_parquet(
  's3://silver/users/snapshot_date=*/data.parquet'
)
WHERE user_id IS NOT NULL
