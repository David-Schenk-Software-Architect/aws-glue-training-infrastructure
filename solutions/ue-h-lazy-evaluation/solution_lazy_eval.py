"""
Ü-H — LÖSUNG (Job-Variante): Lazy Evaluation, die zwei Fallen

Job-Gegenstück zum Notebook `solution.ipynb`. HINWEIS: Diese Übung lebt von den
sichtbaren UDF-Markern — im Notebook erscheinen sie inline pro Aktion. Als Job
landen die print()-Marker im CloudWatch-Log des Runs (und laufen über Executors
verteilt); die Notebook-Variante zeigt den Effekt didaktisch klarer.

Falle 1: zwei Aktionen ohne cache rechnen die Lineage doppelt. Falle 2: eine
Transformation ohne Aktion tut nichts (kein Write, kein Fehler).

Voraussetzung: Catalog-DB raw mit Tabelle orders.

Job-Parameter: --JOB_NAME (automatisch)
Glue-Version: 5.0   Worker: G.1X
"""
import sys

from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from pyspark.sql.functions import col, udf
from pyspark.sql.types import DoubleType

args = getResolvedOptions(sys.argv, ["JOB_NAME"])

sc = SparkContext()
glue_context = GlueContext(sc)
job = Job(glue_context)
job.init(args["JOB_NAME"], args)

orders = glue_context.create_dynamic_frame.from_catalog(
    database="raw", table_name="orders", transformation_ctx="orders"
).toDF()


@udf(DoubleType())
def traced_double(x):
    print("  >> UDF berechnet eine Zeile")   # Seiteneffekt = Zaehl-Marker
    return float(x) if x else 0.0


df = orders.withColumn("total", traced_double(col("order total")))

# Falle 1 — Neuberechnung ohne cache: zwei Aktionen -> Marker erscheinen zweimal
print("Aktion 1: count()")
df.count()
print("Aktion 2: show() -> Marker erscheinen ERNEUT (Neuberechnung)")
df.show()

# Fix — cache() + materialisieren; die zweite Aktion liest aus dem Speicher
df.cache()
print("Materialisieren (1. Aktion, fuellt den Cache):")
df.count()
print("2. Aktion aus dem Cache -> KEINE Marker:")
df.show()

# Falle 2 — Transformation ohne Aktion tut nichts (kein Fehler)
print("nur Transformationen aufbauen ... (keine Arbeit)")
filtered = df.filter(col("total") > 100)
print("Plan steht, aber nichts lief. Erst die Aktion zaehlt:")
print("Treffer:", filtered.count())

# Übertrag: write IST eine Aktion; job.commit() ist KEINE Spark-Aktion, aber der
# Abschluss, der Bookmarks fortschreibt (siehe Ü8.1).
job.commit()
