# ── Optional KMS CMK for Exercise 8.2 (default off) ──────────────────────────
# Glue Security Configurations require a symmetric CMK. The key policy grants
# the account root full management, the Glue role the crypto actions, and the
# CloudWatch Logs service the right to use the key for encrypted log groups.

data "aws_iam_policy_document" "kms" {
  count = var.enable_kms ? 1 : 0

  statement {
    sid       = "EnableRootManagement"
    actions   = ["kms:*"]
    resources = ["*"]

    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::${local.account_id}:root"]
    }
  }

  statement {
    sid = "AllowGlueRole"
    actions = [
      "kms:Decrypt",
      "kms:Encrypt",
      "kms:GenerateDataKey",
      "kms:DescribeKey",
    ]
    resources = ["*"]

    principals {
      type        = "AWS"
      identifiers = [aws_iam_role.glue.arn]
    }
  }

  statement {
    sid = "AllowCloudWatchLogs"
    actions = [
      "kms:Encrypt",
      "kms:Decrypt",
      "kms:GenerateDataKey",
      "kms:DescribeKey",
    ]
    resources = ["*"]

    principals {
      type        = "Service"
      identifiers = ["logs.${local.region}.amazonaws.com"]
    }
  }
}

resource "aws_kms_key" "glue" {
  count = var.enable_kms ? 1 : 0

  description              = "GFU Glue training – CMK for Security Configuration (Ü8.2)"
  key_usage                = "ENCRYPT_DECRYPT"
  customer_master_key_spec = "SYMMETRIC_DEFAULT"
  deletion_window_in_days  = 7
  policy                   = data.aws_iam_policy_document.kms[0].json
}

resource "aws_kms_alias" "glue" {
  count = var.enable_kms ? 1 : 0

  name          = "alias/${var.project}"
  target_key_id = aws_kms_key.glue[0].key_id
}
