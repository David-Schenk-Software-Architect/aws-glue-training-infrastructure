"""
Ü-I — Iceberg-Tabelle in Glue erzeugen und im Catalog anlegen

Skeleton mit TODO-Markern. Ziel: die katalogisierte Tabelle `raw.orders` als
Apache-Iceberg-Tabelle nach processed/ schreiben, sodass sie im Glue Data Catalog
als `processed.orders_iceberg` auftaucht und aus Athena abfragbar ist.

Iceberg ist in Glue 5.0 nativ dabei. Im Job-Setup setzen:
  --datalake-formats = iceberg
  --warehouse_path   = s3://gfu-glue-training-629452195361/processed/
"""
import sys

from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.utils import getResolvedOptions
from pyspark.conf import SparkConf
from pyspark.context import SparkContext

args = getResolvedOptions(sys.argv, ["JOB_NAME", "warehouse_path"])
warehouse = args["warehouse_path"].rstrip("/") + "/"
table_location = warehouse + "orders_iceberg"

# TODO 1: Iceberg-Katalog `glue_catalog` über SparkConf verdrahten. Nötig:
#   spark.sql.extensions       = org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions
#   spark.sql.catalog.glue_catalog             = org.apache.iceberg.spark.SparkCatalog
#   spark.sql.catalog.glue_catalog.warehouse   = <warehouse>
#   spark.sql.catalog.glue_catalog.catalog-impl = org.apache.iceberg.aws.glue.GlueCatalog
#   spark.sql.catalog.glue_catalog.io-impl     = org.apache.iceberg.aws.s3.S3FileIO
# Hinweis: spark.sql.extensions MUSS vor dem SparkContext stehen → SparkConf, nicht spark.conf.set.
conf = SparkConf()
# conf.set(...)

sc = SparkContext(conf=conf)
glue_context = GlueContext(sc)
spark = glue_context.spark_session
job = Job(glue_context)
job.init(args["JOB_NAME"], args)

# TODO 2: Iceberg-Tabelle glue_catalog.processed.orders_iceberg anlegen
#   (USING iceberg, LOCATION = table_location, Spalten:
#    customer_id string, order_total double, order_date string, status string).
# spark.sql(""" CREATE TABLE IF NOT EXISTS ... """)

# TODO 3: aus raw.orders befüllen (INSERT INTO ... SELECT ...).
#   Rohspalten heißen "cust id"/"order total"/"order date" (Backticks!),
#   `order total` nach double casten (leere Zelle → NULL).
# spark.sql(""" INSERT INTO ... SELECT ... FROM raw.orders """)

# TODO 4: Zeilenzahl + Snapshots ins Log ausgeben (Beleg).

job.commit()
