# Ü8.3 — Einen Lauf diagnostizieren (Monitoring-Übung)

Ein absichtlich kaputter Job (`raw.orders_bad` → `processed.orders_diagnosed`) mit
**2 eingebauten Fehlern**, die sich an verschiedenen Orten zeigen. Der Teilnehmer
übt daran die Werkzeugkette aus Block 8, Kapitel „Beobachten":
Run-Status → Job Run Insights → Logs (richtiger Stream!) → Ursache → Fix → Alarm.

- `broken/diagnose_orders.py` — der kaputte Job (Einstiegspunkt, trainee-lesbar).
- `fixed/diagnose_orders.py` — die reparierte Referenzfassung.
- Diese Datei — **Trainer-/Auflösungsreferenz** (nach dem Debugging aufdecken).

Abgrenzung zu **Ü9.A**: dort fünf verschränkte Fehler, überwiegend still oder
driverseitig — das prüft die *Suchstrategie*. Hier zwei Fehler, klar getrennt,
mit dem Executor-Fall, den Ü9.A nicht enthält — das lehrt die *Werkzeugbedienung*.

## Aufbau

Job anlegen mit Skript `scripts/examples/ue8.3-diagnose-job/broken/diagnose_orders.py`,
Rolle `AWSGlueServiceRole-GfuGlueTraining`, Parameter:

```
--output_path                    s3://<bucket>/processed/orders_diagnosed/
--enable-job-insights            true
--enable-metrics                 true
--enable-observability-metrics   true
```

Die Quelle `raw.orders_bad` ist vorab katalogisiert — kein Crawler-Lauf nötig, die
Übung startet direkt bei der Diagnose. Sie hängt **nicht** an Ü8.1 (Bookmark);
beide sind unabhängig durchspielbar.

## Auflösung — Bug ↔ Symptom ↔ Fundort ↔ Fix

Beide Runden wurden am Trainings-Account gegen Glue 5.0 (G.1X ×2) verifiziert;
die zitierten Meldungen sind wörtlich.

| # | Runde | Bug | `ErrorMessage` des Runs | Fix |
|---|---|---|---|---|
| 1 | Aufwärmer | `col("order_amount")` — die Spalte heißt `order_total` | `QUERY_ERROR; Failed Line Number: 84; AnalysisException: [UNRESOLVED_COLUMN.WITH_SUGGESTION] … Did you mean one of the following? [order_date, order_total, …]` | `col("order_total")` |
| 2 | Kern | `float("n/a")` in der Python-UDF | `UNCLASSIFIED_ERROR; Failed Line Number: 107; PythonException:` — Meldung **leer**, und Zeile 107 ist die **Senke**, nicht die UDF in Zeile 81 | Defensiv parsen (`try/except` → `None`) oder den Satz vorher filtern |

## Der didaktische Kern

Bug 1 kommt dem Teilnehmer entgegen: der Run-Status allein nennt Kategorie, exakte
Zeile, Ursache und sogar den richtigen Spaltennamen. Wer hier ein Log öffnet, hat
mehr getan als nötig. Genau deshalb steht er davor — er setzt die Erwartung, die
Bug 2 dann bricht.

Bei Bug 2 stirbt die Arbeit dort, wo sie verteilt stattfindet: eine Python-UDF läuft
nicht im Driver, sondern in den Python-Workern auf den Executors. Der Unterschied
zwischen den drei Ebenen ist die Lektion:

| Ebene | Was sie liefert |
|---|---|
| Run-Status | Zeile 107 (die Spark-Action) + leere Meldung → **führt in die Irre** |
| Driver-Stream | `Task 0 in stage 0.0 failed 4 times` und der zurückgereichte Traceback mit Zeile 81. Steht da — unter 260 Log-Events |
| Executor-Stream | Derselbe Traceback **plus der Datenkontext**: die `print`-Zeilen der UDF, letzte davon `[worker] rechne order_total um: 'n/a'` |

Merksatz: *Der Run-Status sagt dir, wo die Arbeit angestoßen wurde. Der Driver, welche
Exception flog. Erst der Executor, an welchem Datensatz.*

Der `print()` in der UDF ist Absicht: er macht sichtbar, dass Ausgaben aus dem
Worker in einem anderen Stream landen als Ausgaben aus dem Driver.

## Log-Orte bei Glue 5.0 — verifiziert, weicht von der Doku ab

| Gruppe | Inhalt |
|---|---|
| `/aws-glue/jobs/error` | System-, Spark-Daemon-, Glue-Logger-Logs **und alles aus den Workern** |
| `/aws-glue/jobs/output` | stdout/stderr des Drivers — in der Praxis zwei Zeilen Rauschen |

Streams: `jr_<run-id>` = **Driver**, `jr_<run-id>_g-<hash>` = **Executor**.

Drei Abweichungen von der AWS-Dokumentation, alle am echten Lauf geprüft:

1. Die Doku nennt `<run-id>-driver` / `<run-id>-executorNum`. Real ist das Schema
   oben — die nackte Run-ID für den Driver, Suffix `_g-` plus Hash für Executors.
2. Die Doku sagt, stdout/stderr gehe nach `/aws-glue/jobs/output`. Ein `print()`
   **aus einer UDF** landet im Executor-Stream der `error`-Gruppe. Wer seine
   Debug-Ausgaben in `output` sucht, hält den Job für stumm.
3. Trotz `--enable-job-insights true` erschienen **keine** `job-insights-*`-Streams
   — bei keinem der beiden Fehlschläge, in keiner Gruppe. Die Insights-Information
   (Fehlerkategorie + Zeilennummer) steckt stattdessen im Run-Status selbst.

`logs-v2` gilt nur für Glue ≤ 4.0 — dort war Continuous Logging ein Opt-in.

## Abschluss der Übung

Nach dem Fix: Lauf grün, Ausgabe in `processed/orders_diagnosed/`, und ein
CloudWatch-Alarm auf `glue.driver.aggregate.numFailedTasks`, der beim nächsten
Fehlschlag anschlägt:

```
--namespace Glue --metric-name glue.driver.aggregate.numFailedTasks
--dimensions Name=JobName,Value=<job> Name=Type,Value=count
--statistic Sum --period 300 --evaluation-periods 1 --threshold 0
--comparison-operator GreaterThanThreshold --treat-missing-data notBreaching
```

**`JobRunId` weglassen** — eine Run-ID ist pro Lauf neu, der Alarm feuert sonst
genau einmal und ist danach taub. Das ist der häufigste Fehler an dieser Stelle.

Gemessene Werte des Fehllaufs zur Kontrolle: `numFailedTasks = 4` (die vier
Spark-Retries eines einzigen kaputten Satzes), `numCompletedTasks = 0`,
`glue.error.UNCLASSIFIED_ERROR = 1`.

Der Trainee braucht dafür `CloudWatchReadOnlyAccess` — ohne `cloudwatch:ListMetrics`
lässt sich der Namespace `Glue` im Metrik-Explorer nicht durchsuchen. Die Policy
hängt seit Juli 2026 an den Trainee-Usern (`trainee.tf`).
