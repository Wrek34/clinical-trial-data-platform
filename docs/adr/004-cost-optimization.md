# ADR-004: Cost Optimization Strategy

## Status
Accepted

## Date
2024-01-16

## Context

Clinical trial data platforms can become expensive. We need to balance production reliability, development flexibility, and budget constraints.

## Decision

We will implement a **multi-layered cost optimization strategy**:

### 1. Serverless-First Compute

| Workload | Service | Cost Model |
|----------|---------|------------|
| Ingestion | Lambda | Pay per invocation |
| ETL | Glue | Pay per DPU-hour |
| Warehouse | Redshift Serverless | Pay per RPU-hour |

**No always-on compute resources in development.**

### 2. Environment-Specific Configurations

- **Dev**: Minimum resources, aggressive auto-pause (5 min), 30-day data retention
- **Prod**: Scaled resources, moderate auto-pause (30 min), 7-year retention

### 3. S3 Lifecycle Policies

- Bronze: Standard → Standard-IA (90 days) → Glacier (365 days)
- Silver: Standard → Standard-IA (180 days) → Glacier (730 days)  
- Gold: Keep in Standard (active queries)
- Temp: Delete after 7 days

### 4. Teardown Scripts

Development environments can be torn down when not in use, preserving only S3 data.

### 5. Cost Monitoring

CloudWatch billing alarms at $50/month (dev) and $500/month (prod).

## Estimated Costs

| Environment | Active | Idle |
|-------------|--------|------|
| Development | ~$12/month | ~$0.25/month |
| Production | ~$200-500/month | N/A |

## Consequences

### Positive
- Minimal cost during development
- No idle resource charges
- Clear budget boundaries
- Automated cost controls

### Negative
- Cold start latency after pause
- Complexity in environment management
- Must remember to teardown

### Mitigations
- Document teardown procedures
- Automate with scheduled Lambda
- Use Terraform workspaces for environment isolation

## References
- [AWS Pricing Calculator](https://calculator.aws/)
- [Redshift Serverless Pricing](https://aws.amazon.com/redshift/pricing/)
