"""
Ü4.1 — LÖSUNG (Job-Variante): DynamicFrames-Flow als Glue-Job-Skript

Dieselbe Verarbeitung wie das Notebook `solution.ipynb`, aber als submit-fähiges
Glue-Job-Skript: raw.orders lesen → ApplyMapping → Filter (status == "shipped")
→ toDF()/Spark-SQL-Aggregation → Parquet nach processed/orders_nb/ schreiben.

Job vs. Notebook: der Job kapselt den Flow in Job.init/commit und liest Pfade
über --output_path statt einer Notebook-Konstante; show()/Aggregation landen im
CloudWatch-Log des Runs statt inline.

Voraussetzungen: Catalog-DB raw mit Tabelle orders (Crawler Ü3.1), Rolle
AWSGlueServiceRole-GfuGlueTraining, Bucket gfu-glue-training-629452195361.

Job-Parameter:
  --JOB_NAME      (Glue setzt dies automatisch)
  --output_path   s3://gfu-glue-training-629452195361/processed/orders_nb/
Glue-Version: 5.0   Worker: G.1X
"""
import sys

from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.transforms import ApplyMapping, Filter
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext

args = getResolvedOptions(sys.argv, ["JOB_NAME", "output_path"])

sc = SparkContext()
glue_context = GlueContext(sc)
spark = glue_context.spark_session
job = Job(glue_context)
job.init(args["JOB_NAME"], args)

# 1) Lesen — DynamicFrame aus dem Katalog
orders = glue_context.create_dynamic_frame.from_catalog(
    database="raw", table_name="orders", transformation_ctx="orders"
)

# 2) ApplyMapping — schmutzige Spaltennamen (mit Leerzeichen) bereinigen + Typen
mapped = ApplyMapping.apply(
    frame=orders,
    mappings=[
        ("cust id", "string", "customer_id", "string"),
        ("order total", "string", "order_total", "double"),
        ("order date", "string", "order_date", "string"),
        ("status", "string", "status", "string"),
    ],
    transformation_ctx="mapped",
)

# 3) Filter — nur exakt "shipped" (C002 "shipped, partial" faellt bewusst raus)
shipped = Filter.apply(frame=mapped, f=lambda row: row["status"] == "shipped")
print("shipped rows:", shipped.count())

# 4) toDF + Spark SQL — Aggregation nach status (Ausgabe ins Run-Log)
df = mapped.toDF()
df.createOrReplaceTempView("orders")
spark.sql(
    "SELECT status, count(*) AS n, round(sum(order_total), 2) AS total "
    "FROM orders GROUP BY status ORDER BY n DESC"
).show(truncate=False)

# 5) Parquet schreiben (eigener Prefix, kollidiert nicht mit dem Ü5.1-Output)
df.write.mode("overwrite").parquet(args["output_path"])
print("geschrieben nach", args["output_path"])

job.commit()
