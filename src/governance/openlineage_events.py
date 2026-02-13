"""
OpenLineage Events Module

Emits OpenLineage-compatible events for data lineage tracking.
These events can be consumed by Marquez, DataHub, or other lineage tools.

INTERVIEW TALKING POINTS:
"We emit OpenLineage events at each transformation step. This creates a 
standardized lineage graph that can answer two critical questions:
1. Upstream: 'Where did this data come from?' - for root cause analysis
2. Downstream: 'What breaks if we change this?' - for impact assessment

The events are stored in S3 and can be visualized in Marquez or exported
for regulatory audit packages."

WHAT THIS DEMONSTRATES:
- Understanding of data governance standards (OpenLineage)
- Production-grade observability
- Regulatory compliance mindset
"""

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class EventType(Enum):
    """OpenLineage event types."""
    START = "START"
    RUNNING = "RUNNING"
    COMPLETE = "COMPLETE"
    ABORT = "ABORT"
    FAIL = "FAIL"


@dataclass
class DatasetField:
    """Schema field for a dataset."""
    name: str
    type: str
    description: str = ""
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "type": self.type,
            "description": self.description
        }


@dataclass
class Dataset:
    """
    OpenLineage Dataset representation.
    
    Represents a data asset (S3 path, table, etc.) with:
    - Namespace: logical grouping (e.g., "s3://bucket")
    - Name: specific path or table name
    - Facets: additional metadata (schema, quality, etc.)
    """
    namespace: str  # e.g., "s3://clinical-trial-dev-data"
    name: str       # e.g., "bronze/dm/2024/01/15"
    facets: dict = field(default_factory=dict)
    
    def with_schema(self, fields: list[DatasetField]) -> 'Dataset':
        """Add schema facet."""
        self.facets["schema"] = {
            "_producer": "https://github.com/Wrek34/clinical-trial-data-platform",
            "_schemaURL": "https://openlineage.io/spec/facets/1-0-0/SchemaDatasetFacet.json",
            "fields": [f.to_dict() for f in fields]
        }
        return self
    
    def with_data_quality(self, metrics: dict) -> 'Dataset':
        """Add data quality metrics facet."""
        self.facets["dataQuality"] = {
            "_producer": "https://github.com/Wrek34/clinical-trial-data-platform",
            "_schemaURL": "https://openlineage.io/spec/facets/1-0-0/DataQualityMetricsInputDatasetFacet.json",
            **metrics
        }
        return self
    
    def with_lineage_info(self, source_system: str, ingestion_time: str) -> 'Dataset':
        """Add custom lineage info facet."""
        self.facets["lineageInfo"] = {
            "_producer": "https://github.com/Wrek34/clinical-trial-data-platform",
            "sourceSystem": source_system,
            "ingestionTime": ingestion_time
        }
        return self
    
    def to_dict(self) -> dict:
        result = {
            "namespace": self.namespace,
            "name": self.name
        }
        if self.facets:
            result["facets"] = self.facets
        return result


@dataclass
class Job:
    """
    OpenLineage Job representation.
    
    Represents a data transformation job (Glue job, Lambda function, etc.)
    """
    namespace: str  # e.g., "aws-glue"
    name: str       # e.g., "bronze-to-silver-dm"
    facets: dict = field(default_factory=dict)
    
    def with_sql(self, query: str) -> 'Job':
        """Add SQL facet for jobs that execute SQL."""
        self.facets["sql"] = {
            "_producer": "https://github.com/Wrek34/clinical-trial-data-platform",
            "_schemaURL": "https://openlineage.io/spec/facets/1-0-0/SqlJobFacet.json",
            "query": query
        }
        return self
    
    def with_source_code(self, location: str, version: str) -> 'Job':
        """Add source code location facet."""
        self.facets["sourceCodeLocation"] = {
            "_producer": "https://github.com/Wrek34/clinical-trial-data-platform",
            "_schemaURL": "https://openlineage.io/spec/facets/1-0-0/SourceCodeLocationJobFacet.json",
            "type": "git",
            "url": location,
            "version": version
        }
        return self
    
    def to_dict(self) -> dict:
        result = {
            "namespace": self.namespace,
            "name": self.name
        }
        if self.facets:
            result["facets"] = self.facets
        return result


@dataclass
class Run:
    """
    OpenLineage Run representation.
    
    Represents a specific execution of a job with runtime metadata.
    """
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    facets: dict = field(default_factory=dict)
    
    def with_nominal_time(self, start: str, end: str = None) -> 'Run':
        """Add nominal time facet."""
        facet = {
            "_producer": "https://github.com/Wrek34/clinical-trial-data-platform",
            "_schemaURL": "https://openlineage.io/spec/facets/1-0-0/NominalTimeRunFacet.json",
            "nominalStartTime": start
        }
        if end:
            facet["nominalEndTime"] = end
        self.facets["nominalTime"] = facet
        return self
    
    def with_error(self, message: str, stack_trace: str = None) -> 'Run':
        """Add error facet for failed runs."""
        facet = {
            "_producer": "https://github.com/Wrek34/clinical-trial-data-platform",
            "_schemaURL": "https://openlineage.io/spec/facets/1-0-0/ErrorMessageRunFacet.json",
            "message": message,
            "programmingLanguage": "python"
        }
        if stack_trace:
            facet["stackTrace"] = stack_trace
        self.facets["errorMessage"] = facet
        return self
    
    def with_processing_stats(
        self, 
        rows_read: int, 
        rows_written: int,
        bytes_read: int = None,
        bytes_written: int = None
    ) -> 'Run':
        """Add processing statistics facet."""
        self.facets["processingStats"] = {
            "_producer": "https://github.com/Wrek34/clinical-trial-data-platform",
            "rowsRead": rows_read,
            "rowsWritten": rows_written,
            "bytesRead": bytes_read,
            "bytesWritten": bytes_written
        }
        return self
    
    def to_dict(self) -> dict:
        result = {"runId": self.run_id}
        if self.facets:
            result["facets"] = self.facets
        return result


@dataclass
class OpenLineageEvent:
    """
    Complete OpenLineage event.
    
    This is the standard format consumed by Marquez, DataHub, and other
    lineage tools. Each event represents a state change in a job run.
    """
    event_type: EventType
    event_time: str
    producer: str
    schema_url: str
    job: Job
    run: Run
    inputs: list  # List of Dataset
    outputs: list  # List of Dataset
    
    def to_dict(self) -> dict:
        return {
            "eventType": self.event_type.value,
            "eventTime": self.event_time,
            "producer": self.producer,
            "schemaURL": self.schema_url,
            "job": self.job.to_dict(),
            "run": self.run.to_dict(),
            "inputs": [d.to_dict() for d in self.inputs],
            "outputs": [d.to_dict() for d in self.outputs]
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


class OpenLineageEmitter:
    """
    Emits OpenLineage events for pipeline observability.
    
    USAGE:
        emitter = OpenLineageEmitter(
            namespace="aws-glue",
            job_name="bronze-to-silver-dm"
        )
        
        # Start of job
        emitter.emit_start(inputs=[bronze_dataset], outputs=[silver_dataset])
        
        # ... processing ...
        
        # End of job (success)
        emitter.emit_complete(
            inputs=[bronze_dataset],
            outputs=[silver_dataset.with_data_quality(metrics)]
        )
        
        # Or failure
        emitter.emit_fail(error_message="Schema validation failed")
    """
    
    PRODUCER = "https://github.com/Wrek34/clinical-trial-data-platform"
    SCHEMA_URL = "https://openlineage.io/spec/1-0-5/OpenLineage.json"
    
    def __init__(
        self, 
        namespace: str, 
        job_name: str,
        source_code_location: str = None,
        source_code_version: str = None
    ):
        self.namespace = namespace
        self.job_name = job_name
        self.run = Run()
        self.events: list[OpenLineageEvent] = []
        
        # Create job with optional facets
        self.job = Job(namespace=namespace, name=job_name)
        if source_code_location and source_code_version:
            self.job.with_source_code(source_code_location, source_code_version)
    
    def _get_event_time(self) -> str:
        """Get current time in ISO 8601 format with timezone."""
        return datetime.now(timezone.utc).isoformat()
    
    def _create_event(
        self,
        event_type: EventType,
        inputs: list[Dataset],
        outputs: list[Dataset]
    ) -> OpenLineageEvent:
        """Create an OpenLineage event."""
        event = OpenLineageEvent(
            event_type=event_type,
            event_time=self._get_event_time(),
            producer=self.PRODUCER,
            schema_url=self.SCHEMA_URL,
            job=self.job,
            run=self.run,
            inputs=inputs,
            outputs=outputs
        )
        self.events.append(event)
        return event
    
    def emit_start(
        self, 
        inputs: list[Dataset], 
        outputs: list[Dataset]
    ) -> OpenLineageEvent:
        """Emit START event when job begins."""
        self.run.with_nominal_time(self._get_event_time())
        return self._create_event(EventType.START, inputs, outputs)
    
    def emit_running(
        self,
        inputs: list[Dataset],
        outputs: list[Dataset],
        progress_pct: float = None
    ) -> OpenLineageEvent:
        """Emit RUNNING event for long-running jobs (optional)."""
        if progress_pct is not None:
            self.run.facets["progress"] = {
                "_producer": self.PRODUCER,
                "percentComplete": progress_pct
            }
        return self._create_event(EventType.RUNNING, inputs, outputs)
    
    def emit_complete(
        self,
        inputs: list[Dataset],
        outputs: list[Dataset],
        rows_read: int = None,
        rows_written: int = None
    ) -> OpenLineageEvent:
        """Emit COMPLETE event when job succeeds."""
        if rows_read is not None and rows_written is not None:
            self.run.with_processing_stats(rows_read, rows_written)
        return self._create_event(EventType.COMPLETE, inputs, outputs)
    
    def emit_fail(
        self,
        inputs: list[Dataset],
        outputs: list[Dataset],
        error_message: str,
        stack_trace: str = None
    ) -> OpenLineageEvent:
        """Emit FAIL event when job fails."""
        self.run.with_error(error_message, stack_trace)
        return self._create_event(EventType.FAIL, inputs, outputs)
    
    def get_all_events(self) -> list[dict]:
        """Get all emitted events as dictionaries."""
        return [e.to_dict() for e in self.events]
    
    def save_events(self, filepath: str):
        """Save all events to a JSON file."""
        with open(filepath, 'w') as f:
            json.dump(self.get_all_events(), f, indent=2)
    
    def save_to_s3(self, bucket: str, prefix: str = "metadata/lineage"):
        """
        Save events to S3 for consumption by lineage tools.
        
        Events are organized by date and job for easy querying.
        """
        import boto3
        
        s3 = boto3.client('s3')
        date_str = datetime.now().strftime("%Y/%m/%d")
        
        for i, event in enumerate(self.events):
            key = f"{prefix}/{self.job_name}/{date_str}/{self.run.run_id}_{i}.json"
            s3.put_object(
                Bucket=bucket,
                Key=key,
                Body=json.dumps(event.to_dict(), indent=2),
                ContentType="application/json"
            )
        
        return f"s3://{bucket}/{prefix}/{self.job_name}/{date_str}/"


# =============================================================================
# EXAMPLE: Bronze to Silver Job with OpenLineage
# =============================================================================

def example_bronze_to_silver_lineage():
    """Example of emitting lineage for a Bronze to Silver transformation."""
    
    # Initialize emitter
    emitter = OpenLineageEmitter(
        namespace="aws-glue",
        job_name="bronze-to-silver-dm",
        source_code_location="https://github.com/Wrek34/clinical-trial-data-platform",
        source_code_version="v1.2.0"
    )
    
    # Define input dataset (Bronze)
    bronze_dm = Dataset(
        namespace="s3://clinical-trial-dev-data",
        name="bronze/synthetic/dm"
    ).with_schema([
        DatasetField("USUBJID", "string", "Unique Subject Identifier"),
        DatasetField("AGE", "integer", "Age in Years"),
        DatasetField("SEX", "string", "Sex (M/F/U)"),
        DatasetField("ARM", "string", "Treatment Arm")
    ]).with_lineage_info(
        source_system="edc_export",
        ingestion_time="2024-02-10T08:30:00Z"
    )
    
    # Define output dataset (Silver)
    silver_dm = Dataset(
        namespace="s3://clinical-trial-dev-data",
        name="silver/dm"
    ).with_schema([
        DatasetField("USUBJID", "string", "Unique Subject Identifier"),
        DatasetField("AGE", "integer", "Age in Years (validated 0-120)"),
        DatasetField("SEX", "string", "Sex (CDISC CT: M/F/U)"),
        DatasetField("ARM", "string", "Treatment Arm"),
        DatasetField("PROCESSING_TS", "timestamp", "Processing timestamp"),
        DatasetField("PROCESSING_DATE", "date", "Processing date for partitioning")
    ])
    
    # Emit START event
    emitter.emit_start(inputs=[bronze_dm], outputs=[silver_dm])
    print("Emitted START event")
    
    # Simulate processing...
    # In real job, this is where transformation happens
    
    # Add data quality metrics to output
    silver_dm_with_dq = Dataset(
        namespace="s3://clinical-trial-dev-data",
        name="silver/dm"
    ).with_data_quality({
        "rowCount": 500,
        "columnCount": 15,
        "nullCount": {"AGE": 0, "SEX": 0, "ARM": 12},
        "distinctCount": {"USUBJID": 500, "SITEID": 10, "ARM": 3},
        "validationPassRate": 0.98
    })
    
    # Emit COMPLETE event
    emitter.emit_complete(
        inputs=[bronze_dm],
        outputs=[silver_dm_with_dq],
        rows_read=500,
        rows_written=495  # 5 records quarantined
    )
    print("Emitted COMPLETE event")
    
    # Save events locally
    emitter.save_events("lineage_events.json")
    print("\nLineage events saved to: lineage_events.json")
    
    # Print sample event
    print("\nSample Event (COMPLETE):")
    print("-" * 60)
    print(emitter.events[-1].to_json())
    
    return emitter


if __name__ == "__main__":
    print("=" * 60)
    print("OpenLineage Events Demo")
    print("=" * 60)
    example_bronze_to_silver_lineage()
