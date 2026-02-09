# Clinical Trial Data Platform - Terraform Variables

# =============================================================================
# GENERAL
# =============================================================================

variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "owner" {
  description = "Owner of the resources (for tagging)"
  type        = string
  default     = "data-engineering"
}

# =============================================================================
# S3 CONFIGURATION
# =============================================================================

variable "bronze_glacier_transition_days" {
  description = "Days before Bronze data transitions to Glacier"
  type        = number
  default     = 365
}

variable "silver_glacier_transition_days" {
  description = "Days before Silver data transitions to Glacier"
  type        = number
  default     = 730
}

variable "temp_expiration_days" {
  description = "Days before temp/staging data is deleted"
  type        = number
  default     = 7
}

# =============================================================================
# GLUE CONFIGURATION
# =============================================================================

variable "glue_worker_type" {
  description = "Glue worker type (G.1X, G.2X, G.4X)"
  type        = string
  default     = "G.1X"
}

variable "glue_number_of_workers" {
  description = "Number of Glue workers"
  type        = number
  default     = 2
}

# =============================================================================
# REDSHIFT CONFIGURATION
# =============================================================================

variable "redshift_base_capacity" {
  description = "Base RPU capacity for Redshift Serverless"
  type        = number
  default     = 8
}

variable "redshift_max_capacity" {
  description = "Maximum RPU capacity for Redshift Serverless"
  type        = number
  default     = 64
}

# =============================================================================
# MONITORING
# =============================================================================

variable "alert_email" {
  description = "Email address for alerts"
  type        = string
  default     = ""
}

variable "budget_threshold" {
  description = "Monthly budget threshold in USD"
  type        = number
  default     = 50
}
