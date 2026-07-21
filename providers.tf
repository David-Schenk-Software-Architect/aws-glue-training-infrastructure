terraform {
  required_version = ">= 1.6"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.60"
    }
    # Zips the Ü7.3 blueprint source (layout.py + blueprint.cfg) at apply time,
    # so no binary ZIP is committed. See aws_s3_object.blueprint in s3.tf.
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
  }

  # Remote state so the CI pipeline is idempotent across runs. Native S3 locking
  # (use_lockfile) avoids a DynamoDB lock table. The bucket is bootstrapped once
  # outside this stack (see README) — it cannot store its own creation state.
  #
  # Partial config: the bucket name (which embeds the account id) is passed at
  # init time via -backend-config so it is never committed to this public repo.
  #   local: tofu init -backend-config="bucket=$TF_STATE_BUCKET"
  #   CI:    -backend-config="bucket=${{ secrets.TF_STATE_BUCKET }}"
  backend "s3" {
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
