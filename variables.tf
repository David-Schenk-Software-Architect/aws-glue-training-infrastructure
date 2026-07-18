variable "project" {
  description = "Name prefix for all resources (also used for the globally-unique S3 bucket)."
  type        = string
  default     = "gfu-glue-training"
}

variable "region" {
  description = "AWS region for all resources. Matches AWS_DEFAULT_REGION in .env."
  type        = string
  default     = "eu-central-1"
}

variable "enable_kms" {
  description = "Create a symmetric KMS CMK for optional Exercise 8.2 (SSE-KMS/CSE-KMS). A CMK costs ~1 USD/month, so off by default."
  type        = bool
  default     = false
}

variable "enable_dynamodb" {
  description = "Create an on-demand DynamoDB table as the optional Block 9 second target. PAY_PER_REQUEST is effectively free at training scale."
  type        = bool
  default     = true
}

variable "trainee_usernames" {
  description = "Generic, non-PII logins for the training attendees — one IAM user per entry. Deliberately no real names to keep PII out of the IaC. Add entries to scale to N attendees."
  type        = set(string)
  default     = ["gfu-glue-trainee"]
}

variable "enable_reference_jobs" {
  description = "Register the SOLUTION scripts as real Glue jobs and the solution ASL as a Step Functions state machine (instructor reference deployment). ON by default. Reference resources use 'ref-…-solution' names to avoid colliding with the trainee-built 'orders-s3-to-parquet'. NOTE: the ref Glue jobs are visible in every trainee's Glue console (AWSGlueConsoleFullAccess) — accepted trade-off, not hidden via IAM. Set to false to keep them out of the sandbox during teaching."
  type        = bool
  default     = true
}
