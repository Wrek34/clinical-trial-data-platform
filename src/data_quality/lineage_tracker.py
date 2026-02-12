"""
Data Lineage Tracking Module

Tracks the complete journey of data from source to destination,
enabling audit trails and impact analysis.

WHY THIS MATTERS (for interviews):
- FDA 21 CFR Part 11 requires complete audit trails
- GDPR requires knowing where personal data flows
- Impact analysis: "If this source changes, what's affected?"
- Root cause analysis: "Where did this bad data come from?"

INTERVIEW TALKING POINTS:
"I implemented a lightweight lineage tracking system that records:
1. What data came from where (upstream dependencies)
2. What transformations were applied
3. What data was produced (downstream outputs)
4. When each step occurred and who/what triggered it

This creates an audit trail that satisfies regulatory requirements
and enables impact analysis for data governance."
"""

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class LineageEventType(Enum):
    """Types of lineage events we track."""
    INGESTION = "ingestion"           # Data arrived from external source
    TRANSFORMATION = "transformation"  # Data was transformed
    VALIDATION = "validation"          # Data was validated
    PROMOTION = "promotion"            # Data moved between layers
    EXPORT = "export"                  # Data sent to external system


class DataLayer(Enum):
    """Data lake layers."""
    LANDING = "landing"
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    EXPORT = "export"


@dataclass
class DataAsset:
    """
    Represents a data asset (file, table, dataset) in the lineage graph.
    
    This is a node in the lineage graph. Each asset has:
    - Unique identifier
    - Location (S3 path, table name, etc.)
    - Schema information
    - Quality metrics
    """
    asset_id: str
    name: str
    asset_type: str  # "file", "table", "dataset"
    location: str    # S3 path, database.table, etc.
    layer: DataLayer
    schema_hash: Optional[str] = None
    record_count: Optional[int] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: dict = field(default_factory=dict)
    
    @classmethod
    def from_s3_path(cls, s3_path: str, layer: DataLayer, record_count: int = None):
        """Create a DataAsset from an S3 path."""
        name = s3_path.split("/")[-1]
        asset_id = hashlib.md5(s3_path.encode()).hexdigest()[:12]
        
        return cls(
            asset_id=asset_id,
            name=name,
            asset_type="file",
            location=s3_path,
            layer=layer,
            record_count=record_count
        )
    
    def to_dict(self) -> dict:
        return {
            "asset_id": self.asset_id,
            "name": self.name,
            "asset_type": self.asset_type,
            "location": self.location,
            "layer": self.layer.value,
            "schema_hash": self.schema_hash,
            "record_count": self.record_count,
            "created_at": self.created_at,
            "metadata": self.metadata
        }


@dataclass
class LineageEvent:
    """
    Represents a lineage event - a transformation or movement of data.
    
    This is an edge in the lineage graph, connecting:
    - Input assets (upstream)
    - Output assets (downstream)
    - With metadata about what happened
    """
    event_id: str
    event_type: LineageEventType
    timestamp: str
    
    # What triggered this event
    triggered_by: str  # "lambda:ingestion", "glue:bronze_to_silver", "user:manual"
    
    # Input and output assets
    input_assets: list  # List of DataAsset
    output_assets: list  # List of DataAsset
    
    # Transformation details
    transformation_logic: Optional[str] = None  # Description or code reference
    parameters: dict = field(default_factory=dict)
    
    # Quality and audit
    validation_status: Optional[str] = None
    records_in: int = 0
    records_out: int = 0
    records_rejected: int = 0
    
    # Execution context
    execution_id: Optional[str] = None  # Glue job run ID, Lambda request ID
    duration_seconds: Optional[float] = None
    
    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp,
            "triggered_by": self.triggered_by,
            "input_assets": [a.to_dict() if isinstance(a, DataAsset) else a for a in self.input_assets],
            "output_assets": [a.to_dict() if isinstance(a, DataAsset) else a for a in self.output_assets],
            "transformation_logic": self.transformation_logic,
            "parameters": self.parameters,
            "validation_status": self.validation_status,
            "records_in": self.records_in,
            "records_out": self.records_out,
            "records_rejected": self.records_rejected,
            "execution_id": self.execution_id,
            "duration_seconds": self.duration_seconds
        }


class LineageTracker:
    """
    Tracks data lineage throughout the pipeline.
    
    USAGE PATTERN:
    1. Create tracker at start of job
    2. Register input assets
    3. Record transformation
    4. Register output assets
    5. Save lineage record
    
    Example:
        tracker = LineageTracker("glue:bronze_to_silver")
        tracker.add_input(DataAsset.from_s3_path("s3://bucket/bronze/dm/", DataLayer.BRONZE))
        tracker.set_transformation("CDISC standardization and validation")
        tracker.add_output(DataAsset.from_s3_path("s3://bucket/silver/dm/", DataLayer.SILVER))
        tracker.save("s3://bucket/metadata/lineage/")
    """
    
    def __init__(self, triggered_by: str, event_type: LineageEventType = LineageEventType.TRANSFORMATION):
        """
        Initialize lineage tracker.
        
        Args:
            triggered_by: Identifier for what triggered this pipeline run
            event_type: Type of lineage event
        """
        self.event_id = str(uuid.uuid4())
        self.event_type = event_type
        self.triggered_by = triggered_by
        self.start_time = datetime.now()
        
        self.input_assets: list[DataAsset] = []
        self.output_assets: list[DataAsset] = []
        self.transformation_logic: Optional[str] = None
        self.parameters: dict = {}
        self.validation_status: Optional[str] = None
        
        self.records_in = 0
        self.records_out = 0
        self.records_rejected = 0
        
        self.execution_id: Optional[str] = None
        
    def add_input(self, asset: DataAsset):
        """Register an input data asset."""
        self.input_assets.append(asset)
        if asset.record_count:
            self.records_in += asset.record_count
            
    def add_output(self, asset: DataAsset):
        """Register an output data asset."""
        self.output_assets.append(asset)
        if asset.record_count:
            self.records_out += asset.record_count
            
    def set_transformation(self, description: str, parameters: dict = None):
        """Document the transformation applied."""
        self.transformation_logic = description
        if parameters:
            self.parameters = parameters
            
    def set_validation_status(self, status: str, rejected_count: int = 0):
        """Record validation results."""
        self.validation_status = status
        self.records_rejected = rejected_count
        
    def set_execution_id(self, execution_id: str):
        """Set the execution ID (Glue job run ID, Lambda request ID)."""
        self.execution_id = execution_id
        
    def build_event(self) -> LineageEvent:
        """Build the final lineage event."""
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        
        return LineageEvent(
            event_id=self.event_id,
            event_type=self.event_type,
            timestamp=self.start_time.isoformat(),
            triggered_by=self.triggered_by,
            input_assets=self.input_assets,
            output_assets=self.output_assets,
            transformation_logic=self.transformation_logic,
            parameters=self.parameters,
            validation_status=self.validation_status,
            records_in=self.records_in,
            records_out=self.records_out,
            records_rejected=self.records_rejected,
            execution_id=self.execution_id,
            duration_seconds=duration
        )
    
    def save_local(self, filepath: str):
        """Save lineage record to local JSON file."""
        event = self.build_event()
        with open(filepath, 'w') as f:
            json.dump(event.to_dict(), f, indent=2)
        return filepath
    
    def save_to_s3(self, bucket: str, prefix: str = "metadata/lineage"):
        """
        Save lineage record to S3.
        
        Args:
            bucket: S3 bucket name
            prefix: S3 prefix for lineage records
            
        Returns:
            S3 path where lineage was saved
        """
        import boto3
        
        event = self.build_event()
        s3_client = boto3.client('s3')
        
        # Organize by date and event type
        date_str = self.start_time.strftime("%Y/%m/%d")
        key = f"{prefix}/{self.event_type.value}/{date_str}/{self.event_id}.json"
        
        s3_client.put_object(
            Bucket=bucket,
            Key=key,
            Body=json.dumps(event.to_dict(), indent=2),
            ContentType="application/json"
        )
        
        return f"s3://{bucket}/{key}"


class LineageQuery:
    """
    Query lineage records for impact analysis and auditing.
    
    INTERVIEW TALKING POINTS:
    "The lineage system supports two key queries:
    1. Upstream: 'Where did this data come from?' - for root cause analysis
    2. Downstream: 'What uses this data?' - for impact analysis
    
    This is essential for data governance and regulatory compliance."
    """
    
    def __init__(self, lineage_records: list[dict]):
        """
        Initialize with lineage records.
        
        Args:
            lineage_records: List of lineage event dictionaries
        """
        self.records = lineage_records
        self._build_index()
        
    def _build_index(self):
        """Build indexes for efficient querying."""
        self.by_output = {}  # asset_location -> [events that produced it]
        self.by_input = {}   # asset_location -> [events that consumed it]
        
        for record in self.records:
            for input_asset in record.get("input_assets", []):
                loc = input_asset.get("location", "")
                if loc not in self.by_input:
                    self.by_input[loc] = []
                self.by_input[loc].append(record)
                
            for output_asset in record.get("output_assets", []):
                loc = output_asset.get("location", "")
                if loc not in self.by_output:
                    self.by_output[loc] = []
                self.by_output[loc].append(record)
    
    def get_upstream(self, asset_location: str, depth: int = 10) -> list[dict]:
        """
        Get upstream lineage - where did this data come from?
        
        Args:
            asset_location: Location of the asset to trace
            depth: Maximum depth to traverse
            
        Returns:
            List of lineage events showing data origin
        """
        result = []
        visited = set()
        queue = [(asset_location, 0)]
        
        while queue:
            current_loc, current_depth = queue.pop(0)
            
            if current_loc in visited or current_depth > depth:
                continue
            visited.add(current_loc)
            
            # Find events that produced this asset
            events = self.by_output.get(current_loc, [])
            result.extend(events)
            
            # Add inputs of those events to the queue
            for event in events:
                for input_asset in event.get("input_assets", []):
                    input_loc = input_asset.get("location", "")
                    if input_loc not in visited:
                        queue.append((input_loc, current_depth + 1))
        
        return result
    
    def get_downstream(self, asset_location: str, depth: int = 10) -> list[dict]:
        """
        Get downstream lineage - what uses this data?
        
        Args:
            asset_location: Location of the asset to trace
            depth: Maximum depth to traverse
            
        Returns:
            List of lineage events showing data consumers
        """
        result = []
        visited = set()
        queue = [(asset_location, 0)]
        
        while queue:
            current_loc, current_depth = queue.pop(0)
            
            if current_loc in visited or current_depth > depth:
                continue
            visited.add(current_loc)
            
            # Find events that consumed this asset
            events = self.by_input.get(current_loc, [])
            result.extend(events)
            
            # Add outputs of those events to the queue
            for event in events:
                for output_asset in event.get("output_assets", []):
                    output_loc = output_asset.get("location", "")
                    if output_loc not in visited:
                        queue.append((output_loc, current_depth + 1))
        
        return result


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Data Lineage Tracking Demo")
    print("=" * 60)
    
    # Simulate a Bronze to Silver transformation
    tracker = LineageTracker(
        triggered_by="glue:bronze_to_silver",
        event_type=LineageEventType.TRANSFORMATION
    )
    
    # Register inputs
    tracker.add_input(DataAsset(
        asset_id="bronze_dm_001",
        name="dm.parquet",
        asset_type="file",
        location="s3://clinical-trial-dev/bronze/synthetic/dm/dm.parquet",
        layer=DataLayer.BRONZE,
        record_count=1000
    ))
    
    # Document transformation
    tracker.set_transformation(
        description="CDISC SDTM standardization: column renaming, type casting, controlled terminology validation",
        parameters={
            "cdisc_version": "3.3",
            "validation_rules": ["DM_001", "DM_002", "DM_003"]
        }
    )
    
    # Record validation results
    tracker.set_validation_status("PASSED_WITH_WARNINGS", rejected_count=5)
    
    # Register outputs
    tracker.add_output(DataAsset(
        asset_id="silver_dm_001",
        name="dm.parquet",
        asset_type="file",
        location="s3://clinical-trial-dev/silver/dm/dm.parquet",
        layer=DataLayer.SILVER,
        record_count=995
    ))
    
    # Set execution context
    tracker.set_execution_id("jr_abc123xyz")
    
    # Build and display the event
    event = tracker.build_event()
    
    print("\nLineage Event Created:")
    print("-" * 60)
    print(json.dumps(event.to_dict(), indent=2))
    
    # Save locally
    tracker.save_local("lineage_event.json")
    print("\nLineage saved to: lineage_event.json")
