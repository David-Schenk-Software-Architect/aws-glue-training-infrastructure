# Ü-D — Custom Classifier: unstrukturiertes Log crawlen (Trainer-Referenz)

Vertieft die Klassifizierer-Theorie aus **Block 2**, praktisch platziert in **Block 3**
(nach Ü3.1, wo der Crawler-Umgang zum ersten Mal geübt wurde — kein Vorgriff).

**Aufgabe (Trainee):** die Zeilen-Logdatei `raw/serverlog/serverlog.log` in den Catalog
bekommen. Ein Crawler mit den **Built-in-Klassifizierern** scheitert (kein CSV/JSON/…);
er landet als eine einzige String-Spalte oder wird gar nicht klassifiziert. Erst ein
**Custom Classifier vom Typ Grok** zerlegt die Zeile in typisierte Spalten.

> Diese Übung stagt **keine** lauffähige Datei — der Trainee baut Classifier + Crawler in
> der Konsole. Diese README ist die Trainer-Lösung. Der Aufgaben-Brief steht auf der
> Übungs-Slide (Block 3) und im Übungs-Cheatsheet.

## Datengrundlage

`serverlog.log` (Seed, liegt in S3 unter `raw/serverlog/serverlog.log`):

```
2026-06-01T08:14:22Z INFO order-service cust=C001 status=shipped amount=129.90
```

Format je Zeile: `<ISO-Timestamp> <LEVEL> <service> cust=<id> status=<wort> amount=<zahl>`

## Warum Built-in scheitert

Die Built-in-Klassifizierer erkennen CSV/JSON/XML/Avro/Parquet/ORC und einige Log-Formate
(z. B. Apache/CloudTrail) — dieses **applikationseigene** Format passt auf keinen. Der
Crawler erzeugt dann eine unbrauchbare Ein-Spalten-Tabelle (`col0: string`) oder keine
Tabelle. Genau der Auslöser für einen Custom Classifier.

## Lösung — Grok Custom Classifier

Glue → **Crawlers → Classifiers → Add classifier** → Typ **Grok**:

- **Classification** (frei wählbar, wird zur `classification`-Property): `serverlog`
- **Grok pattern**:

  ```
  %{TIMESTAMP_ISO8601:ts} %{LOGLEVEL:level} %{NOTSPACE:service} cust=%{NOTSPACE:customer_id} status=%{WORD:status} amount=%{NUMBER:amount:double}
  ```

- **Custom patterns**: leer (alle verwendeten Patterns sind Grok-Built-ins).

Dann den Crawler anlegen:

1. Data source: S3-Pfad `s3://gfu-glue-training-<account>/raw/serverlog/`.
2. **Custom classifiers**: den `serverlog`-Classifier hinzufügen (Reihenfolge zählt —
   Custom vor Built-in).
3. IAM-Rolle `AWSGlueServiceRole-GfuGlueTraining`, Ziel-DB `raw`.
4. Ausführen.

## Erwartetes Ergebnis

Tabelle `raw.serverlog` mit typisiertem Schema:

| Spalte | Typ |
|---|---|
| `ts` | string |
| `level` | string |
| `service` | string |
| `customer_id` | string |
| `status` | string |
| `amount` | double |

In Athena prüfbar:

```sql
SELECT level, count(*) FROM raw.serverlog GROUP BY level;
```

`classification` der Tabelle steht auf `serverlog` (nicht `UNKNOWN`) — der Beleg, dass der
Custom Classifier gegriffen hat.

## Stolpersteine

- **Classifier-Reihenfolge:** greift ein Built-in zuerst, gewinnt es. Custom nach oben.
- **Grok gierig:** `%{DATA}` statt `%{NOTSPACE}` frisst Trennzeichen mit — `NOTSPACE`/`WORD`
  sind hier präziser.
- **Klassifizierung ändern = neu crawlen:** ein Classifier wird nur bei einem Crawler-Lauf
  angewandt; nachträgliches Anhängen an eine bestehende Tabelle passiert nicht rückwirkend.
- **Kosten:** ein Crawler-Lauf dauert Sekunden (DPU-Sekunden) — Cent-Bereich.
