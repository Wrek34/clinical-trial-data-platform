# Clinical Trial Data Platform - Main Terraform Configuration
# This file orchestrates all AWS resources for the data platform

terraform {
  required_version = ">= 1.5.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# AWS Provider Configuration
provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = "clinical-trial-data-platform"
      Environment = var.environment
      ManagedBy   = "terraform"
      Owner       = var.owner
    }
  }
}

# Data source for current AWS account
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# Local values for resource naming
locals {
  name_prefix = "clinical-trial-${var.environment}"
  account_id  = data.aws_caller_identity.current.account_id
  region      = data.aws_region.current.name
  
  common_tags = {
    Project     = "clinical-trial-data-platform"
    Environment = var.environment
  }
}

# =============================================================================
# S3 MODULE - Data Lake Storage
# =============================================================================

module "s3" {
  source = "./modules/s3"
  
  name_prefix     = local.name_prefix
  environment     = var.environment
  
  # Lifecycle configuration
  bronze_glacier_days   = var.bronze_glacier_transition_days
  silver_glacier_days   = var.silver_glacier_transition_days
  temp_expiration_days  = var.temp_expiration_days
  
  tags = local.common_tags
}

# =============================================================================
# IAM MODULE - Roles and Policies
# =============================================================================

module "iam" {
  source = "./modules/iam"
  
  name_prefix     = local.name_prefix
  environment     = var.environment
  account_id      = local.account_id
  region          = local.region
  
  # S3 bucket ARNs for policy attachment
  data_bucket_arn = module.s3.data_bucket_arn
  
  tags = local.common_tags
}

# =============================================================================
# LAMBDA MODULE - Ingestion Functions
# =============================================================================

module "lambda" {
  source = "./modules/lambda"
  
  name_prefix     = local.name_prefix
  environment     = var.environment
  
  # IAM role for Lambda execution
  lambda_role_arn = module.iam.lambda_role_arn
  
  # S3 configuration
  data_bucket_name = module.s3.data_bucket_name
  data_bucket_arn  = module.s3.data_bucket_arn
  
  # Environment variables for Lambda
  lambda_environment = {
    ENVIRONMENT     = var.environment
    DATA_BUCKET     = module.s3.data_bucket_name
    LOG_LEVEL       = var.environment == "prod" ? "INFO" : "DEBUG"
  }
  
  tags = local.common_tags
}

# =============================================================================
# GLUE MODULE - ETL Jobs
# =============================================================================

module "glue" {
  source = "./modules/glue"
  
  name_prefix     = local.name_prefix
  environment     = var.environment
  
  # IAM role for Glue jobs
  glue_role_arn = module.iam.glue_role_arn
  
  # S3 configuration
  data_bucket_name = module.s3.data_bucket_name
  scripts_bucket   = module.s3.data_bucket_name
  
  # Glue job configuration
  glue_version          = "4.0"
  worker_type           = var.glue_worker_type
  number_of_workers     = var.glue_number_of_workers
  
  tags = local.common_tags
}

# =============================================================================
# REDSHIFT MODULE - Commented out (requires subscription)
# =============================================================================
# Uncomment this section after enabling Redshift in your AWS account
# 
# module "redshift" {
#   source = "./modules/redshift"
#   
#   name_prefix     = local.name_prefix
#   environment     = var.environment
#   
#   redshift_role_arn = module.iam.redshift_role_arn
#   
#   base_capacity = var.redshift_base_capacity
#   max_capacity  = var.redshift_max_capacity
#   
#   data_bucket_arn = module.s3.data_bucket_arn
#   
#   tags = local.common_tags
# }

# =============================================================================
# MONITORING - CloudWatch Alarms and SNS
# =============================================================================

resource "aws_sns_topic" "alerts" {
  name = "${local.name_prefix}-alerts"
  
  tags = local.common_tags
}

resource "aws_sns_topic_subscription" "email" {
  count     = var.alert_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# Budget alarm
resource "aws_cloudwatch_metric_alarm" "billing" {
  count               = var.environment == "prod" ? 1 : 0
  alarm_name          = "${local.name_prefix}-billing-alarm"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "EstimatedCharges"
  namespace           = "AWS/Billing"
  period              = 86400
  statistic           = "Maximum"
  threshold           = var.budget_threshold
  alarm_description   = "Billing alarm when estimated charges exceed threshold"
  
  dimensions = {
    Currency = "USD"
  }
  
  alarm_actions = [aws_sns_topic.alerts.arn]
  
  tags = local.common_tags
}
