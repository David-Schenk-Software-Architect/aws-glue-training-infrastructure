"""
Ü6.1 — LÖSUNG (Job-Variante): Verschachteltes JSON relationalisieren

Job-Gegenstück zum Notebook `solution.ipynb`: raw.customers lesen (geschachtelt),
loyalty_points (mischtypig) mit resolveChoice(cast:string) vereinheitlichen, mit
Relationalize in Root + contacts-Child zerlegen und beide als Parquet schreiben.

Voraussetzungen: Catalog-DB raw mit Tabelle customers (Crawler), Rolle
AWSGlueServiceRole-GfuGlueTraining, Bucket gfu-glue-training-629452195361.

Job-Parameter:
  --JOB_NAME       (automatisch)
  --output_path    s3://gfu-glue-training-629452195361/processed/   (Basis-Prefix)
  --staging_path   s3://gfu-glue-training-629452195361/temp/relationalize/
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

# 5) Beide schreiben — Parquet nach processed/ UND direkt als Katalogtabelle.
#    getSink + setCatalogInfo (enableUpdateCatalog) legt processed.customers_root
#    bzw. processed.customers_contacts an/aktualisiert sie — kein Crawler nötig.
base = args["output_path"].rstrip("/") + "/"

sink_root = glue_context.getSink(
    path=base + "customers_root/",
    connection_type="s3",
    updateBehavior="UPDATE_IN_DATABASE",
    partitionKeys=[],
    enableUpdateCatalog=True,
    transformation_ctx="sink_root",
)
sink_root.setCatalogInfo(catalogDatabase="processed", catalogTableName="customers_root")
sink_root.setFormat("glueparquet")
sink_root.writeFrame(root)

sink_contacts = glue_context.getSink(
    path=base + "customers_contacts/",
    connection_type="s3",
    updateBehavior="UPDATE_IN_DATABASE",
    partitionKeys=[],
    enableUpdateCatalog=True,
    transformation_ctx="sink_contacts",
)
sink_contacts.setCatalogInfo(catalogDatabase="processed", catalogTableName="customers_contacts")
sink_contacts.setFormat("glueparquet")
sink_contacts.writeFrame(contacts)
print("root rows:", root.count(), "| contacts rows:", contacts.count())

job.commit()
