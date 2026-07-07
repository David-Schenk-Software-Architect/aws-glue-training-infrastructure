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

output "trainee_usernames" {
  description = "Generic (non-PII) IAM usernames for the training attendees."
  value       = [for u in aws_iam_user.trainee : u.name]
}

output "trainee_console_url" {
  description = "AWS console sign-in URL (shared by all trainee users)."
  value       = "https://${local.account_id}.signin.aws.amazon.com/console"
}

output "trainee_passwords" {
  description = "Initial console passwords keyed by username (reset required on first sign-in). Fetch: tofu output -json trainee_passwords"
  value       = { for k, p in aws_iam_user_login_profile.trainee : k => p.password }
  sensitive   = true
}

output "trainee_access_key_ids" {
  description = "Programmatic access-key ids keyed by username. Fetch: tofu output -json trainee_access_key_ids"
  value       = { for k, a in aws_iam_access_key.trainee : k => a.id }
  sensitive   = true
}

output "trainee_secret_access_keys" {
  description = "Programmatic secrets keyed by username. Fetch: tofu output -json trainee_secret_access_keys"
  value       = { for k, a in aws_iam_access_key.trainee : k => a.secret }
  sensitive   = true
}
