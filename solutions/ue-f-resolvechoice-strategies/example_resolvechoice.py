"""
Ü-F — BEISPIEL/STARTER (Job-Variante): ResolveChoice, die vier Strategien

Job-Gegenstück zu `example.ipynb`. Die Quelle steht; setz die vier
ResolveChoice-Strategien an den TODO-Stellen und vergleiche die Schemata im
Run-Log. Vergleich danach mit `solution_resolvechoice.py`.

Job-Parameter: --JOB_NAME (automatisch), --input_path
Glue-Version: 5.0   Worker: G.1X
"""
import sys

from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.transforms import ResolveChoice
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext

args = getResolvedOptions(sys.argv, ["JOB_NAME", "input_path"])

sc = SparkContext()
glue_context = GlueContext(sc)
job = Job(glue_context)
job.init(args["JOB_NAME"], args)

# 0) Rohzustand — customers.json direkt per S3-Pfad lesen (kein Katalog nötig)
customers = glue_context.create_dynamic_frame.from_options(
    connection_type="s3",
    connection_options={"paths": [args["input_path"]]},
    format="json",
    transformation_ctx="customers",
)
customers.printSchema()  # loyalty_points: choice<long,string> erwarten

# TODO 1: cast:long   — ResolveChoice.apply(specs=[("loyalty_points", "cast:long")])
# TODO 2: make_cols   — specs=[("loyalty_points", "make_cols")]
# TODO 3: make_struct — specs=[("loyalty_points", "make_struct")]
# TODO 4: project:long— specs=[("loyalty_points", "project:long")]
# Nach jeder Strategie printSchema() + toDF().show() und die Schemata vergleichen:
# wann geht "gold" verloren (cast/project), wann bleibt es (make_cols/make_struct)?

job.commit()
