# ADR-002: Medallion Architecture (Bronze/Silver/Gold)

## Status
Accepted

## Date
2024-01-15

## Context

Clinical trial data flows through multiple stages of processing:
1. Raw ingestion from source systems
2. Validation and standardization
3. Transformation for analytics

We need an architecture that:
- Preserves raw data for audit purposes (regulatory requirement)
- Enables data quality enforcement
- Supports reprocessing when logic changes
- Provides clear data lineage
- Separates concerns between stages

We evaluated:
1. **Medallion Architecture** (Bronze → Silver → Gold)
2. **Lambda Architecture** (Batch + Speed layers)
3. **Kappa Architecture** (Stream-only)
4. **Traditional ETL** (Direct source to warehouse)

## Decision

We will implement a **Medallion Architecture** with three layers:

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  SOURCE      BRONZE           SILVER           GOLD             │
│  SYSTEMS     (Raw)            (Validated)      (Serving)        │
│                                                                 │
│  ┌─────┐    ┌─────────┐      ┌─────────┐      ┌─────────┐      │
│  │ EDC │───▶│ Raw JSON │────▶│ CDISC   │────▶│Analytics│      │
│  └─────┘    │ Parquet  │     │ Standard│     │ Tables  │      │
│             │          │     │ Cleaned │     │         │      │
│  ┌─────┐    │ Append-  │     │ Dedupe  │     │ Aggreg- │      │
│  │ Lab │───▶│ Only     │────▶│ Valid   │────▶│ ations  │      │
│  └─────┘    │          │     │         │     │         │      │
│             │ Partiti- │     │ Type-   │     │ Joined  │      │
│  ┌─────┐    │ oned by  │     │ Safe    │     │ Dimens- │      │
│  │ EHR │───▶│ Date     │────▶│         │────▶│ ional   │      │
│  └─────┘    └─────────┘      └─────────┘      └─────────┘      │
│                                                                 │
│  Storage:   s3://bucket/     s3://bucket/     s3://bucket/     │
│             bronze/          silver/          gold/            │
│                                                                 │
│  Format:    Parquet          Parquet          Parquet +        │
│             (source schema)  (standard)       Redshift         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Layer Definitions

#### Bronze Layer (Raw)
- **Purpose**: Land data exactly as received
- **Processing**: Minimal - only add metadata
- **Schema**: Source system schema (can vary)
- **Storage**: `s3://bucket/bronze/{source}/{domain}/{date}/`
- **Retention**: 7 years (regulatory requirement)
- **Updates**: Append-only (never modify)

#### Silver Layer (Validated)
- **Purpose**: Clean, standardized, validated data
- **Processing**: 
  - Schema enforcement
  - Data type casting
  - Deduplication
  - Null handling
  - CDISC standardization
  - Quality validation
- **Schema**: Standard CDISC-aligned
- **Storage**: `s3://bucket/silver/{domain}/{date}/`
- **Updates**: Reprocessed from Bronze when logic changes

#### Gold Layer (Serving)
- **Purpose**: Analytics-ready data
- **Processing**:
  - Business aggregations
  - Dimensional modeling
  - Pre-computed metrics
  - Cross-domain joins
- **Schema**: Star/snowflake schema
- **Storage**: `s3://bucket/gold/{table}/` + Redshift
- **Updates**: Incremental or full refresh

## Rationale

### Why Medallion?

1. **Regulatory Compliance**
   - Bronze preserves original data for audit
   - Clear lineage from source to analytics
   - Can prove data transformations
   - Supports "right to be forgotten" via tombstoning

2. **Data Quality**
   - Validation happens at clear boundary (Bronze→Silver)
   - Bad data quarantined, doesn't pollute Gold
   - Quality metrics per layer
   - Failed records traceable

3. **Reprocessing**
   - Logic changes don't require re-ingestion
   - Silver can be rebuilt from Bronze
   - Gold can be rebuilt from Silver
   - Supports A/B testing of transformations

4. **Separation of Concerns**
   - Ingestion team owns Bronze
   - Data engineering owns Silver
   - Analytics owns Gold
   - Clear contracts between layers

5. **Performance**
   - Gold optimized for query patterns
   - Silver optimized for processing
   - Bronze optimized for landing

### Why Not Lambda Architecture?

- Complexity of maintaining two code paths (batch + stream)
- Our data is mostly batch-oriented
- Real-time requirements minimal
- Can add streaming later if needed

### Why Not Direct ETL?

- Loses raw data (compliance risk)
- Hard to debug transformations
- Difficult to reprocess
- No clear quality gates

## Consequences

### Positive
- Clear data lineage
- Supports regulatory audits
- Enables data quality enforcement
- Allows iterative processing logic changes
- Scales independently per layer

### Negative
- Storage cost (3 copies of data)
- Latency (multiple processing stages)
- Complexity (more jobs to manage)

### Mitigations
- S3 lifecycle policies move old Bronze to Glacier
- Incremental processing where possible
- Clear naming conventions and documentation
- Automated orchestration

## S3 Path Conventions

```
s3://clinical-trial-platform-{env}/
├── bronze/
│   ├── clinical-edc/
│   │   ├── dm/
│   │   │   └── year=2024/month=01/day=15/
│   │   │       └── dm_20240115_120000.parquet
│   │   ├── ae/
│   │   ├── vs/
│   │   └── lb/
│   └── lab-system/
│       └── ...
├── silver/
│   ├── dm/
│   │   └── year=2024/month=01/day=15/
│   │       └── dm_validated.parquet
│   ├── ae/
│   ├── vs/
│   └── lb/
├── gold/
│   ├── dim_subject/
│   ├── dim_site/
│   ├── fact_adverse_events/
│   ├── fact_vital_signs/
│   └── fact_lab_results/
└── metadata/
    ├── lineage/
    ├── quality/
    └── schemas/
```

## Related Decisions
- ADR-001: AWS-Native Approach
- ADR-003: CDISC Compliance Strategy
- ADR-004: Cost Optimization

## References
- [Databricks Medallion Architecture](https://www.databricks.com/glossary/medallion-architecture)
- [Delta Lake Best Practices](https://docs.delta.io/latest/best-practices.html)
