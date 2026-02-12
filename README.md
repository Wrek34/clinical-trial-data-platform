# Clinical Trial Data Platform

[![CI/CD Pipeline](https://github.com/Wrek34/clinical-trial-data-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/Wrek34/clinical-trial-data-platform/actions/workflows/ci.yml)
[![Infrastructure](https://img.shields.io/badge/IaC-Terraform-purple)](https://www.terraform.io/)
[![AWS](https://img.shields.io/badge/Cloud-AWS-orange)](https://aws.amazon.com/)
[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://www.python.org/)
[![CDISC](https://img.shields.io/badge/Standard-CDISC%20SDTM-green)](https://www.cdisc.org/)

> A production-grade data engineering platform for pharmaceutical clinical trial data, built on AWS with CDISC compliance, comprehensive data quality frameworks, and complete audit trails.

---

## 🎯 Project Overview

This platform demonstrates end-to-end data engineering capabilities for regulated pharmaceutical environments:

- **Ingests** raw clinical trial data from multiple sources
- **Validates** data quality with 20+ automated checks
- **Transforms** to CDISC SDTM regulatory standards
- **Serves** analytics-ready dimensional models
- **Tracks** complete data lineage for audit compliance

### Why This Project?

Clinical trial data engineering presents unique challenges:
1. **Regulatory Compliance**: FDA 21 CFR Part 11 requires complete audit trails
2. **Data Standards**: CDISC SDTM is mandatory for drug submissions
3. **Data Quality**: Patient safety depends on data accuracy
4. **Scale**: Modern trials generate millions of data points

This platform addresses all four challenges with a modern, cloud-native architecture.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     CLINICAL TRIAL DATA PLATFORM                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────┐     ┌─────────────────────────────────────────────┐   │
│  │   SOURCE    │     │              AWS DATA LAKE                   │   │
│  │   SYSTEMS   │     │                                              │   │
│  │             │     │  ┌─────────┐  ┌─────────┐  ┌─────────┐      │   │
│  │ • EDC       │────▶│  │ BRONZE  │─▶│ SILVER  │─▶│  GOLD   │      │   │
│  │ • Labs      │     │  │  (Raw)  │  │(Valid)  │  │(Serving)│      │   │
│  │ • Devices   │     │  └─────────┘  └─────────┘  └─────────┘      │   │
│  └─────────────┘     │       │            │            │            │   │
│                      │       ▼            ▼            ▼            │   │
│                      │  ┌─────────────────────────────────────────┐ │   │
│                      │  │         Amazon S3 Data Lake             │ │   │
│                      │  └─────────────────────────────────────────┘ │   │
│                      └─────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    PROCESSING LAYER                              │   │
│  │  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐  │   │
│  │  │  Lambda  │    │   Glue   │    │   Glue   │    │ Redshift │  │   │
│  │  │ Ingest   │    │ Bronze→  │    │ Silver→  │    │Serverless│  │   │
│  │  │          │    │ Silver   │    │ Gold     │    │          │  │   │
│  │  └──────────┘    └──────────┘    └──────────┘    └──────────┘  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                 GOVERNANCE & QUALITY                             │   │
│  │  • Data Validation (20+ rules)    • CDISC SDTM Compliance       │   │
│  │  • Lineage Tracking               • Audit Logging                │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

### Medallion Architecture

| Layer | Purpose | Retention | Format |
|-------|---------|-----------|--------|
| **Bronze** | Raw data exactly as received | 7 years (regulatory) | Parquet |
| **Silver** | Validated, CDISC-standardized | 7 years | Parquet |
| **Gold** | Analytics-ready dimensional model | Rebuild from Silver | Parquet |

---

## 🔬 CDISC Compliance

The platform implements **CDISC SDTM** (Study Data Tabulation Model) standards required by FDA and EMA:

| Domain | Description | Key Variables |
|--------|-------------|---------------|
| **DM** | Demographics | USUBJID, AGE, SEX, RACE, ARM |
| **AE** | Adverse Events | AETERM, AESEV, AEREL, AESTDTC |
| **VS** | Vital Signs | VSTESTCD, VSORRES, VSNRIND |
| **LB** | Lab Results | LBTESTCD, LBSTRESN, LBNRIND |

---

## ✅ Data Quality Framework

Comprehensive validation framework with 20+ automated checks:

```python
from data_quality.validators import validate_clinical_data, ValidationStatus

report = validate_clinical_data(df, domain="DM")

if report.status == ValidationStatus.PASSED:
    promote_to_silver(df)
else:
    quarantine_for_review(df, report)
```

### Sample Validation Rules

| Rule ID | Domain | Description | Severity |
|---------|--------|-------------|----------|
| DM_001 | Demographics | USUBJID must be unique | ERROR |
| DM_003 | Demographics | Age between 0-120 | ERROR |
| AE_003 | Adverse Events | Severity must be MILD/MODERATE/SEVERE | ERROR |
| VS_004 | Vital Signs | Values within physiological range | WARNING |

---

## 📊 Analytics Capabilities

Pre-built SQL analytics for the Gold layer:

- **Enrollment Dashboard**: Subjects by site, treatment arm, demographics
- **Safety Analysis**: Adverse event rates, serious AE tracking
- **Efficacy Metrics**: Vital signs trends, lab results analysis
- **Data Quality**: Completeness reports, validation summaries

---

## 🚀 Quick Start

### Prerequisites
- AWS Account with CLI configured
- Python 3.11+
- Terraform 1.5+

### Deploy

```bash
# Clone and navigate
git clone https://github.com/Wrek34/clinical-trial-data-platform.git
cd clinical-trial-data-platform

# Deploy infrastructure
cd infrastructure/terraform
terraform init
terraform apply -var-file="environments/dev.tfvars"

# Generate test data
cd ../..
python data/synthetic/generator.py --subjects 500

# Upload to S3
aws s3 cp data/synthetic/output/ s3://YOUR-BUCKET/bronze/synthetic/ --recursive
```

### Teardown (Avoid Charges)

```bash
terraform destroy -var-file="environments/dev.tfvars"
```

---

## 📁 Project Structure

```
clinical-trial-data-platform/
├── data/synthetic/           # CDISC-compliant test data generator
├── docs/
│   ├── architecture/         # System design docs
│   └── adr/                  # Architecture Decision Records
├── infrastructure/terraform/ # IaC modules (S3, Lambda, Glue, IAM)
├── src/
│   ├── ingestion/            # Lambda handlers
│   ├── transformation/       # Glue ETL scripts
│   ├── data_quality/         # Validation & lineage
│   └── analytics/            # SQL queries
└── .github/workflows/        # CI/CD pipelines
```

---

## 💰 Cost Optimization

| Environment | Monthly Cost | Strategy |
|-------------|--------------|----------|
| **Development** | ~$3 | Serverless, auto-pause, aggressive lifecycle |
| **Production** | ~$350 | Scaled compute, standard retention |

---

## 🛠️ Technology Stack

| Category | Technology |
|----------|------------|
| Cloud | AWS (S3, Lambda, Glue, Redshift Serverless) |
| IaC | Terraform |
| Language | Python 3.11, PySpark, SQL |
| CI/CD | GitHub Actions |
| Testing | pytest |
| Standards | CDISC SDTM 3.3 |

---

## 📚 Documentation

- [Architecture Overview](docs/architecture/ARCHITECTURE.md)
- [Data Model](docs/architecture/DATA_MODEL.md)
- [ADR-001: AWS-Native Approach](docs/adr/001-aws-native-approach.md)
- [ADR-002: Medallion Architecture](docs/adr/002-medallion-architecture.md)
- [ADR-003: CDISC Compliance](docs/adr/003-cdisc-compliance.md)
- [ADR-004: Cost Optimization](docs/adr/004-cost-optimization.md)

---

## 👤 Author

Built by a data engineer with 7 years of military healthcare experience and Columbia University CS background.

- GitHub: [@Wrek34](https://github.com/Wrek34)

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.
