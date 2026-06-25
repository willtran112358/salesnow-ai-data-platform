"""Airflow DAGs for SalesNow data platform orchestration."""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator
from airflow.providers.amazon.aws.operators.ecs import EcsRunTaskOperator

default_args = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "email_on_failure": True,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

S3_BUCKET = "salesnow-data-lake"
ECS_CLUSTER = "salesnow-crawl-cluster"
TASK_DEFINITION = "scrapy-corporate-profile"


def validate_silver_quality(**context: object) -> None:
    """Run data quality checks after silver ETL."""
    from src.quality.validator import CompanyRecordValidator

    # In production: read from S3 silver partition for execution date
    result = CompanyRecordValidator().validate_batch([])
    if not result.ok and result.total > 0:
        raise ValueError(f"Quality SLA breached: pass_rate={result.pass_rate:.2%}")


with DAG(
    dag_id="salesnow_daily_pipeline",
    default_args=default_args,
    description="Daily crawl → silver → gold → quality monitoring",
    schedule_interval="0 2 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["salesnow", "ingestion", "etl"],
) as dag:
    start = EmptyOperator(task_id="start")

    crawl_corporate_sites = EcsRunTaskOperator(
        task_id="crawl_corporate_sites",
        cluster=ECS_CLUSTER,
        task_definition=TASK_DEFINITION,
        launch_type="FARGATE",
        overrides={
            "containerOverrides": [
                {
                    "name": "scrapy",
                    "environment": [
                        {"name": "S3_OUTPUT", "value": f"s3://{S3_BUCKET}/bronze/crawl/"},
                        {"name": "SPIDER", "value": "corporate_profile"},
                    ],
                }
            ]
        },
        network_configuration={
            "awsvpcConfiguration": {
                "subnets": ["subnet-xxx"],
                "securityGroups": ["sg-xxx"],
                "assignPublicIp": "ENABLED",
            }
        },
    )

    silver_cleansing = EmptyOperator(task_id="silver_cleansing")

    gold_dimensional = EmptyOperator(task_id="gold_dimensional_model")

    quality_check = PythonOperator(
        task_id="data_quality_monitoring",
        python_callable=validate_silver_quality,
    )

    end = EmptyOperator(task_id="end")

    start >> crawl_corporate_sites >> silver_cleansing >> gold_dimensional >> quality_check >> end
