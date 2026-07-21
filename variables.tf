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
  description = "Create a symmetric KMS CMK for Exercise 8.2 (SSE-KMS/CSE-KMS). Costs ~1 USD/month; on by default so Ü8.2 is runnable, set to false to drop the only standing charge."
  type        = bool
  default     = true
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
  description = "Register the SOLUTION scripts as real Glue jobs, the solution ASL as a Step Functions state machine, and the reference Glue Workflow for Ü7.7 (instructor reference deployment). OFF by default so the reference resources do not pre-empt the live-built exercises (Ü7.2 state machine, Ü7.7 workflow) — the trainee builds those from scratch. Reference resources use 'ref-…-solution' names to avoid colliding with the trainee-built 'orders-s3-to-parquet'. NOTE: when enabled, the ref resources are visible in every trainee's Glue console (AWSGlueConsoleFullAccess) — not hidden via IAM. Flip to true only to hand out live references."
  type        = bool
  default     = false
}
