# ── Athena workgroup ─────────────────────────────────────────────────────────
# Query-result location must be set for Ü3.1/Ü5.1 to run SELECTs. enforce_*
# forces this location so the participant never hits "no output location".

resource "aws_athena_workgroup" "training" {
  name          = var.project
  force_destroy = true

  configuration {
    enforce_workgroup_configuration    = true
    publish_cloudwatch_metrics_enabled = true

    result_configuration {
      output_location = "s3://${aws_s3_bucket.lake.bucket}/athena-results/"
    }
  }
}
