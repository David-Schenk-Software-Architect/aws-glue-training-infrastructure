"""
Ü-F — LÖSUNG (Job-Variante): ResolveChoice, die vier Strategien

Job-Gegenstück zum Notebook `solution.ipynb`. loyalty_points in customers.json ist
choice<long,string>; die vier ResolveChoice-Strategien nebeneinander. HINWEIS:
Als Job laufen printSchema()/show() ins CloudWatch-Log des Runs — die
Notebook-Variante zeigt die Schema-Vergleiche inline und ist hier didaktisch klarer.

Voraussetzung: customers.json unter raw/customers/ (kein Katalog/Crawler nötig).

Job-Parameter:
  --JOB_NAME     (automatisch)
  --input_path   s3://gfu-glue-training-<account>/raw/customers/
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

# 0) Rohzustand — der Choice-Typ. Direkt per S3-Pfad lesen, kein Katalog nötig.
customers = glue_context.create_dynamic_frame.from_options(
    connection_type="s3",
    connection_options={"paths": [args["input_path"]]},
    format="json",
    transformation_ctx="customers",
)
customers.printSchema()  # loyalty_points: choice<long,string> erwarten

# 1) cast:long — auf einen Typ zwingen; "gold" wird zu NULL
cast_long = ResolveChoice.apply(
    frame=customers, specs=[("loyalty_points", "cast:long")],
    transformation_ctx="cast_long",
)
cast_long.printSchema()
cast_long.toDF().select("customer_id", "loyalty_points").show()

# 2) make_cols — je Typ eine eigene Spalte (_long und _string)
make_cols = ResolveChoice.apply(
    frame=customers, specs=[("loyalty_points", "make_cols")],
    transformation_ctx="make_cols",
)
make_cols.printSchema()
make_cols.toDF().show()

# 3) make_struct — beide Varianten in einem struct<long,string>
make_struct = ResolveChoice.apply(
    frame=customers, specs=[("loyalty_points", "make_struct")],
    transformation_ctx="make_struct",
)
make_struct.printSchema()
make_struct.toDF().show(truncate=False)

# 4) project:long — nur den long-Ast behalten; "gold" -> NULL
project_long = ResolveChoice.apply(
    frame=customers, specs=[("loyalty_points", "project:long")],
    transformation_ctx="project_long",
)
project_long.printSchema()
project_long.toDF().select("customer_id", "loyalty_points").show()

# Faustregel: kein Datenverlust -> make_cols/make_struct; eindeutiger Zieltyp
# fuers Warehouse -> cast. Ohne resolveChoice bleibt choice<> und ein
# Parquet-Write scheitert.
job.commit()
