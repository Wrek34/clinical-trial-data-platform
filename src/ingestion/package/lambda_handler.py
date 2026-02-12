"""
Clinical Trial Data Ingestion Lambda Handler

This Lambda function processes incoming clinical trial data files,
validates them, adds metadata, and routes them to the Bronze layer.

Author: [Your Name]
"""

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any
from urllib.parse import unquote_plus

import boto3
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

# Initialize AWS clients
s3_client = boto3.client("s3")

# Environment variables
DATA_BUCKET = os.environ.get("DATA_BUCKET")
ENVIRONMENT = os.environ.get("ENVIRONMENT", "dev")


class IngestionError(Exception):
    """Custom exception for ingestion errors."""
    pass


def handler(event: dict, context: Any) -> dict:
    """
    Main Lambda handler for data ingestion.
    
    Processes S3 events when new files are uploaded to the landing zone,
    validates the files, adds metadata, and moves them to the Bronze layer.
    
    Args:
        event: S3 event notification
        context: Lambda context
        
    Returns:
        dict: Processing result with status and details
    """
    logger.info(f"Processing event: {json.dumps(event)}")
    
    results = []
    
    for record in event.get("Records", []):
        try:
            result = process_record(record)
            results.append(result)
        except Exception as e:
            logger.error(f"Error processing record: {str(e)}")
            results.append({
                "status": "error",
                "error": str(e),
                "record": record
            })
    
    # Determine overall status
    errors = [r for r in results if r.get("status") == "error"]
    
    return {
        "statusCode": 200 if not errors else 207,  # 207 = Multi-Status
        "body": {
            "processed": len(results),
            "successful": len(results) - len(errors),
            "failed": len(errors),
            "results": results
        }
    }


def process_record(record: dict) -> dict:
    """
    Process a single S3 event record.
    
    Args:
        record: S3 event record
        
    Returns:
        dict: Processing result
    """
    # Extract S3 information
    bucket = record["s3"]["bucket"]["name"]
    key = unquote_plus(record["s3"]["object"]["key"])
    size = record["s3"]["object"].get("size", 0)
    
    logger.info(f"Processing file: s3://{bucket}/{key}")
    
    # Validate file
    validation_result = validate_file(bucket, key, size)
    if not validation_result["valid"]:
        raise IngestionError(f"Validation failed: {validation_result['reason']}")
    
    # Determine domain and source from path
    file_info = parse_file_path(key)
    
    # Generate metadata
    metadata = generate_metadata(bucket, key, size, file_info)
    
    # Move to Bronze layer
    bronze_key = move_to_bronze(bucket, key, file_info, metadata)
    
    # Write lineage record
    write_lineage(metadata, bronze_key)
    
    return {
        "status": "success",
        "source_key": key,
        "bronze_key": bronze_key,
        "metadata": metadata
    }


def validate_file(bucket: str, key: str, size: int) -> dict:
    """
    Validate an incoming file.
    
    Args:
        bucket: S3 bucket name
        key: S3 object key
        size: File size in bytes
        
    Returns:
        dict: Validation result with 'valid' bool and 'reason' if invalid
    """
    # Check file size (max 5GB for this example)
    max_size = 5 * 1024 * 1024 * 1024  # 5GB
    if size > max_size:
        return {"valid": False, "reason": f"File too large: {size} bytes"}
    
    if size == 0:
        return {"valid": False, "reason": "Empty file"}
    
    # Check file extension
    valid_extensions = [".csv", ".parquet", ".json", ".xml"]
    if not any(key.lower().endswith(ext) for ext in valid_extensions):
        return {"valid": False, "reason": f"Invalid file type: {key}"}
    
    # Check if file exists and is readable
    try:
        s3_client.head_object(Bucket=bucket, Key=key)
    except ClientError as e:
        return {"valid": False, "reason": f"Cannot access file: {str(e)}"}
    
    return {"valid": True}


def parse_file_path(key: str) -> dict:
    """
    Parse file path to extract domain and source information.
    
    Expected path format: landing/{source}/{domain}/{filename}
    Example: landing/edc-system/dm/demographics_20240115.csv
    
    Args:
        key: S3 object key
        
    Returns:
        dict: Parsed file information
    """
    parts = key.split("/")
    
    # Default values if path doesn't match expected format
    file_info = {
        "source": "unknown",
        "domain": "unknown",
        "filename": parts[-1] if parts else "unknown",
        "extension": ""
    }
    
    # Try to parse expected format
    if len(parts) >= 4 and parts[0] == "landing":
        file_info["source"] = parts[1]
        file_info["domain"] = parts[2]
        file_info["filename"] = parts[-1]
    
    # Extract extension
    if "." in file_info["filename"]:
        file_info["extension"] = file_info["filename"].split(".")[-1].lower()
    
    return file_info


def generate_metadata(
    bucket: str, 
    key: str, 
    size: int, 
    file_info: dict
) -> dict:
    """
    Generate metadata for the ingested file.
    
    Args:
        bucket: Source bucket
        key: Source key
        size: File size
        file_info: Parsed file information
        
    Returns:
        dict: Metadata record
    """
    now = datetime.now(timezone.utc)
    
    return {
        "ingestion_id": str(uuid.uuid4()),
        "ingestion_timestamp": now.isoformat(),
        "ingestion_date": now.strftime("%Y-%m-%d"),
        "source_bucket": bucket,
        "source_key": key,
        "source_system": file_info["source"],
        "domain": file_info["domain"],
        "filename": file_info["filename"],
        "file_extension": file_info["extension"],
        "file_size_bytes": size,
        "environment": ENVIRONMENT,
        "lambda_request_id": None,  # Set from context if available
        "processing_status": "ingested"
    }


def move_to_bronze(
    bucket: str, 
    source_key: str, 
    file_info: dict, 
    metadata: dict
) -> str:
    """
    Move file from landing zone to Bronze layer.
    
    Bronze path format: bronze/{source}/{domain}/year={year}/month={month}/day={day}/{filename}
    
    Args:
        bucket: S3 bucket
        source_key: Original file key
        file_info: Parsed file information
        metadata: Generated metadata
        
    Returns:
        str: Bronze layer key
    """
    # Construct Bronze path with partitioning
    ingestion_date = datetime.fromisoformat(metadata["ingestion_timestamp"])
    
    bronze_key = (
        f"bronze/"
        f"{file_info['source']}/"
        f"{file_info['domain']}/"
        f"year={ingestion_date.year}/"
        f"month={ingestion_date.month:02d}/"
        f"day={ingestion_date.day:02d}/"
        f"{metadata['ingestion_id']}_{file_info['filename']}"
    )
    
    # Copy to Bronze (preserving original)
    copy_source = {"Bucket": bucket, "Key": source_key}
    
    s3_client.copy_object(
        Bucket=DATA_BUCKET,
        Key=bronze_key,
        CopySource=copy_source,
        Metadata={
            "ingestion_id": metadata["ingestion_id"],
            "source_system": file_info["source"],
            "domain": file_info["domain"],
            "ingestion_timestamp": metadata["ingestion_timestamp"]
        },
        MetadataDirective="REPLACE"
    )
    
    logger.info(f"Copied to Bronze: s3://{DATA_BUCKET}/{bronze_key}")
    
    # Optionally delete from landing zone
    # s3_client.delete_object(Bucket=bucket, Key=source_key)
    
    return bronze_key


def write_lineage(metadata: dict, bronze_key: str) -> None:
    """
    Write lineage record for the ingested file.
    
    Args:
        metadata: File metadata
        bronze_key: Bronze layer key
    """
    lineage_record = {
        **metadata,
        "bronze_key": bronze_key,
        "bronze_bucket": DATA_BUCKET,
        "lineage_type": "ingestion",
        "upstream": [
            {
                "type": "source_file",
                "location": f"s3://{metadata['source_bucket']}/{metadata['source_key']}"
            }
        ],
        "downstream": []  # Will be updated by transformation jobs
    }
    
    # Write lineage to metadata location
    lineage_key = (
        f"metadata/lineage/"
        f"year={datetime.now().year}/"
        f"month={datetime.now().month:02d}/"
        f"{metadata['ingestion_id']}.json"
    )
    
    s3_client.put_object(
        Bucket=DATA_BUCKET,
        Key=lineage_key,
        Body=json.dumps(lineage_record, indent=2),
        ContentType="application/json"
    )
    
    logger.info(f"Lineage written: s3://{DATA_BUCKET}/{lineage_key}")
