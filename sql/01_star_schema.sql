-- Star Schema for National Education Performance & Retention Analytics

CREATE TABLE IF NOT EXISTS dim_directorate (
    directorate_key INTEGER PRIMARY KEY,
    aref_code       VARCHAR(16) UNIQUE NOT NULL,
    aref_name       VARCHAR(100) NOT NULL,
    macro_zone      VARCHAR(50) NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_academic_year (
    year_key        INTEGER PRIMARY KEY,
    academic_year   VARCHAR(16) UNIQUE NOT NULL,
    cohort_seq      INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_school_cycle (
    cycle_key       INTEGER PRIMARY KEY,
    cycle_code      VARCHAR(16) UNIQUE NOT NULL,
    cycle_name      VARCHAR(50) NOT NULL
);

CREATE TABLE IF NOT EXISTS fact_cohort_retention (
    fact_id                         INTEGER PRIMARY KEY,
    year_key                        INTEGER NOT NULL REFERENCES dim_academic_year(year_key),
    directorate_key                 INTEGER NOT NULL REFERENCES dim_directorate(directorate_key),
    cycle_key                       INTEGER NOT NULL REFERENCES dim_school_cycle(cycle_key),
    area_type                       VARCHAR(16) NOT NULL,
    enrolled_students               INTEGER NOT NULL,
    retained_students               INTEGER NOT NULL,
    dropouts_total                  INTEGER NOT NULL,
    reintegrated_students           INTEGER NOT NULL,
    dropout_rate_pct                NUMERIC(6, 2) NOT NULL,
    retention_rate_pct              NUMERIC(6, 2) NOT NULL,
    reintegration_rate_pct          NUMERIC(6, 2) NOT NULL,
    avg_commute_km                  NUMERIC(6, 2) NOT NULL,
    student_classroom_ratio         NUMERIC(6, 1) NOT NULL,
    grade_repetition_pct            NUMERIC(6, 2) NOT NULL,
    boarding_transport_coverage_pct NUMERIC(6, 2) NOT NULL,
    exam_pass_rate_pct              NUMERIC(6, 2) NOT NULL
);