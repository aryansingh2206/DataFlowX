
#  DataFlowX —> End-to-End Modern Data Platform (Bronze → Silver → Gold)

DataFlowX is a **production-style data engineering project** that simulates how real-world analytics platforms ingest, transform, and serve data at scale using modern tools and best practices.

This project demonstrates **end-to-end data lifecycle ownership**: ingestion → transformation → storage → analytics.

---

## 🧠 Problem Statement

Most data engineering tutorials stop at:

* basic ETL scripts
* unvalidated outputs
* no orchestration
* no storage strategy

**DataFlowX** was built to answer a more realistic question:

> *How would you design a reliable, analytics-ready data platform from scratch?*

---

## 🏗 Architecture Overview

```
PostgreSQL (Source)
        ↓
   Bronze Layer (Raw Snapshots)
        ↓
   Silver Layer (Cleaned & Normalized)
        ↓
   Gold Layer (Aggregated Metrics)
        ↓
 DuckDB / BI / Analytics
```

### Key Design Principles

* Snapshot-based ingestion (time-travel friendly)
* Idempotent daily pipelines
* Partitioned object storage
* Analytics-optimized formats (Parquet)
* Orchestration with retries & observability

---

## 🛠 Tech Stack

| Layer           | Technology                         |
| --------------- | ---------------------------------- |
| Orchestration   | Apache Airflow                     |
| Storage         | MinIO (S3-compatible object store) |
| Source DB       | PostgreSQL                         |
| File Format     | Parquet (PyArrow)                  |
| Transformations | Pandas                             |
| Analytics       | DuckDB                             |
| Infrastructure  | Docker & Docker Compose            |

---

## 📂 Data Layers Explained

### 🥉 Bronze — Raw Ingestion

* Source: PostgreSQL
* Stored as immutable daily snapshots
* No transformations
* Purpose: **auditability & replay**

```
s3://bronze/users/snapshot_date=YYYY-MM-DD/data.parquet
```

---

### 🥈 Silver — Cleaned & Standardized

* Deduplication
* Type normalization
* Business-ready schema
* Still granular

```
s3://silver/users/snapshot_date=YYYY-MM-DD/data.parquet
```

---

### 🥇 Gold — Analytics-Ready Metrics

* Aggregated business metrics
* Optimized for querying
* Partitioned by snapshot date

```
s3://gold/analytics/daily_user_metrics/
└── snapshot_date=YYYY-MM-DD/
    └── data.parquet
```

Example metrics:

* Total users per country
* Average age per country

---

## ⏱ Orchestration (Airflow DAGs)

| DAG                           | Responsibility             |
| ----------------------------- | -------------------------- |
| `postgres_to_bronze_users`    | Extract source data        |
| `bronze_to_silver_users`      | Clean & standardize        |
| `silver_to_gold_user_metrics` | Build analytics metrics    |
| `platform_health_check`       | Pipeline health validation |

All DAGs:

* Run daily
* Support backfills
* Are retry-safe
* Fail loudly when upstream data is missing

---

## 📊 Querying the Gold Layer (DuckDB)

Gold data can be queried **directly from S3** without loading into a database:

```sql
SELECT *
FROM read_parquet(
  's3://gold/analytics/daily_user_metrics/**/*.parquet'
);
```

This enables:

* Fast analytics
* Zero-copy querying
* Easy BI integration

---

## ✅ Validation & Observability

* Bucket & object verification via MinIO API
* Task-level retries
* Explicit failures when data is missing
* Manual and scheduled DAG runs validated

---

## 📁 Repository Structure

```
DataFlowX/
├── dags/
│   ├── postgres_to_bronze_users.py
│   ├── bronze_to_silver_users.py
│   ├── silver_to_gold_user_metrics.py
│   └── platform_health_check.py
├── docker-compose.yml
├── scripts/
├── README.md
```

---

## 🎯 Why This Project Is Different

✅ Not a toy ETL
✅ Uses real orchestration
✅ Uses modern lakehouse patterns
✅ Storage-first design
✅ Analytics-ready outputs
✅ Interview-explainable architecture

This project mirrors how data platforms are built in **real production environments**.

---

## 🔮 Possible Extensions

* Data quality checks (row counts, nulls)
* Schema evolution handling
* Slowly Changing Dimensions (SCD)
* BI dashboard (Superset / Metabase)
* CI for DAG validation

---

