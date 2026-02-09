# S3 Module - Data Lake Storage
# Creates the S3 bucket with medallion architecture structure

resource "aws_s3_bucket" "data" {
  bucket = "${var.name_prefix}-data-${data.aws_caller_identity.current.account_id}"
  
  tags = merge(var.tags, {
    Name = "${var.name_prefix}-data"
  })
}

data "aws_caller_identity" "current" {}

# Enable versioning for audit trail
resource "aws_s3_bucket_versioning" "data" {
  bucket = aws_s3_bucket.data.id
  
  versioning_configuration {
    status = "Enabled"
  }
}

# Server-side encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "data" {
  bucket = aws_s3_bucket.data.id
  
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

# Block public access
resource "aws_s3_bucket_public_access_block" "data" {
  bucket = aws_s3_bucket.data.id
  
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Lifecycle rules for cost optimization
resource "aws_s3_bucket_lifecycle_configuration" "data" {
  bucket = aws_s3_bucket.data.id
  
  # Bronze layer - transition to Glacier after configured days
  rule {
    id     = "bronze-lifecycle"
    status = "Enabled"
    
    filter {
      prefix = "bronze/"
    }
    
    transition {
      days          = 90
      storage_class = "STANDARD_IA"
    }
    
    transition {
      days          = var.bronze_glacier_days
      storage_class = "GLACIER"
    }
    
    # Never delete Bronze data (regulatory requirement)
  }
  
  # Silver layer - similar lifecycle
  rule {
    id     = "silver-lifecycle"
    status = "Enabled"
    
    filter {
      prefix = "silver/"
    }
    
    transition {
      days          = 180
      storage_class = "STANDARD_IA"
    }
    
    transition {
      days          = var.silver_glacier_days
      storage_class = "GLACIER"
    }
  }
  
  # Gold layer - keep in standard (active queries)
  rule {
    id     = "gold-lifecycle"
    status = "Enabled"
    
    filter {
      prefix = "gold/"
    }
    
    # Gold layer stays in standard for performance
    # Old partitions can be deleted (rebuilt from Silver)
    expiration {
      days = 365
    }
  }
  
  # Temp/staging - aggressive cleanup
  rule {
    id     = "temp-lifecycle"
    status = "Enabled"
    
    filter {
      prefix = "temp/"
    }
    
    expiration {
      days = var.temp_expiration_days
    }
  }
  
  # Clean up incomplete multipart uploads
  rule {
    id     = "abort-multipart"
    status = "Enabled"
    
    filter {
      prefix = ""
    }
    
    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

# S3 event notification for ingestion (optional - can be enabled later)
resource "aws_s3_bucket_notification" "data" {
  bucket = aws_s3_bucket.data.id
  
  # This will be configured when Lambda is ready
  # Keeping as placeholder for the architecture
}

# Create folder structure (using empty objects)
resource "aws_s3_object" "folders" {
  for_each = toset([
    "bronze/",
    "silver/",
    "gold/",
    "temp/",
    "metadata/lineage/",
    "metadata/quality/",
    "metadata/schemas/",
    "scripts/glue/"
  ])
  
  bucket  = aws_s3_bucket.data.id
  key     = each.value
  content = ""
}
