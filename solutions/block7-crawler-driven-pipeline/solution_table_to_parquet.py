"""
Folie 7.8 (Abb. 17) — Referenz-Job der crawler-gesteuerten State Machine

Generischer Tabelle-zu-Parquet-Job: liest `raw.<table>` aus dem Data Catalog und
schreibt sie als Parquet nach `<output_root><table>/`, katalogisiert als
`processed.<table>`. Die Tabelle kommt zur Laufzeit als `--table` herein — die
Step-Functions-Map (`ref-crawler-pipeline-solution`) startet je gefundener
Tabelle einen Lauf dieses einen Jobs.

Kein Übungsartefakt: Vergleichs-/Vorführmaterial zur Folie, kein Ü-Skript.

Bewusst OHNE ApplyMapping und OHNE partitionKeys — beides setzt ein bekanntes
Schema voraus. Dieser Job muss für JEDE Tabelle laufen, die der Crawler findet
(orders wie customers), deshalb bleibt das Schema so, wie der Crawler es
abgeleitet hat. Die Spaltenbereinigung ist Thema von Ü5.1
(`solution_orders_to_parquet.py`), nicht hier.

resolveChoice ist dagegen nicht optional: `customers.loyalty_points` ist
mischtypig (1200 vs. "gold") und der Crawler leitet daraus einen `choice`-Typ ab,
den der Parquet-Writer nicht schreiben kann.

Voraussetzungen (von der Infrastruktur bereitgestellt):
  - Catalog-DB `raw` mit den vom Crawler katalogisierten Tabellen
  - Catalog-DB `processed` (leer, vorab angelegt)
  - IAM-Rolle `AWSGlueServiceRole-GfuGlueTraining`

Job-Parameter:
  --JOB_NAME        (Glue setzt dies automatisch)
  --table           orders | customers | …   (aus der Map)
  --output_root     s3://gfu-glue-training-<account>/processed/
Glue-Version: 5.0   Worker: G.1X
"""
import sys

from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext

args = getResolvedOptions(sys.argv, ["JOB_NAME", "table", "output_root"])

sc = SparkContext()
glue_context = GlueContext(sc)
job = Job(glue_context)
job.init(args["JOB_NAME"], args)

table = args["table"]

# 1) Quelle: die katalogisierte Rohtabelle, deren Name aus der Map kommt.
source = glue_context.create_dynamic_frame.from_catalog(
    database="raw",
    table_name=table,
    transformation_ctx=f"source_{table}",
)

# 2) Mischtypen auflösen. make_struct legt beide Varianten als Unterfelder ab —
#    die einzige Strategie, die ohne Schema-Wissen nichts wegwirft.
resolved = source.resolveChoice(choice="make_struct")

# 3) Senke: Parquet nach processed/<table>/ + Katalogisierung als processed.<table>.
sink = glue_context.getSink(
    path=f"{args['output_root']}{table}/",
    connection_type="s3",
    updateBehavior="UPDATE_IN_DATABASE",
    enableUpdateCatalog=True,
    transformation_ctx=f"sink_{table}",
)
sink.setCatalogInfo(catalogDatabase="processed", catalogTableName=table)
sink.setFormat("glueparquet")
sink.writeFrame(resolved)

job.commit()
