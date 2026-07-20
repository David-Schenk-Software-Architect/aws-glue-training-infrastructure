# ── Glue service role ────────────────────────────────────────────────────────
# Name starts with "AWSGlueServiceRole" (Notion requirement). Used by crawlers,
# jobs AND interactive sessions across Ü3.1 / Ü4.1 / Ü5.1 / Ü6.1 / Ü7.1 / Ü8.x.
# AWS-managed AWSGlueServiceRole covers glue:* (catalog) + CloudWatch logs on
# /aws-glue/*; the inline policy adds S3 on our bucket, whose name is not
# aws-glue-* so it is not covered by the managed policy. The managed policy grants
# NO iam:PassRole — its only iam:* actions are ListRolePolicies/GetRole/GetRolePolicy.
# PassRole is granted explicitly below.

data "aws_iam_policy_document" "glue_assume" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["glue.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "glue" {
  name               = "AWSGlueServiceRole-GfuGlueTraining"
  path               = "/service-role/"
  assume_role_policy = data.aws_iam_policy_document.glue_assume.json
}

# replace_triggered_by is load-bearing: this resource's id is <role-name>/<policy-arn>,
# so a ForceNew on the role (path, name, …) recreates the role WITHOUT re-planning the
# attachment — the apply goes green while the role ends up with no managed policy at all.
# That happened once (commit dddb6ca added path = "/service-role/") and broke every Glue
# Studio data preview until it was re-applied.
resource "aws_iam_role_policy_attachment" "glue_managed" {
  role       = aws_iam_role.glue.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"

  lifecycle {
    replace_triggered_by = [aws_iam_role.glue]
  }
}

data "aws_iam_policy_document" "glue_inline" {
  statement {
    sid       = "BucketList"
    actions   = ["s3:ListBucket", "s3:GetBucketLocation"]
    resources = [aws_s3_bucket.lake.arn]
  }

  statement {
    sid = "ObjectReadWrite"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
    ]
    resources = ["${aws_s3_bucket.lake.arn}/*"]
  }

  # A console notebook kernel runs AS this role (GlueJobRunnerSession) and calls
  # glue:CreateSession passing this same role back, so the role must be allowed to
  # pass itself. Jobs and crawlers never hit this — Glue assumes the role directly.
  # Scoped to this one role and conditioned on Glue, so it cannot pass anything else.
  statement {
    sid       = "PassSelfToGlue"
    actions   = ["iam:PassRole"]
    resources = [aws_iam_role.glue.arn]

    condition {
      test     = "StringEquals"
      variable = "iam:PassedToService"
      values   = ["glue.amazonaws.com"]
    }
  }

  # Explicit catalog writes (also covered by the managed policy) so the role is
  # self-documenting for the Data-Catalog-Update option in Ü5.1.
  statement {
    sid = "CatalogWrite"
    actions = [
      "glue:CreateTable",
      "glue:UpdateTable",
      "glue:GetTable",
      "glue:GetTables",
      "glue:GetDatabase",
      "glue:GetDatabases",
      "glue:BatchCreatePartition",
      "glue:CreatePartition",
      "glue:UpdatePartition",
      "glue:GetPartition",
      "glue:GetPartitions",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "glue_inline" {
  name   = "gfu-glue-s3-catalog"
  role   = aws_iam_role.glue.id
  policy = data.aws_iam_policy_document.glue_inline.json
}

# KMS grants for the Glue role, only when the optional CMK exists (Ü8.2).
data "aws_iam_policy_document" "glue_kms" {
  count = var.enable_kms ? 1 : 0

  statement {
    sid = "GlueKms"
    actions = [
      "kms:Decrypt",
      "kms:Encrypt",
      "kms:GenerateDataKey",
      "kms:DescribeKey",
    ]
    resources = [aws_kms_key.glue[0].arn]
  }

  # Without AssociateKmsKey a Security Configuration with CloudWatch-Logs encryption
  # does not error — it silently stops writing logs. Ü8.2 depends on this.
  statement {
    sid       = "GlueLogsKms"
    actions   = ["logs:AssociateKmsKey"]
    resources = ["arn:aws:logs:${local.region}:${local.account_id}:log-group:/aws-glue/*"]
  }
}

resource "aws_iam_role_policy" "glue_kms" {
  count  = var.enable_kms ? 1 : 0
  name   = "gfu-glue-kms"
  role   = aws_iam_role.glue.id
  policy = data.aws_iam_policy_document.glue_kms[0].json
}

# DynamoDB grants for the Glue role, only when the optional table exists. The
# native DynamoDB connector reads via Scan and writes via BatchWriteItem, both of
# which also call DescribeTable. Needed by Ü-G (write+read-back) and by the Block 9
# capstone that targets the enriched table. Scoped to the one training table.
data "aws_iam_policy_document" "glue_dynamodb" {
  count = var.enable_dynamodb ? 1 : 0

  statement {
    sid = "GlueDynamoDb"
    actions = [
      "dynamodb:DescribeTable",
      "dynamodb:Scan",
      "dynamodb:Query",
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:BatchWriteItem",
    ]
    resources = [aws_dynamodb_table.orders_enriched[0].arn]
  }
}

resource "aws_iam_role_policy" "glue_dynamodb" {
  count  = var.enable_dynamodb ? 1 : 0
  name   = "gfu-glue-dynamodb"
  role   = aws_iam_role.glue.id
  policy = data.aws_iam_policy_document.glue_dynamodb[0].json
}

# ── Step Functions execution role (Ü7.2) ────────────────────────────────────
# Starts and monitors the participant-built Glue job via glue:startJobRun.sync.

data "aws_iam_policy_document" "sfn_assume" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["states.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "step_functions" {
  name               = "StepFunctionsGlueExecutionRole-GfuGlueTraining"
  assume_role_policy = data.aws_iam_policy_document.sfn_assume.json
}

data "aws_iam_policy_document" "sfn_inline" {
  statement {
    sid = "GlueJobControl"
    actions = [
      "glue:StartJobRun",
      "glue:GetJobRun",
      "glue:GetJobRuns",
      "glue:BatchStopJobRun",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "sfn_inline" {
  name   = "gfu-sfn-glue"
  role   = aws_iam_role.step_functions.id
  policy = data.aws_iam_policy_document.sfn_inline.json
}
