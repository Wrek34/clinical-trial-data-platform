"""
Clinical Trial Synthetic Data Generator

Generates realistic synthetic clinical trial data following CDISC SDTM standards.
This module creates interconnected datasets for Demographics (DM), Adverse Events (AE),
Vital Signs (VS), and Laboratory Results (LB) domains.

CDISC SDTM Reference: https://www.cdisc.org/standards/foundational/sdtm

Author: [Your Name]
Created: 2024
"""

import hashlib
import json
import os
import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import click
import pandas as pd
from faker import Faker
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

# Initialize
fake = Faker()
Faker.seed(42)  # Reproducibility
random.seed(42)
console = Console()


# =============================================================================
# CONFIGURATION
# =============================================================================

@dataclass
class StudyConfig:
    """Configuration for a synthetic clinical trial study."""
    
    study_id: str = "CLIN-2024-001"
    study_name: str = "Phase III Clinical Trial - Synthetic"
    sponsor: str = "Synthetic Pharma Inc."
    
    # Study timeline
    study_start_date: datetime = field(
        default_factory=lambda: datetime(2023, 1, 15)
    )
    study_end_date: datetime = field(
        default_factory=lambda: datetime(2024, 6, 30)
    )
    
    # Sites
    site_ids: list = field(default_factory=lambda: [
        "SITE001", "SITE002", "SITE003", "SITE004", "SITE005",
        "SITE006", "SITE007", "SITE008", "SITE009", "SITE010"
    ])
    site_countries: list = field(default_factory=lambda: [
        "USA", "USA", "USA", "CAN", "CAN", "GBR", "GBR", "DEU", "FRA", "JPN"
    ])
    
    # Treatment arms
    treatment_arms: list = field(default_factory=lambda: [
        "PLACEBO",
        "TREATMENT_LOW",
        "TREATMENT_HIGH"
    ])
    arm_allocation: list = field(default_factory=lambda: [0.33, 0.33, 0.34])
    
    # Demographics constraints
    min_age: int = 18
    max_age: int = 75
    
    # Data generation parameters
    visits_per_subject: tuple = (4, 12)  # min, max visits
    ae_probability: float = 0.3  # 30% chance of AE per visit
    lab_tests_per_visit: int = 8
    vital_signs_per_visit: int = 4


# CDISC-aligned controlled terminology
CDISC_SEX = ["M", "F"]
CDISC_SEX_WEIGHTS = [0.52, 0.48]

CDISC_RACE = [
    "WHITE",
    "BLACK OR AFRICAN AMERICAN", 
    "ASIAN",
    "AMERICAN INDIAN OR ALASKA NATIVE",
    "NATIVE HAWAIIAN OR OTHER PACIFIC ISLANDER",
    "MULTIPLE",
    "OTHER",
    "UNKNOWN"
]
CDISC_RACE_WEIGHTS = [0.60, 0.15, 0.12, 0.03, 0.02, 0.04, 0.03, 0.01]

CDISC_ETHNICITY = [
    "HISPANIC OR LATINO",
    "NOT HISPANIC OR LATINO",
    "UNKNOWN"
]
CDISC_ETHNICITY_WEIGHTS = [0.18, 0.80, 0.02]

# Adverse Event controlled terminology
AE_TERMS = [
    ("Headache", "NERVOUS SYSTEM DISORDERS", "MILD"),
    ("Nausea", "GASTROINTESTINAL DISORDERS", "MILD"),
    ("Fatigue", "GENERAL DISORDERS", "MILD"),
    ("Dizziness", "NERVOUS SYSTEM DISORDERS", "MILD"),
    ("Insomnia", "PSYCHIATRIC DISORDERS", "MILD"),
    ("Diarrhea", "GASTROINTESTINAL DISORDERS", "MODERATE"),
    ("Rash", "SKIN AND SUBCUTANEOUS TISSUE DISORDERS", "MILD"),
    ("Back pain", "MUSCULOSKELETAL DISORDERS", "MODERATE"),
    ("Arthralgia", "MUSCULOSKELETAL DISORDERS", "MODERATE"),
    ("Upper respiratory infection", "INFECTIONS AND INFESTATIONS", "MODERATE"),
    ("Hypertension", "VASCULAR DISORDERS", "MODERATE"),
    ("Peripheral edema", "GENERAL DISORDERS", "MILD"),
    ("Constipation", "GASTROINTESTINAL DISORDERS", "MILD"),
    ("Anxiety", "PSYCHIATRIC DISORDERS", "MODERATE"),
    ("Depression", "PSYCHIATRIC DISORDERS", "MODERATE"),
]

AE_SEVERITY = ["MILD", "MODERATE", "SEVERE"]
AE_SEVERITY_WEIGHTS = [0.60, 0.32, 0.08]

AE_RELATIONSHIP = [
    "NOT RELATED",
    "UNLIKELY RELATED", 
    "POSSIBLY RELATED",
    "PROBABLY RELATED",
    "DEFINITELY RELATED"
]
AE_RELATIONSHIP_WEIGHTS = [0.30, 0.25, 0.25, 0.15, 0.05]

AE_OUTCOME = [
    "RECOVERED/RESOLVED",
    "RECOVERING/RESOLVING",
    "NOT RECOVERED/NOT RESOLVED",
    "RECOVERED/RESOLVED WITH SEQUELAE",
    "FATAL",
    "UNKNOWN"
]
AE_OUTCOME_WEIGHTS = [0.65, 0.15, 0.10, 0.05, 0.01, 0.04]

# Vital Signs configuration
VITAL_SIGNS = {
    "HR": {
        "name": "Heart Rate",
        "unit": "beats/min",
        "normal_range": (60, 100),
        "mean": 72,
        "std": 12
    },
    "SYSBP": {
        "name": "Systolic Blood Pressure",
        "unit": "mmHg",
        "normal_range": (90, 140),
        "mean": 120,
        "std": 15
    },
    "DIABP": {
        "name": "Diastolic Blood Pressure", 
        "unit": "mmHg",
        "normal_range": (60, 90),
        "mean": 78,
        "std": 10
    },
    "TEMP": {
        "name": "Temperature",
        "unit": "C",
        "normal_range": (36.1, 37.2),
        "mean": 36.6,
        "std": 0.4
    },
    "RESP": {
        "name": "Respiratory Rate",
        "unit": "breaths/min",
        "normal_range": (12, 20),
        "mean": 16,
        "std": 3
    },
    "WEIGHT": {
        "name": "Weight",
        "unit": "kg",
        "normal_range": (50, 120),
        "mean": 75,
        "std": 15
    },
    "HEIGHT": {
        "name": "Height",
        "unit": "cm",
        "normal_range": (150, 195),
        "mean": 170,
        "std": 10
    },
}

# Laboratory Tests configuration
LAB_TESTS = {
    "ALT": {
        "name": "Alanine Aminotransferase",
        "unit": "U/L",
        "normal_range": (7, 56),
        "mean": 25,
        "std": 12
    },
    "AST": {
        "name": "Aspartate Aminotransferase",
        "unit": "U/L", 
        "normal_range": (10, 40),
        "mean": 22,
        "std": 10
    },
    "CREAT": {
        "name": "Creatinine",
        "unit": "mg/dL",
        "normal_range": (0.7, 1.3),
        "mean": 1.0,
        "std": 0.2
    },
    "GLUC": {
        "name": "Glucose",
        "unit": "mg/dL",
        "normal_range": (70, 100),
        "mean": 90,
        "std": 15
    },
    "HGB": {
        "name": "Hemoglobin",
        "unit": "g/dL",
        "normal_range": (12.0, 17.5),
        "mean": 14.5,
        "std": 1.5
    },
    "WBC": {
        "name": "White Blood Cell Count",
        "unit": "10^9/L",
        "normal_range": (4.5, 11.0),
        "mean": 7.0,
        "std": 2.0
    },
    "PLT": {
        "name": "Platelet Count",
        "unit": "10^9/L",
        "normal_range": (150, 400),
        "mean": 250,
        "std": 60
    },
    "SODIUM": {
        "name": "Sodium",
        "unit": "mmol/L",
        "normal_range": (136, 145),
        "mean": 140,
        "std": 3
    },
    "POTASSIUM": {
        "name": "Potassium",
        "unit": "mmol/L",
        "normal_range": (3.5, 5.0),
        "mean": 4.2,
        "std": 0.4
    },
    "CHOL": {
        "name": "Total Cholesterol",
        "unit": "mg/dL",
        "normal_range": (0, 200),
        "mean": 190,
        "std": 35
    },
}


# =============================================================================
# DATA GENERATORS
# =============================================================================

class SubjectGenerator:
    """Generates subject demographics following CDISC DM domain standards."""
    
    def __init__(self, config: StudyConfig):
        self.config = config
        self.subjects = []
        
    def generate_usubjid(self, site_id: str, subject_num: int) -> str:
        """Generate unique subject identifier."""
        return f"{self.config.study_id}-{site_id}-{subject_num:04d}"
    
    def generate_subject(self, site_id: str, site_country: str, subject_num: int) -> dict:
        """Generate a single subject's demographics."""
        
        usubjid = self.generate_usubjid(site_id, subject_num)
        
        # Random enrollment date within study period
        days_range = (self.config.study_end_date - self.config.study_start_date).days
        enrollment_offset = random.randint(0, int(days_range * 0.7))  # Enroll in first 70%
        rfstdtc = self.config.study_start_date + timedelta(days=enrollment_offset)
        
        # Demographics
        sex = random.choices(CDISC_SEX, weights=CDISC_SEX_WEIGHTS)[0]
        age = random.randint(self.config.min_age, self.config.max_age)
        
        # Age-adjusted for realism
        if sex == "F":
            age = min(age, 70)  # Slightly younger female population
            
        return {
            # Identifiers
            "STUDYID": self.config.study_id,
            "DOMAIN": "DM",
            "USUBJID": usubjid,
            "SUBJID": f"{subject_num:04d}",
            "SITEID": site_id,
            
            # Demographics
            "AGE": age,
            "AGEU": "YEARS",
            "SEX": sex,
            "RACE": random.choices(CDISC_RACE, weights=CDISC_RACE_WEIGHTS)[0],
            "ETHNIC": random.choices(CDISC_ETHNICITY, weights=CDISC_ETHNICITY_WEIGHTS)[0],
            "COUNTRY": site_country,
            
            # Treatment
            "ARM": random.choices(
                self.config.treatment_arms, 
                weights=self.config.arm_allocation
            )[0],
            "ARMCD": None,  # Will be set based on ARM
            "ACTARM": None,  # Actual treatment - same as ARM for this simulation
            
            # Dates
            "RFSTDTC": rfstdtc.strftime("%Y-%m-%d"),
            "RFENDTC": None,  # End of treatment - will be calculated
            "DTHDTC": None,  # Death date if applicable
            "DTHFL": "N",  # Death flag
            
            # Metadata
            "DMDY": 1,  # Study day at DM collection
        }
    
    def generate_all(self, n_subjects: int) -> pd.DataFrame:
        """Generate demographics for all subjects."""
        
        subjects = []
        subject_num = 1
        
        # Distribute subjects across sites
        subjects_per_site = n_subjects // len(self.config.site_ids)
        remainder = n_subjects % len(self.config.site_ids)
        
        for i, (site_id, country) in enumerate(
            zip(self.config.site_ids, self.config.site_countries)
        ):
            # Add extra subjects to first few sites to handle remainder
            site_subjects = subjects_per_site + (1 if i < remainder else 0)
            
            for _ in range(site_subjects):
                subject = self.generate_subject(site_id, country, subject_num)
                
                # Set ARM code
                arm_codes = {"PLACEBO": "PBO", "TREATMENT_LOW": "TRT_L", "TREATMENT_HIGH": "TRT_H"}
                subject["ARMCD"] = arm_codes.get(subject["ARM"], subject["ARM"][:5])
                subject["ACTARM"] = subject["ARM"]
                
                subjects.append(subject)
                subject_num += 1
        
        self.subjects = subjects
        return pd.DataFrame(subjects)


class VisitGenerator:
    """Generates visit schedule for subjects."""
    
    def __init__(self, config: StudyConfig, dm_df: pd.DataFrame):
        self.config = config
        self.dm_df = dm_df
        
    def generate_visits(self, usubjid: str) -> list[dict]:
        """Generate visits for a single subject."""
        
        subject = self.dm_df[self.dm_df["USUBJID"] == usubjid].iloc[0]
        start_date = datetime.strptime(subject["RFSTDTC"], "%Y-%m-%d")
        
        n_visits = random.randint(*self.config.visits_per_subject)
        visits = []
        
        visit_names = [
            "SCREENING",
            "BASELINE",
            "WEEK 2",
            "WEEK 4", 
            "WEEK 8",
            "WEEK 12",
            "WEEK 16",
            "WEEK 20",
            "WEEK 24",
            "END OF TREATMENT",
            "FOLLOW-UP 1",
            "FOLLOW-UP 2"
        ]
        
        current_date = start_date
        
        for i in range(min(n_visits, len(visit_names))):
            visit = {
                "USUBJID": usubjid,
                "VISITNUM": i + 1,
                "VISIT": visit_names[i],
                "VISITDY": (current_date - start_date).days + 1,
                "SVSTDTC": current_date.strftime("%Y-%m-%d"),
            }
            visits.append(visit)
            
            # Next visit timing
            if i == 0:  # Screening to baseline
                current_date += timedelta(days=random.randint(7, 14))
            else:  # Regular intervals with some variance
                current_date += timedelta(days=random.randint(12, 16))
        
        return visits


class AdverseEventGenerator:
    """Generates adverse events following CDISC AE domain standards."""
    
    def __init__(self, config: StudyConfig, dm_df: pd.DataFrame):
        self.config = config
        self.dm_df = dm_df
        
    def generate_ae(self, usubjid: str, visit_date: datetime, aeseq: int) -> Optional[dict]:
        """Generate a single adverse event."""
        
        subject = self.dm_df[self.dm_df["USUBJID"] == usubjid].iloc[0]
        arm = subject["ARM"]
        
        # Adjust AE probability based on treatment arm
        prob_modifier = {"PLACEBO": 0.7, "TREATMENT_LOW": 1.0, "TREATMENT_HIGH": 1.3}
        adjusted_prob = self.config.ae_probability * prob_modifier.get(arm, 1.0)
        
        if random.random() > adjusted_prob:
            return None
            
        # Select AE term
        ae_term, ae_soc, default_severity = random.choice(AE_TERMS)
        
        # Severity - bias toward default but allow variation
        severity_weights = AE_SEVERITY_WEIGHTS.copy()
        default_idx = AE_SEVERITY.index(default_severity)
        severity_weights[default_idx] *= 1.5  # Boost default
        total = sum(severity_weights)
        severity_weights = [w/total for w in severity_weights]
        
        severity = random.choices(AE_SEVERITY, weights=severity_weights)[0]
        
        # Dates
        ae_start = visit_date + timedelta(days=random.randint(0, 7))
        ae_duration = random.randint(1, 30)
        ae_end = ae_start + timedelta(days=ae_duration)
        
        # Outcome
        outcome = random.choices(AE_OUTCOME, weights=AE_OUTCOME_WEIGHTS)[0]
        
        # Serious AE flag
        aeser = "Y" if severity == "SEVERE" or outcome == "FATAL" else "N"
        
        return {
            "STUDYID": self.config.study_id,
            "DOMAIN": "AE",
            "USUBJID": usubjid,
            "AESEQ": aeseq,
            "AETERM": ae_term,
            "AELLT": ae_term.upper(),  # Lowest level term
            "AEDECOD": ae_term,  # Preferred term
            "AEBODSYS": ae_soc,
            "AESEV": severity,
            "AESER": aeser,
            "AEREL": random.choices(AE_RELATIONSHIP, weights=AE_RELATIONSHIP_WEIGHTS)[0],
            "AEOUT": outcome,
            "AESTDTC": ae_start.strftime("%Y-%m-%d"),
            "AEENDTC": ae_end.strftime("%Y-%m-%d") if outcome in ["RECOVERED/RESOLVED", "RECOVERED/RESOLVED WITH SEQUELAE"] else None,
            "AESTDY": (ae_start - datetime.strptime(subject["RFSTDTC"], "%Y-%m-%d")).days + 1,
            "AEENDY": (ae_end - datetime.strptime(subject["RFSTDTC"], "%Y-%m-%d")).days + 1 if outcome in ["RECOVERED/RESOLVED", "RECOVERED/RESOLVED WITH SEQUELAE"] else None,
            "AEACN": "DOSE NOT CHANGED" if severity == "MILD" else random.choice(["DOSE NOT CHANGED", "DOSE REDUCED", "DRUG INTERRUPTED", "DRUG WITHDRAWN"]),
        }
    
    def generate_all(self, visits: list[dict]) -> pd.DataFrame:
        """Generate all adverse events across all visits."""
        
        aes = []
        ae_counts = {}  # Track AESEQ per subject
        
        for visit in visits:
            usubjid = visit["USUBJID"]
            if usubjid not in ae_counts:
                ae_counts[usubjid] = 0
                
            visit_date = datetime.strptime(visit["SVSTDTC"], "%Y-%m-%d")
            
            # Can have multiple AEs per visit
            n_potential_aes = random.randint(0, 3)
            for _ in range(n_potential_aes):
                ae_counts[usubjid] += 1
                ae = self.generate_ae(usubjid, visit_date, ae_counts[usubjid])
                if ae:
                    aes.append(ae)
        
        return pd.DataFrame(aes) if aes else pd.DataFrame()


class VitalSignsGenerator:
    """Generates vital signs following CDISC VS domain standards."""
    
    def __init__(self, config: StudyConfig, dm_df: pd.DataFrame):
        self.config = config
        self.dm_df = dm_df
        self.subject_baselines = {}  # Store baseline values per subject
        
    def get_baseline(self, usubjid: str, test_code: str) -> float:
        """Get or create baseline value for a subject."""
        
        key = (usubjid, test_code)
        if key not in self.subject_baselines:
            test_config = VITAL_SIGNS[test_code]
            # Generate baseline with some individual variation
            baseline = random.gauss(test_config["mean"], test_config["std"])
            self.subject_baselines[key] = baseline
        return self.subject_baselines[key]
    
    def generate_vs(
        self, 
        usubjid: str, 
        visit: dict, 
        vsseq: int, 
        test_code: str
    ) -> dict:
        """Generate a single vital sign measurement."""
        
        subject = self.dm_df[self.dm_df["USUBJID"] == usubjid].iloc[0]
        test_config = VITAL_SIGNS[test_code]
        
        # Get baseline and add visit-to-visit variation
        baseline = self.get_baseline(usubjid, test_code)
        variation = random.gauss(0, test_config["std"] * 0.3)  # Smaller variation than baseline
        value = baseline + variation
        
        # Treatment effect simulation (subtle)
        arm = subject["ARM"]
        if arm == "TREATMENT_HIGH" and test_code in ["SYSBP", "DIABP"]:
            value -= random.uniform(2, 8)  # Blood pressure reduction
        
        # Round appropriately
        if test_code == "TEMP":
            value = round(value, 1)
        elif test_code in ["WEIGHT", "HEIGHT"]:
            value = round(value, 1)
        else:
            value = round(value)
        
        # Determine if within normal range
        low, high = test_config["normal_range"]
        if value < low:
            nrind = "LOW"
        elif value > high:
            nrind = "HIGH"
        else:
            nrind = "NORMAL"
        
        visit_date = datetime.strptime(visit["SVSTDTC"], "%Y-%m-%d")
        ref_date = datetime.strptime(subject["RFSTDTC"], "%Y-%m-%d")
        
        return {
            "STUDYID": self.config.study_id,
            "DOMAIN": "VS",
            "USUBJID": usubjid,
            "VSSEQ": vsseq,
            "VSTESTCD": test_code,
            "VSTEST": test_config["name"],
            "VSORRES": str(value),
            "VSORRESU": test_config["unit"],
            "VSSTRESC": str(value),
            "VSSTRESN": value,
            "VSSTRESU": test_config["unit"],
            "VSNRIND": nrind,
            "VSORNRLO": test_config["normal_range"][0],
            "VSORNRHI": test_config["normal_range"][1],
            "VISITNUM": visit["VISITNUM"],
            "VISIT": visit["VISIT"],
            "VSDTC": visit["SVSTDTC"],
            "VSDY": (visit_date - ref_date).days + 1,
        }
    
    def generate_all(self, visits: list[dict]) -> pd.DataFrame:
        """Generate all vital signs across all visits."""
        
        vs_records = []
        vs_counts = {}  # Track VSSEQ per subject
        
        for visit in visits:
            usubjid = visit["USUBJID"]
            if usubjid not in vs_counts:
                vs_counts[usubjid] = 0
            
            # Generate all vital signs for this visit
            test_codes = list(VITAL_SIGNS.keys())
            for test_code in test_codes[:self.config.vital_signs_per_visit]:
                vs_counts[usubjid] += 1
                vs = self.generate_vs(usubjid, visit, vs_counts[usubjid], test_code)
                vs_records.append(vs)
        
        return pd.DataFrame(vs_records)


class LabResultsGenerator:
    """Generates laboratory results following CDISC LB domain standards."""
    
    def __init__(self, config: StudyConfig, dm_df: pd.DataFrame):
        self.config = config
        self.dm_df = dm_df
        self.subject_baselines = {}
        
    def get_baseline(self, usubjid: str, test_code: str) -> float:
        """Get or create baseline value for a subject."""
        
        key = (usubjid, test_code)
        if key not in self.subject_baselines:
            test_config = LAB_TESTS[test_code]
            baseline = random.gauss(test_config["mean"], test_config["std"])
            # Ensure positive values
            baseline = max(baseline, test_config["normal_range"][0] * 0.5)
            self.subject_baselines[key] = baseline
        return self.subject_baselines[key]
    
    def generate_lb(
        self,
        usubjid: str,
        visit: dict,
        lbseq: int,
        test_code: str
    ) -> dict:
        """Generate a single lab result."""
        
        subject = self.dm_df[self.dm_df["USUBJID"] == usubjid].iloc[0]
        test_config = LAB_TESTS[test_code]
        
        baseline = self.get_baseline(usubjid, test_code)
        variation = random.gauss(0, test_config["std"] * 0.2)
        value = baseline + variation
        
        # Ensure positive
        value = max(value, 0.01)
        
        # Treatment effects on liver enzymes
        arm = subject["ARM"]
        if arm == "TREATMENT_HIGH" and test_code in ["ALT", "AST"]:
            # Slight elevation possible
            if random.random() < 0.1:
                value *= random.uniform(1.2, 1.8)
        
        # Round based on test
        if test_code in ["CREAT"]:
            value = round(value, 2)
        elif test_code in ["HGB"]:
            value = round(value, 1)
        else:
            value = round(value, 1)
        
        # Normal range indicator
        low, high = test_config["normal_range"]
        if value < low:
            nrind = "LOW"
        elif value > high:
            nrind = "HIGH"
        else:
            nrind = "NORMAL"
        
        visit_date = datetime.strptime(visit["SVSTDTC"], "%Y-%m-%d")
        ref_date = datetime.strptime(subject["RFSTDTC"], "%Y-%m-%d")
        
        return {
            "STUDYID": self.config.study_id,
            "DOMAIN": "LB",
            "USUBJID": usubjid,
            "LBSEQ": lbseq,
            "LBTESTCD": test_code,
            "LBTEST": test_config["name"],
            "LBORRES": str(value),
            "LBORRESU": test_config["unit"],
            "LBSTRESC": str(value),
            "LBSTRESN": value,
            "LBSTRESU": test_config["unit"],
            "LBNRIND": nrind,
            "LBORNRLO": test_config["normal_range"][0],
            "LBORNRHI": test_config["normal_range"][1],
            "VISITNUM": visit["VISITNUM"],
            "VISIT": visit["VISIT"],
            "LBDTC": visit["SVSTDTC"],
            "LBDY": (visit_date - ref_date).days + 1,
            "LBSPEC": "BLOOD",
            "LBMETHOD": "AUTOMATED",
        }
    
    def generate_all(self, visits: list[dict]) -> pd.DataFrame:
        """Generate all lab results across all visits."""
        
        lb_records = []
        lb_counts = {}
        
        for visit in visits:
            usubjid = visit["USUBJID"]
            if usubjid not in lb_counts:
                lb_counts[usubjid] = 0
            
            # Generate lab tests for this visit
            test_codes = list(LAB_TESTS.keys())
            for test_code in test_codes[:self.config.lab_tests_per_visit]:
                lb_counts[usubjid] += 1
                lb = self.generate_lb(usubjid, visit, lb_counts[usubjid], test_code)
                lb_records.append(lb)
        
        return pd.DataFrame(lb_records)


# =============================================================================
# MAIN ORCHESTRATOR
# =============================================================================

class ClinicalTrialDataGenerator:
    """Main orchestrator for generating complete clinical trial datasets."""
    
    def __init__(self, config: Optional[StudyConfig] = None):
        self.config = config or StudyConfig()
        self.dm_df = None
        self.ae_df = None
        self.vs_df = None
        self.lb_df = None
        self.visits = None
        
    def generate(self, n_subjects: int) -> dict[str, pd.DataFrame]:
        """Generate all clinical trial data."""
        
        console.print(f"\n[bold blue]Clinical Trial Data Generator[/bold blue]")
        console.print(f"Study: {self.config.study_id}")
        console.print(f"Subjects: {n_subjects}")
        console.print(f"Sites: {len(self.config.site_ids)}")
        console.print()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            # Generate Demographics
            task = progress.add_task("Generating demographics...", total=None)
            subject_gen = SubjectGenerator(self.config)
            self.dm_df = subject_gen.generate_all(n_subjects)
            progress.update(task, completed=True)
            
            # Generate Visits
            task = progress.add_task("Generating visit schedules...", total=None)
            visit_gen = VisitGenerator(self.config, self.dm_df)
            self.visits = []
            for usubjid in self.dm_df["USUBJID"]:
                self.visits.extend(visit_gen.generate_visits(usubjid))
            progress.update(task, completed=True)
            
            # Generate Adverse Events
            task = progress.add_task("Generating adverse events...", total=None)
            ae_gen = AdverseEventGenerator(self.config, self.dm_df)
            self.ae_df = ae_gen.generate_all(self.visits)
            progress.update(task, completed=True)
            
            # Generate Vital Signs
            task = progress.add_task("Generating vital signs...", total=None)
            vs_gen = VitalSignsGenerator(self.config, self.dm_df)
            self.vs_df = vs_gen.generate_all(self.visits)
            progress.update(task, completed=True)
            
            # Generate Lab Results
            task = progress.add_task("Generating lab results...", total=None)
            lb_gen = LabResultsGenerator(self.config, self.dm_df)
            self.lb_df = lb_gen.generate_all(self.visits)
            progress.update(task, completed=True)
        
        return {
            "dm": self.dm_df,
            "ae": self.ae_df,
            "vs": self.vs_df,
            "lb": self.lb_df,
        }
    
    def save(self, output_dir: str, formats: list[str] = None):
        """Save generated data to files."""
        
        formats = formats or ["csv", "parquet"]
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        datasets = {
            "dm": self.dm_df,
            "ae": self.ae_df,
            "vs": self.vs_df,
            "lb": self.lb_df,
        }
        
        for name, df in datasets.items():
            if df is None or df.empty:
                continue
                
            for fmt in formats:
                if fmt == "csv":
                    filepath = output_path / f"{name}.csv"
                    df.to_csv(filepath, index=False)
                elif fmt == "parquet":
                    filepath = output_path / f"{name}.parquet"
                    df.to_parquet(filepath, index=False)
                elif fmt == "json":
                    filepath = output_path / f"{name}.json"
                    df.to_json(filepath, orient="records", indent=2)
        
        # Save metadata
        metadata = {
            "study_id": self.config.study_id,
            "generation_timestamp": datetime.now().isoformat(),
            "n_subjects": len(self.dm_df),
            "n_adverse_events": len(self.ae_df) if self.ae_df is not None else 0,
            "n_vital_signs": len(self.vs_df) if self.vs_df is not None else 0,
            "n_lab_results": len(self.lb_df) if self.lb_df is not None else 0,
            "sites": self.config.site_ids,
            "treatment_arms": self.config.treatment_arms,
        }
        
        with open(output_path / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)
        
        console.print(f"\n[green]✓ Data saved to {output_path}[/green]")
    
    def print_summary(self):
        """Print summary statistics."""
        
        table = Table(title="Generated Data Summary")
        table.add_column("Domain", style="cyan")
        table.add_column("Records", style="green")
        table.add_column("Description", style="white")
        
        table.add_row("DM", str(len(self.dm_df)), "Subject Demographics")
        table.add_row("AE", str(len(self.ae_df) if self.ae_df is not None and not self.ae_df.empty else 0), "Adverse Events")
        table.add_row("VS", str(len(self.vs_df) if self.vs_df is not None else 0), "Vital Signs")
        table.add_row("LB", str(len(self.lb_df) if self.lb_df is not None else 0), "Lab Results")
        
        console.print(table)
        
        # Treatment arm distribution
        arm_dist = self.dm_df["ARM"].value_counts()
        console.print("\n[bold]Treatment Arm Distribution:[/bold]")
        for arm, count in arm_dist.items():
            console.print(f"  {arm}: {count} ({count/len(self.dm_df)*100:.1f}%)")


# =============================================================================
# CLI
# =============================================================================

@click.command()
@click.option(
    "--subjects", "-n",
    default=100,
    help="Number of subjects to generate"
)
@click.option(
    "--output", "-o",
    default="data/synthetic/output",
    help="Output directory"
)
@click.option(
    "--format", "-f",
    multiple=True,
    default=["csv", "parquet"],
    help="Output formats (csv, parquet, json)"
)
@click.option(
    "--seed", "-s",
    default=42,
    help="Random seed for reproducibility"
)
def main(subjects: int, output: str, format: tuple, seed: int):
    """Generate synthetic clinical trial data."""
    
    # Set seeds
    random.seed(seed)
    Faker.seed(seed)
    
    # Generate
    generator = ClinicalTrialDataGenerator()
    generator.generate(subjects)
    generator.print_summary()
    generator.save(output, list(format))


if __name__ == "__main__":
    main()
