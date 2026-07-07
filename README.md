# GFU AWS-Glue Training — Infrastructure

OpenTofu stack that pre-provisions the AWS resources the hands-on exercises of the
2-day **AWS Glue** training expect to already exist (their *"Infrastruktur-
Voraussetzungen — vorab bereitstellen"* sections). Training time then stays on Glue
itself, not on plumbing.

Account `REDACTED`, region `eu-central-1`.

## What this creates

| Resource | Purpose | Exercises |
|---|---|---|
| S3 bucket `gfu-glue-training-<account>` | `raw/ processed/ temp/ athena-results/ seed/` | all |
| Seed data | `raw/orders/orders.csv`, `raw/customers/customers.json`, `seed/orders_2.csv` | Ü3.1, Ü6.1, Ü8.1 |
| IAM role `AWSGlueServiceRole-GfuGlueTraining` | crawlers, jobs, interactive sessions | Ü3.1–Ü8.x |
| IAM role `StepFunctionsGlueExecutionRole-GfuGlueTraining` | Step Functions → Glue | Ü7.2 |
| Athena workgroup `gfu-glue-training` | query-result location set | Ü3.1, Ü5.1 |
| Glue Catalog DBs `raw`, `processed` | catalog targets | Ü3.1, Ü5.1 |
| KMS CMK *(optional, `enable_kms`, default off)* | Security Configuration | Ü8.2 |
| DynamoDB table *(optional, `enable_dynamodb`, default on)* | Block 9 second target | Block 9 |

**Deliberately NOT created** — the participant builds these live during the exercises:
crawlers, the Glue job `orders-s3-to-parquet`, Glue Workflows, Step Functions state
machines, Security Configurations, interactive sessions.

## Usage

Credentials come from `.env` (git-ignored). Export them, then run OpenTofu:

```bash
set -a; source .env; set +a      # AWS_ACCESS_KEY_ID / SECRET / DEFAULT_REGION

tofu init
tofu fmt -check
tofu validate
tofu plan
tofu apply
```

Optional toggles:

```bash
tofu apply -var enable_kms=true        # add the CMK for Ü8.2 (~1 USD/month)
tofu apply -var enable_dynamodb=false  # drop the Block 9 DynamoDB target
```

Outputs (`tofu output`) give the bucket name, role ARNs, workgroup, catalog DBs and the
`s3://` paths to paste into the exercises.

## Teardown (after the training)

```bash
set -a; source .env; set +a
tofu destroy
```

The bucket is `force_destroy = true`, so it is removed together with anything the
participant wrote (Parquet output, Athena results). A KMS CMK, if enabled, is scheduled
for deletion after a 7-day window.

## Cost

Effectively **zero standing cost**: S3 holds a few KB of seed data; Glue/Athena bill only
per run/scan during the session; IAM, Catalog DBs and the Step Functions role are free;
DynamoDB is on-demand. The only standing charge would be a KMS CMK (~1 USD/month) — hence
`enable_kms` defaults to **off**.

## Manual note — console identity

The console user the participant logs in as needs `iam:PassRole` on the Glue role plus
`glue` interactive-session / notebook permissions to run Ü4.1 / Ü6.1 and to pass the role
to jobs. In a sandbox where that user is admin this is already covered — flagged here so
it is not a surprise. This is a property of the *caller* identity, not of the provisioned
role, so it is intentionally out of this stack.

## Open item

Glue version for jobs (Ü5.1) is chosen at job-creation time in the console, not here.
Confirm the desired version (5.0 vs 4.0) is available in `eu-central-1` before the session.
