# Glue Module Outputs

output "bronze_to_silver_job_name" {
  value = aws_glue_job.bronze_to_silver.name
}

output "silver_to_gold_job_name" {
  value = aws_glue_job.silver_to_gold.name
}

output "catalog_database_name" {
  value = aws_glue_catalog_database.main.name
}

output "bronze_crawler_name" {
  value = aws_glue_crawler.bronze.name
}

output "silver_crawler_name" {
  value = aws_glue_crawler.silver.name
}
