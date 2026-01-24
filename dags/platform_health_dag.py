from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
from minio import Minio
from minio.error import S3Error

MINIO_ENDPOINT = "minio:9000"
MINIO_ACCESS_KEY = "minio"
MINIO_SECRET_KEY = "minio123"

REQUIRED_BUCKETS = ["bronze", "silver", "gold"]


def check_minio_buckets():
    client = Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=False,
    )

    existing_buckets = [b.name for b in client.list_buckets()]

    missing = [b for b in REQUIRED_BUCKETS if b not in existing_buckets]

    if missing:
        raise Exception(f"Missing MinIO buckets: {missing}")

    print("✅ All required MinIO buckets are present")


default_args = {
    "owner": "dataflowx",
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}

with DAG(
    dag_id="platform_health_check",
    description="Validates core platform dependencies (MinIO buckets)",
    default_args=default_args,
    start_date=datetime(2026, 1, 1),
    schedule_interval="@daily",
    catchup=False,
    tags=["platform", "healthcheck"],
) as dag:

    check_storage = PythonOperator(
        task_id="check_minio_buckets",
        python_callable=check_minio_buckets,
    )

    check_storage
