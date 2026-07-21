# ── Glue Data Catalog databases ──────────────────────────────────────────────
# `raw` receives the crawler-catalogued orders/customers tables (Ü3.1/Ü6.1);
# `processed` receives the Parquet output of the ETL job (Ü5.1). Pre-created so
# the exercises can point straight at them.

resource "aws_glue_catalog_database" "raw" {
  name        = "raw"
  description = "GFU Glue training – raw source tables (orders, customers)."
}

resource "aws_glue_catalog_database" "processed" {
  name        = "processed"
  description = "GFU Glue training – processed Parquet output tables."
}

# ── Reference Glue jobs + Step Functions (instructor-only) ───────────────────
# Gated behind enable_reference_jobs (default off). Registers the SOLUTION scripts
# as runnable Glue jobs, the solution ASL as a state machine, and the reference
# Glue Workflow (Ü7.7, further down). Names are prefixed 'ref-…-solution' so they
# never collide with the trainee-built 'orders-s3-to-parquet' (Ü5.1). Enabling
# this pre-bakes the answers into the sandbox — keep off during teaching, flip on
# only to hand out live references.

locals {
  # Single source of truth for the parquet ref job name (also used by the ASL).
  ref_parquet_job_name = "ref-orders-to-parquet-solution"

  # Der generische Job der crawler-gesteuerten State Machine (Folie 7.8): eine
  # Tabelle je Lauf, Tabellenname kommt zur Laufzeit aus der Map.
  ref_table_job_name = "ref-table-to-parquet-solution"

  reference_jobs = {
    (local.ref_parquet_job_name) = {
      script_key = aws_s3_object.solution_scripts["ue5.1-orders-to-parquet-job/solution_orders_to_parquet.py"].key
      arguments = {
        "--output_path" = "s3://${aws_s3_bucket.lake.bucket}/processed/orders/"
      }
    }
    "ref-orders-incremental-solution" = {
      script_key = aws_s3_object.solution_scripts["ue8.1-bookmark-job/solution_orders_incremental.py"].key
      arguments = {
        "--output_path"                      = "s3://${aws_s3_bucket.lake.bucket}/processed/orders/"
        "--job-bookmark-option"              = "job-bookmark-enable"
        "--enable-continuous-cloudwatch-log" = "true"
        "--enable-metrics"                   = "true"
      }
    }
    "ref-orders-enriched-solution" = {
      script_key = aws_s3_object.solution_scripts["ue9.a-verhexte-pipeline/fixed/enrich_orders.py"].key
      arguments = {
        "--output_path" = "s3://${aws_s3_bucket.lake.bucket}/processed/orders_enriched/"
      }
    }
    # Ü-I: schreibt raw.orders als Iceberg-Tabelle nach processed/orders_iceberg/
    # und registriert sie im Data Catalog. --datalake-formats=iceberg lädt die
    # Iceberg-Jars; die Katalog-Confs setzt das Skript selbst via SparkConf.
    "ref-orders-iceberg-solution" = {
      script_key = aws_s3_object.solution_scripts["ue-i-iceberg-table/solution_orders_iceberg.py"].key
      arguments = {
        "--warehouse_path"   = "s3://${aws_s3_bucket.lake.bucket}/processed/"
        "--datalake-formats" = "iceberg"
      }
    }
    # Folie 7.8: liest raw.<table> und schreibt processed/<table>/. --table setzt
    # NICHT der Job-Default, sondern die Step-Functions-Map pro Iteration.
    (local.ref_table_job_name) = {
      script_key = aws_s3_object.solution_scripts["block7-crawler-driven-pipeline/solution_table_to_parquet.py"].key
      arguments = {
        "--output_root" = "s3://${aws_s3_bucket.lake.bucket}/processed/"
      }
    }
  }
}

resource "aws_glue_job" "reference" {
  for_each = var.enable_reference_jobs ? local.reference_jobs : {}

  name              = each.key
  role_arn          = aws_iam_role.glue.arn
  glue_version      = "5.0"
  worker_type       = "G.1X"
  number_of_workers = 2

  command {
    name            = "glueetl"
    python_version  = "3"
    script_location = "s3://${aws_s3_bucket.lake.bucket}/${each.value.script_key}"
  }

  # Default waere 1. Die Map in ref-crawler-pipeline-solution faechert je Tabelle
  # einen Lauf DESSELBEN Jobs auf — bei 1 wuerde jeder zweite Lauf sofort mit
  # ConcurrentRunsExceededException abbrechen. Gilt fuer alle Ref-Jobs; harmlos,
  # weil sie sonst ohnehin einzeln laufen.
  execution_property {
    max_concurrent_runs = 5
  }

  default_arguments = merge(
    {
      "--job-language" = "python"
      "--TempDir"      = "s3://${aws_s3_bucket.lake.bucket}/temp/"
    },
    each.value.arguments,
  )
}

# Reference state machine (Ü7.2). JobName is RETARGETED to the reference parquet
# job, not the live-built 'orders-s3-to-parquet' — the git ASL still uses the
# live name for the trainee.
resource "aws_sfn_state_machine" "reference" {
  count = var.enable_reference_jobs ? 1 : 0

  name     = "ref-orders-pipeline-solution"
  role_arn = aws_iam_role.step_functions.arn

  definition = jsonencode({
    Comment = "Referenz-Loesung Ue7.2 - startet den Referenz-Glue-Job synchron (.sync), mit Retry und Catch."
    StartAt = "RunGlueJob"
    States = {
      RunGlueJob = {
        Type       = "Task"
        Resource   = "arn:aws:states:::glue:startJobRun.sync"
        Parameters = { JobName = aws_glue_job.reference[local.ref_parquet_job_name].name }
        Retry = [{
          ErrorEquals     = ["Glue.ConcurrentRunsExceededException"]
          IntervalSeconds = 15
          MaxAttempts     = 3
          BackoffRate     = 2.0
        }]
        Catch = [{ ErrorEquals = ["States.ALL"], Next = "JobFailed" }]
        Next  = "Done"
      }
      JobFailed = {
        Type  = "Fail"
        Error = "GlueJobFailed"
        Cause = "Referenz-Job fehlgeschlagen - siehe Glue-Run-Details / CloudWatch."
      }
      Done = { Type = "Succeed" }
    }
  })
}

# ── Crawler-gesteuerte State Machine (Folie 7.8 / Abb. 17, instructor-only) ──
# Die lauffaehige Fassung der Zeichnung auf Folie 7.8: derselbe Ablauf wie der
# Glue Workflow weiter unten, aber in Step Functions. Kein Uebungsartefakt —
# Vorfuehrmaterial zur Folie. Gleiches Gate und Namensschema wie der Rest.
#
# Quelle mit den LIVE-Namen (und der ausfuehrlichen Begruendung) liegt als
# solutions/block7-crawler-driven-pipeline/example_crawler_pipeline.asl.json im
# Repo und wird nach scripts/examples/ gestaged; hier steht dieselbe Kette,
# retargetet auf die ref-…-solution-Namen. Aenderungen gehoeren in beide.

# Der Crawler, dessen Fund die Map fuellt. Zwei Targets, damit er mehr als EINE
# Tabelle findet — sonst faechert die Map ueber ein Element auf und die Pointe
# der Folie ist weg. raw/serverlog/ bleibt bewusst draussen: kein Built-in-
# Klassifizierer parst es (das ist Ü-D), es wuerde eine Schrott-Tabelle liefern.
# ON-DEMAND (kein 'schedule') — die State Machine startet ihn.
resource "aws_glue_crawler" "crawler_pipeline_raw" {
  count = var.enable_reference_jobs ? 1 : 0

  name          = "ref-raw-all-crawler-solution"
  role          = aws_iam_role.glue.arn
  database_name = aws_glue_catalog_database.raw.name

  s3_target {
    path = "s3://${aws_s3_bucket.lake.bucket}/raw/orders/"
  }

  s3_target {
    path = "s3://${aws_s3_bucket.lake.bucket}/raw/customers/"
  }
}

resource "aws_sfn_state_machine" "crawler_pipeline" {
  count = var.enable_reference_jobs ? 1 : 0

  name     = "ref-crawler-pipeline-solution"
  role_arn = aws_iam_role.step_functions.arn

  definition = jsonencode({
    Comment = "Folie 7.8 / Abb. 17 - Crawler starten, Status pollen, Tabellenliste holen, je Tabelle ein Job-Run."
    StartAt = "StartCrawler"
    # Falls der Crawler nie READY meldet, bricht der Lauf nach 30 min ab statt
    # ewig zu pollen.
    TimeoutSeconds = 1800
    States = {
      # SDK-Integration, KEIN '.sync': eine optimierte Glue-Integration gibt es
      # nur fuer startJobRun. Dieser Task ist sofort fertig, waehrend der
      # Crawler noch laeuft — deshalb ueberhaupt die Poll-Schleife.
      StartCrawler = {
        Type       = "Task"
        Resource   = "arn:aws:states:::aws-sdk:glue:startCrawler"
        Parameters = { Name = aws_glue_crawler.crawler_pipeline_raw[0].name }
        Next       = "WaitForCrawler"
      }
      WaitForCrawler = {
        Type    = "Wait"
        Seconds = 30
        Next    = "GetCrawler"
      }
      # Name als Konstante, nicht aus dem State-Input: die getCrawler-Antwort
      # ERSETZT den State, in Runde 2 waere der Name sonst weg.
      GetCrawler = {
        Type       = "Task"
        Resource   = "arn:aws:states:::aws-sdk:glue:getCrawler"
        Parameters = { Name = aws_glue_crawler.crawler_pipeline_raw[0].name }
        Next       = "CrawlerReady"
      }
      # Choice ruft keinen Service — es vergleicht nur Felder im State-Input.
      CrawlerReady = {
        Type = "Choice"
        Choices = [{
          Variable     = "$.Crawler.State"
          StringEquals = "READY"
          Next         = "GetTables"
        }]
        Default = "WaitForCrawler"
      }
      # Der Crawler gibt keine Tabellennamen zurueck (GetCrawlerMetrics liefert
      # nur Anzahlen) — die Liste kommt aus dem Katalog.
      GetTables = {
        Type       = "Task"
        Resource   = "arn:aws:states:::aws-sdk:glue:getTables"
        Parameters = { DatabaseName = aws_glue_catalog_database.raw.name }
        Next       = "RunJobPerTable"
      }
      RunJobPerTable = {
        Type           = "Map"
        ItemsPath      = "$.TableList"
        MaxConcurrency = 2
        Iterator = {
          StartAt = "RunGlueJob"
          States = {
            RunGlueJob = {
              Type     = "Task"
              Resource = "arn:aws:states:::glue:startJobRun.sync"
              Parameters = {
                JobName = aws_glue_job.reference[local.ref_table_job_name].name
                # Im Iterator IST das Item der State-Input, daher '$.Name'.
                Arguments = { "--table.$" = "$.Name" }
              }
              Retry = [{
                ErrorEquals     = ["Glue.ConcurrentRunsExceededException"]
                IntervalSeconds = 15
                MaxAttempts     = 3
                BackoffRate     = 2.0
              }]
              End = true
            }
          }
        }
        # Catch haengt am Map-State, nicht am inneren Task: ein gescheiterter
        # Job soll den ganzen Lauf in den Fail-State fuehren (so die Folie).
        Catch = [{ ErrorEquals = ["States.ALL"], Next = "PipelineFailed" }]
        Next  = "Done"
      }
      PipelineFailed = {
        Type  = "Fail"
        Error = "PipelineFailed"
        Cause = "Crawler- oder Job-Schritt fehlgeschlagen - siehe Execution-Historie / CloudWatch."
      }
      Done = { Type = "Succeed" }
    }
  })
}

# ── Reference Glue Workflow (Ü7.7, instructor-only) ──────────────────────────
# Das native-Orchestrierung-Gegenstück zur Step-Functions-Referenz oben und zur
# Terraform-Folie 7.4b in Block 7. Gleiche Gate (enable_reference_jobs, default
# off) und 'ref-…-solution'-Namensschema, damit nichts mit dem live in Ü7.7
# gebauten Workflow des Trainee kollidiert. Baut die Anatomie-Kette (Folie 7.4a):
# On-Demand-Trigger → Crawler(raw) → Job → Crawler(processed).
#
# Der Workflow ist NUR die Klammer — er enthält keine Reihenfolge. Die Kette lebt
# vollständig in den Triggern: ein ON_DEMAND-Start plus zwei CONDITIONAL-Trigger,
# die je nach SUCCEEDED des Vorgängers feuern. Beide Crawler sind bewusst
# ON-DEMAND (kein 'schedule'), sonst liefen sie unabhängig vom Workflow doppelt.

# Crawler(raw): katalogisiert raw/orders/ in die raw-DB — erster Knoten der Kette.
resource "aws_glue_crawler" "reference_raw" {
  count = var.enable_reference_jobs ? 1 : 0

  name          = "ref-raw-orders-crawler-solution"
  role          = aws_iam_role.glue.arn
  database_name = aws_glue_catalog_database.raw.name

  s3_target {
    path = "s3://${aws_s3_bucket.lake.bucket}/raw/orders/"
  }
}

# Crawler(processed): katalogisiert den Parquet-Output des Jobs in die processed-DB.
resource "aws_glue_crawler" "reference_processed" {
  count = var.enable_reference_jobs ? 1 : 0

  name          = "ref-processed-orders-crawler-solution"
  role          = aws_iam_role.glue.arn
  database_name = aws_glue_catalog_database.processed.name

  s3_target {
    path = "s3://${aws_s3_bucket.lake.bucket}/processed/orders/"
  }
}

# Die Klammer. default_run_properties = der geteilte Zustand über den ganzen Lauf
# (Folie 7.5): jeder Job liest ihn via get_workflow_run_properties.
resource "aws_glue_workflow" "reference" {
  count = var.enable_reference_jobs ? 1 : 0

  name = "ref-orders-workflow-solution"

  default_run_properties = {
    target_format = "parquet"
  }
}

# Start: ON_DEMAND (der Instructor startet den Lauf) → Crawler(raw).
resource "aws_glue_trigger" "reference_start" {
  count = var.enable_reference_jobs ? 1 : 0

  name          = "ref-start-crawl-raw"
  workflow_name = aws_glue_workflow.reference[0].name
  type          = "ON_DEMAND"

  actions {
    crawler_name = aws_glue_crawler.reference_raw[0].name
  }
}

# Crawler(raw) SUCCEEDED → Job. Der Job ist die Referenz-Parquet-Lösung von oben.
resource "aws_glue_trigger" "reference_after_raw" {
  count = var.enable_reference_jobs ? 1 : 0

  name          = "ref-run-job"
  workflow_name = aws_glue_workflow.reference[0].name
  type          = "CONDITIONAL"

  predicate {
    conditions {
      crawler_name = aws_glue_crawler.reference_raw[0].name
      crawl_state  = "SUCCEEDED"
    }
  }

  actions {
    job_name = aws_glue_job.reference[local.ref_parquet_job_name].name
  }
}

# Job SUCCEEDED → Crawler(processed). Letzter Knoten der Kette.
resource "aws_glue_trigger" "reference_after_job" {
  count = var.enable_reference_jobs ? 1 : 0

  name          = "ref-crawl-processed"
  workflow_name = aws_glue_workflow.reference[0].name
  type          = "CONDITIONAL"

  predicate {
    conditions {
      job_name = aws_glue_job.reference[local.ref_parquet_job_name].name
      state    = "SUCCEEDED"
    }
  }

  actions {
    crawler_name = aws_glue_crawler.reference_processed[0].name
  }
}
