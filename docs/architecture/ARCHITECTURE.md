# Architecture Overview

## System Design

The Clinical Trial Data Platform is a cloud-native data engineering solution built on AWS, designed to process pharmaceutical R&D data while meeting regulatory compliance requirements.

## High-Level Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                         DATA SOURCES                               │
├────────────────────────────────────────────────────────────────────┤
│  EDC Systems    Lab Systems    Medical Devices    EHR Systems      │
└───────┬────────────┬───────────────┬────────────────┬──────────────┘
        │            │               │                │
        ▼            ▼               ▼                ▼
┌────────────────────────────────────────────────────────────────────┐
│                      INGESTION LAYER                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐ │
│  │ S3 Events    │  │   Lambda     │  │  Dead Letter Queue       │ │
│  │ (Trigger)    │──│  Functions   │──│  (Failed Records)        │ │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘ │
└────────────────────────────┬───────────────────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────────────────┐
│                       DATA LAKE (S3)                               │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐            │
│  │   BRONZE    │    │   SILVER    │    │    GOLD     │            │
│  │   (Raw)     │───▶│ (Validated) │───▶│  (Serving)  │            │
│  │             │    │             │    │             │            │
│  │ • Append    │    │ • CDISC     │    │ • Star      │            │
│  │ • Partition │    │ • Quality   │    │ • Aggreg    │            │
│  └─────────────┘    └─────────────┘    └─────────────┘            │
└────────────────────────────┬───────────────────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────────────────┐
│                    TRANSFORMATION LAYER                            │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │                      AWS Glue ETL                            │ │
│  │  • Bronze → Silver: Validation, CDISC transformation         │ │
│  │  • Silver → Gold: Aggregation, dimensional modeling          │ │
│  └──────────────────────────────────────────────────────────────┘ │
└────────────────────────────┬───────────────────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────────────────┐
│                      SERVING LAYER                                 │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │                  Redshift Serverless                         │ │
│  │  • Dimensional tables    • Materialized views                │ │
│  │  • SQL analytics         • BI tool connectivity              │ │
│  └──────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────┘
```

## Component Details

### Ingestion Layer
- **S3 Event Notifications**: Trigger processing when files land
- **Lambda Functions**: Validate, add metadata, route to Bronze
- **Dead Letter Queue**: Capture failed ingestion for retry

### Storage Layer (S3)
- **Bronze**: Raw data, source schema, append-only
- **Silver**: Validated, CDISC-standardized, quality-checked
- **Gold**: Analytics-ready, dimensional model

### Transformation Layer (Glue)
- PySpark-based ETL jobs
- Great Expectations integration
- Lineage tracking

### Serving Layer (Redshift)
- Serverless for cost optimization
- Auto-scaling and auto-pause
- SQL interface for analysts

## Data Flow

1. Source systems upload files to S3 landing zone
2. S3 event triggers Lambda ingestion function
3. Lambda validates and moves to Bronze layer
4. Glue job transforms Bronze → Silver (CDISC compliance)
5. Glue job transforms Silver → Gold (analytics)
6. Redshift loads Gold layer for querying

## Security Architecture

- **Encryption**: SSE-S3 at rest, TLS in transit
- **Access Control**: IAM roles with least privilege
- **Network**: VPC with private subnets for Redshift
- **Audit**: CloudTrail for API logging, S3 access logs

## Monitoring

- CloudWatch metrics and alarms
- SNS notifications for failures
- Data quality dashboards
