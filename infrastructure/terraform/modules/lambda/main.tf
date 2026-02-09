# Lambda Module - Ingestion Functions

# Lambda function for data ingestion
resource "aws_lambda_function" "ingestion" {
  function_name = "${var.name_prefix}-ingestion"
  description   = "Processes incoming clinical trial data and routes to Bronze layer"
  
  role = var.lambda_role_arn
  
  # Runtime configuration
  runtime       = "python3.11"
  handler       = "lambda_handler.handler"
  timeout       = 300  # 5 minutes
  memory_size   = 512
  
  # Code will be deployed separately via CI/CD
  # Using placeholder for initial deployment
  filename         = data.archive_file.lambda_placeholder.output_path
  source_code_hash = data.archive_file.lambda_placeholder.output_base64sha256
  
  environment {
    variables = var.lambda_environment
  }
  
  tags = var.tags
}

# Placeholder code for initial deployment
data "archive_file" "lambda_placeholder" {
  type        = "zip"
  output_path = "${path.module}/lambda_placeholder.zip"
  
  source {
    content  = <<-EOT
      def handler(event, context):
          """Placeholder handler - deploy real code via CI/CD."""
          return {"statusCode": 200, "body": "Placeholder"}
    EOT
    filename = "lambda_handler.py"
  }
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "ingestion" {
  name              = "/aws/lambda/${aws_lambda_function.ingestion.function_name}"
  retention_in_days = var.environment == "prod" ? 365 : 7
  
  tags = var.tags
}

# S3 trigger permission
resource "aws_lambda_permission" "s3" {
  statement_id  = "AllowS3Invoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ingestion.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = var.data_bucket_arn
}

# Dead Letter Queue for failed invocations
resource "aws_sqs_queue" "dlq" {
  name                      = "${var.name_prefix}-ingestion-dlq"
  message_retention_seconds = 1209600  # 14 days
  
  tags = var.tags
}

# Connect DLQ to Lambda
resource "aws_lambda_function_event_invoke_config" "ingestion" {
  function_name = aws_lambda_function.ingestion.function_name
  
  destination_config {
    on_failure {
      destination = aws_sqs_queue.dlq.arn
    }
  }
}
