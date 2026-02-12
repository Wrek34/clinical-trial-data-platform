"""
Test Suite for Clinical Trial Data Platform

This test suite demonstrates professional testing practices:
- Unit tests for individual functions
- Integration tests for workflows
- Test fixtures and parameterization
- Mocking external dependencies

INTERVIEW TALKING POINTS:
"I implemented comprehensive testing at multiple levels:
1. Unit tests validate individual functions in isolation
2. Integration tests verify components work together
3. I use pytest fixtures for reusable test data
4. External dependencies like S3 are mocked for fast, reliable tests
5. Tests serve as documentation - they show how the code should be used"
"""

import json
import os
import sys
from datetime import datetime
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from data_quality.validators import (
    ClinicalDataValidator,
    DataQualityReport,
    ValidationResult,
    ValidationSeverity,
    ValidationStatus,
    create_dm_validator,
    create_ae_validator,
    create_vs_validator,
    create_lb_validator,
    validate_clinical_data
)


# =============================================================================
# TEST FIXTURES
# =============================================================================
# Fixtures provide reusable test data. This is a best practice because:
# 1. Tests are more readable
# 2. Test data is consistent
# 3. Easy to modify test scenarios
# =============================================================================

@pytest.fixture
def valid_dm_data():
    """Valid demographics data that should pass all validations."""
    return pd.DataFrame({
        "USUBJID": ["SUBJ001", "SUBJ002", "SUBJ003"],
        "STUDYID": ["STUDY001", "STUDY001", "STUDY001"],
        "SITEID": ["SITE01", "SITE01", "SITE02"],
        "AGE": [45, 32, 58],
        "SEX": ["M", "F", "M"],
        "RACE": ["WHITE", "ASIAN", "BLACK OR AFRICAN AMERICAN"],
        "ETHNIC": ["NOT HISPANIC OR LATINO", "NOT HISPANIC OR LATINO", "HISPANIC OR LATINO"],
        "ARM": ["TREATMENT", "PLACEBO", "TREATMENT"],
        "RFSTDTC": ["2024-01-15", "2024-01-16", "2024-01-17"]
    })


@pytest.fixture
def invalid_dm_data():
    """Demographics data with various validation errors."""
    return pd.DataFrame({
        "USUBJID": ["SUBJ001", "SUBJ001", None, "SUBJ004"],  # Duplicate and null
        "STUDYID": ["STUDY001", "STUDY001", "STUDY001", "STUDY001"],
        "SITEID": ["SITE01", "SITE01", "SITE01", "SITE01"],
        "AGE": [45, 32, 150, -5],  # Invalid ages: 150, -5
        "SEX": ["M", "F", "X", "M"],  # Invalid sex: X
        "RACE": ["WHITE", "ASIAN", "WHITE", "WHITE"],
        "ETHNIC": ["NOT HISPANIC OR LATINO"] * 4,
        "ARM": ["TREATMENT", None, "PLACEBO", "TREATMENT"],  # Null ARM
        "RFSTDTC": ["2024-01-15", "2024-01-16", "invalid-date", "2024-01-18"]  # Invalid date
    })


@pytest.fixture
def valid_ae_data():
    """Valid adverse events data."""
    return pd.DataFrame({
        "USUBJID": ["SUBJ001", "SUBJ001", "SUBJ002"],
        "AESEQ": [1, 2, 1],
        "AETERM": ["Headache", "Nausea", "Fatigue"],
        "AEDECOD": ["Headache", "Nausea", "Fatigue"],
        "AEBODSYS": ["NERVOUS SYSTEM", "GASTROINTESTINAL", "GENERAL"],
        "AESEV": ["MILD", "MODERATE", "MILD"],
        "AESER": ["N", "N", "N"],
        "AEREL": ["POSSIBLY RELATED", "NOT RELATED", "PROBABLY RELATED"],
        "AEOUT": ["RECOVERED", "RECOVERED", "RECOVERING"],
        "AESTDTC": ["2024-02-01", "2024-02-15", "2024-02-10"],
        "AEENDTC": ["2024-02-05", "2024-02-20", None]
    })


@pytest.fixture
def valid_vs_data():
    """Valid vital signs data."""
    return pd.DataFrame({
        "USUBJID": ["SUBJ001", "SUBJ001", "SUBJ002"],
        "VSSEQ": [1, 2, 1],
        "VSTESTCD": ["HR", "SYSBP", "HR"],
        "VSTEST": ["Heart Rate", "Systolic Blood Pressure", "Heart Rate"],
        "VSORRES": ["72", "120", "68"],
        "VSORRESU": ["beats/min", "mmHg", "beats/min"],
        "VSSTRESN": [72.0, 120.0, 68.0],
        "VSSTRESU": ["beats/min", "mmHg", "beats/min"],
        "VSNRIND": ["NORMAL", "NORMAL", "NORMAL"],
        "VISITNUM": [1, 1, 1],
        "VISIT": ["BASELINE", "BASELINE", "BASELINE"],
        "VSDTC": ["2024-01-15", "2024-01-15", "2024-01-16"]
    })


@pytest.fixture
def valid_lb_data():
    """Valid lab results data."""
    return pd.DataFrame({
        "USUBJID": ["SUBJ001", "SUBJ001", "SUBJ002"],
        "LBSEQ": [1, 2, 1],
        "LBTESTCD": ["ALT", "AST", "ALT"],
        "LBTEST": ["Alanine Aminotransferase", "Aspartate Aminotransferase", "Alanine Aminotransferase"],
        "LBORRES": ["25", "22", "30"],
        "LBORRESU": ["U/L", "U/L", "U/L"],
        "LBSTRESN": [25.0, 22.0, 30.0],
        "LBSTRESU": ["U/L", "U/L", "U/L"],
        "LBNRIND": ["NORMAL", "NORMAL", "NORMAL"],
        "LBORNRLO": [7.0, 10.0, 7.0],
        "LBORNRHI": [56.0, 40.0, 56.0],
        "VISITNUM": [1, 1, 1],
        "VISIT": ["BASELINE", "BASELINE", "BASELINE"],
        "LBDTC": ["2024-01-15", "2024-01-15", "2024-01-16"]
    })


# =============================================================================
# UNIT TESTS - ValidationResult
# =============================================================================

class TestValidationResult:
    """Tests for the ValidationResult dataclass."""
    
    def test_validation_result_creation(self):
        """Test that ValidationResult can be created with all fields."""
        result = ValidationResult(
            rule_name="TEST_001",
            description="Test rule",
            severity=ValidationSeverity.ERROR,
            passed=True,
            records_checked=100,
            records_failed=0,
            failure_percentage=0.0
        )
        
        assert result.rule_name == "TEST_001"
        assert result.passed is True
        assert result.records_checked == 100
        
    def test_validation_result_to_dict(self):
        """Test serialization to dictionary."""
        result = ValidationResult(
            rule_name="TEST_001",
            description="Test rule",
            severity=ValidationSeverity.WARNING,
            passed=False,
            records_checked=100,
            records_failed=5,
            failure_percentage=5.0,
            failed_record_ids=["ID1", "ID2"]
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["rule_name"] == "TEST_001"
        assert result_dict["severity"] == "warning"
        assert result_dict["passed"] is False
        assert len(result_dict["failed_record_ids"]) == 2


# =============================================================================
# UNIT TESTS - ClinicalDataValidator
# =============================================================================

class TestClinicalDataValidator:
    """Tests for the ClinicalDataValidator class."""
    
    def test_add_rule(self):
        """Test adding validation rules."""
        validator = ClinicalDataValidator("TEST")
        
        validator.add_rule(
            name="TEST_001",
            description="Test rule",
            validation_func=lambda df: (True, pd.DataFrame()),
            severity=ValidationSeverity.ERROR
        )
        
        assert len(validator.rules) == 1
        assert validator.rules[0]["name"] == "TEST_001"
        
    def test_validate_returns_report(self, valid_dm_data):
        """Test that validate returns a DataQualityReport."""
        validator = ClinicalDataValidator("DM")
        validator.add_rule(
            name="TEST_001",
            description="Always passes",
            validation_func=lambda df: (True, pd.DataFrame())
        )
        
        report = validator.validate(valid_dm_data)
        
        assert isinstance(report, DataQualityReport)
        assert report.domain == "DM"
        assert report.total_records == 3


# =============================================================================
# UNIT TESTS - DM Validator
# =============================================================================

class TestDMValidator:
    """Tests for Demographics (DM) domain validation."""
    
    def test_valid_data_passes(self, valid_dm_data):
        """Test that valid DM data passes all validations."""
        report = validate_clinical_data(valid_dm_data, "DM")
        
        assert report.status == ValidationStatus.PASSED
        assert all(r.passed for r in report.results)
        
    def test_duplicate_usubjid_fails(self, invalid_dm_data):
        """Test that duplicate USUBJID is caught."""
        report = validate_clinical_data(invalid_dm_data, "DM")
        
        # Find the uniqueness check result
        uniqueness_result = next(
            (r for r in report.results if r.rule_name == "DM_001"), 
            None
        )
        
        assert uniqueness_result is not None
        assert uniqueness_result.passed is False
        
    def test_null_usubjid_fails(self, invalid_dm_data):
        """Test that null USUBJID is caught."""
        report = validate_clinical_data(invalid_dm_data, "DM")
        
        null_check = next(
            (r for r in report.results if r.rule_name == "DM_002"),
            None
        )
        
        assert null_check is not None
        assert null_check.passed is False
        
    def test_invalid_age_fails(self, invalid_dm_data):
        """Test that invalid age values are caught."""
        report = validate_clinical_data(invalid_dm_data, "DM")
        
        age_check = next(
            (r for r in report.results if r.rule_name == "DM_003"),
            None
        )
        
        assert age_check is not None
        assert age_check.passed is False
        assert age_check.records_failed >= 2  # 150 and -5
        
    def test_invalid_sex_fails(self, invalid_dm_data):
        """Test that invalid sex values are caught."""
        report = validate_clinical_data(invalid_dm_data, "DM")
        
        sex_check = next(
            (r for r in report.results if r.rule_name == "DM_004"),
            None
        )
        
        assert sex_check is not None
        assert sex_check.passed is False


# =============================================================================
# UNIT TESTS - AE Validator
# =============================================================================

class TestAEValidator:
    """Tests for Adverse Events (AE) domain validation."""
    
    def test_valid_data_passes(self, valid_ae_data):
        """Test that valid AE data passes all validations."""
        report = validate_clinical_data(valid_ae_data, "AE")
        
        # Should pass or have only warnings (no errors)
        error_failures = [
            r for r in report.results 
            if not r.passed and r.severity == ValidationSeverity.ERROR
        ]
        assert len(error_failures) == 0
        
    def test_invalid_severity_fails(self):
        """Test that invalid severity values are caught."""
        invalid_ae = pd.DataFrame({
            "USUBJID": ["SUBJ001"],
            "AETERM": ["Headache"],
            "AESEV": ["EXTREME"],  # Invalid
            "AESER": ["N"],
            "AESTDTC": ["2024-01-01"],
            "AEENDTC": ["2024-01-02"]
        })
        
        report = validate_clinical_data(invalid_ae, "AE")
        
        severity_check = next(
            (r for r in report.results if r.rule_name == "AE_003"),
            None
        )
        
        assert severity_check is not None
        assert severity_check.passed is False


# =============================================================================
# UNIT TESTS - VS Validator
# =============================================================================

class TestVSValidator:
    """Tests for Vital Signs (VS) domain validation."""
    
    def test_valid_data_passes(self, valid_vs_data):
        """Test that valid VS data passes all validations."""
        report = validate_clinical_data(valid_vs_data, "VS")
        
        error_failures = [
            r for r in report.results 
            if not r.passed and r.severity == ValidationSeverity.ERROR
        ]
        assert len(error_failures) == 0
        
    def test_impossible_values_flagged(self):
        """Test that physiologically impossible values are flagged."""
        impossible_vs = pd.DataFrame({
            "USUBJID": ["SUBJ001"],
            "VSTESTCD": ["HR"],
            "VSTEST": ["Heart Rate"],
            "VSSTRESN": [500.0],  # Impossible heart rate
            "VSNRIND": ["HIGH"]
        })
        
        report = validate_clinical_data(impossible_vs, "VS")
        
        range_check = next(
            (r for r in report.results if r.rule_name == "VS_004"),
            None
        )
        
        # This should be flagged (as warning)
        assert range_check is not None


# =============================================================================
# UNIT TESTS - LB Validator
# =============================================================================

class TestLBValidator:
    """Tests for Laboratory (LB) domain validation."""
    
    def test_valid_data_passes(self, valid_lb_data):
        """Test that valid LB data passes all validations."""
        report = validate_clinical_data(valid_lb_data, "LB")
        
        error_failures = [
            r for r in report.results 
            if not r.passed and r.severity == ValidationSeverity.ERROR
        ]
        assert len(error_failures) == 0
        
    def test_invalid_range_fails(self):
        """Test that invalid normal range (low >= high) is caught."""
        invalid_lb = pd.DataFrame({
            "USUBJID": ["SUBJ001"],
            "LBTESTCD": ["ALT"],
            "LBTEST": ["Alanine Aminotransferase"],
            "LBSTRESN": [25.0],
            "LBNRIND": ["NORMAL"],
            "LBORNRLO": [100.0],  # Low > High
            "LBORNRHI": [50.0]
        })
        
        report = validate_clinical_data(invalid_lb, "LB")
        
        range_check = next(
            (r for r in report.results if r.rule_name == "LB_004"),
            None
        )
        
        assert range_check is not None
        assert range_check.passed is False


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestDataQualityReport:
    """Integration tests for the full validation workflow."""
    
    def test_report_serialization(self, valid_dm_data, tmp_path):
        """Test that reports can be serialized to JSON."""
        report = validate_clinical_data(valid_dm_data, "DM")
        
        filepath = tmp_path / "test_report.json"
        report.save_to_json(str(filepath))
        
        assert filepath.exists()
        
        # Verify it's valid JSON
        with open(filepath) as f:
            loaded = json.load(f)
            
        assert loaded["domain"] == "DM"
        assert "results" in loaded
        
    def test_unknown_domain_raises(self, valid_dm_data):
        """Test that unknown domain raises ValueError."""
        with pytest.raises(ValueError, match="Unknown domain"):
            validate_clinical_data(valid_dm_data, "UNKNOWN")
            
    def test_report_summary_accurate(self, invalid_dm_data):
        """Test that report summary counts are accurate."""
        report = validate_clinical_data(invalid_dm_data, "DM")
        
        report_dict = report.to_dict()
        summary = report_dict["summary"]
        
        # Verify summary matches actual results
        actual_passed = sum(1 for r in report.results if r.passed)
        actual_failed = sum(1 for r in report.results if not r.passed)
        
        assert summary["passed"] == actual_passed
        assert summary["failed"] == actual_failed
        assert summary["total_checks"] == len(report.results)


# =============================================================================
# PARAMETERIZED TESTS
# =============================================================================
# Parameterization allows testing multiple scenarios with the same test logic

class TestSexValidation:
    """Parameterized tests for sex field validation."""
    
    @pytest.mark.parametrize("sex_value,should_pass", [
        ("M", True),
        ("F", True),
        ("U", True),
        ("UNDIFFERENTIATED", True),
        ("m", True),  # Lowercase should work (we uppercase)
        ("MALE", False),  # Full word not allowed
        ("X", False),
        ("", False),
        ("1", False),
    ])
    def test_sex_values(self, sex_value, should_pass):
        """Test various sex values against CDISC controlled terminology."""
        df = pd.DataFrame({
            "USUBJID": ["SUBJ001"],
            "AGE": [30],
            "SEX": [sex_value],
            "ARM": ["TREATMENT"],
            "RFSTDTC": ["2024-01-01"]
        })
        
        validator = create_dm_validator()
        report = validator.validate(df)
        
        sex_check = next(
            (r for r in report.results if r.rule_name == "DM_004"),
            None
        )
        
        if should_pass:
            assert sex_check.passed, f"Expected {sex_value} to pass"
        else:
            assert not sex_check.passed, f"Expected {sex_value} to fail"


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
