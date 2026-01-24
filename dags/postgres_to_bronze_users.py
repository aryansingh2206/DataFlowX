from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.models import Variable
from datetime import datetime, timedelta
import pandas as pd
import psycopg2
from minio import Minio
from io import BytesIO
import pyarrow as pa
import pyarrow.parquet as pq
from quality_checks import validate_dataframe



# ---------------- CONFIG ----------------
POSTGRES_CONN = {
    "host": "postgres",
    "dbname": "airflow",
    "user": "airflow",
    "password": "airflow",
    "port": 5432,
}

MINIO_CONFIG = {
    "endpoint": "minio:9000",
    "access_key": "minio",
    "secret_key": "minio123",
    "secure": False,
}

BUCKET = "bronze"
TABLE = "users"


# ---------------- LOGIC ----------------
def extract_and_load_users(**context):
    execution_date = context["ds"]  # YYYY-MM-DD

    # Last successful load watermark
    last_loaded_ts = Variable.get(
        "users_last_updated_at",
        default_var="1970-01-01 00:00:00",
    )

    query = f"""
        SELECT *
        FROM source.users
        WHERE updated_at > '{last_loaded_ts}'
        ORDER BY updated_at
    """

    conn = psycopg2.connect(**POSTGRES_CONN)
    df = pd.read_sql(query, conn)
    conn.close()

    # ---------------- DATA QUALITY ----------------
    validate_dataframe(
        df=df,
        expectation_file_path="/opt/airflow/great_expectations/expectations/users_bronze_expectations.json",
)


    if df.empty:
        print("No new records found.")
        return

    # Update watermark
    max_updated_at = df["updated_at"].max()
    Variable.set("users_last_updated_at", str(max_updated_at))

    # Write Parquet to memory
    table = pa.Table.from_pandas(df)
    buffer = BytesIO()
    pq.write_table(table, buffer)
    buffer.seek(0)

    # Upload to MinIO
    minio_client = Minio(**MINIO_CONFIG)

    object_path = (
        f"postgres/{TABLE}/load_date={execution_date}/data.parquet"
    )

    minio_client.put_object(
        bucket_name=BUCKET,
        object_name=object_path,
        data=buffer,
        length=buffer.getbuffer().nbytes,
        content_type="application/octet-stream",
    )

    print(f"Loaded {len(df)} records to {object_path}")


# ---------------- DAG ----------------
default_args = {
    "owner": "dataflowx",
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}

with DAG(
    dag_id="postgres_to_bronze_users",
    description="Incremental load of users table from Postgres to Bronze layer",
    default_args=default_args,
    start_date=datetime(2026, 1, 1),
    schedule_interval="@daily",
    catchup=False,
    tags=["bronze", "postgres"],
) as dag:

    ingest_users = PythonOperator(
        task_id="extract_users_incremental",
        python_callable=extract_and_load_users,
        provide_context=True,
    )

    ingest_users
