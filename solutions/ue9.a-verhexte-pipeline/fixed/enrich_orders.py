"""
Ü9.A — FIXED: End-to-End-Pipeline orders × customers (Referenzlösung)

Angereicherte Bestellungen: liest `raw.orders` und `raw.customers`, bereinigt die
Order-Spalten, vereinheitlicht den mischtypigen `loyalty_points`, filtert auf
versendete Bestellungen, joint Kundendaten hinzu und schreibt Parquet nach
`processed/orders_enriched/`.

Dies ist die korrekte Fassung. Die 5 eingebauten Fehler der `broken/`-Pipeline sind
hier behoben — Details in `../README.md` (Bug ↔ Symptom ↔ Fix). Drei der Fehler
sind Code (hier gefixt), zwei sind Umgebung (Crawler-SerDe, IAM — siehe README).

Job-Parameter: --JOB_NAME (automatisch), --output_path
  z. B. s3://gfu-glue-training-629452195361/processed/orders_enriched/
Glue-Version: 5.0
"""
import sys

from awsglue.context import GlueContext
from awsglue.dynamicframe import DynamicFrame
from awsglue.job import Job
from awsglue.transforms import ApplyMapping
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext

args = getResolvedOptions(sys.argv, ["JOB_NAME", "output_path"])

sc = SparkContext()
glue_context = GlueContext(sc)
job = Job(glue_context)
job.init(args["JOB_NAME"], args)

# Orders — mit transformation_ctx (Fix Bug 2) und sauberem Mapping.
orders = glue_context.create_dynamic_frame.from_catalog(
    database="raw", table_name="orders", transformation_ctx="src_orders"
)
orders = ApplyMapping.apply(
    frame=orders,
    mappings=[
        ("cust id", "string", "customer_id", "string"),
        ("order total", "string", "order_total", "double"),
        ("order date", "string", "order_date", "string"),
        ("status", "string", "status", "string"),
    ],
    transformation_ctx="map_orders",
)

# Customers — resolveChoice vereinheitlicht loyalty_points (Fix Bug 3).
customers = glue_context.create_dynamic_frame.from_catalog(
    database="raw", table_name="customers", transformation_ctx="src_customers"
)
customers = customers.resolveChoice(specs=[("loyalty_points", "cast:string")])

odf = orders.toDF()
cdf = customers.toDF().select("customer_id", "name", "loyalty_points")

# Filter auf "shipped" — exakt wie in den Daten geschrieben (Fix Bug 4:
# kleingeschrieben, nicht "Shipped").
shipped = odf.filter(odf.status == "shipped")

enriched = shipped.join(cdf, on="customer_id", how="left")

# Schreiben über den Data Catalog (Glue-Standard): DataFrame -> DynamicFrame, dann
# getSink + setCatalogInfo. Schreibt Parquet nach output_path UND legt/aktualisiert die
# Katalogtabelle processed.orders_enriched (enableUpdateCatalog) — kein separater Crawler.
enriched_dyf = DynamicFrame.fromDF(enriched, glue_context, "enriched")
sink = glue_context.getSink(
    path=args["output_path"],
    connection_type="s3",
    updateBehavior="UPDATE_IN_DATABASE",
    partitionKeys=[],
    enableUpdateCatalog=True,
    transformation_ctx="sink_enriched",
)
sink.setCatalogInfo(catalogDatabase="processed", catalogTableName="orders_enriched")
sink.setFormat("glueparquet")
sink.writeFrame(enriched_dyf)
print("enriched rows:", enriched.count())

job.commit()
