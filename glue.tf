# ── Glue Data Catalog databases ──────────────────────────────────────────────
# `raw` receives the crawler-catalogued orders/customers tables (Ü3.1/Ü6.1);
# `processed` receives the Parquet output of the ETL job (Ü5.1). Pre-created so
# the exercises can point straight at them.

resource "aws_glue_catalog_database" "raw" {
  name        = "raw"
  description = "GFU Glue training – raw source tables (orders, customers)."
}

resource "aws_glue_catalog_database" "processed" {
  name        = "processed"
  description = "GFU Glue training – processed Parquet output tables."
}
