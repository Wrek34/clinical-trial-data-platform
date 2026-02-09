# S3 Module Outputs

output "data_bucket_name" {
  description = "Name of the data bucket"
  value       = aws_s3_bucket.data.id
}

output "data_bucket_arn" {
  description = "ARN of the data bucket"
  value       = aws_s3_bucket.data.arn
}

output "data_bucket_domain" {
  description = "Domain name of the data bucket"
  value       = aws_s3_bucket.data.bucket_domain_name
}
