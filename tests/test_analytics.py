from pathlib import Path

import pandas as pd

from src.analytics_pipeline import run_analytics_pipeline
from src.build_reports import generate_dashboard_visuals, generate_excel_workbook
from src.generate_dataset import build_longitudinal_dataset

ROOT_DIR = Path(__file__).resolve().parent.parent


def test_longitudinal_dataset_dimensions():
    df = build_longitudinal_dataset(seed=2026)
    # 6 years * 12 AREFs * 3 cycles * 2 area types = 432 records
    assert len(df) == 432
    assert df["aref_code"].nunique() == 12
    assert (df["retained_students"] + df["dropouts_total"] == df["enrolled_students"]).all()


def test_analytics_pipeline_and_reports():
    summary = run_analytics_pipeline()
    assert summary["regional_directorates_count"] == 12
    assert summary["latest_2025_dropout_rate_pct"] < summary["baseline_2020_dropout_rate_pct"]
    assert summary["driver_model_r2"] > 0.75

    xlsx_path = generate_excel_workbook()
    assert xlsx_path.exists()
    xl = pd.ExcelFile(xlsx_path)
    assert set(xl.sheet_names) == {
        "Executive_Summary",
        "Regional_Disparity",
        "Cycle_Urban_Rural",
        "Dropout_Drivers",
    }

    images = generate_dashboard_visuals()
    assert len(images) == 2
    assert all(img.exists() for img in images)
