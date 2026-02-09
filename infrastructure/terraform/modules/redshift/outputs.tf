# Redshift Module Outputs

output "namespace_name" {
  value = aws_redshiftserverless_namespace.main.namespace_name
}

output "workgroup_name" {
  value = aws_redshiftserverless_workgroup.main.workgroup_name
}

output "endpoint" {
  value     = aws_redshiftserverless_workgroup.main.endpoint
  sensitive = true
}

output "credentials_secret_arn" {
  value = aws_secretsmanager_secret.redshift.arn
}
