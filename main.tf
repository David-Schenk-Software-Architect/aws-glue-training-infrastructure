locals {
  account_id  = data.aws_caller_identity.current.account_id
  region      = data.aws_region.current.name
  bucket_name = "${var.project}-${local.account_id}"

  tags = {
    Project   = var.project
    ManagedBy = "OpenTofu"
    Purpose   = "gfu-aws-glue-training"
  }
}
