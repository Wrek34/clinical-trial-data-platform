"""
Data Contracts Module

Enforces schema contracts at ingestion boundaries to prevent silent drift
and ensure backward compatibility across the data platform.

INTERVIEW TALKING POINTS:
"Data contracts are the API between data producers and consumers. Just like
microservices have API contracts, data pipelines need schema contracts.
Breaking changes are detected at ingestion and quarantined before they
pollute downstream systems. This prevents the 'garbage in, garbage out'
problem that plagues most data platforms."

WHAT THIS DEMONSTRATES:
- Enterprise data governance maturity
- Understanding of schema evolution challenges
- Proactive vs reactive data quality
"""

import json
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import pandas as pd


class CompatibilityMode(Enum):
    """Schema evolution compatibility modes."""
    BACKWARD = "backward"      # New schema can read old data
    FORWARD = "forward"        # Old schema can read new data  
    FULL = "full"              # Both backward and forward
    NONE = "none"              # No compatibility guaranteed


class ChangeType(Enum):
    """Types of schema changes detected."""
    COLUMN_ADDED = "column_added"
    COLUMN_REMOVED = "column_removed"
    TYPE_CHANGED = "type_changed"
    NULLABLE_CHANGED = "nullable_changed"
    CONSTRAINT_ADDED = "constraint_added"
    CONSTRAINT_REMOVED = "constraint_removed"


@dataclass
class SchemaChange:
    """Represents a detected schema change."""
    change_type: ChangeType
    column_name: str
    old_value: Any
    new_value: Any
    is_breaking: bool
    description: str
    
    def to_dict(self) -> dict:
        return {
            "change_type": self.change_type.value,
            "column_name": self.column_name,
            "old_value": str(self.old_value),
            "new_value": str(self.new_value),
            "is_breaking": self.is_breaking,
            "description": self.description
        }


@dataclass
class ColumnContract:
    """Contract specification for a single column."""
    name: str
    dtype: str  # "string", "int64", "float64", "datetime64", "boolean"
    nullable: bool = True
    unique: bool = False
    allowed_values: list = field(default_factory=list)  # For controlled terminology
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    pattern: Optional[str] = None  # Regex pattern
    description: str = ""
    
    def to_dict(self) -> dict:
        result = {
            "name": self.name,
            "dtype": self.dtype,
            "nullable": self.nullable,
            "unique": self.unique,
            "description": self.description
        }
        if self.allowed_values:
            result["allowed_values"] = self.allowed_values
        if self.min_value is not None:
            result["min_value"] = self.min_value
        if self.max_value is not None:
            result["max_value"] = self.max_value
        if self.pattern:
            result["pattern"] = self.pattern
        return result


@dataclass
class DataContract:
    """
    Full contract specification for a dataset.
    
    A data contract defines:
    1. Schema: columns, types, constraints
    2. Quality expectations: nullability, uniqueness, valid ranges
    3. Semantic rules: controlled terminology, referential integrity
    4. Evolution policy: what changes are allowed
    """
    name: str
    version: str
    domain: str  # CDISC domain: DM, AE, VS, LB
    description: str
    owner: str
    columns: list  # List of ColumnContract
    compatibility_mode: CompatibilityMode = CompatibilityMode.BACKWARD
    primary_key: list = field(default_factory=list)
    foreign_keys: dict = field(default_factory=dict)  # column -> referenced_table.column
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "domain": self.domain,
            "description": self.description,
            "owner": self.owner,
            "compatibility_mode": self.compatibility_mode.value,
            "primary_key": self.primary_key,
            "foreign_keys": self.foreign_keys,
            "columns": [c.to_dict() for c in self.columns],
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    def save(self, filepath: str):
        """Save contract to JSON file."""
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load(cls, filepath: str) -> 'DataContract':
        """Load contract from JSON file."""
        with open(filepath) as f:
            data = json.load(f)
        
        columns = [ColumnContract(**col) for col in data.pop("columns")]
        data["columns"] = columns
        data["compatibility_mode"] = CompatibilityMode(data["compatibility_mode"])
        return cls(**data)
    
    def get_schema_hash(self) -> str:
        """Generate hash of schema for change detection."""
        schema_str = json.dumps(
            [(c.name, c.dtype, c.nullable) for c in self.columns],
            sort_keys=True
        )
        return hashlib.md5(schema_str.encode()).hexdigest()[:8]


class ContractValidator:
    """
    Validates data against contracts and detects schema changes.
    
    USAGE:
        contract = DataContract.load("contracts/dm_v1.json")
        validator = ContractValidator(contract)
        
        # Check incoming data
        result = validator.validate(df)
        if result.has_breaking_changes:
            quarantine(df)
        elif result.is_valid:
            promote(df)
    """
    
    def __init__(self, contract: DataContract):
        self.contract = contract
        self.column_map = {c.name: c for c in contract.columns}
    
    def detect_schema_changes(self, df: pd.DataFrame) -> list[SchemaChange]:
        """
        Compare incoming data schema against contract.
        
        Returns list of detected changes with breaking/non-breaking classification.
        """
        changes = []
        incoming_columns = set(df.columns)
        contract_columns = set(self.column_map.keys())
        
        # Detect added columns (non-breaking for BACKWARD compatibility)
        for col in incoming_columns - contract_columns:
            changes.append(SchemaChange(
                change_type=ChangeType.COLUMN_ADDED,
                column_name=col,
                old_value=None,
                new_value=str(df[col].dtype),
                is_breaking=self.contract.compatibility_mode == CompatibilityMode.FORWARD,
                description=f"New column '{col}' detected in incoming data"
            ))
        
        # Detect removed columns (breaking for BACKWARD compatibility)
        for col in contract_columns - incoming_columns:
            changes.append(SchemaChange(
                change_type=ChangeType.COLUMN_REMOVED,
                column_name=col,
                old_value=self.column_map[col].dtype,
                new_value=None,
                is_breaking=self.contract.compatibility_mode in [
                    CompatibilityMode.BACKWARD, 
                    CompatibilityMode.FULL
                ],
                description=f"Required column '{col}' missing from incoming data"
            ))
        
        # Detect type changes in existing columns
        for col in incoming_columns & contract_columns:
            expected_dtype = self.column_map[col].dtype
            actual_dtype = self._normalize_dtype(df[col].dtype)
            
            if not self._types_compatible(expected_dtype, actual_dtype):
                changes.append(SchemaChange(
                    change_type=ChangeType.TYPE_CHANGED,
                    column_name=col,
                    old_value=expected_dtype,
                    new_value=actual_dtype,
                    is_breaking=True,
                    description=f"Column '{col}' type changed from {expected_dtype} to {actual_dtype}"
                ))
        
        return changes
    
    def _normalize_dtype(self, dtype) -> str:
        """Normalize pandas dtype to contract dtype string."""
        dtype_str = str(dtype)
        if 'int' in dtype_str:
            return 'int64'
        elif 'float' in dtype_str:
            return 'float64'
        elif 'object' in dtype_str or 'string' in dtype_str:
            return 'string'
        elif 'datetime' in dtype_str:
            return 'datetime64'
        elif 'bool' in dtype_str:
            return 'boolean'
        return dtype_str
    
    def _types_compatible(self, expected: str, actual: str) -> bool:
        """Check if types are compatible (allowing safe upcasting)."""
        if expected == actual:
            return True
        # Allow int -> float (safe upcast)
        if expected == 'float64' and actual == 'int64':
            return True
        # Allow string to match object
        if expected == 'string' and actual in ['string', 'object']:
            return True
        return False
    
    def validate_values(self, df: pd.DataFrame) -> dict:
        """
        Validate data values against contract constraints.
        
        Returns dict with validation results per column.
        """
        results = {}
        
        for col_contract in self.contract.columns:
            col_name = col_contract.name
            if col_name not in df.columns:
                continue
            
            col_results = {
                "column": col_name,
                "checks": [],
                "failed_count": 0
            }
            
            col_data = df[col_name]
            
            # Nullability check
            if not col_contract.nullable:
                null_count = col_data.isna().sum()
                col_results["checks"].append({
                    "check": "not_null",
                    "passed": null_count == 0,
                    "failed_count": int(null_count)
                })
                col_results["failed_count"] += null_count
            
            # Uniqueness check
            if col_contract.unique:
                dup_count = col_data.duplicated().sum()
                col_results["checks"].append({
                    "check": "unique",
                    "passed": dup_count == 0,
                    "failed_count": int(dup_count)
                })
                col_results["failed_count"] += dup_count
            
            # Allowed values (controlled terminology)
            if col_contract.allowed_values:
                invalid = ~col_data.isin(col_contract.allowed_values) & col_data.notna()
                invalid_count = invalid.sum()
                col_results["checks"].append({
                    "check": "allowed_values",
                    "passed": invalid_count == 0,
                    "failed_count": int(invalid_count),
                    "allowed": col_contract.allowed_values
                })
                col_results["failed_count"] += invalid_count
            
            # Range checks for numeric columns
            if col_contract.min_value is not None:
                below_min = (col_data < col_contract.min_value).sum()
                col_results["checks"].append({
                    "check": "min_value",
                    "passed": below_min == 0,
                    "failed_count": int(below_min),
                    "min": col_contract.min_value
                })
                col_results["failed_count"] += below_min
            
            if col_contract.max_value is not None:
                above_max = (col_data > col_contract.max_value).sum()
                col_results["checks"].append({
                    "check": "max_value",
                    "passed": above_max == 0,
                    "failed_count": int(above_max),
                    "max": col_contract.max_value
                })
                col_results["failed_count"] += above_max
            
            results[col_name] = col_results
        
        return results


@dataclass
class ContractValidationResult:
    """Complete result of contract validation."""
    contract_name: str
    contract_version: str
    schema_hash: str
    timestamp: str
    
    # Schema validation
    schema_changes: list
    has_breaking_changes: bool
    
    # Value validation
    value_validation: dict
    total_records: int
    failed_records: int
    
    # Overall result
    is_valid: bool
    action: str  # "accept", "quarantine", "alert"
    
    def to_dict(self) -> dict:
        return {
            "contract_name": self.contract_name,
            "contract_version": self.contract_version,
            "schema_hash": self.schema_hash,
            "timestamp": self.timestamp,
            "schema_changes": [c.to_dict() for c in self.schema_changes],
            "has_breaking_changes": self.has_breaking_changes,
            "value_validation": self.value_validation,
            "total_records": self.total_records,
            "failed_records": self.failed_records,
            "is_valid": self.is_valid,
            "action": self.action
        }


def validate_against_contract(
    df: pd.DataFrame, 
    contract: DataContract
) -> ContractValidationResult:
    """
    Main entry point: validate DataFrame against a data contract.
    
    Returns ContractValidationResult with action recommendation:
    - "accept": Data passes all checks, promote to next layer
    - "quarantine": Breaking changes detected, isolate for review
    - "alert": Non-breaking changes detected, accept but notify
    """
    validator = ContractValidator(contract)
    
    # Detect schema changes
    schema_changes = validator.detect_schema_changes(df)
    has_breaking = any(c.is_breaking for c in schema_changes)
    
    # Validate values
    value_validation = validator.validate_values(df)
    failed_records = sum(v["failed_count"] for v in value_validation.values())
    
    # Determine action
    if has_breaking:
        action = "quarantine"
        is_valid = False
    elif failed_records > 0:
        # Threshold: if >5% records fail, quarantine
        if failed_records / len(df) > 0.05:
            action = "quarantine"
            is_valid = False
        else:
            action = "alert"
            is_valid = True
    elif schema_changes:
        action = "alert"  # Non-breaking changes, but notify
        is_valid = True
    else:
        action = "accept"
        is_valid = True
    
    return ContractValidationResult(
        contract_name=contract.name,
        contract_version=contract.version,
        schema_hash=contract.get_schema_hash(),
        timestamp=datetime.now().isoformat(),
        schema_changes=schema_changes,
        has_breaking_changes=has_breaking,
        value_validation=value_validation,
        total_records=len(df),
        failed_records=failed_records,
        is_valid=is_valid,
        action=action
    )


# =============================================================================
# PRE-BUILT CONTRACTS FOR CDISC DOMAINS
# =============================================================================

def create_dm_contract() -> DataContract:
    """Create data contract for Demographics (DM) domain."""
    return DataContract(
        name="clinical_trial_dm",
        version="1.0.0",
        domain="DM",
        description="Demographics domain - one record per subject",
        owner="data-engineering",
        compatibility_mode=CompatibilityMode.BACKWARD,
        primary_key=["USUBJID"],
        columns=[
            ColumnContract(
                name="STUDYID",
                dtype="string",
                nullable=False,
                description="Study Identifier"
            ),
            ColumnContract(
                name="DOMAIN",
                dtype="string",
                nullable=False,
                allowed_values=["DM"],
                description="Domain Abbreviation"
            ),
            ColumnContract(
                name="USUBJID",
                dtype="string",
                nullable=False,
                unique=True,
                description="Unique Subject Identifier"
            ),
            ColumnContract(
                name="SUBJID",
                dtype="string",
                nullable=False,
                description="Subject Identifier for the Study"
            ),
            ColumnContract(
                name="SITEID",
                dtype="string",
                nullable=False,
                description="Study Site Identifier"
            ),
            ColumnContract(
                name="AGE",
                dtype="int64",
                nullable=False,
                min_value=0,
                max_value=120,
                description="Age in Years"
            ),
            ColumnContract(
                name="AGEU",
                dtype="string",
                nullable=False,
                allowed_values=["YEARS"],
                description="Age Units"
            ),
            ColumnContract(
                name="SEX",
                dtype="string",
                nullable=False,
                allowed_values=["M", "F", "U", "UNDIFFERENTIATED"],
                description="Sex (CDISC CT)"
            ),
            ColumnContract(
                name="RACE",
                dtype="string",
                nullable=True,
                description="Race"
            ),
            ColumnContract(
                name="ETHNIC",
                dtype="string",
                nullable=True,
                description="Ethnicity"
            ),
            ColumnContract(
                name="ARM",
                dtype="string",
                nullable=True,
                description="Treatment Arm"
            ),
            ColumnContract(
                name="ARMCD",
                dtype="string",
                nullable=True,
                description="Treatment Arm Code"
            ),
            ColumnContract(
                name="COUNTRY",
                dtype="string",
                nullable=True,
                description="Country"
            ),
            ColumnContract(
                name="RFSTDTC",
                dtype="string",
                nullable=True,
                pattern=r"^\d{4}-\d{2}-\d{2}",
                description="Subject Reference Start Date (ISO 8601)"
            ),
            ColumnContract(
                name="RFENDTC",
                dtype="string",
                nullable=True,
                description="Subject Reference End Date (ISO 8601)"
            )
        ]
    )


def create_ae_contract() -> DataContract:
    """Create data contract for Adverse Events (AE) domain."""
    return DataContract(
        name="clinical_trial_ae",
        version="1.0.0",
        domain="AE",
        description="Adverse Events domain - one record per adverse event per subject",
        owner="data-engineering",
        compatibility_mode=CompatibilityMode.BACKWARD,
        primary_key=["USUBJID", "AESEQ"],
        foreign_keys={"USUBJID": "DM.USUBJID"},
        columns=[
            ColumnContract(
                name="STUDYID",
                dtype="string",
                nullable=False,
                description="Study Identifier"
            ),
            ColumnContract(
                name="DOMAIN",
                dtype="string",
                nullable=False,
                allowed_values=["AE"],
                description="Domain Abbreviation"
            ),
            ColumnContract(
                name="USUBJID",
                dtype="string",
                nullable=False,
                description="Unique Subject Identifier"
            ),
            ColumnContract(
                name="AESEQ",
                dtype="int64",
                nullable=False,
                min_value=1,
                description="Sequence Number"
            ),
            ColumnContract(
                name="AETERM",
                dtype="string",
                nullable=False,
                description="Reported Term for the Adverse Event"
            ),
            ColumnContract(
                name="AEDECOD",
                dtype="string",
                nullable=True,
                description="Dictionary-Derived Term (MedDRA PT)"
            ),
            ColumnContract(
                name="AEBODSYS",
                dtype="string",
                nullable=True,
                description="Body System or Organ Class (MedDRA SOC)"
            ),
            ColumnContract(
                name="AESEV",
                dtype="string",
                nullable=False,
                allowed_values=["MILD", "MODERATE", "SEVERE"],
                description="Severity/Intensity (CDISC CT)"
            ),
            ColumnContract(
                name="AESER",
                dtype="string",
                nullable=False,
                allowed_values=["Y", "N"],
                description="Serious Event (Y/N)"
            ),
            ColumnContract(
                name="AEREL",
                dtype="string",
                nullable=True,
                description="Causality/Relationship to Treatment"
            ),
            ColumnContract(
                name="AEOUT",
                dtype="string",
                nullable=True,
                description="Outcome of Adverse Event"
            ),
            ColumnContract(
                name="AESTDTC",
                dtype="string",
                nullable=True,
                description="Start Date/Time (ISO 8601)"
            ),
            ColumnContract(
                name="AEENDTC",
                dtype="string",
                nullable=True,
                description="End Date/Time (ISO 8601)"
            )
        ]
    )


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Data Contracts Demo")
    print("=" * 60)
    
    # Create and save DM contract
    dm_contract = create_dm_contract()
    dm_contract.save("dm_contract_v1.json")
    print(f"\nCreated DM contract v{dm_contract.version}")
    print(f"Schema hash: {dm_contract.get_schema_hash()}")
    
    # Simulate incoming data with schema change
    incoming_df = pd.DataFrame({
        "STUDYID": ["STUDY001", "STUDY001"],
        "DOMAIN": ["DM", "DM"],
        "USUBJID": ["SUBJ001", "SUBJ002"],
        "SUBJID": ["001", "002"],
        "SITEID": ["SITE01", "SITE01"],
        "AGE": [45, 150],  # 150 is invalid
        "AGEU": ["YEARS", "YEARS"],
        "SEX": ["M", "X"],  # X is invalid
        "NEW_COLUMN": ["test", "test"],  # Schema change!
        # Missing: RACE, ETHNIC, ARM, etc. (nullable so OK)
    })
    
    # Validate against contract
    result = validate_against_contract(incoming_df, dm_contract)
    
    print(f"\n{'=' * 60}")
    print("Validation Result:")
    print(f"{'=' * 60}")
    print(f"Valid: {result.is_valid}")
    print(f"Action: {result.action}")
    print(f"Breaking changes: {result.has_breaking_changes}")
    print(f"Schema changes: {len(result.schema_changes)}")
    for change in result.schema_changes:
        print(f"  - {change.description} (breaking: {change.is_breaking})")
    print(f"Failed records: {result.failed_records}/{result.total_records}")
