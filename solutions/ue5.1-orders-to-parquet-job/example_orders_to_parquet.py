"""
Ü5.1 — ETL-Job `orders-s3-to-parquet` (S3 → S3)

Skelett zum Selbermachen. Der Boilerplate (Imports, GlueContext, Job-Init/Commit,
Quelle) steht; die drei Kern-TODOs baust du selbst:
  TODO 1 — Mapping der schmutzigen Spaltennamen auf saubere, typisierte Spalten
  TODO 2 — Senke: partitioniertes Parquet + Katalogisierung als processed.orders

Job-Parameter: --JOB_NAME (automatisch), --output_path
Glue-Version: 5.0   Worker: G.1X
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

# 1) Quelle: katalogisierte Rohtabelle raw.orders
source = glue_context.create_dynamic_frame.from_catalog(
    database="raw",
    table_name="orders",
    transformation_ctx="source_orders",
)

# TODO 1: ApplyMapping — die Rohspalten heißen "cust id", "order total",
#         "order date", "status" (mit Leerzeichen!). Mappe sie auf
#         customer_id (string), order_total (double), order_date (string),
#         status (string). Denk an transformation_ctx.
# mapped = ApplyMapping.apply(
#     frame=source,
#     mappings=[ ... ],
#     transformation_ctx="mapped_orders",
# )

# TODO 2: Senke — schreibe `mapped` als partitioniertes Parquet nach
#         args["output_path"], partitioniert nach order_date, und katalogisiere
#         es als processed.orders. Tipp: glue_context.getSink(...) +
#         sink.setCatalogInfo(catalogDatabase="processed", catalogTableName="orders")
#         + sink.setFormat("glueparquet") + sink.writeFrame(mapped).

job.commit()
