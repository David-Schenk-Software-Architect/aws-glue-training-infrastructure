# GFU AWS-Glue Training — Infrastructure

OpenTofu stack that pre-provisions the AWS resources the hands-on exercises of the
2-day **AWS Glue** training expect to already exist (their *"Infrastruktur-
Voraussetzungen — vorab bereitstellen"* sections). Training time then stays on Glue
itself, not on plumbing.

Region `eu-central-1`. The target account id is not hard-coded in this repo — it comes
from the caller's credentials / repo secrets at deploy time.

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

## Deployment (CI/CD)

Deploys run through **GitHub Actions** (`.github/workflows/deploy.yml`):

- **Push to `main`** → `init → fmt → validate → plan → apply` (full deploy).
- **Pull request to `main`** → same, but stops after `plan` (review gate, no apply).
- A guard step aborts if the runner's AWS account ≠ the expected one.

State lives in a remote **S3 backend** (native S3 locking) so every run is idempotent.
The state-bucket name embeds the account id, so it is **not** committed here — it is
supplied at `init` time via `-backend-config="bucket=..."`. Auth + config come from repo
**secrets** `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` / `AWS_ACCOUNT_ID` /
`TF_STATE_BUCKET` and the repo **variable** `AWS_DEFAULT_REGION`.

The **first push to `main` performs the initial apply** — no manual first-apply needed.
Watch it with `gh run watch`.

### One-time state-bucket bootstrap

The backend bucket must exist before the first `tofu init`. Run once (with `.env` creds).
The bucket name is derived from the current account id, so nothing sensitive is hard-coded:

```bash
set -a; source .env; set +a
B="gfu-glue-training-tfstate-$(aws sts get-caller-identity --query Account --output text)"
aws s3api create-bucket --bucket "$B" --region eu-central-1 \
  --create-bucket-configuration LocationConstraint=eu-central-1
aws s3api put-bucket-versioning --bucket "$B" \
  --versioning-configuration Status=Enabled
aws s3api put-bucket-encryption --bucket "$B" \
  --server-side-encryption-configuration \
  '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"},"BucketKeyEnabled":true}]}'
aws s3api put-public-access-block --bucket "$B" \
  --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
```

## Local usage

Credentials come from `.env` (git-ignored). Export them, then run OpenTofu against the
same remote state:

```bash
set -a; source .env; set +a      # AWS_ACCESS_KEY_ID / SECRET / DEFAULT_REGION
export TF_STATE_BUCKET="gfu-glue-training-tfstate-$(aws sts get-caller-identity --query Account --output text)"

tofu init -backend-config="bucket=$TF_STATE_BUCKET"   # initialises the S3 backend
tofu fmt -check
tofu validate
tofu plan
tofu apply                       # prefer letting CI apply; local apply shares the same state
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
