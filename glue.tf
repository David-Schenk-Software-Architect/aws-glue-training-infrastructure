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
# as runnable Glue jobs and the solution ASL as a state machine. Names are
# prefixed 'ref-…-solution' so they never collide with the trainee-built
# 'orders-s3-to-parquet' (Ü5.1). Enabling this pre-bakes the answers into the
# sandbox — keep off during teaching, flip on only to hand out live references.

locals {
  # Single source of truth for the parquet ref job name (also used by the ASL).
  ref_parquet_job_name = "ref-orders-to-parquet-solution"

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
