# Clinical Trial Data Platform - Terraform Outputs

# =============================================================================
# S3 OUTPUTS
# =============================================================================

output "data_bucket_name" {
  description = "Name of the main data bucket"
  value       = module.s3.data_bucket_name
}

output "data_bucket_arn" {
  description = "ARN of the main data bucket"
  value       = module.s3.data_bucket_arn
}

output "bronze_prefix" {
  description = "S3 prefix for Bronze layer"
  value       = "s3://${module.s3.data_bucket_name}/bronze/"
}

output "silver_prefix" {
  description = "S3 prefix for Silver layer"
  value       = "s3://${module.s3.data_bucket_name}/silver/"
}

output "gold_prefix" {
  description = "S3 prefix for Gold layer"
  value       = "s3://${module.s3.data_bucket_name}/gold/"
}

# =============================================================================
# LAMBDA OUTPUTS
# =============================================================================

output "ingestion_lambda_arn" {
  description = "ARN of the ingestion Lambda function"
  value       = module.lambda.ingestion_function_arn
}

output "ingestion_lambda_name" {
  description = "Name of the ingestion Lambda function"
  value       = module.lambda.ingestion_function_name
}

# =============================================================================
# GLUE OUTPUTS
# =============================================================================

output "bronze_to_silver_job_name" {
  description = "Name of the Bronze to Silver Glue job"
  value       = module.glue.bronze_to_silver_job_name
}

output "silver_to_gold_job_name" {
  description = "Name of the Silver to Gold Glue job"
  value       = module.glue.silver_to_gold_job_name
}

# =============================================================================
# IAM OUTPUTS
# =============================================================================

output "lambda_role_arn" {
  description = "ARN of the Lambda execution role"
  value       = module.iam.lambda_role_arn
}

output "glue_role_arn" {
  description = "ARN of the Glue execution role"
  value       = module.iam.glue_role_arn
}

# =============================================================================
# MONITORING OUTPUTS
# =============================================================================

output "sns_topic_arn" {
  description = "ARN of the alerts SNS topic"
  value       = aws_sns_topic.alerts.arn
}

# =============================================================================
# SUMMARY
# =============================================================================

output "deployment_summary" {
  description = "Summary of deployed resources"
  value = <<-EOT
    
    =====================================================
    Clinical Trial Data Platform - Deployment Summary
    =====================================================
    
    Environment: ${var.environment}
    Region:      ${var.aws_region}
    
    S3 Data Lake:
      Bucket: ${module.s3.data_bucket_name}
      Bronze: s3://${module.s3.data_bucket_name}/bronze/
      Silver: s3://${module.s3.data_bucket_name}/silver/
      Gold:   s3://${module.s3.data_bucket_name}/gold/
    
    Lambda Functions:
      Ingestion: ${module.lambda.ingestion_function_name}
    
    Glue Jobs:
      Bronze -> Silver: ${module.glue.bronze_to_silver_job_name}
      Silver -> Gold:   ${module.glue.silver_to_gold_job_name}
    
    Note: Redshift Serverless not deployed (requires subscription)
    
    =====================================================
  EOT
}
