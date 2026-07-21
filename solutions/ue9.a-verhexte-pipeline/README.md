# Ü9.A — Die verhexte Pipeline (Debugging-Challenge)

Eine absichtlich kaputte End-to-End-Pipeline (`orders` × `customers` →
`processed.orders_enriched`) mit **5 eingebauten Fehlern**. Der Teilnehmer
diagnostiziert, benennt die Root-Cause und repariert; danach Vergleich mit
`fixed/`.

- `broken/enrich_orders.py` — die kaputte Pipeline (Einstiegspunkt).
- `fixed/enrich_orders.py` — die reparierte Referenzfassung.
- Diese Datei — **Trainer-/Auflösungsreferenz** (nach dem Debugging aufdecken).

3 Fehler stecken im Code (`broken/enrich_orders.py`), 2 in der Umgebung
(Crawler-SerDe, IAM). Aufbau der Challenge: den Job mit
`--output_path s3://gfu-glue-training-629452195361/processed/orders_enriched/` und
der Rolle `AWSGlueServiceRole-GfuGlueTraining` anlegen und laufen lassen.

## Auflösung — Bug ↔ Symptom ↔ Fix

| # | Ort | Bug | Symptom | Fix |
|---|---|---|---|---|
| 1 | Umgebung (Crawler) | `raw.orders` mit OpenCSVSerDe **ohne** `quoteChar` katalogisiert | Zeile `C002` (`"shipped, partial"`) wird am Komma zerrissen → `status` verstümmelt / Spalte verschoben | Am Table-SerDe `quoteChar='"'` (und ggf. `escapeChar`) setzen und neu crawlen — oder Crawler mit korrekter CSV-Classification anlegen |
| 2 | Code | Quellen ohne `transformation_ctx` | Bei aktiviertem Job-Bookmark wird nichts inkrementell verfolgt; Wiederholungsläufe verarbeiten alles neu | `transformation_ctx="src_orders"` / `"src_customers"` / `"map_orders"` ergänzen |
| 3 | Code | `resolveChoice` auf `loyalty_points` fehlt | `loyalty_points` bleibt `choice` (int **und** string, da `1200` vs `"gold"`) → Schema-Überraschung, `select` liefert Struct/NULL statt Wert | `customers = customers.resolveChoice(specs=[("loyalty_points", "cast:string")])` vor `toDF()` |
| 4 | Code | Filter `status == "Shipped"` (Großschreibung) | **0 Zeilen** matchen (Daten sind kleingeschrieben) → leere Ausgabe | Auf `status == "shipped"` korrigieren (die Daten sind durchgängig lowercase) |
| 5 | Umgebung (IAM) | Job läuft mit zu enger Rolle ohne Schreibrecht auf `processed/` bzw. ohne `glue:CreateTable` | `AccessDenied` / `EntityNotFoundException` beim Schreiben bzw. Katalogisieren | Job mit `AWSGlueServiceRole-GfuGlueTraining` ausführen (deckt `s3:PutObject` auf den Bucket + Katalog-Schreibrechte ab) |

## Hinweis zur Reihenfolge

Bugs 3 und 4 fallen sofort auf (leere Ausgabe, seltsames Schema). Bug 1 zeigt sich
nur bei genauem Blick auf Zeile `C002`. Bug 2 wird erst bei einem **zweiten** Lauf
mit Bookmark sichtbar. Bug 5 hängt davon ab, mit welcher Rolle der Job angelegt
wurde — gutes Gespräch über Least-Privilege vs. bereitgestellte Trainingsrolle.
