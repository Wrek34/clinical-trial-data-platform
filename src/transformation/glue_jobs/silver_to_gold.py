"""
Silver to Gold ETL Job
Transforms validated Silver layer data into analytics-ready Gold layer.

Creates dimensional model with fact and dimension tables optimized for querying.
"""

import sys
from datetime import datetime

from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from pyspark.sql import functions as F
from pyspark.sql.window import Window

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
SILVER_PATH = f"s3://{DATA_BUCKET}/silver/"
GOLD_PATH = f"s3://{DATA_BUCKET}/gold/"


def create_dim_subject():
    """Create subject dimension table."""
    print("Creating dim_subject...")
    
    dm = spark.read.parquet(f"{SILVER_PATH}dm/")
    
    dim_subject = dm.select(
        F.monotonically_increasing_id().alias("subject_key"),
        F.col("USUBJID").alias("usubjid"),
        F.col("STUDYID").alias("study_id"),
        F.col("SUBJID").alias("subject_id"),
        F.col("SITEID").alias("site_id"),
        F.col("AGE").alias("age"),
        F.col("SEX").alias("sex"),
        F.col("RACE").alias("race"),
        F.col("ETHNIC").alias("ethnicity"),
        F.col("COUNTRY").alias("country"),
        F.col("ARM").alias("treatment_arm"),
        F.col("ARMCD").alias("treatment_arm_code"),
        F.to_date(F.col("RFSTDTC")).alias("enrollment_date"),
        F.to_date(F.col("RFENDTC")).alias("end_date"),
        F.current_timestamp().alias("etl_timestamp")
    ).dropDuplicates(["usubjid"])
    
    dim_subject.write.mode("overwrite").parquet(f"{GOLD_PATH}dim_subject/")
    print(f"dim_subject: {dim_subject.count()} records")
    return dim_subject


def create_dim_site(dim_subject):
    """Create site dimension table."""
    print("Creating dim_site...")
    
    dim_site = dim_subject.select(
        F.col("site_id"),
        F.col("country")
    ).dropDuplicates().withColumn(
        "site_key", F.monotonically_increasing_id()
    ).select(
        "site_key",
        "site_id", 
        "country",
        F.current_timestamp().alias("etl_timestamp")
    )
    
    dim_site.write.mode("overwrite").parquet(f"{GOLD_PATH}dim_site/")
    print(f"dim_site: {dim_site.count()} records")
    return dim_site


def create_fact_adverse_events(dim_subject):
    """Create adverse events fact table."""
    print("Creating fact_adverse_events...")
    
    try:
        ae = spark.read.parquet(f"{SILVER_PATH}ae/")
        
        fact_ae = ae.join(
            dim_subject.select("subject_key", "usubjid"),
            ae.USUBJID == dim_subject.usubjid,
            "left"
        ).select(
            F.monotonically_increasing_id().alias("ae_key"),
            F.col("subject_key"),
            F.col("USUBJID").alias("usubjid"),
            F.col("AESEQ").alias("ae_sequence"),
            F.col("AETERM").alias("ae_term"),
            F.col("AEDECOD").alias("ae_preferred_term"),
            F.col("AEBODSYS").alias("body_system"),
            F.col("AESEV").alias("severity"),
            F.col("AESER").alias("is_serious"),
            F.col("AEREL").alias("relationship"),
            F.col("AEOUT").alias("outcome"),
            F.to_date(F.col("AESTDTC")).alias("start_date"),
            F.to_date(F.col("AEENDTC")).alias("end_date"),
            F.datediff(F.col("AEENDTC"), F.col("AESTDTC")).alias("duration_days"),
            F.current_timestamp().alias("etl_timestamp")
        )
        
        fact_ae.write.mode("overwrite").parquet(f"{GOLD_PATH}fact_adverse_events/")
        print(f"fact_adverse_events: {fact_ae.count()} records")
    except Exception as e:
        print(f"fact_adverse_events skipped: {e}")


def create_fact_vital_signs(dim_subject):
    """Create vital signs fact table."""
    print("Creating fact_vital_signs...")
    
    try:
        vs = spark.read.parquet(f"{SILVER_PATH}vs/")
        
        fact_vs = vs.join(
            dim_subject.select("subject_key", "usubjid"),
            vs.USUBJID == dim_subject.usubjid,
            "left"
        ).select(
            F.monotonically_increasing_id().alias("vs_key"),
            F.col("subject_key"),
            F.col("USUBJID").alias("usubjid"),
            F.col("VSTESTCD").alias("test_code"),
            F.col("VSTEST").alias("test_name"),
            F.col("VSSTRESN").alias("result_value"),
            F.col("VSSTRESU").alias("result_unit"),
            F.col("VSNRIND").alias("normal_range_indicator"),
            F.col("VISITNUM").alias("visit_number"),
            F.col("VISIT").alias("visit_name"),
            F.to_date(F.col("VSDTC")).alias("measurement_date"),
            F.current_timestamp().alias("etl_timestamp")
        )
        
        fact_vs.write.mode("overwrite").parquet(f"{GOLD_PATH}fact_vital_signs/")
        print(f"fact_vital_signs: {fact_vs.count()} records")
    except Exception as e:
        print(f"fact_vital_signs skipped: {e}")


def create_fact_lab_results(dim_subject):
    """Create lab results fact table."""
    print("Creating fact_lab_results...")
    
    try:
        lb = spark.read.parquet(f"{SILVER_PATH}lb/")
        
        fact_lb = lb.join(
            dim_subject.select("subject_key", "usubjid"),
            lb.USUBJID == dim_subject.usubjid,
            "left"
        ).select(
            F.monotonically_increasing_id().alias("lb_key"),
            F.col("subject_key"),
            F.col("USUBJID").alias("usubjid"),
            F.col("LBTESTCD").alias("test_code"),
            F.col("LBTEST").alias("test_name"),
            F.col("LBSTRESN").alias("result_value"),
            F.col("LBSTRESU").alias("result_unit"),
            F.col("LBNRIND").alias("normal_range_indicator"),
            F.col("LBORNRLO").alias("normal_range_low"),
            F.col("LBORNRHI").alias("normal_range_high"),
            F.col("VISITNUM").alias("visit_number"),
            F.col("VISIT").alias("visit_name"),
            F.to_date(F.col("LBDTC")).alias("collection_date"),
            F.current_timestamp().alias("etl_timestamp")
        )
        
        fact_lb.write.mode("overwrite").parquet(f"{GOLD_PATH}fact_lab_results/")
        print(f"fact_lab_results: {fact_lb.count()} records")
    except Exception as e:
        print(f"fact_lab_results skipped: {e}")


def create_summary_tables(dim_subject):
    """Create pre-aggregated summary tables."""
    print("Creating summary tables...")
    
    # Subject summary by site and treatment arm
    subject_summary = dim_subject.groupBy(
        "site_id", "treatment_arm"
    ).agg(
        F.count("*").alias("subject_count"),
        F.avg("age").alias("avg_age"),
        F.min("age").alias("min_age"),
        F.max("age").alias("max_age")
    ).withColumn("etl_timestamp", F.current_timestamp())
    
    subject_summary.write.mode("overwrite").parquet(f"{GOLD_PATH}summary_subjects_by_site/")
    print(f"summary_subjects_by_site: {subject_summary.count()} records")


# Main execution
if __name__ == "__main__":
    print(f"Starting Silver to Gold ETL - {datetime.now()}")
    print(f"Data Bucket: {DATA_BUCKET}")
    print(f"Environment: {ENVIRONMENT}")
    
    # Create dimensions first
    dim_subject = create_dim_subject()
    dim_site = create_dim_site(dim_subject)
    
    # Create fact tables
    create_fact_adverse_events(dim_subject)
    create_fact_vital_signs(dim_subject)
    create_fact_lab_results(dim_subject)
    
    # Create summaries
    create_summary_tables(dim_subject)
    
    print(f"ETL Complete - {datetime.now()}")
    job.commit()
