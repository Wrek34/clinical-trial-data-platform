# ADR-001: AWS-Native Approach for Clinical Trial Data Platform

## Status
Accepted

## Date
2024-01-15

## Context

We need to build a data engineering platform for clinical trial data that will:
- Process data from multiple sources (clinical trials, lab systems, medical devices)
- Meet pharmaceutical regulatory requirements
- Scale with growing data volumes
- Be maintainable by a small team

We evaluated three approaches:
1. **AWS-native services** (S3, Lambda, Glue, Redshift)
2. **Open-source stack on AWS** (Airflow, Spark, PostgreSQL on EC2/EKS)
3. **Multi-cloud/cloud-agnostic** (Databricks, Snowflake)

## Decision

We will adopt an **AWS-native approach** using managed services:
- **S3** for data lake storage
- **Lambda** for event-driven ingestion
- **Glue** for ETL transformations
- **Redshift Serverless** for data warehousing
- **CloudWatch** for monitoring
- **IAM** for access control

## Rationale

### Why AWS-Native?

1. **Regulatory Compliance**
   - AWS has extensive HIPAA, GxP, and FDA 21 CFR Part 11 compliance documentation
   - BAA (Business Associate Agreement) readily available
   - Audit logging built into all services
   - Encryption at rest and in transit by default

2. **Operational Simplicity**
   - Managed services reduce operational burden
   - No infrastructure to patch or maintain
   - Automatic scaling handles variable workloads
   - Built-in high availability

3. **Cost Efficiency for Variable Workloads**
   - Lambda: Pay only for execution time
   - Glue: Pay per DPU-hour, no idle costs
   - Redshift Serverless: Auto-scales and pauses when inactive
   - S3: Tiered storage with lifecycle policies

4. **Integration Cohesion**
   - Native integration between services (S3 events → Lambda)
   - IAM provides unified access control
   - CloudWatch provides unified monitoring
   - VPC provides unified networking

5. **Team Skillset**
   - AWS is the most common enterprise cloud
   - Extensive documentation and community support
   - Easier to hire AWS-skilled engineers

### Why Not Open-Source Stack?

- Higher operational overhead (managing Airflow, Spark clusters)
- More complex security configuration
- Requires dedicated DevOps resources
- Not significantly cheaper for our scale

### Why Not Multi-Cloud?

- Added complexity without clear benefit
- Vendor lock-in concerns are overstated for our use case
- Data residency in single cloud simplifies compliance
- Databricks/Snowflake add significant cost

## Consequences

### Positive
- Faster time to production
- Lower operational burden
- Simplified compliance story
- Cost optimization through serverless pricing
- Easier hiring and onboarding

### Negative
- AWS vendor dependency
- Some services have learning curves (Glue)
- May need to refactor if moving clouds later
- Less flexibility than raw Spark/Airflow

### Mitigations
- Use Terraform for infrastructure (portable patterns)
- Keep business logic in Python (portable code)
- Abstract AWS-specific code behind interfaces
- Document all AWS-specific configurations

## Related Decisions
- ADR-002: Medallion Architecture
- ADR-004: Cost Optimization Strategy

## References
- [AWS HIPAA Compliance](https://aws.amazon.com/compliance/hipaa-compliance/)
- [AWS GxP Compliance](https://aws.amazon.com/compliance/gxp-part-11-background/)
- [Serverless Data Lake Framework](https://aws.amazon.com/solutions/implementations/serverless-data-lake-framework/)
