"""
Ü5.1 — LÖSUNG: ETL-Job `orders-s3-to-parquet` (S3 → S3)

Kanonischer Glue-ETL-Job des Trainings. Liest die katalogisierte Tabelle
`raw.orders`, bereinigt die "schmutzigen" Spaltennamen (Leerzeichen) und Typen,
schreibt partitioniertes Parquet nach `processed/orders/` und katalogisiert das
Ergebnis als `processed.orders`.

Vergleichsartefakt NACH der Übung: der Teilnehmer baut den Job in Glue Studio
(Visual) selbst und inspiziert den generierten Skript — dieses Skript zeigt, wie
das äquivalente Skript-first-Ergebnis aussieht. Alle späteren Übungen (Ü7.1/7.2
Orchestrierung, Ü8.1 Bookmarks, Ü9.A) bauen auf diesem Job auf.

Voraussetzungen (von der Infrastruktur bereitgestellt):
  - Catalog-DB `raw` mit Tabelle `orders` (Crawler aus Ü3.1)
  - Catalog-DB `processed` (leer, vorab angelegt)
  - IAM-Rolle `AWSGlueServiceRole-GfuGlueTraining`
  - Bucket `gfu-glue-training-629452195361`

Job-Parameter:
  --JOB_NAME        (Glue setzt dies automatisch)
  --output_path     s3://gfu-glue-training-629452195361/processed/orders/
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

# 2) ApplyMapping — schmutzige Spaltennamen bereinigen + Typen setzen.
#    Der Crawler leitet die Spalten mit Leerzeichen ab ("cust id", "order total",
#    "order date"); hier werden sie zu sauberen, typisierten Zielspalten gemappt.
#    "order total" -> double: die leere Zelle (C004) wird korrekt zu NULL.
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

# 3) Senke: partitioniertes Parquet nach processed/orders/ + Katalogisierung als
#    processed.orders. getSink + setCatalogInfo legt die Katalogtabelle an bzw.
#    aktualisiert sie; partitionKeys=["order_date"] erzeugt Hive-Partitionen.
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

job.commit()
