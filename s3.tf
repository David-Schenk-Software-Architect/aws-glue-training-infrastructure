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
# orders_2.csv → seed/ (NOT raw/orders/ — the participant copies it in during
#                Ü8.1 to trigger the incremental bookmark run)

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

resource "aws_s3_object" "orders_2_seed" {
  bucket = aws_s3_bucket.lake.id
  key    = "seed/orders_2.csv"
  source = "${path.module}/data/orders_2.csv"
  etag   = filemd5("${path.module}/data/orders_2.csv")
}
