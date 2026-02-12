"""
Data Quality Validation Module for Clinical Trial Data

This module implements data quality checks following Great Expectations patterns,
specifically designed for CDISC-compliant clinical trial data.

WHY THIS MATTERS (for interviews):
- Regulatory submissions require proof of data quality
- FDA 21 CFR Part 11 requires data integrity controls
- Bad data caught early saves millions in failed trials

ARCHITECTURE DECISION:
We validate at the Bronze→Silver boundary because:
1. Raw data is preserved in Bronze for audit
2. Only clean data enters Silver
3. Failed records are quarantined with full context
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional

import pandas as pd


class ValidationSeverity(Enum):
    """
    Severity levels for validation failures.
    
    ERROR = Record is rejected, cannot proceed
    WARNING = Record proceeds but flagged for review
    INFO = Logged for monitoring, no action needed
    """
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationStatus(Enum):
    """Overall validation result for a dataset."""
    PASSED = "passed"
    FAILED = "failed"
    PASSED_WITH_WARNINGS = "passed_with_warnings"


@dataclass
class ValidationResult:
    """
    Result of a single validation check.
    
    This structure is designed for:
    1. Audit logging - every check is recorded
    2. Downstream processing - failed records can be filtered
    3. Reporting - aggregated into quality dashboards
    """
    rule_name: str
    description: str
    severity: ValidationSeverity
    passed: bool
    records_checked: int
    records_failed: int
    failure_percentage: float
    failed_record_ids: list = field(default_factory=list)
    details: dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "rule_name": self.rule_name,
            "description": self.description,
            "severity": self.severity.value,
            "passed": self.passed,
            "records_checked": self.records_checked,
            "records_failed": self.records_failed,
            "failure_percentage": round(self.failure_percentage, 2),
            "failed_record_ids": self.failed_record_ids[:100],  # Limit for storage
            "details": self.details,
            "timestamp": self.timestamp
        }


@dataclass
class DataQualityReport:
    """
    Complete quality report for a dataset.
    
    This report is:
    1. Stored in S3 for audit trail
    2. Used to gate data promotion (Bronze→Silver)
    3. Aggregated for quality dashboards
    """
    domain: str
    source_path: str
    validation_timestamp: str
    total_records: int
    status: ValidationStatus
    results: list  # List of ValidationResult
    metadata: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "domain": self.domain,
            "source_path": self.source_path,
            "validation_timestamp": self.validation_timestamp,
            "total_records": self.total_records,
            "status": self.status.value,
            "summary": {
                "total_checks": len(self.results),
                "passed": sum(1 for r in self.results if r.passed),
                "failed": sum(1 for r in self.results if not r.passed),
                "errors": sum(1 for r in self.results if not r.passed and r.severity == ValidationSeverity.ERROR),
                "warnings": sum(1 for r in self.results if not r.passed and r.severity == ValidationSeverity.WARNING)
            },
            "results": [r.to_dict() for r in self.results],
            "metadata": self.metadata
        }
    
    def save_to_json(self, filepath: str):
        """Save report to JSON file."""
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)


class ClinicalDataValidator:
    """
    Validates clinical trial data against CDISC standards and custom rules.
    
    INTERVIEW TALKING POINTS:
    - Rule-based validation is configurable and auditable
    - Each rule has clear pass/fail criteria
    - Failed records are identified for remediation
    - Reports provide evidence for regulatory submissions
    """
    
    def __init__(self, domain: str):
        """
        Initialize validator for a specific CDISC domain.
        
        Args:
            domain: CDISC domain code (DM, AE, VS, LB, etc.)
        """
        self.domain = domain
        self.rules: list[dict] = []
        self.results: list[ValidationResult] = []
        
    def add_rule(
        self,
        name: str,
        description: str,
        validation_func: Callable[[pd.DataFrame], tuple[bool, pd.DataFrame]],
        severity: ValidationSeverity = ValidationSeverity.ERROR
    ):
        """
        Add a validation rule.
        
        Args:
            name: Unique rule identifier
            description: Human-readable description
            validation_func: Function that takes DataFrame, returns (is_valid, failed_records)
            severity: How serious a failure is
        """
        self.rules.append({
            "name": name,
            "description": description,
            "func": validation_func,
            "severity": severity
        })
        
    def validate(self, df: pd.DataFrame, id_column: str = "USUBJID") -> DataQualityReport:
        """
        Run all validation rules against the dataset.
        
        Args:
            df: DataFrame to validate
            id_column: Column containing unique record identifiers
            
        Returns:
            DataQualityReport with all results
        """
        self.results = []
        total_records = len(df)
        
        for rule in self.rules:
            try:
                # Run the validation function
                passed, failed_df = rule["func"](df)
                
                records_failed = len(failed_df)
                failure_pct = (records_failed / total_records * 100) if total_records > 0 else 0
                
                # Get IDs of failed records
                failed_ids = []
                if not failed_df.empty and id_column in failed_df.columns:
                    failed_ids = failed_df[id_column].tolist()
                
                result = ValidationResult(
                    rule_name=rule["name"],
                    description=rule["description"],
                    severity=rule["severity"],
                    passed=passed,
                    records_checked=total_records,
                    records_failed=records_failed,
                    failure_percentage=failure_pct,
                    failed_record_ids=failed_ids
                )
                
            except Exception as e:
                # Validation itself failed - this is an error
                result = ValidationResult(
                    rule_name=rule["name"],
                    description=rule["description"],
                    severity=ValidationSeverity.ERROR,
                    passed=False,
                    records_checked=total_records,
                    records_failed=total_records,
                    failure_percentage=100.0,
                    details={"error": str(e)}
                )
            
            self.results.append(result)
        
        # Determine overall status
        has_errors = any(not r.passed and r.severity == ValidationSeverity.ERROR for r in self.results)
        has_warnings = any(not r.passed and r.severity == ValidationSeverity.WARNING for r in self.results)
        
        if has_errors:
            status = ValidationStatus.FAILED
        elif has_warnings:
            status = ValidationStatus.PASSED_WITH_WARNINGS
        else:
            status = ValidationStatus.PASSED
        
        return DataQualityReport(
            domain=self.domain,
            source_path="",  # Set by caller
            validation_timestamp=datetime.now().isoformat(),
            total_records=total_records,
            status=status,
            results=self.results
        )


# =============================================================================
# PRE-BUILT VALIDATORS FOR CDISC DOMAINS
# =============================================================================

def create_dm_validator() -> ClinicalDataValidator:
    """
    Create validator for Demographics (DM) domain.
    
    DM is the most critical domain - every other domain references it.
    These rules ensure referential integrity across the study.
    """
    validator = ClinicalDataValidator("DM")
    
    # Rule 1: USUBJID must be unique
    def check_usubjid_unique(df):
        duplicates = df[df.duplicated(subset=['USUBJID'], keep=False)]
        return duplicates.empty, duplicates
    
    validator.add_rule(
        name="DM_001",
        description="USUBJID must be unique - each subject appears only once",
        validation_func=check_usubjid_unique,
        severity=ValidationSeverity.ERROR
    )
    
    # Rule 2: USUBJID cannot be null
    def check_usubjid_not_null(df):
        null_records = df[df['USUBJID'].isna()]
        return null_records.empty, null_records
    
    validator.add_rule(
        name="DM_002",
        description="USUBJID cannot be null",
        validation_func=check_usubjid_not_null,
        severity=ValidationSeverity.ERROR
    )
    
    # Rule 3: Age must be within valid range
    def check_age_range(df):
        invalid = df[(df['AGE'] < 0) | (df['AGE'] > 120)]
        return invalid.empty, invalid
    
    validator.add_rule(
        name="DM_003",
        description="AGE must be between 0 and 120 years",
        validation_func=check_age_range,
        severity=ValidationSeverity.ERROR
    )
    
    # Rule 4: Sex must be valid CDISC terminology
    def check_sex_values(df):
        valid_sex = ['M', 'F', 'U', 'UNDIFFERENTIATED']
        invalid = df[~df['SEX'].str.upper().isin(valid_sex)]
        return invalid.empty, invalid
    
    validator.add_rule(
        name="DM_004",
        description="SEX must be M, F, U, or UNDIFFERENTIATED (CDISC CT)",
        validation_func=check_sex_values,
        severity=ValidationSeverity.ERROR
    )
    
    # Rule 5: Treatment arm should not be null for randomized subjects
    def check_arm_populated(df):
        null_arm = df[df['ARM'].isna()]
        return null_arm.empty, null_arm
    
    validator.add_rule(
        name="DM_005",
        description="ARM (treatment arm) should be populated",
        validation_func=check_arm_populated,
        severity=ValidationSeverity.WARNING
    )
    
    # Rule 6: Reference start date should be valid ISO 8601
    def check_rfstdtc_format(df):
        def is_valid_date(date_str):
            if pd.isna(date_str):
                return False
            try:
                datetime.strptime(str(date_str)[:10], '%Y-%m-%d')
                return True
            except:
                return False
        
        invalid = df[~df['RFSTDTC'].apply(is_valid_date)]
        return invalid.empty, invalid
    
    validator.add_rule(
        name="DM_006",
        description="RFSTDTC must be valid ISO 8601 date format (YYYY-MM-DD)",
        validation_func=check_rfstdtc_format,
        severity=ValidationSeverity.ERROR
    )
    
    return validator


def create_ae_validator() -> ClinicalDataValidator:
    """
    Create validator for Adverse Events (AE) domain.
    
    AE data is critical for safety reporting.
    FDA requires complete and accurate AE reporting.
    """
    validator = ClinicalDataValidator("AE")
    
    # Rule 1: USUBJID cannot be null
    def check_usubjid_not_null(df):
        null_records = df[df['USUBJID'].isna()]
        return null_records.empty, null_records
    
    validator.add_rule(
        name="AE_001",
        description="USUBJID cannot be null",
        validation_func=check_usubjid_not_null,
        severity=ValidationSeverity.ERROR
    )
    
    # Rule 2: AETERM (adverse event term) cannot be null
    def check_aeterm_not_null(df):
        null_records = df[df['AETERM'].isna()]
        return null_records.empty, null_records
    
    validator.add_rule(
        name="AE_002",
        description="AETERM (adverse event term) cannot be null",
        validation_func=check_aeterm_not_null,
        severity=ValidationSeverity.ERROR
    )
    
    # Rule 3: Severity must be valid
    def check_severity_values(df):
        valid_severity = ['MILD', 'MODERATE', 'SEVERE']
        invalid = df[~df['AESEV'].str.upper().isin(valid_severity)]
        return invalid.empty, invalid
    
    validator.add_rule(
        name="AE_003",
        description="AESEV must be MILD, MODERATE, or SEVERE",
        validation_func=check_severity_values,
        severity=ValidationSeverity.ERROR
    )
    
    # Rule 4: Serious AE flag must be Y or N
    def check_serious_flag(df):
        valid_flags = ['Y', 'N']
        invalid = df[~df['AESER'].str.upper().isin(valid_flags)]
        return invalid.empty, invalid
    
    validator.add_rule(
        name="AE_004",
        description="AESER (serious flag) must be Y or N",
        validation_func=check_serious_flag,
        severity=ValidationSeverity.ERROR
    )
    
    # Rule 5: End date should be >= start date
    def check_date_logic(df):
        # Only check where both dates exist
        with_dates = df[df['AESTDTC'].notna() & df['AEENDTC'].notna()]
        invalid = with_dates[with_dates['AEENDTC'] < with_dates['AESTDTC']]
        return invalid.empty, invalid
    
    validator.add_rule(
        name="AE_005",
        description="AEENDTC (end date) must be >= AESTDTC (start date)",
        validation_func=check_date_logic,
        severity=ValidationSeverity.ERROR
    )
    
    return validator


def create_vs_validator() -> ClinicalDataValidator:
    """
    Create validator for Vital Signs (VS) domain.
    """
    validator = ClinicalDataValidator("VS")
    
    # Rule 1: USUBJID cannot be null
    def check_usubjid_not_null(df):
        null_records = df[df['USUBJID'].isna()]
        return null_records.empty, null_records
    
    validator.add_rule(
        name="VS_001",
        description="USUBJID cannot be null",
        validation_func=check_usubjid_not_null,
        severity=ValidationSeverity.ERROR
    )
    
    # Rule 2: Test code must be populated
    def check_vstestcd_not_null(df):
        null_records = df[df['VSTESTCD'].isna()]
        return null_records.empty, null_records
    
    validator.add_rule(
        name="VS_002",
        description="VSTESTCD (test code) cannot be null",
        validation_func=check_vstestcd_not_null,
        severity=ValidationSeverity.ERROR
    )
    
    # Rule 3: Numeric result should be positive for most vitals
    def check_positive_values(df):
        numeric_df = df[df['VSSTRESN'].notna()]
        invalid = numeric_df[numeric_df['VSSTRESN'] < 0]
        return invalid.empty, invalid
    
    validator.add_rule(
        name="VS_003",
        description="VSSTRESN (numeric result) should be positive",
        validation_func=check_positive_values,
        severity=ValidationSeverity.WARNING
    )
    
    # Rule 4: Check for physiologically impossible values
    def check_vital_ranges(df):
        """Flag values that are likely data entry errors."""
        conditions = []
        
        # Heart rate: 20-250 bpm
        hr = df[(df['VSTESTCD'] == 'HR') & ((df['VSSTRESN'] < 20) | (df['VSSTRESN'] > 250))]
        conditions.append(hr)
        
        # Systolic BP: 50-250 mmHg
        sysbp = df[(df['VSTESTCD'] == 'SYSBP') & ((df['VSSTRESN'] < 50) | (df['VSSTRESN'] > 250))]
        conditions.append(sysbp)
        
        # Temperature: 30-45 C
        temp = df[(df['VSTESTCD'] == 'TEMP') & ((df['VSSTRESN'] < 30) | (df['VSSTRESN'] > 45))]
        conditions.append(temp)
        
        invalid = pd.concat(conditions) if conditions else pd.DataFrame()
        return invalid.empty, invalid
    
    validator.add_rule(
        name="VS_004",
        description="Vital sign values must be within physiological range",
        validation_func=check_vital_ranges,
        severity=ValidationSeverity.WARNING
    )
    
    return validator


def create_lb_validator() -> ClinicalDataValidator:
    """
    Create validator for Laboratory Results (LB) domain.
    """
    validator = ClinicalDataValidator("LB")
    
    # Rule 1: USUBJID cannot be null
    def check_usubjid_not_null(df):
        null_records = df[df['USUBJID'].isna()]
        return null_records.empty, null_records
    
    validator.add_rule(
        name="LB_001",
        description="USUBJID cannot be null",
        validation_func=check_usubjid_not_null,
        severity=ValidationSeverity.ERROR
    )
    
    # Rule 2: Test code must be populated
    def check_lbtestcd_not_null(df):
        null_records = df[df['LBTESTCD'].isna()]
        return null_records.empty, null_records
    
    validator.add_rule(
        name="LB_002",
        description="LBTESTCD (test code) cannot be null",
        validation_func=check_lbtestcd_not_null,
        severity=ValidationSeverity.ERROR
    )
    
    # Rule 3: Normal range indicator should be valid
    def check_nrind_values(df):
        valid_nrind = ['LOW', 'NORMAL', 'HIGH', 'ABNORMAL']
        # Only check where LBNRIND exists
        with_nrind = df[df['LBNRIND'].notna()]
        invalid = with_nrind[~with_nrind['LBNRIND'].str.upper().isin(valid_nrind)]
        return invalid.empty, invalid
    
    validator.add_rule(
        name="LB_003",
        description="LBNRIND must be LOW, NORMAL, HIGH, or ABNORMAL",
        validation_func=check_nrind_values,
        severity=ValidationSeverity.WARNING
    )
    
    # Rule 4: Normal range low should be < normal range high
    def check_range_logic(df):
        with_ranges = df[df['LBORNRLO'].notna() & df['LBORNRHI'].notna()]
        invalid = with_ranges[with_ranges['LBORNRLO'] >= with_ranges['LBORNRHI']]
        return invalid.empty, invalid
    
    validator.add_rule(
        name="LB_004",
        description="LBORNRLO must be less than LBORNRHI",
        validation_func=check_range_logic,
        severity=ValidationSeverity.ERROR
    )
    
    return validator


# =============================================================================
# VALIDATION RUNNER
# =============================================================================

def validate_clinical_data(
    df: pd.DataFrame,
    domain: str,
    source_path: str = ""
) -> DataQualityReport:
    """
    Main entry point for validating clinical trial data.
    
    Args:
        df: DataFrame containing clinical data
        domain: CDISC domain code (DM, AE, VS, LB)
        source_path: Path to source file for tracking
        
    Returns:
        DataQualityReport with complete validation results
        
    Example:
        >>> df = pd.read_parquet("bronze/dm/data.parquet")
        >>> report = validate_clinical_data(df, "DM", "s3://bucket/bronze/dm/")
        >>> if report.status == ValidationStatus.PASSED:
        ...     # Promote to Silver
        ... else:
        ...     # Quarantine and alert
    """
    # Select appropriate validator
    validators = {
        "DM": create_dm_validator,
        "AE": create_ae_validator,
        "VS": create_vs_validator,
        "LB": create_lb_validator
    }
    
    if domain not in validators:
        raise ValueError(f"Unknown domain: {domain}. Supported: {list(validators.keys())}")
    
    validator = validators[domain]()
    report = validator.validate(df)
    report.source_path = source_path
    
    return report


# =============================================================================
# EXAMPLE USAGE AND TESTING
# =============================================================================

if __name__ == "__main__":
    # Example: Create sample data and validate
    sample_dm = pd.DataFrame({
        "USUBJID": ["SUBJ001", "SUBJ002", "SUBJ003", None, "SUBJ002"],  # Has null and duplicate
        "AGE": [45, 32, 150, 28, 55],  # 150 is invalid
        "SEX": ["M", "F", "X", "M", "F"],  # X is invalid
        "ARM": ["TREATMENT", "PLACEBO", "TREATMENT", None, "PLACEBO"],
        "RFSTDTC": ["2024-01-15", "2024-01-16", "invalid-date", "2024-01-18", "2024-01-19"]
    })
    
    print("=" * 60)
    print("Clinical Data Quality Validation Demo")
    print("=" * 60)
    
    report = validate_clinical_data(sample_dm, "DM", "demo/sample_dm.csv")
    
    print(f"\nDomain: {report.domain}")
    print(f"Status: {report.status.value}")
    print(f"Total Records: {report.total_records}")
    print(f"\nValidation Results:")
    print("-" * 60)
    
    for result in report.results:
        status = "✓ PASS" if result.passed else "✗ FAIL"
        print(f"{status} | {result.rule_name}: {result.description}")
        if not result.passed:
            print(f"       Failed: {result.records_failed} records ({result.failure_percentage:.1f}%)")
    
    print("\n" + "=" * 60)
    print("Full report saved to: validation_report.json")
    report.save_to_json("validation_report.json")
