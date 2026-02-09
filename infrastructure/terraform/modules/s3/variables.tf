# S3 Module Variables

variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "bronze_glacier_days" {
  description = "Days before Bronze data transitions to Glacier"
  type        = number
  default     = 365
}

variable "silver_glacier_days" {
  description = "Days before Silver data transitions to Glacier"
  type        = number
  default     = 730
}

variable "temp_expiration_days" {
  description = "Days before temp data is deleted"
  type        = number
  default     = 7
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
