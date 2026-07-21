"""
Ü8.3 — BROKEN: Diagnose-Job `orders-diagnose` (Monitoring-Übung)

Dieser Job SOLL `raw.orders_bad` lesen, den Bestellwert in Cent umrechnen und das
Ergebnis nach `processed/orders_diagnosed/` schreiben. Er tut es nicht. Zwei
Fehler stecken drin, und sie zeigen sich an sehr verschiedenen Orten:

  Runde 1 — der Fehler kommt dir entgegen. Der Job stirbt sofort, der Stacktrace
            steht vollständig im Driver-Log, Job Run Insights nennt dir die
            Skriptzeile. Fixe ihn und starte neu.

  Runde 2 — der Fehler versteckt sich. Der Job läuft an, rechnet eine Weile und
            stirbt dann. Das Driver-Log sagt dir nur, DASS eine Task viermal
            gescheitert ist — nicht warum und nicht an welchem Datensatz. Die
            Antwort liegt in einem anderen Log-Stream.

Nicht spicken: die Auflösung steht in `../README.md`, die korrigierte Fassung in
`../fixed/diagnose_orders.py`. Erst selbst diagnostizieren, dann vergleichen.

Vorgehen (Block 8, Kapitel "Beobachten"):
  Run-Status -> Job Run Insights -> Logs (welcher Stream?) -> Ursache -> Fix.

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

# 2) Spaltennamen mit Leerzeichen bereinigen. "order total" bleibt bewusst
#    string — die Umrechnung passiert unten in der UDF.
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


# 3) Umrechnung in Cent. Eine Python-UDF läuft NICHT im Driver, sondern in den
#    Python-Workern auf den Executors — merk dir das für Runde 2.
@udf(returnType=DoubleType())
def to_cents(raw_value):
    print(f"[worker] rechne order_total um: {raw_value!r}")
    return float(raw_value) * 100.0


sdf = sdf.withColumn("order_total_cents", to_cents(col("order_amount")))

# 4) Nur versendete Bestellungen behalten.
shipped = sdf.filter(col("status") == "shipped")

# 5) Senke: Parquet nach output_path + Katalogisierung als
#    processed.orders_diagnosed.
from awsglue.dynamicframe import DynamicFrame  # noqa: E402

out = DynamicFrame.fromDF(shipped, glue_context, "out_orders_diagnosed")

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
