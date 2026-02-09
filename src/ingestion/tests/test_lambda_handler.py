"""
Unit tests for the ingestion Lambda handler.

Uses moto to mock AWS services for isolated testing.
"""

import json
import os
from unittest.mock import MagicMock, patch

import pytest
from moto import mock_aws

# Set environment variables before importing handler
os.environ["DATA_BUCKET"] = "test-bucket"
os.environ["ENVIRONMENT"] = "test"
os.environ["LOG_LEVEL"] = "DEBUG"


@pytest.fixture
def aws_credentials():
    """Mock AWS credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


@pytest.fixture
def s3_client(aws_credentials):
    """Create mock S3 client."""
    with mock_aws():
        import boto3
        
        client = boto3.client("s3", region_name="us-east-1")
        
        # Create test buckets
        client.create_bucket(Bucket="test-bucket")
        client.create_bucket(Bucket="source-bucket")
        
        yield client


@pytest.fixture
def sample_s3_event():
    """Generate a sample S3 event for testing."""
    return {
        "Records": [
            {
                "eventVersion": "2.1",
                "eventSource": "aws:s3",
                "awsRegion": "us-east-1",
                "eventTime": "2024-01-15T12:00:00.000Z",
                "eventName": "ObjectCreated:Put",
                "s3": {
                    "bucket": {
                        "name": "source-bucket"
                    },
                    "object": {
                        "key": "landing/edc-system/dm/demographics_20240115.csv",
                        "size": 1024
                    }
                }
            }
        ]
    }


class TestValidateFile:
    """Tests for file validation function."""
    
    def test_validate_valid_csv(self, s3_client):
        """Test validation passes for valid CSV file."""
        from src.ingestion.lambda_handler import validate_file
        
        # Create test file
        s3_client.put_object(
            Bucket="source-bucket",
            Key="test.csv",
            Body=b"col1,col2\nval1,val2"
        )
        
        result = validate_file("source-bucket", "test.csv", 100)
        
        assert result["valid"] is True
    
    def test_validate_empty_file(self, s3_client):
        """Test validation fails for empty file."""
        from src.ingestion.lambda_handler import validate_file
        
        result = validate_file("source-bucket", "test.csv", 0)
        
        assert result["valid"] is False
        assert "Empty file" in result["reason"]
    
    def test_validate_invalid_extension(self, s3_client):
        """Test validation fails for invalid file extension."""
        from src.ingestion.lambda_handler import validate_file
        
        s3_client.put_object(
            Bucket="source-bucket",
            Key="test.exe",
            Body=b"binary content"
        )
        
        result = validate_file("source-bucket", "test.exe", 100)
        
        assert result["valid"] is False
        assert "Invalid file type" in result["reason"]
    
    def test_validate_file_too_large(self, s3_client):
        """Test validation fails for oversized file."""
        from src.ingestion.lambda_handler import validate_file
        
        # 6GB file (over 5GB limit)
        size = 6 * 1024 * 1024 * 1024
        
        result = validate_file("source-bucket", "test.csv", size)
        
        assert result["valid"] is False
        assert "too large" in result["reason"]


class TestParseFilePath:
    """Tests for file path parsing function."""
    
    def test_parse_valid_path(self):
        """Test parsing a valid file path."""
        from src.ingestion.lambda_handler import parse_file_path
        
        key = "landing/edc-system/dm/demographics_20240115.csv"
        result = parse_file_path(key)
        
        assert result["source"] == "edc-system"
        assert result["domain"] == "dm"
        assert result["filename"] == "demographics_20240115.csv"
        assert result["extension"] == "csv"
    
    def test_parse_parquet_extension(self):
        """Test parsing parquet file extension."""
        from src.ingestion.lambda_handler import parse_file_path
        
        key = "landing/lab-system/lb/results.parquet"
        result = parse_file_path(key)
        
        assert result["extension"] == "parquet"
    
    def test_parse_invalid_path(self):
        """Test parsing an invalid/unexpected path."""
        from src.ingestion.lambda_handler import parse_file_path
        
        key = "random/file.csv"
        result = parse_file_path(key)
        
        # Should return defaults for unrecognized format
        assert result["source"] == "unknown"
        assert result["domain"] == "unknown"
        assert result["filename"] == "file.csv"


class TestGenerateMetadata:
    """Tests for metadata generation function."""
    
    def test_generate_metadata(self):
        """Test metadata generation."""
        from src.ingestion.lambda_handler import generate_metadata
        
        file_info = {
            "source": "edc-system",
            "domain": "dm",
            "filename": "test.csv",
            "extension": "csv"
        }
        
        result = generate_metadata(
            bucket="source-bucket",
            key="landing/edc-system/dm/test.csv",
            size=1024,
            file_info=file_info
        )
        
        assert "ingestion_id" in result
        assert "ingestion_timestamp" in result
        assert result["source_system"] == "edc-system"
        assert result["domain"] == "dm"
        assert result["file_size_bytes"] == 1024
        assert result["environment"] == "test"


class TestHandler:
    """Integration tests for the main handler function."""
    
    def test_handler_success(self, s3_client, sample_s3_event):
        """Test successful file processing."""
        from src.ingestion.lambda_handler import handler
        
        # Create source file
        s3_client.put_object(
            Bucket="source-bucket",
            Key="landing/edc-system/dm/demographics_20240115.csv",
            Body=b"usubjid,age,sex\nSUBJ001,45,M"
        )
        
        # Mock context
        context = MagicMock()
        context.aws_request_id = "test-request-id"
        
        result = handler(sample_s3_event, context)
        
        assert result["statusCode"] == 200
        assert result["body"]["processed"] == 1
        assert result["body"]["successful"] == 1
        assert result["body"]["failed"] == 0
    
    def test_handler_empty_event(self):
        """Test handler with empty event."""
        from src.ingestion.lambda_handler import handler
        
        result = handler({}, None)
        
        assert result["statusCode"] == 200
        assert result["body"]["processed"] == 0


class TestMoveToBronze:
    """Tests for Bronze layer file movement."""
    
    def test_bronze_path_format(self, s3_client):
        """Test that Bronze path follows expected format."""
        from src.ingestion.lambda_handler import move_to_bronze
        
        # Create source file
        s3_client.put_object(
            Bucket="source-bucket",
            Key="landing/edc-system/dm/test.csv",
            Body=b"test data"
        )
        
        file_info = {
            "source": "edc-system",
            "domain": "dm",
            "filename": "test.csv",
            "extension": "csv"
        }
        
        metadata = {
            "ingestion_id": "test-uuid-1234",
            "ingestion_timestamp": "2024-01-15T12:00:00+00:00"
        }
        
        bronze_key = move_to_bronze(
            bucket="source-bucket",
            source_key="landing/edc-system/dm/test.csv",
            file_info=file_info,
            metadata=metadata
        )
        
        # Verify path format
        assert bronze_key.startswith("bronze/edc-system/dm/")
        assert "year=2024" in bronze_key
        assert "month=01" in bronze_key
        assert "day=15" in bronze_key
        assert "test.csv" in bronze_key
        
        # Verify file exists in Bronze
        response = s3_client.head_object(Bucket="test-bucket", Key=bronze_key)
        assert response is not None


# Fixtures for pytest discovery
pytest_plugins = []
