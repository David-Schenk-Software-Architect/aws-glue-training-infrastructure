"""
Ü6.1 — LÖSUNG (Job-Variante): Verschachteltes JSON relationalisieren

Job-Gegenstück zum Notebook `solution.ipynb`: raw.customers lesen (geschachtelt),
loyalty_points (mischtypig) mit resolveChoice(cast:string) vereinheitlichen, mit
Relationalize in Root + contacts-Child zerlegen und beide als Parquet schreiben.

Voraussetzungen: Catalog-DB raw mit Tabelle customers (Crawler), Rolle
AWSGlueServiceRole-GfuGlueTraining, Bucket gfu-glue-training-<account>.

Job-Parameter:
  --JOB_NAME       (automatisch)
  --output_path    s3://gfu-glue-training-<account>/processed/   (Basis-Prefix)
  --staging_path   s3://gfu-glue-training-<account>/temp/relationalize/
Glue-Version: 5.0   Worker: G.1X
"""
import sys

from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext

args = getResolvedOptions(sys.argv, ["JOB_NAME", "output_path", "staging_path"])

sc = SparkContext()
glue_context = GlueContext(sc)
job = Job(glue_context)
job.init(args["JOB_NAME"], args)

# 1) Lesen — geschachteltes JSON aus dem Katalog
customers = glue_context.create_dynamic_frame.from_catalog(
    database="raw", table_name="customers", transformation_ctx="customers"
)
customers.printSchema()  # loyalty_points als choice<long,string> sichtbar

# 2) resolveChoice — loyalty_points verlustfrei auf string vereinheitlichen
resolved = customers.resolveChoice(specs=[("loyalty_points", "cast:string")])

# 3) Relationalize — geschachteltes Dokument in flache Frames (Root + contacts)
frames = resolved.relationalize(
    root_table_name="customers", staging_path=args["staging_path"]
)
print("erzeugte Frames:", frames.keys())

# 4) Root- und Child-Frame herausgreifen
root = frames.select("customers")
contacts = frames.select("customers_contacts")

# 5) Beide als Parquet schreiben
base = args["output_path"].rstrip("/") + "/"
root.toDF().write.mode("overwrite").parquet(base + "customers_root/")
contacts.toDF().write.mode("overwrite").parquet(base + "customers_contacts/")
print("root rows:", root.count(), "| contacts rows:", contacts.count())

job.commit()
