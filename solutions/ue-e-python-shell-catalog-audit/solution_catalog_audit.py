"""
Ü-E — LÖSUNG: Catalog-Audit als Python-Shell-Job (kein Spark)

Zeigt, dass **nicht jeder Glue-Job Spark braucht**. Ein Python-Shell-Job läuft mit
0.0625 oder 1 DPU (statt eines Spark-Clusters) und eignet sich für leichte
Katalog-/Governance-Aufgaben. Dieser Job inventarisiert den Data Catalog
**nur lesend** und schreibt einen kurzen Report nach S3:

  - listet alle Datenbanken und Tabellen,
  - zählt Partitionen je Tabelle,
  - prüft je Tabelle, ob unter ihrem S3-`location`-Prefix überhaupt Objekte liegen
    (leere/verwaiste Tabelle = häufige Betriebsstolperfalle),
  - schreibt das Ergebnis als Textreport nach `temp/catalog-audit/`.

Vergleichsartefakt NACH der Übung: der Teilnehmer baut den Job in Glue Studio als
**Python Shell** (nicht Spark ETL) und referenziert dieses Skript bzw. tippt es ab.

Voraussetzungen (von der Infrastruktur bereitgestellt):
  - Catalog-DBs `raw` (Tabellen aus Ü3.1/Ü6.1) und `processed` (aus Ü5.1)
  - IAM-Rolle `AWSGlueServiceRole-GfuGlueTraining` — deckt glue:Get* + S3 auf dem
    Bucket ab (nur Lesen + PutObject für den Report; KEINE Löschrechte).
  - Bucket `gfu-glue-training-<account>`

Job-Setup in Glue Studio:
  - Typ: **Python Shell** (nicht Spark). Python 3.9, boto3 vorinstalliert.
  - KEINE Glue/Spark-Bibliotheken — reines boto3.
  - Job-Parameter:
      --report_bucket   gfu-glue-training-<account>
  - Kosten: Bruchteil eines Spark-Laufs (0.0625 DPU möglich).
"""
import sys
from datetime import datetime, timezone

import boto3
from awsglue.utils import getResolvedOptions

args = getResolvedOptions(sys.argv, ["report_bucket"])
bucket = args["report_bucket"]

glue = boto3.client("glue")
s3 = boto3.client("s3")


def s3_prefix_has_objects(location):
    """True, wenn unter der S3-location der Tabelle mindestens ein Objekt liegt."""
    if not location or not location.startswith("s3://"):
        return None  # keine S3-Tabelle (z. B. DynamoDB) -> nicht prüfbar
    without_scheme = location[len("s3://"):]
    buck, _, prefix = without_scheme.partition("/")
    resp = s3.list_objects_v2(Bucket=buck, Prefix=prefix, MaxKeys=1)
    return resp.get("KeyCount", 0) > 0


def count_partitions(database, table):
    """Partitionen zählen (paginiert, rein lesend)."""
    total = 0
    paginator = glue.get_paginator("get_partitions")
    for page in paginator.paginate(DatabaseName=database, TableName=table):
        total += len(page.get("Partitions", []))
    return total


lines = [f"# Catalog-Audit  {datetime.now(timezone.utc).isoformat()}", ""]

db_paginator = glue.get_paginator("get_databases")
for db_page in db_paginator.paginate():
    for db in db_page["DatabaseList"]:
        db_name = db["Name"]
        lines.append(f"## Datenbank: {db_name}")
        tbl_paginator = glue.get_paginator("get_tables")
        table_count = 0
        for tbl_page in tbl_paginator.paginate(DatabaseName=db_name):
            for tbl in tbl_page["TableList"]:
                table_count += 1
                name = tbl["Name"]
                location = tbl.get("StorageDescriptor", {}).get("Location", "")
                n_parts = count_partitions(db_name, name)
                has_data = s3_prefix_has_objects(location)
                flag = ""
                if has_data is False:
                    flag = "  <-- WARNUNG: leerer/verwaister S3-Prefix"
                lines.append(
                    f"  - {name}: {n_parts} Partition(en), location={location or '(keine)'}{flag}"
                )
        if table_count == 0:
            lines.append("  (keine Tabellen)")
        lines.append("")

report = "\n".join(lines)
print(report)

key = f"temp/catalog-audit/report-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.txt"
s3.put_object(Bucket=bucket, Key=key, Body=report.encode("utf-8"))
print(f"Report geschrieben nach s3://{bucket}/{key}")
