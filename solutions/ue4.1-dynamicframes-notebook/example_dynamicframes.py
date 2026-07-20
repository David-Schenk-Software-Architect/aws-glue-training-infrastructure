"""
Ü4.1 — BEISPIEL/STARTER (Job-Variante): DynamicFrames-Flow als Glue-Job-Skript

Job-Gegenstück zum Notebook `example.ipynb`. Boilerplate (Job.init/commit,
Quelle) steht; die Kern-TODOs baust du selbst. Vergleich danach mit
`solution_dynamicframes.py`.

Job-Parameter: --JOB_NAME (automatisch), --output_path
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

# 1) Quelle — katalogisierte Rohtabelle raw.orders
orders = glue_context.create_dynamic_frame.from_catalog(
    database="raw", table_name="orders", transformation_ctx="orders"
)

# TODO 1: ApplyMapping — "cust id"/"order total"/"order date"/status auf
#         customer_id/order_total(double)/order_date/status mappen -> `mapped`.

# TODO 2: Filter.apply auf status == "shipped"; count() ins Log ausgeben.

# TODO 3: mapped.toDF() -> createOrReplaceTempView("orders") -> spark.sql(
#         "SELECT status, count(*) ... GROUP BY status").show()

# TODO 4: mapped.toDF().write.mode("overwrite").parquet(args["output_path"])

job.commit()
