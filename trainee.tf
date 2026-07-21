# ── Trainee IAM users ────────────────────────────────────────────────────────
# One login per training attendee, driven by var.trainee_usernames — add entries
# to scale to N attendees. Usernames are generic on purpose: no real names, so no
# PII lands in the IaC or state. Permissions are deliberately broad ("more than
# required"): this is a throwaway sandbox torn down after the training, so wide
# AWS-managed *FullAccess policies beat hand-scoped least-privilege here. Not a
# pattern for shared/prod accounts.

resource "aws_iam_user" "trainee" {
  for_each = var.trainee_usernames
  name     = each.value
  # Drop the user on destroy even with a live login profile / access key attached.
  force_destroy = true
}

resource "aws_iam_user_login_profile" "trainee" {
  for_each                = aws_iam_user.trainee
  user                    = each.value.name
  password_length         = 20
  password_reset_required = true
}

resource "aws_iam_access_key" "trainee" {
  for_each = aws_iam_user.trainee
  user     = each.value.name
}

# Broad managed policies covering every exercise across all 9 blocks.
# AmazonS3FullAccess is deliberately NOT here — S3 access to the data lake is
# scoped by aws_iam_policy.trainee_bucket below (allow-list, hides scripts/solutions/).
locals {
  trainee_managed_policies = [
    "arn:aws:iam::aws:policy/AWSGlueConsoleFullAccess",
    "arn:aws:iam::aws:policy/AmazonAthenaFullAccess",
    "arn:aws:iam::aws:policy/AWSStepFunctionsFullAccess",
    "arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess",
    "arn:aws:iam::aws:policy/CloudWatchLogsFullAccess",
    # Ü8.3 (monitoring): CloudWatchLogsFullAccess covers logs but NOT metrics —
    # without cloudwatch:ListMetrics the metric explorer can't browse the Glue
    # namespace, so picking a metric for an alarm is guesswork. Note that
    # PutMetricAlarm/DescribeAlarms already arrive incidentally via
    # AmazonAthenaFullAccess; this policy adds the read side that makes them usable.
    "arn:aws:iam::aws:policy/CloudWatchReadOnlyAccess",
    "arn:aws:iam::aws:policy/IAMReadOnlyAccess",
  ]

  # One attachment per (user, policy) pair.
  trainee_attachments = {
    for pair in setproduct(var.trainee_usernames, local.trainee_managed_policies) :
    "${pair[0]}|${pair[1]}" => { user = pair[0], policy = pair[1] }
  }
}

resource "aws_iam_user_policy_attachment" "trainee" {
  for_each   = local.trainee_attachments
  user       = aws_iam_user.trainee[each.value.user].name
  policy_arn = each.value.policy
}

# Explicit PassRole so each attendee can hand the Glue and Step Functions service
# roles to crawlers, jobs, interactive sessions and the state machine — even where
# a managed policy's PassRole condition would otherwise block it.
data "aws_iam_policy_document" "trainee_passrole" {
  statement {
    sid       = "PassServiceRoles"
    actions   = ["iam:PassRole"]
    resources = [aws_iam_role.glue.arn, aws_iam_role.step_functions.arn]
  }
}

resource "aws_iam_user_policy" "trainee_passrole" {
  for_each = aws_iam_user.trainee
  name     = "gfu-trainee-passrole"
  user     = each.value.name
  policy   = data.aws_iam_policy_document.trainee_passrole.json
}

# ── Scoped S3 access to the data lake ────────────────────────────────────────
# Replaces AmazonS3FullAccess. ALLOW-LIST ONLY — no Deny, no NotResource. The
# scripts/solutions/ prefix is hidden from trainees purely by being absent from
# every statement below. All trainees share this policy and can see all trainee
# workspaces; only solutions/ is withheld.

locals {
  lake_arn = aws_s3_bucket.lake.arn

  # Exercise data prefixes trainees may read + write freely.
  trainee_rw_data_prefixes = [
    "raw/",
    "processed/",
    "reporting/",
    "temp/",
    "athena-results/",
    "seed/",
  ]
}

data "aws_iam_policy_document" "trainee_bucket" {
  # 1) Read+write on all exercise data prefixes.
  statement {
    sid       = "DataObjectsReadWrite"
    actions   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
    resources = [for p in local.trainee_rw_data_prefixes : "${local.lake_arn}/${p}*"]
  }

  # 2) Read-only on the staged example artifacts.
  statement {
    sid       = "ExampleScriptsReadOnly"
    actions   = ["s3:GetObject"]
    resources = ["${local.lake_arn}/scripts/examples/*"]
  }

  # 3) Read+write on EVERY trainee workspace (shared — all trainees see all).
  statement {
    sid       = "TraineeWorkspacesReadWrite"
    actions   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
    resources = [for u in var.trainee_usernames : "${local.lake_arn}/scripts/${u}/*"]
  }

  # 4) List ONLY the allow-listed prefixes. Do NOT add "" (non-delimited),
  #    "scripts/" or "scripts/*" here — any of those would let a trainee
  #    enumerate scripts/solutions/ and defeat the whole hiding scheme. The
  #    delimited root list is granted separately in statement 4b.
  statement {
    sid       = "ListAllowedPrefixesOnly"
    actions   = ["s3:ListBucket"]
    resources = [local.lake_arn]

    condition {
      test     = "StringLike"
      variable = "s3:prefix"
      values = concat(
        [for p in local.trainee_rw_data_prefixes : "${p}*"],
        ["scripts/examples/*"],
        [for u in var.trainee_usernames : "scripts/${u}/*"],
      )
    }
  }

  # 4b) Delimited root listing only, for S3-console / Glue-Studio "Browse S3".
  #     prefix="" is permitted ONLY together with delimiter="/", so it returns
  #     top-level common prefixes (raw/, scripts/, …) but can never recurse into
  #     scripts/ — solutions/ stays invisible.
  statement {
    sid       = "ListBucketRootDelimitedOnly"
    actions   = ["s3:ListBucket"]
    resources = [local.lake_arn]

    condition {
      test     = "StringEquals"
      variable = "s3:prefix"
      values   = [""]
    }
    condition {
      test     = "StringEquals"
      variable = "s3:delimiter"
      values   = ["/"]
    }
  }

  # 5) Console usability: enumerate buckets and resolve region.
  statement {
    sid       = "AccountBucketMetadata"
    actions   = ["s3:GetBucketLocation", "s3:ListAllMyBuckets"]
    resources = ["*"]
  }
}

resource "aws_iam_policy" "trainee_bucket" {
  name        = "gfu-trainee-bucket-scoped"
  description = "Scoped S3 access to the training data lake: RW on data prefixes + all trainee workspaces, RO on scripts/examples/, no visibility of scripts/solutions/."
  policy      = data.aws_iam_policy_document.trainee_bucket.json
}

resource "aws_iam_user_policy_attachment" "trainee_bucket" {
  for_each   = aws_iam_user.trainee
  user       = each.value.name
  policy_arn = aws_iam_policy.trainee_bucket.arn
}

# ── CMK access for Ü8.2 ──────────────────────────────────────────────────────
# AWSGlueConsoleFullAccess brings kms:ListAliases + kms:DescribeKey, which is
# enough to PICK the CMK when creating the Security Configuration — but not to
# VERIFY the result afterwards: reading the SSE-KMS Parquet output in Athena and
# opening the encrypted log group both call kms:Decrypt as the trainee identity,
# and the key policy names only root, the Glue role and the Logs service. Without
# this the exercise's last step ("prüfen, dass alles verschlüsselt ist") fails
# with AccessDenied on the trainee, not on Glue.
data "aws_iam_policy_document" "trainee_kms" {
  count = var.enable_kms ? 1 : 0

  statement {
    sid = "TraineeCmkUse"
    actions = [
      "kms:Decrypt",
      "kms:Encrypt",
      "kms:GenerateDataKey",
      "kms:DescribeKey",
    ]
    resources = [aws_kms_key.glue[0].arn]
  }
}

resource "aws_iam_user_policy" "trainee_kms" {
  for_each = var.enable_kms ? aws_iam_user.trainee : {}
  name     = "gfu-trainee-kms"
  user     = each.value.name
  policy   = data.aws_iam_policy_document.trainee_kms[0].json
}
