# Lambda Module Variables

variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "lambda_role_arn" {
  description = "IAM role ARN for Lambda execution"
  type        = string
}

variable "data_bucket_name" {
  description = "Name of the data bucket"
  type        = string
}

variable "data_bucket_arn" {
  description = "ARN of the data bucket"
  type        = string
}

variable "lambda_environment" {
  description = "Environment variables for Lambda"
  type        = map(string)
  default     = {}
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
