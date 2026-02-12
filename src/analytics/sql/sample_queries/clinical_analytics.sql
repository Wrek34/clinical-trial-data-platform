-- ============================================================================
-- Clinical Trial Analytics Queries
-- ============================================================================
-- These queries run against the Gold layer dimensional model.
-- They demonstrate the types of analytics that pharmaceutical companies need.
--
-- INTERVIEW TALKING POINTS:
-- "The Gold layer uses a dimensional model optimized for analytics.
-- Fact tables contain measurements and events, dimension tables contain
-- descriptive attributes. This star schema pattern enables efficient
-- aggregations and supports BI tools like Tableau, QuickSight, or PowerBI."
-- ============================================================================


-- ============================================================================
-- QUERY 1: Subject Enrollment Summary
-- ============================================================================
-- Purpose: Overview of study enrollment by site and treatment arm
-- Business Use: Track recruitment progress, identify underperforming sites
-- ============================================================================

SELECT 
    site_id,
    treatment_arm,
    COUNT(*) as subject_count,
    ROUND(AVG(age), 1) as avg_age,
    MIN(age) as min_age,
    MAX(age) as max_age,
    SUM(CASE WHEN sex = 'M' THEN 1 ELSE 0 END) as male_count,
    SUM(CASE WHEN sex = 'F' THEN 1 ELSE 0 END) as female_count,
    MIN(enrollment_date) as first_enrollment,
    MAX(enrollment_date) as last_enrollment
FROM gold.dim_subject
GROUP BY site_id, treatment_arm
ORDER BY site_id, treatment_arm;


-- ============================================================================
-- QUERY 2: Adverse Event Analysis by Treatment Arm
-- ============================================================================
-- Purpose: Compare safety profiles across treatment groups
-- Business Use: Safety signal detection, regulatory reporting
-- Regulatory Note: This type of analysis is required for FDA submissions
-- ============================================================================

SELECT 
    s.treatment_arm,
    ae.ae_preferred_term,
    ae.severity,
    COUNT(*) as event_count,
    COUNT(DISTINCT ae.usubjid) as subjects_affected,
    ROUND(COUNT(DISTINCT ae.usubjid) * 100.0 / 
          (SELECT COUNT(*) FROM gold.dim_subject WHERE treatment_arm = s.treatment_arm), 2
    ) as pct_subjects_affected,
    ROUND(AVG(ae.duration_days), 1) as avg_duration_days
FROM gold.fact_adverse_events ae
JOIN gold.dim_subject s ON ae.subject_key = s.subject_key
GROUP BY s.treatment_arm, ae.ae_preferred_term, ae.severity
HAVING COUNT(*) >= 3  -- Only show AEs occurring 3+ times
ORDER BY s.treatment_arm, event_count DESC;


-- ============================================================================
-- QUERY 3: Serious Adverse Events Summary
-- ============================================================================
-- Purpose: Identify and track serious adverse events
-- Business Use: Safety monitoring, expedited regulatory reporting
-- Note: SAEs must be reported to FDA within 15 days
-- ============================================================================

SELECT 
    ae.usubjid,
    s.site_id,
    s.treatment_arm,
    ae.ae_term,
    ae.ae_preferred_term,
    ae.body_system,
    ae.severity,
    ae.relationship,
    ae.outcome,
    ae.start_date,
    ae.end_date,
    ae.duration_days
FROM gold.fact_adverse_events ae
JOIN gold.dim_subject s ON ae.subject_key = s.subject_key
WHERE ae.is_serious = 'Y'
ORDER BY ae.start_date DESC;


-- ============================================================================
-- QUERY 4: Vital Signs Trends Over Time
-- ============================================================================
-- Purpose: Track vital sign changes throughout the study
-- Business Use: Efficacy analysis (e.g., blood pressure reduction)
-- ============================================================================

SELECT 
    s.treatment_arm,
    vs.test_code,
    vs.test_name,
    vs.visit_name,
    vs.visit_number,
    COUNT(*) as measurement_count,
    ROUND(AVG(vs.result_value), 2) as avg_value,
    ROUND(STDDEV(vs.result_value), 2) as std_dev,
    MIN(vs.result_value) as min_value,
    MAX(vs.result_value) as max_value,
    SUM(CASE WHEN vs.normal_range_indicator = 'HIGH' THEN 1 ELSE 0 END) as high_count,
    SUM(CASE WHEN vs.normal_range_indicator = 'LOW' THEN 1 ELSE 0 END) as low_count
FROM gold.fact_vital_signs vs
JOIN gold.dim_subject s ON vs.subject_key = s.subject_key
WHERE vs.test_code IN ('SYSBP', 'DIABP', 'HR')  -- Blood pressure and heart rate
GROUP BY s.treatment_arm, vs.test_code, vs.test_name, vs.visit_name, vs.visit_number
ORDER BY s.treatment_arm, vs.test_code, vs.visit_number;


-- ============================================================================
-- QUERY 5: Lab Results Outside Normal Range
-- ============================================================================
-- Purpose: Identify potentially clinically significant lab abnormalities
-- Business Use: Safety monitoring, identify subjects needing follow-up
-- ============================================================================

SELECT 
    lb.usubjid,
    s.site_id,
    s.treatment_arm,
    lb.test_code,
    lb.test_name,
    lb.result_value,
    lb.result_unit,
    lb.normal_range_low,
    lb.normal_range_high,
    lb.normal_range_indicator,
    lb.visit_name,
    lb.collection_date,
    -- Calculate how far outside normal range
    CASE 
        WHEN lb.normal_range_indicator = 'HIGH' THEN 
            ROUND((lb.result_value - lb.normal_range_high) / lb.normal_range_high * 100, 1)
        WHEN lb.normal_range_indicator = 'LOW' THEN 
            ROUND((lb.normal_range_low - lb.result_value) / lb.normal_range_low * 100, 1)
        ELSE 0
    END as pct_outside_range
FROM gold.fact_lab_results lb
JOIN gold.dim_subject s ON lb.subject_key = s.subject_key
WHERE lb.normal_range_indicator IN ('HIGH', 'LOW')
ORDER BY ABS(pct_outside_range) DESC
LIMIT 100;


-- ============================================================================
-- QUERY 6: Treatment Efficacy - Blood Pressure Reduction
-- ============================================================================
-- Purpose: Compare baseline vs. end-of-study blood pressure by treatment
-- Business Use: Primary efficacy analysis for hypertension studies
-- ============================================================================

WITH baseline AS (
    SELECT 
        vs.usubjid,
        vs.test_code,
        AVG(vs.result_value) as baseline_value
    FROM gold.fact_vital_signs vs
    WHERE vs.visit_name = 'BASELINE'
      AND vs.test_code IN ('SYSBP', 'DIABP')
    GROUP BY vs.usubjid, vs.test_code
),
endpoint AS (
    SELECT 
        vs.usubjid,
        vs.test_code,
        AVG(vs.result_value) as endpoint_value
    FROM gold.fact_vital_signs vs
    WHERE vs.visit_name = 'END OF TREATMENT'
      AND vs.test_code IN ('SYSBP', 'DIABP')
    GROUP BY vs.usubjid, vs.test_code
)
SELECT 
    s.treatment_arm,
    b.test_code,
    COUNT(*) as subject_count,
    ROUND(AVG(b.baseline_value), 1) as avg_baseline,
    ROUND(AVG(e.endpoint_value), 1) as avg_endpoint,
    ROUND(AVG(e.endpoint_value - b.baseline_value), 1) as avg_change,
    ROUND(AVG((e.endpoint_value - b.baseline_value) / b.baseline_value * 100), 1) as pct_change
FROM baseline b
JOIN endpoint e ON b.usubjid = e.usubjid AND b.test_code = e.test_code
JOIN gold.dim_subject s ON b.usubjid = s.usubjid
GROUP BY s.treatment_arm, b.test_code
ORDER BY s.treatment_arm, b.test_code;


-- ============================================================================
-- QUERY 7: Site Performance Metrics
-- ============================================================================
-- Purpose: Evaluate site performance for study management
-- Business Use: Identify sites needing support, inform future study planning
-- ============================================================================

SELECT 
    site.site_id,
    site.country,
    COUNT(DISTINCT s.usubjid) as enrolled_subjects,
    
    -- Enrollment rate (subjects per month)
    ROUND(COUNT(DISTINCT s.usubjid) * 30.0 / 
          NULLIF(DATEDIFF('day', MIN(s.enrollment_date), MAX(s.enrollment_date)), 0), 2
    ) as subjects_per_month,
    
    -- Data quality: subjects with AEs recorded
    COUNT(DISTINCT ae.usubjid) as subjects_with_ae,
    
    -- Safety: SAE rate
    SUM(CASE WHEN ae.is_serious = 'Y' THEN 1 ELSE 0 END) as serious_ae_count,
    
    -- Dropout rate (subjects with end date)
    ROUND(SUM(CASE WHEN s.end_date IS NOT NULL THEN 1 ELSE 0 END) * 100.0 / 
          COUNT(DISTINCT s.usubjid), 1
    ) as completion_rate_pct

FROM gold.dim_site site
JOIN gold.dim_subject s ON site.site_id = s.site_id
LEFT JOIN gold.fact_adverse_events ae ON s.subject_key = ae.subject_key
GROUP BY site.site_id, site.country
ORDER BY enrolled_subjects DESC;


-- ============================================================================
-- QUERY 8: Demographics Summary for Regulatory Submission
-- ============================================================================
-- Purpose: Standard demographics table required in regulatory submissions
-- Business Use: FDA/EMA submission documentation
-- Note: This format aligns with ICH E3 guidance for clinical study reports
-- ============================================================================

SELECT 
    'All Subjects' as category,
    treatment_arm,
    COUNT(*) as n,
    
    -- Age statistics
    ROUND(AVG(age), 1) as age_mean,
    ROUND(STDDEV(age), 1) as age_sd,
    MIN(age) as age_min,
    MAX(age) as age_max,
    
    -- Sex distribution
    SUM(CASE WHEN sex = 'M' THEN 1 ELSE 0 END) as male_n,
    ROUND(SUM(CASE WHEN sex = 'M' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as male_pct,
    SUM(CASE WHEN sex = 'F' THEN 1 ELSE 0 END) as female_n,
    ROUND(SUM(CASE WHEN sex = 'F' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as female_pct,
    
    -- Race distribution (top categories)
    SUM(CASE WHEN race = 'WHITE' THEN 1 ELSE 0 END) as white_n,
    ROUND(SUM(CASE WHEN race = 'WHITE' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as white_pct,
    SUM(CASE WHEN race = 'BLACK OR AFRICAN AMERICAN' THEN 1 ELSE 0 END) as black_n,
    SUM(CASE WHEN race = 'ASIAN' THEN 1 ELSE 0 END) as asian_n

FROM gold.dim_subject
GROUP BY treatment_arm

UNION ALL

SELECT 
    'Total' as category,
    'ALL' as treatment_arm,
    COUNT(*) as n,
    ROUND(AVG(age), 1) as age_mean,
    ROUND(STDDEV(age), 1) as age_sd,
    MIN(age) as age_min,
    MAX(age) as age_max,
    SUM(CASE WHEN sex = 'M' THEN 1 ELSE 0 END) as male_n,
    ROUND(SUM(CASE WHEN sex = 'M' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as male_pct,
    SUM(CASE WHEN sex = 'F' THEN 1 ELSE 0 END) as female_n,
    ROUND(SUM(CASE WHEN sex = 'F' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as female_pct,
    SUM(CASE WHEN race = 'WHITE' THEN 1 ELSE 0 END) as white_n,
    ROUND(SUM(CASE WHEN race = 'WHITE' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as white_pct,
    SUM(CASE WHEN race = 'BLACK OR AFRICAN AMERICAN' THEN 1 ELSE 0 END) as black_n,
    SUM(CASE WHEN race = 'ASIAN' THEN 1 ELSE 0 END) as asian_n
FROM gold.dim_subject

ORDER BY category, treatment_arm;


-- ============================================================================
-- QUERY 9: Data Completeness Report
-- ============================================================================
-- Purpose: Assess data quality and completeness across domains
-- Business Use: Identify data collection issues, prepare for database lock
-- ============================================================================

SELECT 
    'Demographics (DM)' as domain,
    COUNT(*) as total_records,
    SUM(CASE WHEN usubjid IS NULL THEN 1 ELSE 0 END) as null_usubjid,
    SUM(CASE WHEN age IS NULL THEN 1 ELSE 0 END) as null_age,
    SUM(CASE WHEN sex IS NULL THEN 1 ELSE 0 END) as null_sex,
    SUM(CASE WHEN treatment_arm IS NULL THEN 1 ELSE 0 END) as null_arm,
    ROUND(100.0 - (SUM(CASE WHEN age IS NULL OR sex IS NULL OR treatment_arm IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*)), 1) as completeness_pct
FROM gold.dim_subject

UNION ALL

SELECT 
    'Adverse Events (AE)' as domain,
    COUNT(*) as total_records,
    SUM(CASE WHEN usubjid IS NULL THEN 1 ELSE 0 END) as null_usubjid,
    SUM(CASE WHEN ae_term IS NULL THEN 1 ELSE 0 END) as null_term,
    SUM(CASE WHEN severity IS NULL THEN 1 ELSE 0 END) as null_severity,
    SUM(CASE WHEN start_date IS NULL THEN 1 ELSE 0 END) as null_start_date,
    ROUND(100.0 - (SUM(CASE WHEN ae_term IS NULL OR severity IS NULL THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0)), 1) as completeness_pct
FROM gold.fact_adverse_events

UNION ALL

SELECT 
    'Vital Signs (VS)' as domain,
    COUNT(*) as total_records,
    SUM(CASE WHEN usubjid IS NULL THEN 1 ELSE 0 END) as null_usubjid,
    SUM(CASE WHEN test_code IS NULL THEN 1 ELSE 0 END) as null_test,
    SUM(CASE WHEN result_value IS NULL THEN 1 ELSE 0 END) as null_result,
    SUM(CASE WHEN measurement_date IS NULL THEN 1 ELSE 0 END) as null_date,
    ROUND(100.0 - (SUM(CASE WHEN result_value IS NULL THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0)), 1) as completeness_pct
FROM gold.fact_vital_signs

UNION ALL

SELECT 
    'Lab Results (LB)' as domain,
    COUNT(*) as total_records,
    SUM(CASE WHEN usubjid IS NULL THEN 1 ELSE 0 END) as null_usubjid,
    SUM(CASE WHEN test_code IS NULL THEN 1 ELSE 0 END) as null_test,
    SUM(CASE WHEN result_value IS NULL THEN 1 ELSE 0 END) as null_result,
    SUM(CASE WHEN collection_date IS NULL THEN 1 ELSE 0 END) as null_date,
    ROUND(100.0 - (SUM(CASE WHEN result_value IS NULL THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0)), 1) as completeness_pct
FROM gold.fact_lab_results;


-- ============================================================================
-- QUERY 10: Executive Dashboard Metrics
-- ============================================================================
-- Purpose: High-level KPIs for study leadership
-- Business Use: Study status reporting, executive dashboards
-- ============================================================================

SELECT 
    -- Enrollment
    (SELECT COUNT(*) FROM gold.dim_subject) as total_enrolled,
    (SELECT COUNT(DISTINCT site_id) FROM gold.dim_subject) as active_sites,
    
    -- Safety
    (SELECT COUNT(*) FROM gold.fact_adverse_events) as total_aes,
    (SELECT COUNT(*) FROM gold.fact_adverse_events WHERE is_serious = 'Y') as total_saes,
    (SELECT COUNT(DISTINCT usubjid) FROM gold.fact_adverse_events WHERE is_serious = 'Y') as subjects_with_sae,
    
    -- Data Volume
    (SELECT COUNT(*) FROM gold.fact_vital_signs) as total_vital_signs,
    (SELECT COUNT(*) FROM gold.fact_lab_results) as total_lab_results,
    
    -- Treatment Distribution
    (SELECT COUNT(*) FROM gold.dim_subject WHERE treatment_arm = 'PLACEBO') as placebo_count,
    (SELECT COUNT(*) FROM gold.dim_subject WHERE treatment_arm = 'TREATMENT_LOW') as treatment_low_count,
    (SELECT COUNT(*) FROM gold.dim_subject WHERE treatment_arm = 'TREATMENT_HIGH') as treatment_high_count;
