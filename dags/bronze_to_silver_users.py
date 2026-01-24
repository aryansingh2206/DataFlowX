from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import pandas as pd
from minio import Minio
from io import BytesIO
import pyarrow as pa
import pyarrow.parquet as pq


# ---------------- CONFIG ----------------
MINIO_CONFIG = {
    "endpoint": "minio:9000",
    "access_key": "minio",
    "secret_key": "minio123",
    "secure": False,
}

BRONZE_BUCKET = "bronze"
SILVER_BUCKET = "silver"

TABLE = "users"


# ---------------- LOGIC ----------------
def transform_users(**context):
    execution_date = context["ds"]

    minio_client = Minio(**MINIO_CONFIG)

    bronze_prefix = (
        f"postgres/{TABLE}/load_date={execution_date}/"
    )

    objects = list(
        minio_client.list_objects(
            BRONZE_BUCKET,
            prefix=bronze_prefix,
            recursive=True,
        )
    )

    if not objects:
        raise Exception("No bronze data found for this date")

    # Read Parquet from MinIO
    for obj in objects:
        response = minio_client.get_object(
            BRONZE_BUCKET,
            obj.object_name,
        )
        df = pd.read_parquet(BytesIO(response.read()))
        response.close()
        response.release_conn()

    # ---------------- CLEANING ----------------
    df = df.drop_duplicates(subset=["user_id"])
    df = df[df["email"].notnull()]
    df["email"] = df["email"].str.lower()
    df["country"] = df["country"].fillna("UNKNOWN")
    df["is_active"] = df["is_active"].fillna(True)

    # Enforce types
    df["user_id"] = df["user_id"].astype(int)
    df["is_active"] = df["is_active"].astype(bool)

    # ---------------- WRITE SILVER ----------------
    table = pa.Table.from_pandas(df)
    buffer = BytesIO()
    pq.write_table(table, buffer)
    buffer.seek(0)

    object_path = (
        f"{TABLE}/snapshot_date={execution_date}/data.parquet"
    )

    minio_client.put_object(
        bucket_name=SILVER_BUCKET,
        object_name=object_path,
        data=buffer,
        length=buffer.getbuffer().nbytes,
        content_type="application/octet-stream",
    )

    print(f"Silver users snapshot written: {object_path}")


# ---------------- DAG ----------------
default_args = {
    "owner": "dataflowx",
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}

with DAG(
    dag_id="bronze_to_silver_users",
    description="Clean and normalize users data from Bronze to Silver",
    default_args=default_args,
    start_date=datetime(2026, 1, 1),
    schedule_interval="@daily",
    catchup=False,
    tags=["silver", "transform"],
) as dag:

    transform_task = PythonOperator(
        task_id="transform_users",
        python_callable=transform_users,
        provide_context=True,
    )

    transform_task
