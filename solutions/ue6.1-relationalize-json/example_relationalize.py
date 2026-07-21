"""
Ü6.1 — (Job-Variante): Verschachteltes JSON relationalisieren

Job-Gegenstück zu `example.ipynb`. Quelle + Boilerplate stehen; resolveChoice,
Relationalize, Frame-Auswahl und Parquet-Write baust du selbst.

Job-Parameter: --JOB_NAME (automatisch), --output_path, --staging_path
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

# 1) Quelle — geschachteltes JSON raw.customers
customers = glue_context.create_dynamic_frame.from_catalog(
    database="raw", table_name="customers", transformation_ctx="customers"
)
customers.printSchema()

# TODO 1: customers.resolveChoice(specs=[("loyalty_points", "cast:string")]) -> resolved

# TODO 2: resolved.relationalize(root_table_name="customers",
#         staging_path=args["staging_path"]) -> frames; frames.keys() ausgeben

# TODO 3: frames.select("customers") und frames.select("customers_contacts")

# TODO 4: root und contacts je in einer eigenen Senke schreiben — getSink +
#         setCatalogInfo(catalogDatabase="processed", catalogTableName=...) mit
#         enableUpdateCatalog=True, setFormat("glueparquet"), writeFrame(...).
#         Pfade: <output_path>/customers_root/ bzw. /customers_contacts/.
#         So landet jede Tabelle als Parquet in S3 UND direkt im Data Catalog.

job.commit()
