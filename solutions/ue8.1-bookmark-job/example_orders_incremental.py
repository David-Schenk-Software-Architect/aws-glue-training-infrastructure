"""
Ü8.1 — `orders-s3-to-parquet` inkrementell machen

Ausgangspunkt ist dein fertiger Ü5.1-Job. Aufgabe: ihn inkrementell machen, sodass
wiederholte Läufe nur neue Dateien verarbeiten. Zwei Baustellen:
  TODO 1 — `transformation_ctx` auf Quelle, Mapping und Senke setzen (das ist der
           Bookmark-Schlüssel; ohne ihn greift der Bookmark nicht).
  TODO 2 — beim Anlegen des Jobs die Parameter setzen (siehe unten).

Job-Parameter, die du in Glue Studio setzen musst:
  --job-bookmark-option                 job-bookmark-enable
  --enable-continuous-cloudwatch-log    true
  --enable-metrics                      true
  --output_path                         s3://gfu-glue-training-629452195361/processed/orders/

Test: 1x laufen lassen → `seed/orders_2.csv` nach `raw/orders/` kopieren → erneut
laufen lassen → prüfen, dass nur orders_2.csv verarbeitet wurde (CloudWatch/Metriken).
Glue-Version: 5.0
"""
import sys

from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.transforms import ApplyMapping
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext

args = getResolvedOptions(sys.argv, ["JOB_NAME", "output_path"])

sc = SparkContext()
glue_context = GlueContext(sc)
job = Job(glue_context)
job.init(args["JOB_NAME"], args)

# TODO 1a: transformation_ctx="source_orders" ergaenzen.
source = glue_context.create_dynamic_frame.from_catalog(
    database="raw",
    table_name="orders",
)

# TODO 1b: transformation_ctx="mapped_orders" ergaenzen.
mapped = ApplyMapping.apply(
    frame=source,
    mappings=[
        ("cust id", "string", "customer_id", "string"),
        ("order total", "string", "order_total", "double"),
        ("order date", "string", "order_date", "string"),
        ("status", "string", "status", "string"),
    ],
)

# TODO 1c: transformation_ctx="sink_orders" ergaenzen.
sink = glue_context.getSink(
    path=args["output_path"],
    connection_type="s3",
    updateBehavior="UPDATE_IN_DATABASE",
    partitionKeys=["order_date"],
    enableUpdateCatalog=True,
)
sink.setCatalogInfo(catalogDatabase="processed", catalogTableName="orders")
sink.setFormat("glueparquet")
sink.writeFrame(mapped)

job.commit()
