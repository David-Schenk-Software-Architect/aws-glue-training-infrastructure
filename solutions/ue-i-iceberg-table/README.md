# Ü-I — Iceberg-Tabelle in Glue erzeugen & im Catalog anlegen (Trainer-Referenz)

Optionale Vertiefung zu **Block 3** (offene Tabellenformate, Slides 3.8–3.12). Macht
die Theorie „Open Table Format" praktisch: der Trainee legt eine **Apache-Iceberg**-
Tabelle an, befüllt sie aus `raw.orders` und sieht sie danach als `processed.orders_iceberg`
im **Glue Data Catalog** — direkt aus Athena abfragbar.

**Aufgabe (Trainee):** aus der katalogisierten Rohtabelle `raw.orders` eine Iceberg-
Tabelle `processed.orders_iceberg` erzeugen und im Catalog registrieren. Kern ist nicht
der ETL-Inhalt (der ist wie Ü5.1), sondern **Format + Catalog-Anbindung**: `USING iceberg`
plus der `GlueCatalog`-Impl, der die Tabelle automatisch in den Data Catalog schreibt.

Zwei Formen (beide gestaged, `example*`/`solution*`):

- **Notebook** (`.ipynb`, Interactive Session) — zeigt Schema, Row-Count und die
  `.snapshots`-Metadatentabelle inline. Empfohlene Form zum Vorführen.
- **Job-Skript** (`.py`, submit-fähig mit `Job.init`/`job.commit`) — identische Logik,
  Ausgaben landen im CloudWatch-Log.

## Voraussetzungen (von der Infrastruktur bereitgestellt)

- Catalog-DB `raw` mit Tabelle `orders` (Crawler aus Ü2.1/Ü3.1) — 48 Zeilen, „schmutzige"
  Spaltennamen mit Leerzeichen (`cust id`, `order total`, `order date`), zwei leere
  `order total` (→ NULL).
- Catalog-DB `processed` (leer, vorab angelegt) — Ziel-DB der Iceberg-Tabelle.
- IAM-Rolle `AWSGlueServiceRole-GfuGlueTraining`: S3 R/W auf den Bucket + `glue:CreateTable`/
  `glue:UpdateTable` (beides vorhanden). **Kein zusätzliches IAM nötig.**
- Die Tabelle landet unter `s3://…/processed/orders_iceberg/` — im `processed/`-Prefix,
  das der Trainee ohnehin lesen/schreiben/listen darf, deshalb sofort aus Athena lesbar.

## Iceberg in Glue 5.0 aktivieren

Iceberg ist ab Glue 3.0 **nativ** dabei — kein Connector, kein Dependency-Management.
Eingeschaltet über den Job-/Session-Parameter:

```
--datalake-formats = iceberg
```

Dazu ein **named Catalog** `glue_catalog`, der Spark SQL an den Glue Data Catalog bindet:

| Conf | Wert |
|---|---|
| `spark.sql.extensions` | `org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions` |
| `spark.sql.catalog.glue_catalog` | `org.apache.iceberg.spark.SparkCatalog` |
| `spark.sql.catalog.glue_catalog.warehouse` | `s3://gfu-glue-training-629452195361/processed/` |
| `spark.sql.catalog.glue_catalog.catalog-impl` | `org.apache.iceberg.aws.glue.GlueCatalog` |
| `spark.sql.catalog.glue_catalog.io-impl` | `org.apache.iceberg.aws.s3.S3FileIO` |

- **Notebook:** die Confs im `%%configure`-Block setzen (siehe `solution.ipynb`) — sie
  müssen beim Session-Bau stehen, `spark.sql.extensions` lässt sich später nicht mehr setzen.
- **Job:** im Skript über `SparkConf` **vor** dem `SparkContext` (siehe `solution_orders_iceberg.py`),
  dann bleibt außer `--datalake-formats` kein `--conf`-Parameter im Job-Setup.

## Lösung — die SQL-Schritte

**1) Tabelle anlegen (+ Catalog-Registrierung in einem):**

```sql
CREATE TABLE IF NOT EXISTS glue_catalog.processed.orders_iceberg (
    customer_id string,
    order_total double,
    order_date  string,
    status      string
)
USING iceberg
LOCATION 's3://gfu-glue-training-629452195361/processed/orders_iceberg'
TBLPROPERTIES ('format-version' = '2');
```

`CREATE TABLE` über den `GlueCatalog`-Impl legt die Tabelle sofort als
`processed.orders_iceberg` im Data Catalog an — kein separater Crawler nötig.

**2) Aus `raw.orders` befüllen** (Backticks für die Spalten mit Leerzeichen, `order total`
nach `double` casten → leere Zelle wird NULL):

```sql
INSERT INTO glue_catalog.processed.orders_iceberg
SELECT
    `cust id`                     AS customer_id,
    CAST(`order total` AS double) AS order_total,
    `order date`                  AS order_date,
    status                        AS status
FROM raw.orders;
```

**3) Prüfen:**

```sql
SELECT count(*) FROM glue_catalog.processed.orders_iceberg;            -- 48
DESCRIBE EXTENDED glue_catalog.processed.orders_iceberg;               -- Provider: iceberg
SELECT snapshot_id, operation
FROM glue_catalog.processed.orders_iceberg.snapshots;                  -- 1 Snapshot (append)
```

**4) Compaction — Small Files messbar zusammenpacken:**

Der `INSERT` schreibt viele kleine Dateien (ein Task je Spark-Partition). Erst zählen,
dann bin-pack, dann erneut zählen — die Datei-Zahl fällt sichtbar:

```sql
SELECT count(*) FROM glue_catalog.processed.orders_iceberg.files;      -- vorher: viele

CALL glue_catalog.system.rewrite_data_files(table => 'processed.orders_iceberg');

SELECT count(*) FROM glue_catalog.processed.orders_iceberg.files;      -- nachher: meist 1
```

`.files` ist die Iceberg-Metadaten-Tabelle (wie `.snapshots`). In **Athena** liefe dasselbe
über `OPTIMIZE processed.orders_iceberg REWRITE DATA USING BIN_PACK` (dort heißt die
Metadaten-Tabelle `…$files`, und der Tabellenname darf **nicht** gequotet sein). Spark kann
über `strategy => 'sort'` zusätzlich sortieren; Athena nur bin-pack.

## Erwartetes Ergebnis

- Tabelle `processed.orders_iceberg` im Glue Data Catalog, Typ **Iceberg**, 48 Zeilen.
- In **Athena** (als Trainee) direkt abfragbar — Athena v3 liest Iceberg über den Catalog nativ:

  ```sql
  SELECT status, count(*) FROM processed.orders_iceberg GROUP BY status;
  ```

- Unter `s3://…/processed/orders_iceberg/` liegen ein `data/`- und ein `metadata/`-Ordner
  (die Iceberg-Metadaten-Schicht — der eigentliche Unterschied zu reinem Parquet).

## Stolpersteine

- **`--datalake-formats` vergessen:** ohne den Parameter fehlen die Iceberg-Jars →
  `USING iceberg` scheitert mit „datasource not found". Häufigster Fehler.
- **`spark.sql.extensions` zur Laufzeit gesetzt:** greift nicht mehr. Muss beim Session-Bau
  stehen (SparkConf im Job, `%%configure` im Notebook).
- **`raw.orders` ohne Backticks:** die Rohspalten heißen `cust id`/`order total`/`order date`
  mit Leerzeichen — ohne Backticks ist es ein Syntaxfehler.
- **Falscher Catalog-Präfix:** Tabelle über `glue_catalog.processed.…` ansprechen. `raw.orders`
  liegt im Default-Catalog (Glue) und wird ohne Präfix gelesen.
- **Kosten:** eine Interactive Session bzw. ein kurzer G.1X-Lauf — wenige DPU-Minuten, im
  Cent- bis unteren Euro-Bereich. Session danach stoppen (`%stop_session` / Idle-Timeout).

## Aufräumen

```sql
DROP TABLE glue_catalog.processed.orders_iceberg PURGE;   -- Catalog-Eintrag + S3-Dateien
```

`PURGE` löscht auch die Daten unter `processed/orders_iceberg/`. Ohne `PURGE` bleibt nur
der Catalog-Eintrag weg, die S3-Dateien nicht.
