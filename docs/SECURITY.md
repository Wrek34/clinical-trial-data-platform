# Security Architecture

> This document describes the security posture of the Clinical Trial Data Platform, including threat model, controls, and compliance mapping.

## Overview

Clinical trial data platforms handle sensitive patient information subject to multiple regulatory frameworks. This platform implements defense-in-depth security controls aligned with:

- **HIPAA** (Health Insurance Portability and Accountability Act)
- **FDA 21 CFR Part 11** (Electronic Records; Electronic Signatures)
- **GDPR** (General Data Protection Regulation) - where applicable
- **AWS Well-Architected Framework** - Security Pillar

---

## Threat Model

### Assets to Protect

| Asset | Classification | Impact if Compromised |
|-------|---------------|----------------------|
| Patient identifiers (USUBJID contains site/subject) | PHI | HIPAA breach, regulatory action |
| Clinical measurements (vitals, labs) | PHI | Patient privacy violation |
| Adverse event data | PHI + Safety Critical | Patient safety risk |
| Treatment arm assignments | Confidential | Study unblinding |
| AWS credentials | Critical | Full infrastructure compromise |

### Threat Actors

| Actor | Capability | Motivation |
|-------|------------|------------|
| External attacker | Medium-High | Data theft, ransomware |
| Malicious insider | High (authorized access) | Data theft, sabotage |
| Accidental insider | Low (mistakes) | Unintentional exposure |
| Competitor | Medium | Corporate espionage |
| Regulatory auditor | Full access (authorized) | Compliance verification |

### Attack Vectors

1. **Credential compromise** - AWS keys exposed in code/logs
2. **Data exfiltration** - Unauthorized S3 access
3. **Injection attacks** - Malicious data in ingestion
4. **Privilege escalation** - Over-permissioned IAM roles
5. **Supply chain** - Compromised dependencies

---

## Security Controls

### 1. Identity & Access Management (IAM)

**Principle: Least Privilege**

```
┌─────────────────────────────────────────────────────────────┐
│                    IAM Architecture                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    │
│  │   Lambda    │    │    Glue     │    │  Redshift   │    │
│  │    Role     │    │    Role     │    │    Role     │    │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘    │
│         │                  │                  │            │
│         ▼                  ▼                  ▼            │
│  ┌─────────────────────────────────────────────────────┐  │
│  │              Scoped IAM Policies                     │  │
│  │  • S3: specific bucket/prefix only                  │  │
│  │  • Glue: specific database/tables only              │  │
│  │  • CloudWatch: specific log groups only             │  │
│  │  • NO admin permissions                             │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Controls Implemented:**

| Control | Implementation |
|---------|---------------|
| Role separation | Separate roles for Lambda, Glue, Redshift |
| Least privilege | Each role has only required permissions |
| No long-lived credentials | Service roles use temporary credentials |
| Resource-level permissions | S3 access limited to specific buckets/prefixes |
| Condition keys | Restrict by source IP, VPC, time where applicable |

**Example Lambda Policy (Scoped):**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "S3AccessBronzeOnly",
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject"],
      "Resource": [
        "arn:aws:s3:::clinical-trial-${env}-data/landing/*",
        "arn:aws:s3:::clinical-trial-${env}-data/bronze/*"
      ]
    },
    {
      "Sid": "DenyOtherBuckets",
      "Effect": "Deny",
      "Action": "s3:*",
      "NotResource": "arn:aws:s3:::clinical-trial-${env}-data/*"
    }
  ]
}
```

### 2. Encryption

**At Rest:**

| Layer | Encryption | Key Management |
|-------|------------|----------------|
| S3 Bronze/Silver/Gold | SSE-KMS | AWS managed key (option: CMK) |
| Redshift | AES-256 | AWS managed |
| Secrets Manager | AES-256 | AWS managed |
| CloudWatch Logs | AES-256 | AWS managed |

**In Transit:**

| Connection | Encryption |
|------------|------------|
| S3 access | TLS 1.2+ enforced via bucket policy |
| Glue connections | TLS 1.2+ |
| Redshift connections | SSL required |
| API calls | HTTPS only |

**S3 Bucket Policy (Enforce TLS):**

```json
{
  "Statement": [
    {
      "Sid": "DenyInsecureTransport",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:*",
      "Resource": [
        "arn:aws:s3:::clinical-trial-${env}-data",
        "arn:aws:s3:::clinical-trial-${env}-data/*"
      ],
      "Condition": {
        "Bool": {"aws:SecureTransport": "false"}
      }
    }
  ]
}
```

### 3. Data Protection

**Tokenization/Masking Strategy:**

For production environments with real PHI:

```
┌────────────────────────────────────────────────────────┐
│                 Data Protection Flow                    │
├────────────────────────────────────────────────────────┤
│                                                        │
│  Raw Data ──▶ Tokenization ──▶ Bronze (tokenized)     │
│                    │                                   │
│                    ▼                                   │
│           Token Vault (Secrets Manager)               │
│           • Original ↔ Token mapping                  │
│           • Access audit logged                       │
│           • Separate IAM policy                       │
│                                                        │
│  Silver/Gold: Only tokenized IDs, no direct PHI      │
│                                                        │
└────────────────────────────────────────────────────────┘
```

**Fields requiring protection:**

| Field | Protection Method |
|-------|-------------------|
| Patient name (if present) | Not stored - tokenize at source |
| Date of birth | Generalize to age at consent |
| Site-specific subject ID | Deterministic hash/token |
| Geographic data | Aggregate to region level |

**Current Implementation (Dev/Demo):**

This demo environment uses **synthetic data only** - no real PHI is processed. The data generator creates realistic but fake identifiers.

For production deployment:
1. Enable tokenization module before ingestion
2. Configure Secrets Manager for token vault
3. Implement column-level encryption for sensitive fields
4. Enable Macie for PHI detection

### 4. Network Security

**Architecture:**

```
┌─────────────────────────────────────────────────────────────┐
│                    VPC Architecture                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                   Private Subnets                    │   │
│  │                                                      │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐         │   │
│  │  │  Glue    │  │ Redshift │  │  Lambda  │         │   │
│  │  │  Jobs    │  │ Cluster  │  │(VPC mode)│         │   │
│  │  └──────────┘  └──────────┘  └──────────┘         │   │
│  │                                                      │   │
│  └───────────────────────┬──────────────────────────────┘   │
│                          │                                   │
│                 ┌────────▼────────┐                         │
│                 │  VPC Endpoints  │                         │
│                 │  • S3 Gateway   │                         │
│                 │  • Glue         │                         │
│                 │  • Secrets Mgr  │                         │
│                 └─────────────────┘                         │
│                                                             │
│  NO INTERNET GATEWAY for data plane traffic                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Controls:**

- VPC endpoints for AWS service access (no internet traversal)
- Security groups restrict inbound to known sources
- No public IP addresses on compute resources
- Flow logs enabled for network monitoring

### 5. Audit & Logging

**Comprehensive audit trail for 21 CFR Part 11:**

| Event Type | Log Destination | Retention |
|------------|-----------------|-----------|
| AWS API calls | CloudTrail → S3 | 7 years |
| S3 data access | S3 Access Logs | 7 years |
| Lambda execution | CloudWatch Logs | 7 years |
| Glue job runs | CloudWatch Logs | 7 years |
| Data validation | S3 (JSON artifacts) | 7 years |
| Lineage events | S3 (OpenLineage) | 7 years |
| Redshift queries | Audit logging | 7 years |

**Log Protection:**

- Logs stored in separate "audit" bucket
- Object Lock enabled (WORM - Write Once Read Many)
- Cross-account replication for tamper resistance
- Encryption at rest

### 6. Secrets Management

**No hardcoded credentials:**

| Secret | Storage | Rotation |
|--------|---------|----------|
| Redshift admin password | Secrets Manager | 90 days |
| API keys (if any) | Secrets Manager | 90 days |
| Database connection strings | Secrets Manager | On change |

**Access Pattern:**

```python
# Correct: Retrieve at runtime
import boto3

def get_secret():
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId='redshift-credentials')
    return json.loads(response['SecretString'])

# NEVER: Hardcode credentials
# password = "my-secret-password"  # ❌ NEVER DO THIS
```

---

## Compliance Mapping

### HIPAA Technical Safeguards

| Requirement | Control | Status |
|-------------|---------|--------|
| Access Control (§164.312(a)(1)) | IAM roles, least privilege | ✅ |
| Audit Controls (§164.312(b)) | CloudTrail, access logs | ✅ |
| Integrity Controls (§164.312(c)(1)) | Checksums, versioning | ✅ |
| Transmission Security (§164.312(e)(1)) | TLS 1.2+, VPC endpoints | ✅ |
| Encryption (§164.312(a)(2)(iv)) | SSE-KMS, TLS | ✅ |

### FDA 21 CFR Part 11

| Requirement | Control | Status |
|-------------|---------|--------|
| Audit trail (§11.10(e)) | Lineage tracking, CloudTrail | ✅ |
| Record retention (§11.10(c)) | S3 lifecycle, 7-year retention | ✅ |
| System access controls (§11.10(d)) | IAM, role separation | ✅ |
| Authority checks (§11.10(g)) | IAM policies, resource boundaries | ✅ |
| Input checks (§11.10(h)) | Data validation, contracts | ✅ |

---

## Incident Response

### Severity Levels

| Level | Definition | Response Time |
|-------|------------|---------------|
| P1 - Critical | Active data breach, system compromise | 15 minutes |
| P2 - High | Potential breach, unusual access patterns | 1 hour |
| P3 - Medium | Failed security controls, misconfigurations | 4 hours |
| P4 - Low | Security improvement opportunities | 24 hours |

### Response Procedures

1. **Detect** - CloudWatch alarms, GuardDuty findings
2. **Contain** - Revoke credentials, isolate resources
3. **Investigate** - Analyze CloudTrail, access logs
4. **Remediate** - Patch vulnerabilities, rotate secrets
5. **Report** - Document incident, notify stakeholders
6. **Improve** - Update controls, runbooks

---

## Security Checklist

### Deployment Checklist

- [ ] IAM roles follow least privilege
- [ ] S3 bucket policies enforce TLS
- [ ] Encryption enabled on all storage
- [ ] VPC endpoints configured
- [ ] CloudTrail enabled and logging
- [ ] Secrets in Secrets Manager (not hardcoded)
- [ ] Security groups reviewed
- [ ] Audit logging retention configured

### Periodic Review Checklist (Quarterly)

- [ ] Review IAM policies for privilege creep
- [ ] Audit CloudTrail for anomalous access
- [ ] Rotate secrets
- [ ] Review security group rules
- [ ] Test incident response procedures
- [ ] Update threat model if needed

---

## Contact

For security concerns, contact the platform owner or create a private security advisory.
