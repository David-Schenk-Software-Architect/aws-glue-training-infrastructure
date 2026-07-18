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
| Reference artifacts | `solutions/**` staged to `scripts/examples/` (trainee-readable) and `scripts/solutions/` (trainee-hidden) | Ü4.1, Ü5.1, Ü6.1, Ü7.2, Ü8.1, Ü9.A |
| Trainee workspaces | `scripts/<username>/{notebooks,scripts}/` per trainee (read+write) | all |
| Reference Glue jobs + state machine *(`enable_reference_jobs`, default on)* | `ref-…-solution` jobs + `ref-orders-pipeline-solution` state machine | Ü5.1, Ü7.2, Ü8.1, Ü9.A |
| IAM role `AWSGlueServiceRole-GfuGlueTraining` | crawlers, jobs, interactive sessions | Ü3.1–Ü8.x |
| IAM role `StepFunctionsGlueExecutionRole-GfuGlueTraining` | Step Functions → Glue | Ü7.2 |
| Athena workgroup `gfu-glue-training` | query-result location set | Ü3.1, Ü5.1 |
| Glue Catalog DBs `raw`, `processed` | catalog targets | Ü3.1, Ü5.1 |
| KMS CMK *(optional, `enable_kms`, default off)* | Security Configuration | Ü8.2 |
| DynamoDB table *(optional, `enable_dynamodb`, default on)* | Block 9 second target | Block 9 |
| IAM users (`trainee_usernames`, default 1) | attendee console + CLI logins (scoped S3, broad Glue/Athena) | all |

**Deliberately NOT created** — the participant builds these live during the exercises:
crawlers, the Glue job `orders-s3-to-parquet`, Glue Workflows, Step Functions state
machines, Security Configurations, interactive sessions.

## Solutions / reference artifacts

`solutions/` holds **compare-after-exercise** reference code — a starter/example and a
worked solution per in-scope exercise (Glue job scripts, interactive-session notebooks,
a Step Functions ASL definition, and the Ü9.A debugging challenge). The scripts target the
same bucket, roles and catalog DBs this stack creates. See
[`solutions/README.md`](solutions/README.md).

**Everything is staged to S3** under `scripts/`, split into two sibling prefixes:

- `scripts/examples/…` — the starters (`example*`, `broken/`). **Trainee-readable.**
- `scripts/solutions/…` — the worked solutions (`solution*`, `fixed/`). **Hidden from
  trainees** by the scoped S3 policy (`aws_iam_policy.trainee_bucket`), which is an
  *allow-list* — `scripts/solutions/` is simply never granted, so it never appears in a
  trainee's listing. There is deliberately **no explicit `Deny`**.

Each trainee also gets a workspace `scripts/<username>/{notebooks,scripts}/` (read+write;
all trainees can see all workspaces). Trainee S3 access is scoped (no `AmazonS3FullAccess`)
to the data prefixes + examples + trainee workspaces; Glue/Athena/Step-Functions access
stays broad.

**`enable_reference_jobs`** (default **on**) registers the solution scripts as runnable
Glue jobs (`ref-…-solution`) and the solution ASL as a state machine
(`ref-orders-pipeline-solution`, whose `JobName` targets the `ref-…` job, not the
live-built `orders-s3-to-parquet`). While on, those jobs are visible in every trainee's
Glue console — set it to `false` to keep the reference jobs out of the sandbox during
teaching (esp. the Ü9.A challenge).

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

## Trainee access

The stack provisions one IAM user **per attendee**, driven by the `trainee_usernames`
variable (default a single `gfu-glue-trainee`; generic by design — no real names, so no
PII in the IaC). Scale to N attendees by listing more names:

```bash
tofu apply -var 'trainee_usernames=["gfu-glue-trainee-1","gfu-glue-trainee-2"]'
```

Each user carries broad AWS-managed `*FullAccess` policies for Glue, S3, Athena, Step
Functions, DynamoDB and CloudWatch Logs, plus `IAMReadOnlyAccess` and an explicit
`iam:PassRole` on the Glue and Step Functions roles — enough to run every exercise,
deliberately over-scoped for a throwaway sandbox.

Fetch the credentials after apply (they live only in the encrypted remote state, never in
this repo). Outputs are maps keyed by username:

```bash
tofu output      trainee_console_url          # shared sign-in URL
tofu output -json trainee_usernames           # ["gfu-glue-trainee"]
tofu output -json trainee_passwords           # {username: initial password (reset forced)}
tofu output -json trainee_access_key_ids      # {username: CLI access key id}
tofu output -json trainee_secret_access_keys  # {username: CLI secret}
```

The users are torn down with the stack (`tofu destroy`), so the logins and keys disappear
after the training. Rotate/destroy promptly once the session is over.

## Manual note — console identity

The console user the participant logs in as needs `iam:PassRole` on the Glue role plus
`glue` interactive-session / notebook permissions to run Ü4.1 / Ü6.1 and to pass the role
to jobs — the provisioned `gfu-glue-trainee` user above already covers this. Flagged here
so it is not a surprise if a different caller identity is used instead.

## Open item

Glue version for jobs (Ü5.1) is chosen at job-creation time in the console, not here.
Confirm the desired version (5.0 vs 4.0) is available in `eu-central-1` before the session.
