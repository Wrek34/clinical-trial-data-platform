<div align="center">

# 🏥 Clinical Trial Data Platform

### Production-Grade Data Engineering for Pharmaceutical R&D

[![CI Pipeline](https://github.com/Wrek34/clinical-trial-data-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/Wrek34/clinical-trial-data-platform/actions/workflows/ci.yml)
&nbsp;
[![Terraform](https://img.shields.io/badge/IaC-Terraform-7B42BC?logo=terraform)](https://www.terraform.io/)
&nbsp;
[![AWS](https://img.shields.io/badge/Cloud-AWS-FF9900?logo=amazonaws)](https://aws.amazon.com/)
&nbsp;
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://www.python.org/)
&nbsp;
[![CDISC](https://img.shields.io/badge/Standard-CDISC%20SDTM-00A99D)](https://www.cdisc.org/)

<br/>

[Features](#-features) •
[Architecture](#-architecture) •
[Quick Start](#-quick-start) •
[Documentation](#-documentation)

<br/>

<img src="https://raw.githubusercontent.com/Wrek34/clinical-trial-data-platform/main/docs/architecture/banner.png" alt="Platform Banner" width="800"/>

</div>

---

## 🎯 Overview

A **production-grade data platform** for pharmaceutical clinical trials that transforms raw study data into regulatory-compliant, analytics-ready datasets.

<table>
<tr>
<td width="50%">

### The Challenge

Clinical trial data engineering is uniquely complex:

- 📋 **Regulatory Compliance** - FDA 21 CFR Part 11
- 📊 **Data Standards** - CDISC SDTM mandatory
- ✅ **Data Quality** - Patient safety depends on it
- 📈 **Scale** - Millions of data points per study

</td>
<td width="50%">

### The Solution

This platform addresses all four:

- 🔒 **Complete Audit Trails** - Every change tracked
- 🏷️ **CDISC Native** - Built for SDTM from day one
- 🛡️ **20+ Validation Rules** - Automated quality gates
- ☁️ **Serverless Scale** - Pay only for what you use

</td>
</tr>
</table>

---

## ✨ Features

<table>
<tr>
<td align="center" width="25%">
<img src="https://img.icons8.com/fluency/96/000000/database.png" width="48"/>
<br/><b>Medallion Architecture</b>
<br/><sub>Bronze → Silver → Gold layers</sub>
</td>
<td align="center" width="25%">
<img src="https://img.icons8.com/fluency/96/000000/checked.png" width="48"/>
<br/><b>Data Quality</b>
<br/><sub>20+ automated validation rules</sub>
</td>
<td align="center" width="25%">
<img src="https://img.icons8.com/fluency/96/000000/flow-chart.png" width="48"/>
<br/><b>Data Lineage</b>
<br/><sub>Complete audit trail tracking</sub>
</td>
<td align="center" width="25%">
<img src="https://img.icons8.com/fluency/96/000000/medical-doctor.png" width="48"/>
<br/><b>CDISC Compliant</b>
<br/><sub>FDA/EMA submission ready</sub>
</td>
</tr>
</table>

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        CLINICAL TRIAL DATA PLATFORM                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌──────────┐      ┌─────────────────────────────────────────────────┐    │
│   │  SOURCE  │      │               AWS DATA LAKE (S3)                │    │
│   │ SYSTEMS  │      │                                                 │    │
│   │          │      │   ┌─────────┐   ┌─────────┐   ┌─────────┐      │    │
│   │ • EDC    │ ───▶ │   │ BRONZE  │──▶│ SILVER  │──▶│  GOLD   │      │    │
│   │ • Labs   │      │   │  (Raw)  │   │(Valid)  │   │(Serving)│      │    │
│   │ • Devices│      │   └─────────┘   └─────────┘   └─────────┘      │    │
│   └──────────┘      │        │             │             │           │    │
│                     │        ▼             ▼             ▼           │    │
│                     │   ┌─────────────────────────────────────┐      │    │
│                     │   │     Lambda  │  Glue ETL  │ Redshift │      │    │
│                     │   └─────────────────────────────────────┘      │    │
│                     └─────────────────────────────────────────────────┘    │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │  📋 Validation    📊 Lineage    🔐 IAM    📈 CloudWatch    🏷️ CDISC │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Medallion Architecture

| Layer | Purpose | Retention | Key Feature |
|:------|:--------|:----------|:------------|
| 🥉 **Bronze** | Raw data preservation | 7 years | Immutable audit trail |
| 🥈 **Silver** | Validated & standardized | 7 years | CDISC SDTM compliant |
| 🥇 **Gold** | Analytics-ready | Rebuildable | Dimensional model |

---

## 🔬 CDISC Domains

<table>
<tr>
<th>Domain</th>
<th>Description</th>
<th>Key Variables</th>
<th>Validation Rules</th>
</tr>
<tr>
<td><b>DM</b></td>
<td>Demographics</td>
<td><code>USUBJID</code>, <code>AGE</code>, <code>SEX</code>, <code>ARM</code></td>
<td>6 rules</td>
</tr>
<tr>
<td><b>AE</b></td>
<td>Adverse Events</td>
<td><code>AETERM</code>, <code>AESEV</code>, <code>AESER</code></td>
<td>5 rules</td>
</tr>
<tr>
<td><b>VS</b></td>
<td>Vital Signs</td>
<td><code>VSTESTCD</code>, <code>VSSTRESN</code>, <code>VSNRIND</code></td>
<td>4 rules</td>
</tr>
<tr>
<td><b>LB</b></td>
<td>Lab Results</td>
<td><code>LBTESTCD</code>, <code>LBSTRESN</code>, <code>LBNRIND</code></td>
<td>4 rules</td>
</tr>
</table>

---

## 🚀 Quick Start

### Prerequisites

- AWS Account with CLI configured
- Python 3.11+
- Terraform 1.5+

### Deploy

```bash
# Clone repository
git clone https://github.com/Wrek34/clinical-trial-data-platform.git
cd clinical-trial-data-platform

# Generate test data
python data/synthetic/generator.py --subjects 500

# Deploy infrastructure
cd infrastructure/terraform
terraform init
terraform apply -var-file="environments/dev.tfvars"

# Upload data to S3
aws s3 cp ../../data/synthetic/output/ s3://YOUR-BUCKET/bronze/ --recursive
```

### Teardown

```bash
terraform destroy -var-file="environments/dev.tfvars"
```

---

## 📁 Project Structure

```
clinical-trial-data-platform/
├── 📊 data/synthetic/          # CDISC test data generator
├── 📚 docs/
│   ├── architecture/           # System design & diagrams
│   └── adr/                    # Architecture decisions
├── 🏗️ infrastructure/terraform/
│   └── modules/                # S3, Lambda, Glue, IAM
├── 💻 src/
│   ├── ingestion/              # Lambda handlers
│   ├── transformation/         # Glue ETL scripts
│   ├── data_quality/           # Validators & lineage
│   └── analytics/              # SQL queries
└── ⚙️ .github/workflows/       # CI/CD pipelines
```

---

## 💰 Cost Optimization

| Environment | Monthly Cost | Strategy |
|:------------|:-------------|:---------|
| 🔧 **Development** | ~$3 | Serverless, auto-pause |
| 🚀 **Production** | ~$350 | Scaled, standard retention |

---

## 🛠️ Tech Stack

<table>
<tr>
<td align="center"><img src="https://img.icons8.com/color/48/000000/amazon-web-services.png"/><br/><b>AWS</b></td>
<td align="center"><img src="https://img.icons8.com/color/48/000000/terraform.png"/><br/><b>Terraform</b></td>
<td align="center"><img src="https://img.icons8.com/color/48/000000/python.png"/><br/><b>Python</b></td>
<td align="center"><img src="https://img.icons8.com/color/48/000000/apache-spark.png"/><br/><b>PySpark</b></td>
<td align="center"><img src="https://img.icons8.com/color/48/000000/postgreesql.png"/><br/><b>SQL</b></td>
<td align="center"><img src="https://img.icons8.com/color/48/000000/github.png"/><br/><b>GitHub Actions</b></td>
</tr>
</table>

---

## 📚 Documentation

| Document | Description |
|:---------|:------------|
| [Architecture Overview](docs/architecture/ARCHITECTURE.md) | System design |
| [Architecture Diagrams](docs/architecture/DIAGRAMS.md) | Visual diagrams |
| [Data Model](docs/architecture/DATA_MODEL.md) | CDISC specifications |
| [ADR-001: AWS Native](docs/adr/001-aws-native-approach.md) | Why AWS |
| [ADR-002: Medallion](docs/adr/002-medallion-architecture.md) | Why medallion |
| [ADR-003: CDISC](docs/adr/003-cdisc-compliance.md) | CDISC implementation |
| [ADR-004: Cost](docs/adr/004-cost-optimization.md) | Cost strategy |

---

## 👤 Author

<table>
<tr>
<td>
<b>Background</b><br/>
• 7 years military healthcare<br/>
• Columbia University CS<br/>
• Healthcare data engineering focus
</td>
<td>
<b>Connect</b><br/>
• GitHub: <a href="https://github.com/Wrek34">@Wrek34</a><br/>
• LinkedIn: [Your LinkedIn]
</td>
</tr>
</table>

---

<div align="center">

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

<br/>

**Built with ❤️ for better clinical trials**

</div>
