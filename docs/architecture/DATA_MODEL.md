# Data Model Specification

## Overview

This document describes the data models used in the Clinical Trial Data Platform, aligned with CDISC SDTM (Study Data Tabulation Model) standards.

## CDISC Domains Implemented

### DM - Demographics

Subject-level demographic information.

| Variable | Label | Type | Description |
|----------|-------|------|-------------|
| STUDYID | Study Identifier | String | Unique study identifier |
| DOMAIN | Domain Abbreviation | String | Always "DM" |
| USUBJID | Unique Subject ID | String | Primary key: STUDYID-SITEID-SUBJID |
| SUBJID | Subject ID | String | Subject ID within site |
| SITEID | Site Identifier | String | Study site identifier |
| AGE | Age | Integer | Age at enrollment |
| AGEU | Age Units | String | Always "YEARS" |
| SEX | Sex | String | M, F, U, UNDIFFERENTIATED |
| RACE | Race | String | CDISC controlled terminology |
| ETHNIC | Ethnicity | String | HISPANIC OR LATINO, NOT HISPANIC OR LATINO |
| COUNTRY | Country | String | ISO 3166-1 alpha-3 |
| ARM | Treatment Arm | String | Planned treatment arm |
| ARMCD | Arm Code | String | Short code for ARM |
| RFSTDTC | Reference Start Date | String | ISO 8601 date |
| RFENDTC | Reference End Date | String | ISO 8601 date |

### AE - Adverse Events

Records of adverse events experienced by subjects.

| Variable | Label | Type | Description |
|----------|-------|------|-------------|
| STUDYID | Study Identifier | String | Unique study identifier |
| DOMAIN | Domain Abbreviation | String | Always "AE" |
| USUBJID | Unique Subject ID | String | Foreign key to DM |
| AESEQ | Sequence Number | Integer | Unique within subject |
| AETERM | Reported Term | String | Verbatim AE term |
| AEDECOD | Dictionary Term | String | MedDRA preferred term |
| AEBODSYS | Body System | String | System organ class |
| AESEV | Severity | String | MILD, MODERATE, SEVERE |
| AESER | Serious | String | Y, N |
| AEREL | Relationship | String | Relationship to treatment |
| AEOUT | Outcome | String | AE outcome |
| AESTDTC | Start Date | String | ISO 8601 date |
| AEENDTC | End Date | String | ISO 8601 date |

### VS - Vital Signs

Vital sign measurements.

| Variable | Label | Type | Description |
|----------|-------|------|-------------|
| STUDYID | Study Identifier | String | Unique study identifier |
| DOMAIN | Domain Abbreviation | String | Always "VS" |
| USUBJID | Unique Subject ID | String | Foreign key to DM |
| VSSEQ | Sequence Number | Integer | Unique within subject |
| VSTESTCD | Test Code | String | HR, SYSBP, DIABP, TEMP, etc. |
| VSTEST | Test Name | String | Full test name |
| VSORRES | Original Result | String | Result as collected |
| VSORRESU | Original Units | String | Units of VSORRES |
| VSSTRESN | Numeric Result | Float | Standardized numeric |
| VSNRIND | Normal Range Ind | String | LOW, NORMAL, HIGH |
| VISITNUM | Visit Number | Integer | Visit sequence |
| VSDTC | Date/Time | String | ISO 8601 date |

### LB - Laboratory Results

Laboratory test results.

| Variable | Label | Type | Description |
|----------|-------|------|-------------|
| STUDYID | Study Identifier | String | Unique study identifier |
| DOMAIN | Domain Abbreviation | String | Always "LB" |
| USUBJID | Unique Subject ID | String | Foreign key to DM |
| LBSEQ | Sequence Number | Integer | Unique within subject |
| LBTESTCD | Test Code | String | ALT, AST, CREAT, etc. |
| LBTEST | Test Name | String | Full test name |
| LBORRES | Original Result | String | Result as collected |
| LBORRESU | Original Units | String | Units of LBORRES |
| LBSTRESN | Numeric Result | Float | Standardized numeric |
| LBNRIND | Normal Range Ind | String | LOW, NORMAL, HIGH |
| LBORNRLO | Normal Range Low | Float | Lower limit |
| LBORNRHI | Normal Range High | Float | Upper limit |
| VISITNUM | Visit Number | Integer | Visit sequence |
| LBDTC | Date/Time | String | ISO 8601 date |
| LBSPEC | Specimen Type | String | BLOOD, URINE, etc. |

## Gold Layer - Dimensional Model

### Dimension Tables

**dim_subject**
- subject_key (surrogate)
- usubjid (natural)
- study_id, site_id
- age, sex, race, ethnicity
- treatment_arm
- enrollment_date

**dim_site**
- site_key (surrogate)
- site_id (natural)
- country, region

**dim_date**
- date_key (surrogate)
- full_date
- year, quarter, month, day
- is_weekend, is_holiday

### Fact Tables

**fact_adverse_events**
- ae_key, subject_key, site_key, date_key
- ae_term, severity, seriousness
- relationship, outcome
- duration_days

**fact_vital_signs**
- vs_key, subject_key, site_key, date_key
- test_code, result_value, unit
- normal_range_indicator

**fact_lab_results**
- lb_key, subject_key, site_key, date_key
- test_code, result_value, unit
- normal_range_indicator
