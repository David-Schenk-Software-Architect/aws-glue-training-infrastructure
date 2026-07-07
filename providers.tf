terraform {
  required_version = ">= 1.6"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.60"
    }
  }

  # Remote state so the CI pipeline is idempotent across runs. Native S3 locking
  # (use_lockfile) avoids a DynamoDB lock table. The bucket is bootstrapped once
  # outside this stack (see README) — it cannot store its own creation state.
  backend "s3" {
    bucket       = "gfu-glue-training-tfstate-REDACTED"
    key          = "infra/terraform.tfstate"
    region       = "eu-central-1"
    encrypt      = true
    use_lockfile = true
  }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = local.tags
  }
}

data "aws_caller_identity" "current" {}

data "aws_region" "current" {}
