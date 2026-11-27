-- 1. Longitudinal Regional Disparity & Year-over-Year Dropout Delta (Window Functions)
WITH regional_annual AS (
    SELECT
        y.academic_year,
        y.cohort_seq,
        d.aref_code,
        d.aref_name,
        d.macro_zone,
        SUM(f.enrolled_students) AS total_enrolled,
        SUM(f.dropouts_total) AS total_dropouts,
        ROUND(SUM(f.dropouts_total) * 100.0 / SUM(f.enrolled_students), 2) AS weighted_dropout_pct,
        ROUND(AVG(f.exam_pass_rate_pct), 2) AS avg_exam_pass_pct
    FROM fact_cohort_retention f
    JOIN dim_academic_year y ON f.year_key = y.year_key
    JOIN dim_directorate d ON f.directorate_key = d.directorate_key
    GROUP BY 1, 2, 3, 4, 5
)
SELECT
    academic_year,
    aref_code,
    aref_name,
    macro_zone,
    total_enrolled,
    total_dropouts,
    weighted_dropout_pct,
    ROUND(
        weighted_dropout_pct - LAG(weighted_dropout_pct) OVER (
            PARTITION BY aref_code ORDER BY cohort_seq
        ),
        2
    ) AS yoy_dropout_delta_pct,
    RANK() OVER (
        PARTITION BY academic_year ORDER BY weighted_dropout_pct DESC
    ) AS disparity_priority_rank,
    avg_exam_pass_pct
FROM regional_annual
ORDER BY academic_year DESC, disparity_priority_rank ASC;

-- 2. Cycle Bottleneck & Urban-Rural Equity Breakdown (Latest Academic Cohort)
SELECT
    c.cycle_name,
    f.area_type,
    SUM(f.enrolled_students) AS enrolled_students,
    SUM(f.dropouts_total) AS dropouts_total,
    ROUND(SUM(f.dropouts_total) * 100.0 / SUM(f.enrolled_students), 2) AS dropout_rate_pct,
    ROUND(AVG(f.grade_repetition_pct), 2) AS avg_repetition_pct,
    ROUND(AVG(f.boarding_transport_coverage_pct), 2) AS avg_support_coverage_pct
FROM fact_cohort_retention f
JOIN dim_academic_year y ON f.year_key = y.year_key
JOIN dim_school_cycle c ON f.cycle_key = c.cycle_key
WHERE y.academic_year = '2025-2026'
GROUP BY 1, 2
ORDER BY dropout_rate_pct DESC;