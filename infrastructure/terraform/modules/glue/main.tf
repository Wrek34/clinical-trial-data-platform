# Glue Module - ETL Jobs

# Glue Catalog Database
resource "aws_glue_catalog_database" "main" {
  name        = replace("${var.name_prefix}_db", "-", "_")
  description = "Clinical trial data catalog"
}

# Bronze to Silver ETL Job
resource "aws_glue_job" "bronze_to_silver" {
  name     = "${var.name_prefix}-bronze-to-silver"
  role_arn = var.glue_role_arn
  
  glue_version      = var.glue_version
  worker_type       = var.worker_type
  number_of_workers = var.number_of_workers
  
  command {
    name            = "glueetl"
    script_location = "s3://${var.data_bucket_name}/scripts/glue/bronze_to_silver.py"
    python_version  = "3"
  }
  
  default_arguments = {
    "--job-language"                     = "python"
    "--job-bookmark-option"              = "job-bookmark-enable"
    "--enable-metrics"                   = "true"
    "--enable-continuous-cloudwatch-log" = "true"
    "--enable-glue-datacatalog"          = "true"
    "--DATA_BUCKET"                      = var.data_bucket_name
    "--ENVIRONMENT"                      = var.environment
    "--additional-python-modules"        = "great-expectations==0.18.0"
  }
  
  execution_property {
    max_concurrent_runs = 1
  }
  
  tags = var.tags
}

# Silver to Gold ETL Job
resource "aws_glue_job" "silver_to_gold" {
  name     = "${var.name_prefix}-silver-to-gold"
  role_arn = var.glue_role_arn
  
  glue_version      = var.glue_version
  worker_type       = var.worker_type
  number_of_workers = var.number_of_workers
  
  command {
    name            = "glueetl"
    script_location = "s3://${var.data_bucket_name}/scripts/glue/silver_to_gold.py"
    python_version  = "3"
  }
  
  default_arguments = {
    "--job-language"                     = "python"
    "--job-bookmark-option"              = "job-bookmark-enable"
    "--enable-metrics"                   = "true"
    "--enable-continuous-cloudwatch-log" = "true"
    "--enable-glue-datacatalog"          = "true"
    "--DATA_BUCKET"                      = var.data_bucket_name
    "--ENVIRONMENT"                      = var.environment
  }
  
  execution_property {
    max_concurrent_runs = 1
  }
  
  tags = var.tags
}

# Glue Crawler for Bronze layer
resource "aws_glue_crawler" "bronze" {
  name          = "${var.name_prefix}-bronze-crawler"
  role          = var.glue_role_arn
  database_name = aws_glue_catalog_database.main.name
  
  s3_target {
    path = "s3://${var.data_bucket_name}/bronze/"
  }
  
  schema_change_policy {
    delete_behavior = "LOG"
    update_behavior = "UPDATE_IN_DATABASE"
  }
  
  tags = var.tags
}

# Glue Crawler for Silver layer
resource "aws_glue_crawler" "silver" {
  name          = "${var.name_prefix}-silver-crawler"
  role          = var.glue_role_arn
  database_name = aws_glue_catalog_database.main.name
  
  s3_target {
    path = "s3://${var.data_bucket_name}/silver/"
  }
  
  schema_change_policy {
    delete_behavior = "LOG"
    update_behavior = "UPDATE_IN_DATABASE"
  }
  
  tags = var.tags
}
