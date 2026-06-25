"""
PySpark entity resolution job for Databricks.

Resolves duplicate company records using corporate number and fuzzy name matching.
"""

from __future__ import annotations

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window


def create_spark() -> SparkSession:
    return (
        SparkSession.builder.appName("salesnow_entity_resolution")
        .config("spark.sql.adaptive.enabled", "true")
        .getOrCreate()
    )


def normalize_name_col(col: str) -> F.Column:
    return F.regexp_replace(F.trim(F.col(col)), r"^(株式会社|（株）|\(株\))", "")


def resolve_entities(silver_df: DataFrame) -> DataFrame:
    """Deduplicate companies: exact corporate_number first, then normalized name."""
    with_corp = silver_df.filter(F.col("corporate_number").isNotNull())
    without_corp = silver_df.filter(F.col("corporate_number").isNull())

    deduped_by_corp = (
        with_corp.withColumn(
            "row_num",
            F.row_number().over(
                Window.partitionBy("corporate_number").orderBy(F.desc("updated_at"))
            ),
        )
        .filter(F.col("row_num") == 1)
        .drop("row_num")
    )

    deduped_by_name = (
        without_corp.withColumn("name_norm", normalize_name_col("company_name"))
        .withColumn(
            "row_num",
            F.row_number().over(
                Window.partitionBy("name_norm", "prefecture_code").orderBy(
                    F.desc("updated_at")
                )
            ),
        )
        .filter(F.col("row_num") == 1)
        .drop("row_num", "name_norm")
    )

    return deduped_by_corp.unionByName(deduped_by_name, allowMissingColumns=True)


def run(silver_path: str, gold_path: str) -> None:
    spark = create_spark()
    silver_df = spark.read.parquet(silver_path)
    gold_df = resolve_entities(silver_df)
    gold_df.write.mode("overwrite").partitionBy("prefecture_code").parquet(gold_path)
    spark.stop()
