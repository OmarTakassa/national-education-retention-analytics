import json
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler

from src.generate_dataset import build_longitudinal_dataset

ROOT_DIR = Path(__file__).resolve().parent.parent


def run_analytics_pipeline() -> dict:
    raw_csv = ROOT_DIR / "data" / "raw" / "regional_education_cohorts_2020_2026.csv"
    if not raw_csv.exists():
        df = build_longitudinal_dataset()
    else:
        df = pd.read_csv(raw_csv)

    proc_dir = ROOT_DIR / "data" / "processed"
    proc_dir.mkdir(parents=True, exist_ok=True)
    db_path = proc_dir / "education_warehouse.db"
    if db_path.exists():
        db_path.unlink()

    # Build Dimensional Tables
    dim_directorate = (
        df[["aref_code", "aref_name", "macro_zone"]]
        .drop_duplicates()
        .sort_values("aref_code")
        .reset_index(drop=True)
    )
    dim_directorate["directorate_key"] = dim_directorate.index + 1

    dim_academic_year = (
        df[["academic_year", "cohort_seq"]]
        .drop_duplicates()
        .sort_values("cohort_seq")
        .reset_index(drop=True)
    )
    dim_academic_year["year_key"] = dim_academic_year.index + 1

    dim_school_cycle = df[["cycle_code", "cycle_name"]].drop_duplicates().reset_index(drop=True)
    dim_school_cycle["cycle_key"] = dim_school_cycle.index + 1

    fact = (
        df.merge(dim_directorate[["aref_code", "directorate_key"]], on="aref_code")
        .merge(dim_academic_year[["academic_year", "year_key"]], on="academic_year")
        .merge(dim_school_cycle[["cycle_code", "cycle_key"]], on="cycle_code")
    )
    fact["fact_id"] = fact.index + 1

    fact_cols = [
        "fact_id",
        "year_key",
        "directorate_key",
        "cycle_key",
        "area_type",
        "enrolled_students",
        "retained_students",
        "dropouts_total",
        "reintegrated_students",
        "dropout_rate_pct",
        "retention_rate_pct",
        "reintegration_rate_pct",
        "avg_commute_km",
        "student_classroom_ratio",
        "grade_repetition_pct",
        "boarding_transport_coverage_pct",
        "exam_pass_rate_pct",
    ]
    fact_table = fact[fact_cols]

    # Export Star Schema CSVs for Power BI Desktop import
    pbi_dir = ROOT_DIR / "dashboards" / "powerbi"
    pbi_dir.mkdir(parents=True, exist_ok=True)
    dim_directorate.to_csv(pbi_dir / "dim_directorate.csv", index=False)
    dim_academic_year.to_csv(pbi_dir / "dim_academic_year.csv", index=False)
    dim_school_cycle.to_csv(pbi_dir / "dim_school_cycle.csv", index=False)
    fact_table.to_csv(pbi_dir / "fact_cohort_retention.csv", index=False)

    # Load into SQLite Star Schema Warehouse and execute analytical SQL views
    schema_sql = (ROOT_DIR / "sql" / "01_star_schema.sql").read_text(encoding="utf-8")
    kpi_sql = (ROOT_DIR / "sql" / "02_analytical_kpis.sql").read_text(encoding="utf-8")
    queries = [q.strip() for q in kpi_sql.split(";") if q.strip()]

    with sqlite3.connect(db_path) as conn:
        conn.executescript(schema_sql)
        dim_directorate.to_sql("dim_directorate", conn, if_exists="append", index=False)
        dim_academic_year.to_sql("dim_academic_year", conn, if_exists="append", index=False)
        dim_school_cycle.to_sql("dim_school_cycle", conn, if_exists="append", index=False)
        fact_table.to_sql("fact_cohort_retention", conn, if_exists="append", index=False)

        regional_kpis = pd.read_sql_query(queries[0], conn)
        cycle_equity = pd.read_sql_query(queries[1], conn)

    regional_kpis.to_csv(proc_dir / "regional_disparity_kpis.csv", index=False)
    cycle_equity.to_csv(proc_dir / "cycle_equity_breakdown.csv", index=False)

    # Standardized Multivariate Driver Analysis for Student Dropout
    model_df = df.copy()
    model_df["is_rural"] = (model_df["area_type"] == "Rural").astype(float)
    model_df["is_lower_secondary"] = (model_df["cycle_code"] == "LSEC").astype(float)

    feature_labels = {
        "is_lower_secondary": "Lower Secondary Transition Bottleneck",
        "is_rural": "Rural School Location Exposure",
        "grade_repetition_pct": "Grade Repetition Rate (%)",
        "avg_commute_km": "Average Student Commute Distance (km)",
        "boarding_transport_coverage_pct": "Boarding & Transport Support Coverage (%)",
        "exam_pass_rate_pct": "Regional Exam Pass Rate (%)",
    }
    features = list(feature_labels.keys())
    X = model_df[features].values
    y = model_df["dropout_rate_pct"].values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    reg = LinearRegression().fit(X_scaled, y)
    r2_score = float(reg.score(X_scaled, y))

    drivers_df = pd.DataFrame(
        {
            "feature_code": features,
            "driver_name": [feature_labels[f] for f in features],
            "standardized_beta": np.round(reg.coef_, 4),
            "abs_impact": np.round(np.abs(reg.coef_), 4),
            "direction": ["Increases Dropout" if c > 0 else "Reduces Dropout" for c in reg.coef_],
        }
    ).sort_values("abs_impact", ascending=False)
    drivers_df.to_csv(proc_dir / "dropout_drivers_ranked.csv", index=False)

    # Summary Metrics JSON
    latest = regional_kpis[regional_kpis["academic_year"] == "2025-2026"]
    first = regional_kpis[regional_kpis["academic_year"] == "2020-2021"]

    latest_rate = round(
        float(latest["total_dropouts"].sum() * 100.0 / latest["total_enrolled"].sum()), 2
    )
    first_rate = round(
        float(first["total_dropouts"].sum() * 100.0 / first["total_enrolled"].sum()), 2
    )

    summary = {
        "cohorts_analyzed": "2020-2021 to 2025-2026",
        "regional_directorates_count": int(df["aref_code"].nunique()),
        "total_cohort_records": int(len(df)),
        "latest_year_enrolled": int(latest["total_enrolled"].sum()),
        "latest_year_dropouts": int(latest["total_dropouts"].sum()),
        "baseline_2020_dropout_rate_pct": first_rate,
        "latest_2025_dropout_rate_pct": latest_rate,
        "six_year_dropout_reduction_bps": round((first_rate - latest_rate) * 100, 1),
        "highest_disparity_aref": str(latest.iloc[0]["aref_name"]),
        "highest_disparity_dropout_pct": float(latest.iloc[0]["weighted_dropout_pct"]),
        "lowest_disparity_aref": str(latest.iloc[-1]["aref_name"]),
        "lowest_disparity_dropout_pct": float(latest.iloc[-1]["weighted_dropout_pct"]),
        "driver_model_r2": round(r2_score, 4),
        "top_dropout_driver": str(drivers_df.iloc[0]["driver_name"]),
    }
    (proc_dir / "executive_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    return summary


if __name__ == "__main__":
    print(json.dumps(run_analytics_pipeline(), indent=2))
