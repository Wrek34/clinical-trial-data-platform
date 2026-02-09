# Redshift Module - Serverless Data Warehouse

# Redshift Serverless Namespace
resource "aws_redshiftserverless_namespace" "main" {
  namespace_name      = replace(var.name_prefix, "-", "")
  db_name             = "clinical_trial"
  admin_username      = "admin"
  admin_user_password = random_password.redshift.result
  
  iam_roles = [var.redshift_role_arn]
  
  tags = var.tags
}

# Random password for Redshift admin
resource "random_password" "redshift" {
  length  = 32
  special = false  # Redshift has restrictions on special chars
}

# Store password in Secrets Manager
resource "aws_secretsmanager_secret" "redshift" {
  name        = "${var.name_prefix}-redshift-credentials"
  description = "Redshift Serverless admin credentials"
  
  tags = var.tags
}

resource "aws_secretsmanager_secret_version" "redshift" {
  secret_id = aws_secretsmanager_secret.redshift.id
  
  secret_string = jsonencode({
    username = "admin"
    password = random_password.redshift.result
    dbname   = "clinical_trial"
  })
}

# Redshift Serverless Workgroup
resource "aws_redshiftserverless_workgroup" "main" {
  namespace_name = aws_redshiftserverless_namespace.main.namespace_name
  workgroup_name = replace(var.name_prefix, "-", "")
  
  base_capacity = var.base_capacity
  max_capacity  = var.max_capacity
  
  publicly_accessible = false
  
  tags = var.tags
}
