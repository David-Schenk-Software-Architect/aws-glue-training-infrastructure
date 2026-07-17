# Lösungs- & Beispielartefakte für die praktischen Übungen

Referenzcode zu den praktischen Übungen des AWS-Glue-Trainings. **Zum Vergleichen nach
der Übung** — der Teilnehmer baut Crawler, Jobs, Notebooks, Workflows und State Machines
in der Sandbox selbst (das ist didaktisch gewollt). Diese Dateien sind das Material
davor und danach:

- `example.*` / `broken/` — **Starter/Beispiel**: Skeleton mit `# TODO`-Markern bzw. die
  absichtlich kaputte Pipeline. Einstiegspunkt.
- `solution.*` / `fixed/` — **Lösung**: fertig, kommentiert, lauffähig gegen die Sandbox.

> **Nicht Terraform-managed.** Dieses Verzeichnis wird von keiner `.tf`-Ressource
> referenziert und von der CI **nicht** deployed. Reine Lehr-/Referenzartefakte.

**Glue-Version:** alle Skripte/Notebooks sind auf **Glue 5.0** ausgelegt (Spark 3.5,
Python 3.11). Bei Bedarf auf 4.0 anpassen — im Zweifel die Version beim Job-/Session-Start
gemäß Notion-Block wählen.

## Übung → Artefakt

| Übung | Thema | Artefakte | Typ |
|---|---|---|---|
| **Ü4.1** | DynamicFrames im Notebook erkunden | `ue4.1-dynamicframes-notebook/{example,solution}.ipynb` | Glue-Interactive-Session-Notebook |
| **Ü5.1** | Erster ETL-Job: S3 → S3 | `ue5.1-orders-to-parquet-job/{example,solution}_orders_to_parquet.py` | Glue-Job-Skript (PySpark) |
| **Ü6.1** | Verschachteltes JSON relationalisieren | `ue6.1-relationalize-json/{example,solution}.ipynb` | Glue-Interactive-Session-Notebook |
| **Ü7.2** | Step-Functions State Machine | `ue7.2-step-functions/{example,solution}.asl.json` | Amazon States Language (ASL) |
| **Ü8.1** | Job Bookmark & Monitoring | `ue8.1-bookmark-job/{example,solution}_orders_incremental.py` | Glue-Job-Skript (inkrementell) |
| **Ü9.A** | Die verhexte Pipeline (Debugging) | `ue9.a-verhexte-pipeline/{broken,fixed}/` + `README.md` | Debugging-Challenge |

## In die Sandbox laden

- **Job-Skript** (`.py`): alle `.py` aus diesem Verzeichnis werden vom Stack nach
  `s3://gfu-glue-training-<account>/scripts/` gespiegelt (Pfad erhalten, z. B.
  `scripts/ue5.1-orders-to-parquet-job/solution_orders_to_parquet.py`). Beim Job-Anlegen
  in Glue Studio als Skript-Location referenzieren — oder Skriptinhalt in den *Script
  editor* einfügen. IAM-Rolle `AWSGlueServiceRole-GfuGlueTraining`, Glue 5.0,
  Job-Parameter setzen (siehe Header jeder Datei). `tofu output s3_paths` → `scripts`.
  *Hinweis:* die Lösungsskripte liegen damit im selben Bucket, den der Teilnehmer sieht —
  bei Debugging-Challenges (Ü9.A) ggf. erst nach der Übung aushändigen.
- **Notebook** (`.ipynb`): Glue Studio → *Notebook* → *Upload notebook*. Die
  `%`-Magics in den ersten Zellen konfigurieren die Interactive Session (Rolle,
  Glue-Version, Worker). Alternativ Zellen in ein neues Session-Notebook kopieren.
- **ASL** (`.asl.json`): Step Functions → *Create state machine* → *Write your workflow
  in code* → JSON einfügen. Ausführungsrolle `StepFunctionsGlueExecutionRole-GfuGlueTraining`.

## Datengrundlage (Seed-Daten, bereits in S3)

Alle Artefakte arbeiten gegen dieselben Seed-Daten aus `../data/`:

| Datei | S3-Pfad | Besonderheit |
|---|---|---|
| `orders.csv` | `raw/orders/orders.csv` | Header **mit Leerzeichen** `cust id,order total,order date,status`; eine Zeile mit gequotetem Komma (`"shipped, partial"`); eine leere `order total` |
| `orders_2.csv` | `seed/orders_2.csv` | Gleiche Struktur, spätere Daten — für den Bookmark-Lauf (Ü8.1) nach `raw/orders/` kopieren |
| `customers.json` | `raw/customers/customers.json` | Geschachtelt (`address`, `contacts[]`); `loyalty_points` **mischtypig** (`1200` vs `"gold"`); ein leeres `contacts:[]` |

Feste Namen aus dem Stack (siehe `tofu output`): Bucket `gfu-glue-training-<account>`,
Catalog-DBs `raw`/`processed`, Glue-Rolle `AWSGlueServiceRole-GfuGlueTraining`,
SFN-Rolle `StepFunctionsGlueExecutionRole-GfuGlueTraining`, Athena-Workgroup
`gfu-glue-training`.
