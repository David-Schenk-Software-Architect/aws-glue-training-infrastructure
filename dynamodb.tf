# ── Optional DynamoDB target for Ü-G (default on) ────────────────────────────
# Lean non-S3 target: Ü-G writes orders × customers enriched and reads it back.
# PAY_PER_REQUEST => no standing capacity cost; storage at training scale ~free.

resource "aws_dynamodb_table" "orders_enriched" {
  count = var.enable_dynamodb ? 1 : 0

  name         = "${var.project}-orders-enriched"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "customer_id"

  attribute {
    name = "customer_id"
    type = "S"
  }
}
