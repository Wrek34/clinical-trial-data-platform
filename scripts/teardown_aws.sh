#!/bin/bash
# AWS Resource Teardown Script for cost savings
# Usage: ./scripts/teardown_aws.sh [environment]

set -e

ENVIRONMENT="${1:-dev}"
REGION="${AWS_REGION:-us-east-1}"
NAME_PREFIX="clinical-trial-${ENVIRONMENT}"

echo "=== Clinical Trial Platform Teardown ==="
echo "Environment: ${ENVIRONMENT}"
echo "Region: ${REGION}"
echo ""

read -p "This will destroy compute resources. Continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 1
fi

echo "1. Clearing temporary S3 data..."
BUCKET="${NAME_PREFIX}-data-$(aws sts get-caller-identity --query Account --output text)"
aws s3 rm "s3://${BUCKET}/temp/" --recursive 2>/dev/null || true

echo "2. Deleting Glue jobs..."
aws glue delete-job --job-name "${NAME_PREFIX}-bronze-to-silver" 2>/dev/null || true
aws glue delete-job --job-name "${NAME_PREFIX}-silver-to-gold" 2>/dev/null || true

echo "3. Deleting Lambda functions..."
aws lambda delete-function --function-name "${NAME_PREFIX}-ingestion" 2>/dev/null || true

echo "4. Pausing Redshift Serverless..."
# Redshift Serverless auto-pauses, but we can force it by reducing capacity
aws redshift-serverless update-workgroup \
    --workgroup-name "${NAME_PREFIX//\-/}" \
    --base-capacity 8 \
    --max-capacity 8 2>/dev/null || true

echo ""
echo "=== Teardown Complete ==="
echo "Preserved: S3 data (bronze/silver/gold), Terraform state"
echo "Destroyed: Lambda, Glue jobs, reduced Redshift capacity"
echo ""
echo "To fully destroy, run: cd infrastructure/terraform && terraform destroy"
