# Clinical Trial Data Platform

[![CI/CD Pipeline](https://github.com/YOUR_USERNAME/clinical-trial-data-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_USERNAME/clinical-trial-data-platform/actions/workflows/ci.yml)
[![Infrastructure](https://img.shields.io/badge/IaC-Terraform-purple)](https://www.terraform.io/)
[![AWS](https://img.shields.io/badge/Cloud-AWS-orange)](https://aws.amazon.com/)
[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A production-grade data engineering platform for clinical trial data, built on AWS with CDISC compliance, comprehensive data quality frameworks, and full lineage tracking. Designed to meet pharmaceutical R&D regulatory requirements including FDA 21 CFR Part 11 considerations.

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        CLINICAL TRIAL DATA PLATFORM                             │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│   DATA SOURCES              MEDALLION ARCHITECTURE              CONSUMERS       │
│   ────────────              ────────────────────────            ─────────       │
│                                                                                 │
│   ┌──────────┐         ┌─────────┐    ┌─────────┐    ┌─────────┐              │
│   │  Clinical │         │ BRONZE  │    │ SILVER  │    │  GOLD   │   ┌────────┐ │
│   │  Trials   │────────▶│  (Raw)  │───▶│(Clean)  │───▶│(Serving)│──▶│Redshift│ │
│   └──────────┘    │    └─────────┘    └─────────┘    └─────────┘   └────────┘ │
│                   │         │              │              │              │      │
│   ┌──────────┐    │         ▼              ▼              ▼              ▼      │
│   │   Lab    │    │    ┌─────────────────────────────────────────────────────┐ │
│   │ Results  │────┤    │                    AWS S3 DATA LAKE                 │ │
│   └──────────┘    │    │  s3://clinical-trial-platform-{env}/                │ │
│                   │    │    ├── bronze/     (raw ingested data)              │ │
│   ┌──────────┐    │    │    ├── silver/     (validated, standardized)        │ │
│   │  Vital   │────┤    │    ├── gold/       (analytics-ready)                │ │
│   │  Signs   │    │    │    └── metadata/   (lineage, quality metrics)       │ │
│   └──────────┘    │    └─────────────────────────────────────────────────────┘ │
│                   │                                                             │
│   ┌──────────┐    │    ┌─────────┐    ┌─────────┐    ┌─────────────────────┐   │
│   │ Adverse  │────┘    │ Lambda  │    │  Glue   │    │    Data Quality     │   │
│   │ Events   │         │Ingest   │    │  ETL    │    │  Great Expectations │   │
│   └──────────┘         └─────────┘    └─────────┘    └─────────────────────┘   │
│                                                                                 │
│   ┌─────────────────────────────────────────────────────────────────────────┐  │
│   │                        GOVERNANCE & COMPLIANCE                          │  │
│   │  • Data Lineage Tracking    • Audit Logging    • CDISC Compliance      │  │
│   │  • Quality KPIs             • Encryption       • Access Controls        │  │
│   └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
│   ┌─────────────────────────────────────────────────────────────────────────┐  │
│   │                        INFRASTRUCTURE                                    │  │
│   │  • Terraform IaC           • GitHub Actions CI/CD    • Docker           │  │
│   └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 🎯 Key Features

### Data Engineering
- **Medallion Architecture**: Bronze → Silver → Gold data layers with clear separation of concerns
- **CDISC Compliance**: Data models aligned with CDISC SDTM standards (DM, AE, VS, LB domains)
- **Scalable Ingestion**: Event-driven Lambda functions with automatic retry and dead-letter queues
- **Efficient Transformations**: AWS Glue PySpark jobs with optimized partitioning strategies

### Data Quality & Governance
- **Validation Framework**: Great Expectations integration with custom clinical data validators
- **Data Lineage**: End-to-end tracking from source to serving layer
- **Audit Logging**: Complete audit trail for regulatory compliance
- **Quality KPIs**: Real-time metrics on data freshness, completeness, and accuracy

### Infrastructure & Operations
- **Infrastructure as Code**: 100% Terraform-managed AWS resources
- **CI/CD Pipeline**: Automated testing, linting, and deployment via GitHub Actions
- **Cost Optimization**: Auto-scaling, lifecycle policies, and resource teardown scripts
- **Monitoring**: CloudWatch dashboards and SNS alerting

## 📊 Data Model

The platform implements CDISC SDTM-aligned domains for clinical trial data:

| Domain | Description | Key Variables |
|--------|-------------|---------------|
| **DM** | Demographics | USUBJID, SITEID, AGE, SEX, RACE, ARM |
| **AE** | Adverse Events | AETERM, AESEV, AEREL, AESTDTC, AEENDTC |
| **VS** | Vital Signs | VSTESTCD, VSORRES, VSORRESU, VSDTC |
| **LB** | Lab Results | LBTESTCD, LBORRES, LBORNRLO, LBORNRHI |

See [DATA_MODEL.md](docs/architecture/DATA_MODEL.md) for complete schema documentation.

## 🚀 Quick Start

### Prerequisites
- AWS Account with appropriate permissions
- Python 3.11+
- Terraform 1.5+
- AWS CLI configured

### Local Development Setup

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/clinical-trial-data-platform.git
cd clinical-trial-data-platform

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run tests
make test
```

### Deploy Infrastructure

```bash
# Initialize Terraform
cd infrastructure/terraform
terraform init

# Deploy to dev environment
terraform workspace new dev
terraform plan -var-file=environments/dev.tfvars
terraform apply -var-file=environments/dev.tfvars
```

### Generate Synthetic Data

```bash
# Generate test clinical trial data
python data/synthetic/generator.py --subjects 1000 --output data/synthetic/output/
```

## 📁 Project Structure

```
clinical-trial-data-platform/
├── README.md
├── docs/
│   ├── architecture/           # System design documentation
│   ├── adr/                    # Architecture Decision Records
│   └── runbooks/               # Operational guides
├── infrastructure/
│   ├── terraform/              # IaC for all AWS resources
│   └── docker/                 # Container definitions
├── src/
│   ├── ingestion/              # Lambda ingestion functions
│   ├── transformation/         # Glue ETL jobs
│   ├── data_quality/           # Validation & lineage
│   └── analytics/              # SQL schemas & queries
├── data/
│   └── synthetic/              # Test data generation
├── .github/
│   └── workflows/              # CI/CD pipelines
└── scripts/                    # Utility scripts
```

## 🔒 Security & Compliance

This platform is designed with pharmaceutical regulatory requirements in mind:

- **Encryption**: All data encrypted at rest (S3 SSE-S3) and in transit (TLS 1.2+)
- **Access Control**: IAM roles with least-privilege principles
- **Audit Trail**: Complete logging of all data operations
- **Data Lineage**: Full traceability from source to destination
- **HIPAA Considerations**: Designed for PHI handling (synthetic data used in demo)

## 📈 Cost Optimization

Estimated monthly costs for development environment:

| Service | Configuration | Est. Cost |
|---------|--------------|-----------|
| S3 | < 5GB storage | ~$0.12 |
| Lambda | < 1M invocations | Free tier |
| Glue | 2-3 DPU hours/day | ~$1-2 |
| Redshift Serverless | Auto-pause enabled | ~$0-5 |
| **Total** | | **~$2-8/month** |

Use `scripts/teardown_aws.sh` to destroy all resources when not in use.

## 🗺️ Roadmap

- [x] Core data pipeline (Bronze → Silver → Gold)
- [x] CDISC-compliant data model
- [x] Data quality framework
- [x] Terraform infrastructure
- [x] CI/CD pipeline
- [ ] Real-time streaming ingestion (Kinesis)
- [ ] ML feature store integration
- [ ] Advanced analytics views
- [ ] Multi-region deployment

## 📚 Documentation

- [Architecture Overview](docs/architecture/ARCHITECTURE.md)
- [Data Model Specification](docs/architecture/DATA_MODEL.md)
- [Deployment Guide](docs/runbooks/DEPLOYMENT.md)
- [Troubleshooting Guide](docs/runbooks/TROUBLESHOOTING.md)

### Architecture Decision Records
- [ADR-001: AWS-Native Approach](docs/adr/001-aws-native-approach.md)
- [ADR-002: Medallion Architecture](docs/adr/002-medallion-architecture.md)
- [ADR-003: CDISC Compliance Strategy](docs/adr/003-cdisc-compliance.md)
- [ADR-004: Cost Optimization](docs/adr/004-cost-optimization.md)

## 🤝 Contributing

Contributions are welcome! Please read our contributing guidelines and submit pull requests.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Note**: This platform uses synthetic clinical trial data for demonstration purposes. No real patient data is used or stored.
