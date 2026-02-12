"""
Bronze to Silver ETL Job
Transforms raw clinical trial data to validated, CDISC-compliant format.

This script runs on AWS Glue and processes data from the Bronze layer,
applies validation and standardization, and writes to the Silver layer.
"""

import sys
from datetime import datetime

from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from pyspark.sql import functions as F
from pyspark.sql.types import *

# Initialize Glue context
args = getResolvedOptions(sys.argv, ['JOB_NAME', 'DATA_BUCKET', 'ENVIRONMENT'])
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

# Configuration
DATA_BUCKET = args['DATA_BUCKET']
ENVIRONMENT = args['ENVIRONMENT']
BRONZE_PATH = f"s3://{DATA_BUCKET}/bronze/"
SILVER_PATH = f"s3://{DATA_BUCKET}/silver/"

def process_demographics():
    """Process DM (Demographics) domain."""
    print("Processing Demographics (DM)...")
    
    # Read from Bronze
    dm_path = f"{BRONZE_PATH}synthetic/dm/"
    
    try:
        df = spark.read.parquet(dm_path)
    except:
        df = spark.read.option("header", "true").csv(dm_path)
    
    # Standardization and validation
    dm_clean = df.select(
        F.col("STUDYID"),
        F.lit("DM").alias("DOMAIN"),
        F.col("USUBJID"),
        F.col("SUBJID"),
        F.col("SITEID"),
        F.col("AGE").cast("int"),
        F.col("AGEU"),
        F.upper(F.col("SEX")).alias("SEX"),
        F.upper(F.col("RACE")).alias("RACE"),
        F.col("ETHNIC"),
        F.col("COUNTRY"),
        F.col("ARM"),
        F.col("ARMCD"),
        F.col("RFSTDTC"),
        F.col("RFENDTC")
    ).filter(
        # Basic validation
        F.col("USUBJID").isNotNull() &
        F.col("AGE").between(0, 120) &
        F.col("SEX").isin("M", "F", "U")
    ).withColumn(
        "PROCESSING_TS", F.current_timestamp()
    ).withColumn(
        "PROCESSING_DATE", F.current_date()
    )
    
    # Write to Silver
    output_path = f"{SILVER_PATH}dm/"
    dm_clean.write.mode("overwrite").partitionBy("PROCESSING_DATE").parquet(output_path)
    
    print(f"DM: Processed {dm_clean.count()} records")
    return dm_clean.count()

def process_adverse_events():
    """Process AE (Adverse Events) domain."""
    print("Processing Adverse Events (AE)...")
    
    ae_path = f"{BRONZE_PATH}synthetic/dm/"  # AE data location
    
    try:
        # Try to read AE if exists
        df = spark.read.parquet(ae_path.replace("/dm/", "/ae/"))
        
        ae_clean = df.select(
            F.col("STUDYID"),
            F.lit("AE").alias("DOMAIN"),
            F.col("USUBJID"),
            F.col("AESEQ").cast("int"),
            F.col("AETERM"),
            F.col("AEDECOD"),
            F.col("AEBODSYS"),
            F.upper(F.col("AESEV")).alias("AESEV"),
            F.upper(F.col("AESER")).alias("AESER"),
            F.col("AEREL"),
            F.col("AEOUT"),
            F.col("AESTDTC"),
            F.col("AEENDTC")
        ).filter(
            F.col("USUBJID").isNotNull() &
            F.col("AETERM").isNotNull()
        ).withColumn(
            "PROCESSING_TS", F.current_timestamp()
        ).withColumn(
            "PROCESSING_DATE", F.current_date()
        )
        
        output_path = f"{SILVER_PATH}ae/"
        ae_clean.write.mode("overwrite").partitionBy("PROCESSING_DATE").parquet(output_path)
        
        print(f"AE: Processed {ae_clean.count()} records")
        return ae_clean.count()
    except Exception as e:
        print(f"AE processing skipped: {e}")
        return 0

def process_vital_signs():
    """Process VS (Vital Signs) domain."""
    print("Processing Vital Signs (VS)...")
    
    try:
        vs_path = f"{BRONZE_PATH}synthetic/dm/".replace("/dm/", "/vs/")
        df = spark.read.parquet(vs_path)
        
        vs_clean = df.select(
            F.col("STUDYID"),
            F.lit("VS").alias("DOMAIN"),
            F.col("USUBJID"),
            F.col("VSSEQ").cast("int"),
            F.col("VSTESTCD"),
            F.col("VSTEST"),
            F.col("VSORRES"),
            F.col("VSORRESU"),
            F.col("VSSTRESN").cast("double"),
            F.col("VSSTRESU"),
            F.col("VSNRIND"),
            F.col("VISITNUM").cast("int"),
            F.col("VISIT"),
            F.col("VSDTC")
        ).filter(
            F.col("USUBJID").isNotNull()
        ).withColumn(
            "PROCESSING_TS", F.current_timestamp()
        ).withColumn(
            "PROCESSING_DATE", F.current_date()
        )
        
        output_path = f"{SILVER_PATH}vs/"
        vs_clean.write.mode("overwrite").partitionBy("PROCESSING_DATE").parquet(output_path)
        
        print(f"VS: Processed {vs_clean.count()} records")
        return vs_clean.count()
    except Exception as e:
        print(f"VS processing skipped: {e}")
        return 0

def process_lab_results():
    """Process LB (Laboratory) domain."""
    print("Processing Lab Results (LB)...")
    
    try:
        lb_path = f"{BRONZE_PATH}synthetic/dm/".replace("/dm/", "/lb/")
        df = spark.read.parquet(lb_path)
        
        lb_clean = df.select(
            F.col("STUDYID"),
            F.lit("LB").alias("DOMAIN"),
            F.col("USUBJID"),
            F.col("LBSEQ").cast("int"),
            F.col("LBTESTCD"),
            F.col("LBTEST"),
            F.col("LBORRES"),
            F.col("LBORRESU"),
            F.col("LBSTRESN").cast("double"),
            F.col("LBSTRESU"),
            F.col("LBNRIND"),
            F.col("LBORNRLO").cast("double"),
            F.col("LBORNRHI").cast("double"),
            F.col("VISITNUM").cast("int"),
            F.col("VISIT"),
            F.col("LBDTC")
        ).filter(
            F.col("USUBJID").isNotNull()
        ).withColumn(
            "PROCESSING_TS", F.current_timestamp()
        ).withColumn(
            "PROCESSING_DATE", F.current_date()
        )
        
        output_path = f"{SILVER_PATH}lb/"
        lb_clean.write.mode("overwrite").partitionBy("PROCESSING_DATE").parquet(output_path)
        
        print(f"LB: Processed {lb_clean.count()} records")
        return lb_clean.count()
    except Exception as e:
        print(f"LB processing skipped: {e}")
        return 0

def write_job_metrics(metrics):
    """Write job metrics to S3."""
    metrics_df = spark.createDataFrame([metrics])
    metrics_path = f"s3://{DATA_BUCKET}/metadata/quality/bronze_to_silver/"
    metrics_df.write.mode("append").json(metrics_path)

# Main execution
if __name__ == "__main__":
    print(f"Starting Bronze to Silver ETL - {datetime.now()}")
    print(f"Data Bucket: {DATA_BUCKET}")
    print(f"Environment: {ENVIRONMENT}")
    
    metrics = {
        "job_name": args['JOB_NAME'],
        "run_timestamp": datetime.now().isoformat(),
        "environment": ENVIRONMENT,
        "dm_records": process_demographics(),
        "ae_records": process_adverse_events(),
        "vs_records": process_vital_signs(),
        "lb_records": process_lab_results()
    }
    
    write_job_metrics(metrics)
    
    print(f"ETL Complete - {datetime.now()}")
    job.commit()
