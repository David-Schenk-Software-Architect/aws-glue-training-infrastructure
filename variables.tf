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
