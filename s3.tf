# ── Data-lake bucket ─────────────────────────────────────────────────────────
# One bucket holds raw/, processed/, temp/, athena-results/ and a seed/ staging
# area. force_destroy lets `tofu destroy` remove it cleanly after the training,
# including any Parquet/query output the participant produced (R11).

resource "aws_s3_bucket" "lake" {
  bucket        = local.bucket_name
  force_destroy = true
}

resource "aws_s3_bucket_public_access_block" "lake" {
  bucket = aws_s3_bucket.lake.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "lake" {
  bucket = aws_s3_bucket.lake.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# ── Empty prefix markers ─────────────────────────────────────────────────────
# raw/orders/ and raw/customers/ are created implicitly by the seed objects
# below; these are the prefixes the exercises reference but that start empty.

resource "aws_s3_object" "prefixes" {
  for_each = toset([
    "processed/",
    "temp/",
    "athena-results/",
  ])

  bucket       = aws_s3_bucket.lake.id
  key          = each.value
  content_type = "application/x-directory"
}

# ── Seed datasets ────────────────────────────────────────────────────────────
# orders.csv  → raw/orders/   (Ü3.1 source; reused in Ü4.1, Ü5.1, Block 9)
# customers.json → raw/customers/ (Ü6.1 nested-JSON source; second Block 9 source)
# events.json → raw/events/ (Block 9 capstone source: NEW nested clickstream, never
#                used in B1–B8; view/add_to_cart/purchase, price as string (Choice),
#                customer_ids consistent with customers.json, dates overlap orders.csv)
# orders_2.csv → seed/ (NOT raw/orders/ — the participant copies it in during
#                Ü8.1 to trigger the incremental bookmark run)
# serverlog.log → raw/serverlog/ (Ü-D custom-classifier source: app log no built-in
#                classifier parses; the trainee builds a Grok classifier)

resource "aws_s3_object" "orders" {
  bucket = aws_s3_bucket.lake.id
  key    = "raw/orders/orders.csv"
  source = "${path.module}/data/orders.csv"
  etag   = filemd5("${path.module}/data/orders.csv")
}

resource "aws_s3_object" "customers" {
  bucket = aws_s3_bucket.lake.id
  key    = "raw/customers/customers.json"
  source = "${path.module}/data/customers.json"
  etag   = filemd5("${path.module}/data/customers.json")
}

resource "aws_s3_object" "events" {
  bucket = aws_s3_bucket.lake.id
  key    = "raw/events/events.json"
  source = "${path.module}/data/events.json"
  etag   = filemd5("${path.module}/data/events.json")
}

resource "aws_s3_object" "orders_2_seed" {
  bucket = aws_s3_bucket.lake.id
  key    = "seed/orders_2.csv"
  source = "${path.module}/data/orders_2.csv"
  etag   = filemd5("${path.module}/data/orders_2.csv")
}

resource "aws_s3_object" "serverlog" {
  bucket = aws_s3_bucket.lake.id
  key    = "raw/serverlog/serverlog.log"
  source = "${path.module}/data/serverlog.log"
  etag   = filemd5("${path.module}/data/serverlog.log")
}

# ── Reference artifacts staged under scripts/ ────────────────────────────────
# Every artifact under solutions/ is mirrored into two sibling prefixes:
#   scripts/examples/…   — trainee-READABLE starters   (example*, broken/**)
#   scripts/solutions/…  — trainee-INVISIBLE solutions  (solution*, fixed/**)
# READMEs match neither classification and are intentionally not staged. The
# examples/solutions split is enforced for trainees by the scoped IAM policy in
# trainee.tf (allow-list; scripts/solutions/ is simply never granted).

locals {
  solutions_dir = "${path.module}/solutions"

  # examples ← example* + broken/**   ;   solutions ← solution* + fixed/**
  # __pycache__/ fliegt raus: die Globs greifen sonst auch
  # <übung>/__pycache__/example_*.cpython-*.pyc — gitignored, aber lokal
  # vorhanden, ein Apply vom Entwicklerrechner lüde Bytecode in die Sandbox.
  example_files = toset([
    for f in concat(
      tolist(fileset(local.solutions_dir, "**/example*")),
      tolist(fileset(local.solutions_dir, "**/broken/**")),
    ) : f if !strcontains(f, "__pycache__/")
  ])
  solution_files = toset([
    for f in concat(
      tolist(fileset(local.solutions_dir, "**/solution*")),
      tolist(fileset(local.solutions_dir, "**/fixed/**")),
    ) : f if !strcontains(f, "__pycache__/")
  ])

  # content_type keyed by the last dotted segment (handles *.asl.json → "json").
  script_content_types = {
    py    = "text/x-python"
    ipynb = "application/x-ipynb+json"
    json  = "application/json"
  }
}

resource "aws_s3_object" "example_scripts" {
  for_each = local.example_files

  bucket       = aws_s3_bucket.lake.id
  key          = "scripts/examples/${each.value}"
  source       = "${local.solutions_dir}/${each.value}"
  etag         = filemd5("${local.solutions_dir}/${each.value}")
  content_type = lookup(local.script_content_types, element(reverse(split(".", each.value)), 0), "application/octet-stream")
}

resource "aws_s3_object" "solution_scripts" {
  for_each = local.solution_files

  bucket       = aws_s3_bucket.lake.id
  key          = "scripts/solutions/${each.value}"
  source       = "${local.solutions_dir}/${each.value}"
  etag         = filemd5("${local.solutions_dir}/${each.value}")
  content_type = lookup(local.script_content_types, element(reverse(split(".", each.value)), 0), "application/octet-stream")
}

# ── Blueprint seed (Ü7.3, optional) ──────────────────────────────────────────
# A Glue Blueprint is a ZIP of layout.py + blueprint.cfg. The AWS provider has NO
# aws_glue_blueprint resource, so the stack only STAGES the ZIP in S3 (built at
# apply from the source dir); the trainee registers + runs it in the console
# (CreateBlueprint / StartBlueprintRun). It lives under scripts/examples/ so the
# scoped trainee policy already grants read access; the two source files match
# none of the example*/solution*/broken/fixed globs above, so they are not
# double-seeded as loose scripts.

data "archive_file" "blueprint" {
  type        = "zip"
  source_dir  = "${path.module}/solutions/ue7.3-blueprint/blueprint"
  output_path = "${path.module}/.build/orders-pipeline-blueprint.zip"
}

resource "aws_s3_object" "blueprint" {
  bucket       = aws_s3_bucket.lake.id
  key          = "scripts/examples/blueprints/orders-pipeline.zip"
  source       = data.archive_file.blueprint.output_path
  etag         = data.archive_file.blueprint.output_md5
  content_type = "application/zip"
}

# ── Per-trainee workspaces ───────────────────────────────────────────────────
# One folder per trainee with notebooks/ + scripts/ sub-prefixes where they save
# their own work. All trainees can see all trainee folders (shared policy).

resource "aws_s3_object" "trainee_workspaces" {
  for_each = {
    for pair in setproduct(tolist(var.trainee_usernames), ["notebooks/", "scripts/"]) :
    "scripts/${pair[0]}/${pair[1]}" => true
  }

  bucket       = aws_s3_bucket.lake.id
  key          = each.key
  content_type = "application/x-directory"
}
