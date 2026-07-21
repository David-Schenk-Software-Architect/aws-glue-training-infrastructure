"""
Ü8.3 — FIXED: Diagnose-Job `orders-diagnose` (Referenzlösung)

Liest `raw.orders_bad`, rechnet den Bestellwert in Cent um, filtert auf
versendete Bestellungen und schreibt Parquet nach `processed/orders_diagnosed/`.

Dies ist die korrigierte Fassung. Die zwei Fehler der `broken/`-Variante sind
hier behoben — Details in `../README.md` (Bug <-> Symptom <-> Fundort <-> Fix):

  Bug 1 (Driver):   `col("order_amount")` — die Spalte heisst `order_total`.
                    AnalysisException, voller Stacktrace im Driver-Stream.
  Bug 2 (Executor): `float("n/a")` in der UDF. Der Driver meldet nur
                    "Task failed 4 times"; der auslösende Wert steht im
                    Executor-Stream. Hier defensiv geparst statt zu werfen.

Voraussetzungen (von der Infrastruktur bereitgestellt):
  - Catalog-DB `raw` mit Tabelle `orders_bad`
  - Catalog-DB `processed`
  - IAM-Rolle `AWSGlueServiceRole-GfuGlueTraining`

Job-Parameter:
  --JOB_NAME                        (Glue setzt dies automatisch)
  --output_path                     s3://<bucket>/processed/orders_diagnosed/
  --enable-job-insights             true
  --enable-metrics                  true
  --enable-observability-metrics    true
Glue-Version: 5.0   Worker: G.1X
"""
import sys

from awsglue.context import GlueContext
from awsglue.dynamicframe import DynamicFrame
from awsglue.job import Job
from awsglue.transforms import ApplyMapping
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from pyspark.sql.functions import col, udf
from pyspark.sql.types import DoubleType

args = getResolvedOptions(sys.argv, ["JOB_NAME", "output_path"])

sc = SparkContext()
glue_context = GlueContext(sc)
job = Job(glue_context)
job.init(args["JOB_NAME"], args)

# 1) Quelle: katalogisierte Rohtabelle raw.orders_bad
source = glue_context.create_dynamic_frame.from_catalog(
    database="raw",
    table_name="orders_bad",
    transformation_ctx="source_orders_bad",
)

# 2) Spaltennamen mit Leerzeichen bereinigen.
mapped = ApplyMapping.apply(
    frame=source,
    mappings=[
        ("cust id", "string", "customer_id", "string"),
        ("order total", "string", "order_total", "string"),
        ("order date", "string", "order_date", "string"),
        ("status", "string", "status", "string"),
    ],
    transformation_ctx="mapped_orders_bad",
)

sdf = mapped.toDF()


# 3) Umrechnung in Cent (Fix Bug 2: unparsbare Werte werden NULL statt zu werfen).
#    Die UDF läuft in den Python-Workern auf den Executors; alles, was sie
#    ausgibt, landet im Executor-Log-Stream, nicht im Driver-Stream.
@udf(returnType=DoubleType())
def to_cents(raw_value):
    try:
        return float(raw_value) * 100.0
    except (TypeError, ValueError):
        return None


# Fix Bug 1: die Spalte heisst order_total, nicht order_amount.
sdf = sdf.withColumn("order_total_cents", to_cents(col("order_total")))

# 4) Nur versendete Bestellungen behalten.
shipped = sdf.filter(col("status") == "shipped")

out = DynamicFrame.fromDF(shipped, glue_context, "out_orders_diagnosed")

# 5) Senke: Parquet + Katalogisierung als processed.orders_diagnosed.
sink = glue_context.getSink(
    path=args["output_path"],
    connection_type="s3",
    updateBehavior="UPDATE_IN_DATABASE",
    partitionKeys=[],
    enableUpdateCatalog=True,
    transformation_ctx="sink_orders_diagnosed",
)
sink.setCatalogInfo(
    catalogDatabase="processed", catalogTableName="orders_diagnosed"
)
sink.setFormat("glueparquet")
sink.writeFrame(out)

job.commit()
