"""
Ü-G — LÖSUNG (Job-Variante): DynamoDB nativ schreiben & zurücklesen

Job-Gegenstück zum Notebook `solution.ipynb`. raw.orders × customers.json
angereichert, je Kunde eine Zeile (Hash-Key customer_id eindeutig) nativ nach
DynamoDB geschrieben und per Scan-API zurückgelesen.

Voraussetzungen: enable_dynamodb (default an) + DynamoDB-Rechte der Glue-Rolle;
Tabelle gfu-glue-training-orders-enriched (hash_key customer_id, PAY_PER_REQUEST);
Catalog-DB raw mit orders; customers.json unter raw/customers/.

Job-Parameter:
  --JOB_NAME         (automatisch)
  --customers_path   s3://gfu-glue-training-<account>/raw/customers/
  --ddb_table        gfu-glue-training-orders-enriched
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

# 1) Quellen lesen & je Kunde eine Zeile bilden
orders = glue_context.create_dynamic_frame.from_catalog(
    database="raw", table_name="orders", transformation_ctx="orders"
).toDF()
customers = glue_context.create_dynamic_frame.from_options(
    connection_type="s3",
    connection_options={"paths": [args["customers_path"]]},
    format="json", transformation_ctx="customers",
).toDF()

# Rohspalten haben Leerzeichen -> sauber benennen/casten
o = orders.selectExpr(
    "`cust id` AS customer_id",
    "CAST(`order total` AS double) AS order_total",
    "`order date` AS order_date",
)
# je Kunde die letzte Bestellung (Hash-Key muss eindeutig sein)
w = Window.partitionBy("customer_id").orderBy(col("order_date").desc())
latest = o.withColumn("rn", row_number().over(w)).filter(col("rn") == 1).drop("rn")
enriched = latest.join(
    customers.select(col("customer_id"), col("name"), col("address.city").alias("city")),
    "customer_id", "left",
)

# 2) Nach DynamoDB schreiben (nativ). Attribute als String = robust fuers Demo.
enriched_str = enriched.selectExpr(
    "CAST(customer_id AS string) customer_id",
    "CAST(order_total AS string) order_total",
    "CAST(order_date AS string) order_date",
    "CAST(name AS string) name", "CAST(city AS string) city",
)
dyf = DynamicFrame.fromDF(enriched_str, glue_context, "dyf")
glue_context.write_dynamic_frame.from_options(
    frame=dyf,
    connection_type="dynamodb",
    connection_options={
        "dynamodb.output.tableName": args["ddb_table"],
        "dynamodb.throughput.write.percent": "1.0",
    },
)
print("geschrieben nach", args["ddb_table"])

# 3) Aus DynamoDB zurücklesen (Scan-API)
back = glue_context.create_dynamic_frame.from_options(
    connection_type="dynamodb",
    connection_options={
        "dynamodb.input.tableName": args["ddb_table"],
        "dynamodb.throughput.read.percent": "1.0",
    },
    transformation_ctx="back",
)
back.printSchema()
back.toDF().show(truncate=False)

job.commit()
