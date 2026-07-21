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

| # | Runde | Bug | Symptom | Wo steht die Antwort | Fix |
|---|---|---|---|---|---|
| 1 | Aufwärmer | `col("order_amount")` — die Spalte heißt `order_total` | Job stirbt sofort, `AnalysisException: cannot resolve` | Driver-Stream (`<run-id>-driver`), vollständig. Job Run Insights nennt die Skriptzeile direkt | `col("order_total")` |
| 2 | Kern | `float("n/a")` in der Python-UDF | Job läuft an und stirbt dann: *„Task failed 4 times"* | **Executor-Stream** (`<run-id>-executorN`) — dort steht der `ValueError` samt ausgelöstem Wert. Der Driver kennt ihn nicht | Defensiv parsen (`try/except` → `None`) oder den Satz vorher filtern |

## Der didaktische Kern

Bug 1 kommt dem Teilnehmer entgegen: ein Blick ins Driver-Log genügt, Insights
zeigt sogar die Zeilennummer. Genau deshalb steht er davor — er setzt die
Erwartung, die Bug 2 dann bricht.

Bei Bug 2 stirbt die Arbeit dort, wo sie verteilt stattfindet. Eine Python-UDF
läuft nicht im Driver, sondern in den Python-Workern auf den Executors. Der Driver
erfährt nur, *dass* eine Task viermal gescheitert ist. Welcher Datensatz sie
umgebracht hat, steht ausschließlich im Executor-Stream — plus im
`job-insights-rca-driver`-Stream, der die Executor-ID nennt und damit den Weg
dorthin weist.

Der `print()` in der UDF ist Absicht: er macht sichtbar, dass Ausgaben aus dem
Worker in einem anderen Stream landen als Ausgaben aus dem Driver.

## Log-Orte bei Glue 5.0 (nicht `logs-v2`!)

| Gruppe | Inhalt |
|---|---|
| `/aws-glue/jobs/error` | System-, Spark-Daemon- und Glue-Logger-Logs |
| `/aws-glue/jobs/output` | stdout/stderr aus dem Skript — hier landet `print()` |

Streams: `<run-id>-driver`, `<run-id>-executorN`, `<run-id>-progress-bar`.
Bei Fehlschlag zusätzlich `<run-id>-job-insights-rca-driver` und
`<run-id>-job-insights-rule-driver`.

`logs-v2` gilt nur für Glue ≤ 4.0 — dort war Continuous Logging ein Opt-in.

## Abschluss der Übung

Nach dem Fix: Lauf grün, Ausgabe in `processed/orders_diagnosed/`, und ein
CloudWatch-Alarm auf `glue.driver.aggregate.numFailedTasks` (Dimension `JobName`,
Statistik `Sum`), der beim nächsten Fehlschlag anschlägt.
