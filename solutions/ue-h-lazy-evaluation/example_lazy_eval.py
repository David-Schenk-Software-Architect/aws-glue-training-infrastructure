"""
Ü-H — BEISPIEL/STARTER (Job-Variante): Lazy Evaluation, die zwei Fallen

Job-Gegenstück zu `example.ipynb`. Falle 1 (Neuberechnung) steht; ergänze den
cache()-Fix und beobachte, dass die UDF-Marker im Run-Log dann nur einmal
erscheinen. Vergleich danach mit `solution_lazy_eval.py`.

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

# TODO Fix: df.cache() setzen, mit einer ersten Aktion (count) materialisieren,
#           dann zweite Aktion (show) -> im Run-Log KEINE Marker mehr.

# Falle 2 — Transformation ohne Aktion tut nichts (kein Fehler)
print("nur Transformationen aufbauen ... (keine Arbeit)")
filtered = df.filter(col("total") > 100)
print("Plan steht, aber nichts lief. Erst die Aktion zaehlt:")
print("Treffer:", filtered.count())

job.commit()
