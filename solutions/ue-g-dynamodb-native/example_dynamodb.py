"""
Ü-G — (Job-Variante): DynamoDB nativ schreiben & zurücklesen

Job-Gegenstück zu `example.ipynb`. Anreicherung + Boilerplate stehen; den
nativen DynamoDB-Write und den Scan-Read baust du an den TODO-Stellen.

Job-Parameter: --JOB_NAME (automatisch), --customers_path, --ddb_table
Glue-Version: 5.0   Worker: G.1X
"""
import sys

from awsglue.context import GlueContext
from awsglue.dynamicframe import DynamicFrame
from awsglue.job import Job
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from pyspark.sql.functions import col, row_number
from pyspark.sql.window import Window

args = getResolvedOptions(sys.argv, ["JOB_NAME", "customers_path", "ddb_table"])

sc = SparkContext()
glue_context = GlueContext(sc)
job = Job(glue_context)
job.init(args["JOB_NAME"], args)

# 1) Quellen lesen & je Kunde eine Zeile bilden (Hash-Key eindeutig)
orders = glue_context.create_dynamic_frame.from_catalog(
    database="raw", table_name="orders", transformation_ctx="orders"
).toDF()
customers = glue_context.create_dynamic_frame.from_options(
    connection_type="s3",
    connection_options={"paths": [args["customers_path"]]},
    format="json", transformation_ctx="customers",
).toDF()

o = orders.selectExpr(
    "`cust id` AS customer_id",
    "CAST(`order total` AS double) AS order_total",
    "`order date` AS order_date",
)
w = Window.partitionBy("customer_id").orderBy(col("order_date").desc())
latest = o.withColumn("rn", row_number().over(w)).filter(col("rn") == 1).drop("rn")
enriched = latest.join(
    customers.select(col("customer_id"), col("name"), col("address.city").alias("city")),
    "customer_id", "left",
)
enriched_str = enriched.selectExpr(
    "CAST(customer_id AS string) customer_id",
    "CAST(order_total AS string) order_total",
    "CAST(order_date AS string) order_date",
    "CAST(name AS string) name", "CAST(city AS string) city",
)
dyf = DynamicFrame.fromDF(enriched_str, glue_context, "dyf")

# TODO 1: nativ nach DynamoDB schreiben —
#         glue_context.write_dynamic_frame.from_options(frame=dyf,
#         connection_type="dynamodb",
#         connection_options={"dynamodb.output.tableName": args["ddb_table"],
#                             "dynamodb.throughput.write.percent": "1.0"})

# TODO 2: per Scan-API zurücklesen —
#         glue_context.create_dynamic_frame.from_options(connection_type="dynamodb",
#         connection_options={"dynamodb.input.tableName": args["ddb_table"],
#                             "dynamodb.throughput.read.percent": "1.0"})
#         -> printSchema() + toDF().show()

job.commit()
