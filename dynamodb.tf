# ── Optional DynamoDB target for Block 9 (default on) ────────────────────────
# Lean second target for the capstone pipeline (orders × customers enriched).
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
