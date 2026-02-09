# IAM Module Outputs

output "lambda_role_arn" {
  description = "ARN of the Lambda execution role"
  value       = aws_iam_role.lambda.arn
}

output "lambda_role_name" {
  description = "Name of the Lambda execution role"
  value       = aws_iam_role.lambda.name
}

output "glue_role_arn" {
  description = "ARN of the Glue execution role"
  value       = aws_iam_role.glue.arn
}

output "glue_role_name" {
  description = "Name of the Glue execution role"
  value       = aws_iam_role.glue.name
}

output "redshift_role_arn" {
  description = "ARN of the Redshift execution role"
  value       = aws_iam_role.redshift.arn
}

output "redshift_role_name" {
  description = "Name of the Redshift execution role"
  value       = aws_iam_role.redshift.name
}
