# Lösungs- & Beispielartefakte für die praktischen Übungen

Referenzcode zu den praktischen Übungen des AWS-Glue-Trainings. **Zum Vergleichen nach
der Übung** — der Teilnehmer baut Crawler, Jobs, Notebooks, Workflows und State Machines
in der Sandbox selbst (das ist didaktisch gewollt). Diese Dateien sind das Material
davor und danach:

- `example.*` / `broken/` — **Starter/Beispiel**: Skeleton mit `# TODO`-Markern bzw. die
  absichtlich kaputte Pipeline. Einstiegspunkt.
- `solution.*` / `fixed/` — **Lösung**: fertig, kommentiert, lauffähig gegen die Sandbox.

> **Nach S3 gestaged.** Der Stack spiegelt alle Artefakte in den Bucket unter `scripts/`:
> Starter (`example*`, `broken/`) → `scripts/examples/…` (**Trainee-sichtbar**), Lösungen
> (`solution*`, `fixed/`) → `scripts/solutions/…` (**für Trainees unsichtbar** via gescopter
> S3-Policy, Allow-Liste ohne Deny). Zusätzlich werden die Lösungsskripte via
> `enable_reference_jobs` (default **an**) als echte Glue-Jobs registriert.

**Glue-Version:** alle Skripte/Notebooks sind auf **Glue 5.0** ausgelegt (Spark 3.5,
Python 3.11). Bei Bedarf auf 4.0 anpassen — im Zweifel die Version beim Job-/Session-Start
gemäß Notion-Block wählen.

## Übung → Artefakt

| Übung | Thema | Artefakte | Typ |
|---|---|---|---|
| **Ü4.1** | DynamicFrames im Notebook erkunden | `…/{example,solution}.ipynb` **+** `…/{example,solution}_dynamicframes.py` | Notebook **+** Job-Skript |
| **Ü5.1** | Erster ETL-Job: S3 → S3 | `…/{example,solution}_orders_to_parquet.py` **+** `…/{example,solution}_orders_to_parquet.ipynb` | Job-Skript **+** Notebook |
| **Ü6.1** | Verschachteltes JSON relationalisieren | `…/{example,solution}.ipynb` **+** `…/{example,solution}_relationalize.py` | Notebook **+** Job-Skript |
| **Ü7.2** | Step-Functions State Machine | `ue7.2-step-functions/{example,solution}.asl.json` | Amazon States Language (ASL) |
| **Ü8.1** | Job Bookmark & Monitoring | `…/{example,solution}_orders_incremental.py` **+** `…/{example,solution}_orders_incremental.ipynb` | Job-Skript **+** Notebook |
| **Ü9.A** | Die verhexte Pipeline (Debugging) | `ue9.a-verhexte-pipeline/{broken,fixed}/` + `README.md` | Debugging-Challenge |

### Optionale Vertiefungen (kosteneffizient)

| Übung | Thema | Artefakte | Typ |
|---|---|---|---|
| **Ü-D** | Custom Classifier: Log crawlen (Block 3) | `ue-d-custom-classifier/README.md` | Trainer-Referenz (kein Skript — Konsolenaufgabe) |
| **Ü-E** | Python-Shell-Job: Catalog-Audit (Block 5) | `ue-e-python-shell-catalog-audit/{example,solution}_catalog_audit.py` | Python-Shell-Job (boto3, kein Spark) |
| **Ü-F** | ResolveChoice: vier Strategien (Block 4) | `…/{example,solution}.ipynb` **+** `…/{example,solution}_resolvechoice.py` | Notebook **+** Job-Skript |
| **Ü-G** | DynamoDB nativ: schreiben & lesen (Block 6) | `…/{example,solution}.ipynb` **+** `…/{example,solution}_dynamodb.py` | Notebook **+** Job-Skript |
| **Ü-H** | Lazy Evaluation: die zwei Fallen (Block 4) | `…/{example,solution}.ipynb` **+** `…/{example,solution}_lazy_eval.py` | Notebook **+** Job-Skript |
| **Ü-I** | Iceberg-Tabelle erzeugen & katalogisieren (Block 3) | `…/{example,solution}.ipynb` **+** `…/{example,solution}_orders_iceberg.py` | Notebook **+** Job-Skript |

> **Zwei Formen je Spark-Übung.** Ü4.1, Ü5.1, Ü6.1, Ü8.1, Ü-F, Ü-G, Ü-H, Ü-I liegen als
> **Notebook** (`.ipynb`, Interactive Session) **und** als **Job-Skript** (`.py`,
> submit-fähig mit `Job.init`/`job.commit` + `getResolvedOptions`) vor — Beispiel und
> Lösung jeweils. Beide werden per Glob (`example*`/`solution*`) automatisch nach
> `scripts/{examples,solutions}/` gestaged; kein Terraform-Eintrag nötig. Didaktik-Notiz:
> bei Ü-F (Schema-Vergleiche) und Ü-H (UDF-Marker) zeigt die **Notebook**-Form die
> Ausgaben inline — die Job-Form schreibt sie ins CloudWatch-Log; die Docstrings weisen
> darauf hin. Bewusst **einformig**: Ü-D (Konsole), Ü-E (Python Shell, „nicht alles braucht
> Spark"), Ü7.2 (ASL-Orchestrierung), Ü9.A (broken/fixed-Challenge).
>
> **Ü-D stagt keine Datei** — der Trainee baut Classifier + Crawler in der Konsole; die
> README ist die Trainer-Lösung. **Ü-E** wird als Job-Typ **Python Shell** angelegt (nicht
> Spark ETL), Parameter `--report_bucket`, bleibt bewusst read-only (glue:Get* + s3
> Get/Put, kein Löschen). **Ü-G** braucht `enable_dynamodb` (default an) und die
> DynamoDB-Rechte der Glue-Rolle (`gfu-glue-dynamodb`, ergänzt in `iam.tf`).

## In die Sandbox laden

S3-Layout (Pfad je Artefakt erhalten):
`scripts/examples/<übung>/…` (Starter) · `scripts/solutions/<übung>/…` (Lösung, nur Trainer).
Jeder Trainee hat zudem `scripts/<username>/{notebooks,scripts}/` für eigene Arbeit.

- **Job-Skript** (`.py`): beim Job-Anlegen in Glue Studio die S3-Location referenzieren, z. B.
  `s3://gfu-glue-training-629452195361/scripts/solutions/ue5.1-orders-to-parquet-job/solution_orders_to_parquet.py`
  — oder Skriptinhalt in den *Script editor* einfügen. IAM-Rolle
  `AWSGlueServiceRole-GfuGlueTraining`, Glue 5.0, Job-Parameter setzen (siehe Header jeder
  Datei). Starter unter `scripts/examples/…`.
- **Notebook** (`.ipynb`): aus `scripts/examples/…` bzw. `scripts/solutions/…` laden →
  Glue Studio → *Notebook* → *Upload notebook*. Die `%`-Magics in den ersten Zellen
  konfigurieren die Interactive Session. Alternativ Zellen in ein neues Session-Notebook
  kopieren.
- **ASL** (`.asl.json`): Step Functions → *Create state machine* → *Write your workflow
  in code* → JSON einfügen. Ausführungsrolle `StepFunctionsGlueExecutionRole-GfuGlueTraining`.
  *(Bei `enable_reference_jobs` (default an) ist die Lösung bereits als
  `ref-orders-pipeline-solution` deployed.)*

*Sichtbarkeit:* Lösungen unter `scripts/solutions/` sind für Trainees per S3-Policy
unsichtbar. Da `enable_reference_jobs` default **an** ist, tauchen die `ref-…-solution`-Jobs
allerdings in der Glue-Konsole der Trainees auf — bei Debugging-Challenges (Ü9.A) daher
`enable_reference_jobs = false` setzen.

## Datengrundlage (Seed-Daten, bereits in S3)

Alle Artefakte arbeiten gegen dieselben Seed-Daten aus `../data/`:

| Datei | S3-Pfad | Besonderheit |
|---|---|---|
| `orders.csv` | `raw/orders/orders.csv` | **48 Zeilen** über 10 Kunden (C001–C010; C009/C010 **ohne** Order → Outer-Join-Fall). Header **mit Leerzeichen** `cust id,order total,order date,status`; eine Zeile mit gequotetem Komma (`"shipped, partial"`); zwei leere `order total` (C004, C005) → NULL |
| `orders_2.csv` | `seed/orders_2.csv` | **22 Zeilen**, gleiche Struktur, spätere Daten (2026-06-10…16, alle 10 Kunden) — für den Bookmark-Lauf (Ü8.1) nach `raw/orders/` kopieren. Enthält dieselben Quirks (gequotetes Komma, leere `order total`) |
| `customers.json` | `raw/customers/customers.json` | **10 Kunden** (C001–C010). Geschachtelt (`address`, `contacts[]`); `loyalty_points` **mischtypig** (`1200` vs `"gold"`/`"platinum"`); zwei leere `contacts:[]` (C003, C009) |
| `serverlog.log` | `raw/serverlog/serverlog.log` | Zeilen-App-Log, **kein Built-in-Klassifizierer** parst es — Ü-D baut einen Grok-Custom-Classifier |

Feste Namen aus dem Stack (siehe `tofu output`): Bucket `gfu-glue-training-629452195361`,
Catalog-DBs `raw`/`processed`, Glue-Rolle `AWSGlueServiceRole-GfuGlueTraining`,
SFN-Rolle `StepFunctionsGlueExecutionRole-GfuGlueTraining`, Athena-Workgroup
`gfu-glue-training`.
