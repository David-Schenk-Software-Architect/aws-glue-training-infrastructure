"""
Ü8.1 — LÖSUNG: `orders-s3-to-parquet` inkrementell (Job Bookmark + Monitoring)

Die Bookmark-Variante des Ü5.1-Jobs. Fachlich identisch, aber so aufgesetzt, dass
wiederholte Läufe nur NEUE Dateien verarbeiten. Der Schlüssel ist `transformation_ctx`
auf Quelle und Senke — Glue nutzt diese stabilen IDs, um pro Job den Bookmark-Stand
(bereits gelesene S3-Objekte) zu führen.

Ablauf der Übung:
  1. Job mit den Parametern unten anlegen und EINMAL laufen lassen (verarbeitet
     orders.csv). 2. `seed/orders_2.csv` nach `raw/orders/` kopieren. 3. Job erneut
     laufen lassen — nur orders_2.csv wird verarbeitet (Bookmark überspringt orders.csv).

Job-Parameter (in Glue Studio unter "Job details" / "Job parameters" setzen):
  --job-bookmark-option        job-bookmark-enable      (Bookmark aktivieren)
  --enable-continuous-cloudwatch-log   true             (Continuous Logging)
  --enable-metrics             true                     (Observability-Metriken)
  --output_path                s3://gfu-glue-training-629452195361/processed/orders/
  --JOB_NAME                   (Glue setzt dies automatisch)
Glue-Version: 5.0   Worker: G.1X

Hinweis: Bookmark zurücksetzen (für erneutes Vollverarbeiten) via Glue-Konsole
"Reset job bookmark" oder `aws glue reset-job-bookmark --job-name <name>`.
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

# Quelle mit transformation_ctx="source_orders" — DIESE ID traegt den Bookmark.
# Ohne transformation_ctx wuerde der Bookmark nicht greifen und jeder Lauf
# verarbeitet alles neu.
source = glue_context.create_dynamic_frame.from_catalog(
    database="raw",
    table_name="orders",
    transformation_ctx="source_orders",
)

mapped = ApplyMapping.apply(
    frame=source,
    mappings=[
        ("cust id", "string", "customer_id", "string"),
        ("order total", "string", "order_total", "double"),
        ("order date", "string", "order_date", "string"),
        ("status", "string", "status", "string"),
    ],
    transformation_ctx="mapped_orders",
)

# Senke ebenfalls mit stabilem transformation_ctx="sink_orders".
sink = glue_context.getSink(
    path=args["output_path"],
    connection_type="s3",
    updateBehavior="UPDATE_IN_DATABASE",
    partitionKeys=["order_date"],
    enableUpdateCatalog=True,
    transformation_ctx="sink_orders",
)
sink.setCatalogInfo(catalogDatabase="processed", catalogTableName="orders")
sink.setFormat("glueparquet")
sink.writeFrame(mapped)

job.commit()  # commit() persistiert auch den Bookmark-Stand fuer den naechsten Lauf.
