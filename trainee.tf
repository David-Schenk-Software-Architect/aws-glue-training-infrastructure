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
locals {
  trainee_managed_policies = [
    "arn:aws:iam::aws:policy/AWSGlueConsoleFullAccess",
    "arn:aws:iam::aws:policy/AmazonS3FullAccess",
    "arn:aws:iam::aws:policy/AmazonAthenaFullAccess",
    "arn:aws:iam::aws:policy/AWSStepFunctionsFullAccess",
    "arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess",
    "arn:aws:iam::aws:policy/CloudWatchLogsFullAccess",
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
