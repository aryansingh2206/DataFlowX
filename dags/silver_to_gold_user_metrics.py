from datetime import datetime, timedelta
import io
import logging

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from minio import Minio
from minio.error import S3Error

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.datasets import Dataset


# -------------------------------------------------------------------
# Config
# -------------------------------------------------------------------

MINIO_ENDPOINT = "minio:9000"
MINIO_ACCESS_KEY = "minio"
MINIO_SECRET_KEY = "minio123"

SILVER_BUCKET = "silver"
GOLD_BUCKET = "gold"

# Dataset contract (must match Silver DAG outlet)
SILVER_USERS_DATASET = Dataset("s3://silver/users")


# -------------------------------------------------------------------
# Task logic
# -------------------------------------------------------------------

def build_user_metrics(**context):
    """
    Reads Silver users snapshot for the current data interval,
    aggregates metrics, writes Gold snapshot.
    """

    # Dataset-triggered DAG → this date is guaranteed to exist
    snapshot_date = context["data_interval_start"].date().isoformat()

    silver_object = f"users/snapshot_date={snapshot_date}/data.parquet"
    gold_object = f"user_metrics/snapshot_date={snapshot_date}/data.parquet"

    logging.info(f"Reading Silver data: {silver_object}")

    minio_client = Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=False,
    )

    # -----------------------------
    # Read from Silver
    # -----------------------------
    try:
        response = minio_client.get_object(SILVER_BUCKET, silver_object)
        silver_df = pq.read_table(response).to_pandas()
    except S3Error as e:
        raise RuntimeError(
            f"Silver snapshot missing for {snapshot_date}. "
            f"Upstream Silver pipeline did not publish expected data."
        ) from e
    finally:
        try:
            response.close()
            response.release_conn()
        except Exception:
            pass

    if silver_df.empty:
        raise ValueError("Silver dataset is empty — aborting Gold build")

    logging.info(f"Loaded {len(silver_df)} rows from Silver")

    # -----------------------------
    # Transform → Metrics
    # -----------------------------
    metrics_df = (
        silver_df
        .groupby("country", as_index=False)
        .agg(
            total_users=("user_id", "count"),
            avg_age=("age", "mean"),
        )
    )

    metrics_df["snapshot_date"] = snapshot_date

    logging.info("User metrics computed successfully")

    # -----------------------------
    # Write to Gold
    # -----------------------------
    buffer = io.BytesIO()
    table = pa.Table.from_pandas(metrics_df)
    pq.write_table(table, buffer)
    buffer.seek(0)

    minio_client.put_object(
        bucket_name=GOLD_BUCKET,
        object_name=gold_object,
        data=buffer,
        length=buffer.getbuffer().nbytes,
        content_type="application/octet-stream",
    )

    logging.info(f"Gold data written: {gold_object}")


# -------------------------------------------------------------------
# DAG definition
# -------------------------------------------------------------------

with DAG(
    dag_id="silver_to_gold_user_metrics",
    start_date=datetime(2026, 1, 23),
    schedule=[SILVER_USERS_DATASET],   # 🔥 Dataset-driven
    catchup=False,
    default_args={
        "owner": "dataflowx",
        "retries": 1,
        "retry_delay": timedelta(minutes=5),
    },
    tags=["gold", "metrics"],
) as dag:

    build_user_metrics_task = PythonOperator(
        task_id="build_user_metrics",
        python_callable=build_user_metrics,
    )
