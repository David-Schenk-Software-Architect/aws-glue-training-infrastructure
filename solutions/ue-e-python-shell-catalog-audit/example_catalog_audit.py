"""
Ü-E — Catalog-Audit als Python-Shell-Job (kein Spark)

Ziel: einen **Python-Shell-Job** (statt Spark-ETL) bauen, der den Data Catalog
NUR LESEND inventarisiert und einen Textreport nach S3 schreibt. Zeigt, dass
nicht jeder Glue-Job einen Spark-Cluster braucht.

Job-Setup in Glue Studio:
  - Typ: **Python Shell** (nicht Spark). Python 3.9, boto3 vorinstalliert.
  - Job-Parameter: --report_bucket   gfu-glue-training-629452195361

Fülle die # TODO-Stellen. Die IAM-Rolle darf glue:Get* + s3:GetObject/PutObject,
aber NICHT löschen — der Job bleibt bewusst read-only.
"""
import sys
from datetime import datetime, timezone

import boto3
from awsglue.utils import getResolvedOptions

args = getResolvedOptions(sys.argv, ["report_bucket"])
bucket = args["report_bucket"]

glue = boto3.client("glue")
s3 = boto3.client("s3")

lines = [f"# Catalog-Audit  {datetime.now(timezone.utc).isoformat()}", ""]

# TODO 1: über alle Datenbanken paginieren  (glue.get_paginator("get_databases"))
# TODO 2: je DB über alle Tabellen paginieren (get_tables) und Name + location lesen
# TODO 3: je Tabelle die Partitionen zählen (get_partitions, paginiert)
# TODO 4: je Tabelle prüfen, ob unter der S3-location Objekte liegen
#         (s3.list_objects_v2(..., MaxKeys=1) -> KeyCount) und leere markieren
# TODO 5: Report bauen (an `lines` anhängen)

report = "\n".join(lines)
print(report)

# TODO 6: Report nach s3://<bucket>/temp/catalog-audit/report-<ts>.txt schreiben
#         (s3.put_object)
