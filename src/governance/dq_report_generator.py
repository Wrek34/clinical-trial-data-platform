"""
Data Quality KPI Report Generator

Generates weekly/daily data quality reports with trend analysis.
These reports demonstrate "owning outcomes, not just transforms."

INTERVIEW TALKING POINTS:
"We treat data pipelines as products with SLOs. This report tracks:
- Freshness: Is data arriving on time?
- Completeness: Are we getting all expected records?
- Validity: What percentage pass quality rules?
- Quarantine rate: How much data needs manual review?

We track trends over time to catch degradation early, not after
downstream consumers complain."

WHAT THIS DEMONSTRATES:
- Operational maturity
- Product mindset for data
- Proactive quality management
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional
import random  # For demo data generation


@dataclass
class DomainMetrics:
    """Quality metrics for a single CDISC domain."""
    domain: str
    date: str
    
    # Volume metrics
    records_received: int
    records_processed: int
    records_quarantined: int
    
    # Quality metrics
    validation_pass_rate: float  # 0.0 - 1.0
    null_rate: float
    duplicate_rate: float
    
    # Freshness metrics
    expected_arrival_time: str
    actual_arrival_time: str
    freshness_slo_met: bool
    latency_minutes: int
    
    # Contract metrics
    schema_changes_detected: int
    breaking_changes_detected: int
    
    def to_dict(self) -> dict:
        return {
            "domain": self.domain,
            "date": self.date,
            "volume": {
                "received": self.records_received,
                "processed": self.records_processed,
                "quarantined": self.records_quarantined,
                "quarantine_rate": round(self.records_quarantined / max(self.records_received, 1), 4)
            },
            "quality": {
                "validation_pass_rate": self.validation_pass_rate,
                "null_rate": self.null_rate,
                "duplicate_rate": self.duplicate_rate
            },
            "freshness": {
                "expected": self.expected_arrival_time,
                "actual": self.actual_arrival_time,
                "slo_met": self.freshness_slo_met,
                "latency_minutes": self.latency_minutes
            },
            "contracts": {
                "schema_changes": self.schema_changes_detected,
                "breaking_changes": self.breaking_changes_detected
            }
        }


@dataclass 
class PipelineKPIs:
    """Overall pipeline KPIs across all domains."""
    report_date: str
    report_period: str  # "daily", "weekly"
    
    # Aggregate metrics
    total_records_processed: int
    total_records_quarantined: int
    overall_pass_rate: float
    
    # SLO compliance
    freshness_slo_compliance: float  # % of domains meeting SLO
    quality_slo_compliance: float    # % meeting quality threshold
    
    # Trend indicators
    volume_trend: str      # "increasing", "stable", "decreasing"
    quality_trend: str     # "improving", "stable", "degrading"
    
    # Alerts
    active_alerts: list = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "report_date": self.report_date,
            "report_period": self.report_period,
            "aggregates": {
                "total_processed": self.total_records_processed,
                "total_quarantined": self.total_records_quarantined,
                "overall_pass_rate": self.overall_pass_rate,
                "quarantine_rate": round(self.total_records_quarantined / max(self.total_records_processed, 1), 4)
            },
            "slo_compliance": {
                "freshness": self.freshness_slo_compliance,
                "quality": self.quality_slo_compliance
            },
            "trends": {
                "volume": self.volume_trend,
                "quality": self.quality_trend
            },
            "alerts": self.active_alerts
        }


@dataclass
class DQReport:
    """Complete Data Quality Report."""
    report_id: str
    generated_at: str
    report_period_start: str
    report_period_end: str
    environment: str
    
    pipeline_kpis: PipelineKPIs
    domain_metrics: list  # List of DomainMetrics
    
    # Historical comparison
    previous_period_comparison: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "report_id": self.report_id,
            "generated_at": self.generated_at,
            "period": {
                "start": self.report_period_start,
                "end": self.report_period_end
            },
            "environment": self.environment,
            "pipeline_kpis": self.pipeline_kpis.to_dict(),
            "domain_metrics": [d.to_dict() for d in self.domain_metrics],
            "comparison": self.previous_period_comparison
        }
    
    def save_json(self, filepath: str):
        """Save report as JSON."""
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    def generate_markdown(self) -> str:
        """Generate human-readable markdown report."""
        md = []
        md.append(f"# Data Quality Report")
        md.append(f"\n**Report ID:** {self.report_id}")
        md.append(f"**Generated:** {self.generated_at}")
        md.append(f"**Period:** {self.report_period_start} to {self.report_period_end}")
        md.append(f"**Environment:** {self.environment}")
        
        # Executive Summary
        md.append("\n## Executive Summary\n")
        kpis = self.pipeline_kpis
        
        # Status indicator
        if kpis.overall_pass_rate >= 0.98 and kpis.freshness_slo_compliance >= 0.95:
            status = "🟢 HEALTHY"
        elif kpis.overall_pass_rate >= 0.95 and kpis.freshness_slo_compliance >= 0.90:
            status = "🟡 WARNING"
        else:
            status = "🔴 CRITICAL"
        
        md.append(f"**Overall Status:** {status}\n")
        
        md.append("| KPI | Value | Target | Status |")
        md.append("|-----|-------|--------|--------|")
        md.append(f"| Records Processed | {kpis.total_records_processed:,} | - | - |")
        md.append(f"| Quarantine Rate | {kpis.total_records_quarantined / max(kpis.total_records_processed, 1) * 100:.2f}% | <5% | {'✅' if kpis.total_records_quarantined / max(kpis.total_records_processed, 1) < 0.05 else '❌'} |")
        md.append(f"| Validation Pass Rate | {kpis.overall_pass_rate * 100:.2f}% | ≥98% | {'✅' if kpis.overall_pass_rate >= 0.98 else '❌'} |")
        md.append(f"| Freshness SLO | {kpis.freshness_slo_compliance * 100:.1f}% | ≥95% | {'✅' if kpis.freshness_slo_compliance >= 0.95 else '❌'} |")
        md.append(f"| Quality SLO | {kpis.quality_slo_compliance * 100:.1f}% | ≥95% | {'✅' if kpis.quality_slo_compliance >= 0.95 else '❌'} |")
        
        # Trends
        md.append("\n## Trends\n")
        vol_emoji = {"increasing": "📈", "stable": "➡️", "decreasing": "📉"}
        qual_emoji = {"improving": "📈", "stable": "➡️", "degrading": "📉"}
        md.append(f"- **Volume Trend:** {vol_emoji.get(kpis.volume_trend, '')} {kpis.volume_trend}")
        md.append(f"- **Quality Trend:** {qual_emoji.get(kpis.quality_trend, '')} {kpis.quality_trend}")
        
        # Active Alerts
        if kpis.active_alerts:
            md.append("\n## Active Alerts\n")
            for alert in kpis.active_alerts:
                md.append(f"- ⚠️ {alert}")
        
        # Domain Breakdown
        md.append("\n## Domain Metrics\n")
        md.append("| Domain | Records | Quarantined | Pass Rate | Freshness SLO |")
        md.append("|--------|---------|-------------|-----------|---------------|")
        for dm in self.domain_metrics:
            qrate = dm.records_quarantined / max(dm.records_received, 1) * 100
            md.append(
                f"| {dm.domain} | {dm.records_received:,} | "
                f"{dm.records_quarantined} ({qrate:.1f}%) | "
                f"{dm.validation_pass_rate * 100:.1f}% | "
                f"{'✅' if dm.freshness_slo_met else '❌'} |"
            )
        
        # Contract Changes
        md.append("\n## Schema/Contract Changes\n")
        total_schema = sum(d.schema_changes_detected for d in self.domain_metrics)
        total_breaking = sum(d.breaking_changes_detected for d in self.domain_metrics)
        md.append(f"- Schema changes detected: {total_schema}")
        md.append(f"- Breaking changes detected: {total_breaking}")
        if total_breaking > 0:
            md.append(f"\n⚠️ **{total_breaking} breaking change(s) quarantined for review**")
        
        return "\n".join(md)
    
    def save_markdown(self, filepath: str):
        """Save report as markdown."""
        with open(filepath, 'w') as f:
            f.write(self.generate_markdown())


class DQReportGenerator:
    """
    Generates data quality reports from pipeline metrics.
    
    In production, this would read from:
    - CloudWatch metrics
    - S3 validation artifacts
    - Glue job run histories
    
    For demo, we generate realistic synthetic metrics.
    """
    
    def __init__(self, environment: str = "dev"):
        self.environment = environment
        self.domains = ["DM", "AE", "VS", "LB"]
        self.freshness_slo_hours = {"DM": 4, "AE": 2, "VS": 1, "LB": 1}
        self.quality_slo_threshold = 0.98
    
    def generate_domain_metrics(
        self, 
        domain: str, 
        date: str,
        base_volume: int = None
    ) -> DomainMetrics:
        """Generate realistic metrics for a domain."""
        
        # Realistic base volumes by domain
        base_volumes = {"DM": 500, "AE": 1800, "VS": 16000, "LB": 32000}
        volume = base_volume or base_volumes.get(domain, 1000)
        
        # Add some variance
        volume = int(volume * random.uniform(0.95, 1.05))
        
        # Quality metrics (realistic for clinical data)
        pass_rate = random.uniform(0.96, 0.995)
        quarantine_rate = 1 - pass_rate + random.uniform(0, 0.02)
        quarantined = int(volume * quarantine_rate)
        
        # Freshness
        slo_hours = self.freshness_slo_hours.get(domain, 4)
        latency = random.randint(
            int(slo_hours * 60 * 0.3),  # Best case: 30% of SLO
            int(slo_hours * 60 * 1.2)   # Occasional breach
        )
        slo_met = latency <= slo_hours * 60
        
        expected_time = f"{date}T08:00:00Z"
        actual_minutes = 8 * 60 + latency
        actual_hour = actual_minutes // 60
        actual_min = actual_minutes % 60
        actual_time = f"{date}T{actual_hour:02d}:{actual_min:02d}:00Z"
        
        return DomainMetrics(
            domain=domain,
            date=date,
            records_received=volume,
            records_processed=volume - quarantined,
            records_quarantined=quarantined,
            validation_pass_rate=round(pass_rate, 4),
            null_rate=round(random.uniform(0.001, 0.02), 4),
            duplicate_rate=round(random.uniform(0, 0.005), 4),
            expected_arrival_time=expected_time,
            actual_arrival_time=actual_time,
            freshness_slo_met=slo_met,
            latency_minutes=latency,
            schema_changes_detected=random.choices([0, 1], weights=[0.9, 0.1])[0],
            breaking_changes_detected=random.choices([0, 1], weights=[0.98, 0.02])[0]
        )
    
    def generate_report(
        self,
        period_start: str,
        period_end: str,
        report_type: str = "weekly"
    ) -> DQReport:
        """Generate a complete DQ report."""
        
        # Generate metrics for each domain
        domain_metrics = [
            self.generate_domain_metrics(domain, period_end)
            for domain in self.domains
        ]
        
        # Calculate aggregates
        total_processed = sum(d.records_processed for d in domain_metrics)
        total_quarantined = sum(d.records_quarantined for d in domain_metrics)
        
        # Weighted average pass rate
        total_received = sum(d.records_received for d in domain_metrics)
        overall_pass = sum(
            d.validation_pass_rate * d.records_received 
            for d in domain_metrics
        ) / total_received
        
        # SLO compliance
        freshness_compliance = sum(
            1 for d in domain_metrics if d.freshness_slo_met
        ) / len(domain_metrics)
        
        quality_compliance = sum(
            1 for d in domain_metrics 
            if d.validation_pass_rate >= self.quality_slo_threshold
        ) / len(domain_metrics)
        
        # Determine trends (in real system, compare to previous period)
        volume_trend = random.choice(["increasing", "stable", "stable", "stable"])
        quality_trend = random.choice(["improving", "stable", "stable", "stable"])
        
        # Generate alerts
        alerts = []
        if freshness_compliance < 0.95:
            slow_domains = [d.domain for d in domain_metrics if not d.freshness_slo_met]
            alerts.append(f"Freshness SLO breach in: {', '.join(slow_domains)}")
        if any(d.breaking_changes_detected > 0 for d in domain_metrics):
            alerts.append("Breaking schema changes detected - review quarantine")
        if total_quarantined / total_received > 0.05:
            alerts.append(f"High quarantine rate: {total_quarantined/total_received*100:.1f}%")
        
        pipeline_kpis = PipelineKPIs(
            report_date=datetime.now().isoformat(),
            report_period=report_type,
            total_records_processed=total_processed,
            total_records_quarantined=total_quarantined,
            overall_pass_rate=round(overall_pass, 4),
            freshness_slo_compliance=freshness_compliance,
            quality_slo_compliance=quality_compliance,
            volume_trend=volume_trend,
            quality_trend=quality_trend,
            active_alerts=alerts
        )
        
        return DQReport(
            report_id=f"DQ-{period_end.replace('-', '')}-{random.randint(1000, 9999)}",
            generated_at=datetime.now().isoformat(),
            report_period_start=period_start,
            report_period_end=period_end,
            environment=self.environment,
            pipeline_kpis=pipeline_kpis,
            domain_metrics=domain_metrics,
            previous_period_comparison={
                "volume_change_pct": round(random.uniform(-5, 10), 1),
                "quality_change_pct": round(random.uniform(-0.5, 1), 2),
                "quarantine_change_pct": round(random.uniform(-20, 20), 1)
            }
        )


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Data Quality Report Generator Demo")
    print("=" * 60)
    
    generator = DQReportGenerator(environment="dev")
    
    # Generate weekly report
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    
    report = generator.generate_report(start_date, end_date, "weekly")
    
    # Save outputs
    report.save_json("dq_report.json")
    report.save_markdown("dq_report.md")
    
    print(f"\nReport ID: {report.report_id}")
    print(f"Period: {report.report_period_start} to {report.report_period_end}")
    print(f"\nSaved: dq_report.json, dq_report.md")
    
    # Print markdown preview
    print("\n" + "=" * 60)
    print("REPORT PREVIEW")
    print("=" * 60)
    print(report.generate_markdown())
