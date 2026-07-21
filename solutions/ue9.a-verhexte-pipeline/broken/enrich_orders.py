"""
Ü9.A — BROKEN: End-to-End-Pipeline orders × customers (Debugging-Challenge)

Diese Pipeline SOLL angereicherte, versendete Bestellungen nach
`processed/orders_enriched/` schreiben — tut es aber nicht korrekt. Sie enthält
absichtlich eingebaute Fehler (Code + Umgebung). Deine Aufgabe: diagnostizieren,
Root-Cause benennen, reparieren.

Nicht spicken: die Auflösung steht in `../README.md` und die korrigierte Fassung in
`../fixed/enrich_orders.py`. Erst selbst debuggen, dann vergleichen.

Symptome, die du beobachten wirst: leere/kaputte Ausgabe, Schema-Überraschung bei
den Kundendaten, und (je nach Umgebung) ein Fehler beim Schreiben.

Job-Parameter: --JOB_NAME (automatisch), --output_path
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

orders = glue_context.create_dynamic_frame.from_catalog(
    database="raw", table_name="orders"
)
orders = ApplyMapping.apply(
    frame=orders,
    mappings=[
        ("cust id", "string", "customer_id", "string"),
        ("order total", "string", "order_total", "double"),
        ("order date", "string", "order_date", "string"),
        ("status", "string", "status", "string"),
    ],
)

customers = glue_context.create_dynamic_frame.from_catalog(
    database="raw", table_name="customers"
)

odf = orders.toDF()
cdf = customers.toDF().select("customer_id", "name", "loyalty_points")

shipped = odf.filter(odf.status == "Shipped")

enriched = shipped.join(cdf, on="customer_id", how="left")

# Schreiben über den Data Catalog: DynamicFrame + getSink schreibt Parquet nach
# output_path und katalogisiert als processed.orders_enriched (enableUpdateCatalog).
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
