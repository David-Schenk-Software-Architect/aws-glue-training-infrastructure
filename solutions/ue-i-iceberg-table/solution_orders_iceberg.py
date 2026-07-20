"""
Ü-I — LÖSUNG: Iceberg-Tabelle in Glue erzeugen und im Catalog anlegen (S3 → Iceberg)

Optionale Vertiefung zu Block 3 (offene Tabellenformate, Slides 3.8–3.12).
Liest die katalogisierte Rohtabelle `raw.orders`, bereinigt die "schmutzigen"
Spaltennamen (Leerzeichen) und Typen und schreibt das Ergebnis als **Apache-
Iceberg**-Tabelle. Über den `GlueCatalog`-Impl registriert sich die Tabelle dabei
automatisch im Glue Data Catalog als `processed.orders_iceberg` — ab da ist sie
direkt aus Athena abfragbar.

Kernpunkt der Übung: NICHT der ETL-Inhalt (der ist wie Ü5.1), sondern das
Format + die Catalog-Anbindung. Iceberg ist in Glue 5.0 nativ dabei; eingeschaltet
wird es über den Job-Parameter --datalake-formats=iceberg. Der named Catalog
`glue_catalog` verbindet Spark SQL mit dem Glue Data Catalog.

Vergleichsartefakt NACH der Übung: der Teilnehmer baut den Job (oder das Notebook)
selbst; dieses Skript zeigt das lauffähige Skript-first-Ergebnis.

Voraussetzungen (von der Infrastruktur bereitgestellt):
  - Catalog-DB `raw` mit Tabelle `orders` (Crawler aus Ü2.1/Ü3.1)
  - Catalog-DB `processed` (leer, vorab angelegt) — hier landet die Iceberg-Tabelle
  - IAM-Rolle `AWSGlueServiceRole-GfuGlueTraining` (S3 R/W + glue:CreateTable/UpdateTable)
  - Bucket `gfu-glue-training-<account>`

Job-Parameter:
  --JOB_NAME          (Glue setzt dies automatisch)
  --warehouse_path    s3://gfu-glue-training-<account>/processed/
  --datalake-formats  iceberg   (lädt die Iceberg-Jars — im Job-Setup setzen!)
Glue-Version: 5.0   Worker: G.1X

Die Iceberg-Katalog-Konfiguration wird hier IM Skript über SparkConf gesetzt
(vor dem SparkContext), damit außer --datalake-formats keine --conf-Parameter im
Job-Setup nötig sind. spark.sql.extensions MUSS vor dem Session-Bau stehen —
deshalb SparkConf und nicht spark.conf.set zur Laufzeit.
"""
import sys

from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.utils import getResolvedOptions
from pyspark.conf import SparkConf
from pyspark.context import SparkContext

args = getResolvedOptions(sys.argv, ["JOB_NAME", "warehouse_path"])
warehouse = args["warehouse_path"].rstrip("/") + "/"
table_location = warehouse + "orders_iceberg"

# 1) Iceberg-Katalog verdrahten. Ein named Catalog `glue_catalog` zeigt über den
#    GlueCatalog-Impl auf den Glue Data Catalog; S3FileIO schreibt die Daten- und
#    Metadaten-Dateien nach S3. spark.sql.extensions aktiviert die Iceberg-SQL-
#    Syntax (MERGE, Time Travel, …) und muss vor dem Session-Bau gesetzt sein.
conf = SparkConf()
conf.set("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions")
conf.set("spark.sql.catalog.glue_catalog", "org.apache.iceberg.spark.SparkCatalog")
conf.set("spark.sql.catalog.glue_catalog.warehouse", warehouse)
conf.set("spark.sql.catalog.glue_catalog.catalog-impl", "org.apache.iceberg.aws.glue.GlueCatalog")
conf.set("spark.sql.catalog.glue_catalog.io-impl", "org.apache.iceberg.aws.s3.S3FileIO")

sc = SparkContext(conf=conf)
glue_context = GlueContext(sc)
spark = glue_context.spark_session
job = Job(glue_context)
job.init(args["JOB_NAME"], args)

# 2) Iceberg-Tabelle anlegen. USING iceberg macht es zu einer Iceberg-Tabelle;
#    LOCATION legt die Dateien unter processed/orders_iceberg/ ab (dort, wo der
#    Trainee ohnehin lesen/schreiben darf). CREATE ... registriert die Tabelle
#    über den GlueCatalog sofort im Data Catalog als processed.orders_iceberg.
#    IF NOT EXISTS macht den Job idempotent (Wiederholung überschreibt nicht).
spark.sql(f"""
    CREATE TABLE IF NOT EXISTS glue_catalog.processed.orders_iceberg (
        customer_id string,
        order_total double,
        order_date  string,
        status      string
    )
    USING iceberg
    LOCATION '{table_location}'
    TBLPROPERTIES ('format-version' = '2')
""")

# 3) Aus raw.orders befüllen. Die Rohspalten heißen "cust id", "order total",
#    "order date" (Leerzeichen → Backticks). CAST("order total" AS double) macht
#    aus der leeren Zelle (C004, C005) korrekt NULL. raw.orders liegt im Glue Data
#    Catalog, also ist es über den Default-Catalog direkt als raw.orders lesbar.
spark.sql("""
    INSERT INTO glue_catalog.processed.orders_iceberg
    SELECT
        `cust id`                    AS customer_id,
        CAST(`order total` AS double) AS order_total,
        `order date`                 AS order_date,
        status                       AS status
    FROM raw.orders
""")

# 4) Beleg im Log: Zeilenzahl + Nachweis, dass es eine Iceberg-Tabelle ist
#    (Provider=iceberg) und dass der erste Snapshot geschrieben wurde.
count = spark.sql("SELECT count(*) AS n FROM glue_catalog.processed.orders_iceberg").collect()[0]["n"]
print("orders_iceberg rows:", count)  # erwartet: 48
print("Snapshots:")
spark.sql("SELECT snapshot_id, operation FROM glue_catalog.processed.orders_iceberg.snapshots").show(truncate=False)

job.commit()
