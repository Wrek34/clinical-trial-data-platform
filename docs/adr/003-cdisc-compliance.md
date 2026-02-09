# ADR-003: CDISC Compliance Strategy

## Status
Accepted

## Date
2024-01-16

## Context

Clinical trial data submitted to regulatory agencies (FDA, EMA) must follow standardized formats. The Clinical Data Interchange Standards Consortium (CDISC) provides these standards:

- **SDTM** (Study Data Tabulation Model): Standard for submitting clinical trial data
- **ADaM** (Analysis Data Model): Standard for analysis-ready datasets
- **CDASH** (Clinical Data Acquisition Standards Harmonization): Standard for data collection
- **ODM** (Operational Data Model): Standard for data exchange

Our platform must:
1. Accept data in various source formats
2. Transform and store data in CDISC-compliant structures
3. Support regulatory submissions
4. Enable audit traceability

## Decision

We will implement **CDISC SDTM alignment** in our Silver layer with the following approach:

### Core Domains Implemented

| Domain | Description | Key Variables |
|--------|-------------|---------------|
| DM | Demographics | USUBJID, SITEID, AGE, SEX, RACE, ARM |
| AE | Adverse Events | AETERM, AESEV, AEREL, AESTDTC |
| VS | Vital Signs | VSTESTCD, VSORRES, VSORRESU |
| LB | Laboratory | LBTESTCD, LBORRES, LBNRIND |
| CM | Concomitant Meds | CMTRT, CMDOSE, CMSTDTC |
| MH | Medical History | MHTERM, MHSTDTC |

### Variable Naming Conventions

Following SDTM naming standards:
```
{DOMAIN}{VARNAME}

Examples:
- USUBJID: Unique Subject Identifier (used across all domains)
- AESTDTC: Adverse Event Start Date/Time Character
- VSORRESU: Vital Signs Original Result Unit
- LBNRIND: Lab Normal Range Indicator
```

### Controlled Terminology

We enforce CDISC Controlled Terminology for:
- Sex (M, F, U, UNDIFFERENTIATED)
- Race (WHITE, BLACK OR AFRICAN AMERICAN, ASIAN, etc.)
- Severity (MILD, MODERATE, SEVERE)
- Relationship (NOT RELATED, POSSIBLY RELATED, etc.)
- Units (standardized per test type)

## Implementation

### Bronze → Silver Transformation

```python
# Pseudocode for CDISC transformation
class CDISCTransformer:
    def transform_demographics(self, raw_df):
        """Transform raw demographics to SDTM DM domain."""
        return (
            raw_df
            .with_column("DOMAIN", lit("DM"))
            .with_column("USUBJID", 
                concat(col("STUDYID"), lit("-"), 
                       col("SITEID"), lit("-"), 
                       col("SUBJID")))
            .with_column("SEX", 
                when(col("gender") == "Male", "M")
                .when(col("gender") == "Female", "F")
                .otherwise("U"))
            # ... more transformations
            .select(DM_COLUMNS)  # Enforce column order
        )
```

### Validation Rules

Each domain has specific validation rules:

```yaml
# dm_validation_rules.yaml
domain: DM
rules:
  - name: usubjid_unique
    type: uniqueness
    column: USUBJID
    severity: error
    
  - name: age_range
    type: range
    column: AGE
    min: 0
    max: 120
    severity: warning
    
  - name: sex_controlled_terminology
    type: allowed_values
    column: SEX
    values: ["M", "F", "U", "UNDIFFERENTIATED"]
    severity: error
    
  - name: arm_not_null
    type: not_null
    column: ARM
    severity: error
```

### Schema Enforcement

Silver layer enforces strict schemas:

```python
DM_SCHEMA = {
    "STUDYID": StringType(),
    "DOMAIN": StringType(),  # Always "DM"
    "USUBJID": StringType(),  # Primary key
    "SUBJID": StringType(),
    "SITEID": StringType(),
    "AGE": IntegerType(),
    "AGEU": StringType(),  # Always "YEARS"
    "SEX": StringType(),  # Controlled terminology
    "RACE": StringType(),  # Controlled terminology
    "ETHNIC": StringType(),
    "COUNTRY": StringType(),
    "ARM": StringType(),
    "ARMCD": StringType(),
    "RFSTDTC": StringType(),  # ISO 8601 format
    "RFENDTC": StringType(),
}
```

## Rationale

### Why SDTM (not ADaM)?

1. **Foundation First**: SDTM is the source for ADaM derivations
2. **Regulatory Requirement**: SDTM required for FDA submissions
3. **Simpler Scope**: ADaM requires analysis-specific transformations
4. **Future Extension**: Can build ADaM on top of SDTM Silver layer

### Why Partial Implementation?

1. **Pragmatic Scope**: Full SDTM has 50+ domains
2. **Core Coverage**: DM, AE, VS, LB cover majority of use cases
3. **Extensible Design**: Easy to add domains as needed
4. **Demonstrate Competency**: Shows understanding without over-engineering

### Why Silver Layer (not Bronze)?

1. **Bronze Preserves Source**: Raw data needed for audit
2. **Silver is Transformed**: Natural place for standardization
3. **Separation of Concerns**: Ingestion vs. transformation
4. **Reprocessing**: CDISC logic changes don't require re-ingestion

## Consequences

### Positive
- Regulatory submission ready
- Consistent data structure
- Industry-standard terminology
- Interoperability with other CDISC tools
- Clear documentation of standards

### Negative
- Mapping complexity from source systems
- Maintenance of controlled terminology
- Training requirement for team
- Some source richness may be lost

### Mitigations
- Source-to-SDTM mapping documentation
- Automated terminology validation
- CDISC training resources linked in docs
- Preserve original values in Bronze

## Data Quality Impact

CDISC compliance enables specific quality checks:

| Check | Domain | Rule |
|-------|--------|------|
| Referential Integrity | All | USUBJID exists in DM |
| Date Consistency | AE | AESTDTC >= RFSTDTC |
| Controlled Terms | All | Values in allowed list |
| Required Fields | All | Domain-specific requirements |
| Cross-Domain | AE/CM | Concomitant medication for AE treatment |

## Related Decisions
- ADR-002: Medallion Architecture (where CDISC fits)
- ADR-001: AWS-Native Approach (implementation platform)

## References
- [CDISC SDTM Implementation Guide](https://www.cdisc.org/standards/foundational/sdtm)
- [CDISC Controlled Terminology](https://www.cdisc.org/standards/terminology)
- [FDA Study Data Standards](https://www.fda.gov/industry/fda-resources-data-standards/study-data-standards-resources)
- [CDISC SHARE API](https://www.cdisc.org/cdisc-share)
