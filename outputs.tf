output "bucket_name" {
  description = "Data-lake S3 bucket."
  value       = aws_s3_bucket.lake.bucket
}

output "s3_paths" {
  description = "S3 paths the exercises reference."
  value = {
    raw_orders     = "s3://${aws_s3_bucket.lake.bucket}/raw/orders/"
    raw_customers  = "s3://${aws_s3_bucket.lake.bucket}/raw/customers/"
    processed      = "s3://${aws_s3_bucket.lake.bucket}/processed/"
    temp           = "s3://${aws_s3_bucket.lake.bucket}/temp/"
    athena_results = "s3://${aws_s3_bucket.lake.bucket}/athena-results/"
    orders_2_seed  = "s3://${aws_s3_bucket.lake.bucket}/seed/orders_2.csv"
  }
}

output "glue_role_arn" {
  description = "IAM role for Glue crawlers, jobs and interactive sessions."
  value       = aws_iam_role.glue.arn
}

output "step_functions_role_arn" {
  description = "IAM role for the Step Functions state machine (Ü7.2)."
  value       = aws_iam_role.step_functions.arn
}

output "athena_workgroup" {
  description = "Athena workgroup name."
  value       = aws_athena_workgroup.training.name
}

output "catalog_databases" {
  description = "Pre-created Glue Data Catalog databases."
  value       = [aws_glue_catalog_database.raw.name, aws_glue_catalog_database.processed.name]
}

output "kms_key_arn" {
  description = "Optional CMK ARN for Ü8.2 (null when enable_kms = false)."
  value       = var.enable_kms ? aws_kms_key.glue[0].arn : null
}

output "dynamodb_table" {
  description = "Optional Block 9 DynamoDB target (null when enable_dynamodb = false)."
  value       = var.enable_dynamodb ? aws_dynamodb_table.orders_enriched[0].name : null
}
