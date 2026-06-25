# Databricks notebook source
# MAGIC %md
# MAGIC # SalesNow — Activity Delta Detection
# MAGIC
# MAGIC Detects new hiring, funding, and news signals for intent scoring.
# MAGIC Runs daily on Databricks; output to `gold/fact_activity`.

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.sql.window import Window

BRONZE_PATH = "s3://salesnow-data-lake/silver/activities/"
GOLD_PATH = "s3://salesnow-data-lake/gold/fact_activity/"

# COMMAND ----------

activities = spark.read.parquet(BRONZE_PATH)

window = Window.partitionBy("company_id", "activity_type").orderBy(F.desc("activity_date"))
latest = (
    activities.withColumn("row_num", F.row_number().over(window))
    .filter(F.col("row_num") == 1)
    .drop("row_num")
)

deltas = latest.filter(
    F.col("activity_date") >= F.date_sub(F.current_date(), 1)
).withColumn("signal_strength", F.lit(1.0))

deltas.write.mode("append").partitionBy("activity_type").parquet(GOLD_PATH)

# COMMAND ----------

display(deltas.groupBy("activity_type").count())
