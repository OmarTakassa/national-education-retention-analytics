import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from src.analytics_pipeline import run_analytics_pipeline

ROOT_DIR = Path(__file__).resolve().parent.parent


def generate_excel_workbook() -> Path:
    proc_dir = ROOT_DIR / "data" / "processed"
    if not (proc_dir / "executive_summary.json").exists():
        run_analytics_pipeline()

    summary = json.loads((proc_dir / "executive_summary.json").read_text(encoding="utf-8"))
    regional = pd.read_csv(proc_dir / "regional_disparity_kpis.csv")
    cycle_eq = pd.read_csv(proc_dir / "cycle_equity_breakdown.csv")
    drivers = pd.read_csv(proc_dir / "dropout_drivers_ranked.csv")

    excel_path = ROOT_DIR / "dashboards" / "excel" / "education_retention_executive_report.xlsx"
    excel_path.parent.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(excel_path, engine="xlsxwriter") as writer:
        wb = writer.book
        header_fmt = wb.add_format(
            {"bold": True, "bg_color": "#1B365D", "font_color": "#FFFFFF", "border": 1}
        )
        title_fmt = wb.add_format({"bold": True, "font_size": 14, "font_color": "#1B365D"})
        pct_fmt = wb.add_format({"num_format": '0.00"%"'})
        int_fmt = wb.add_format({"num_format": "#,##0"})

        # Sheet 1: Executive Summary
        kpi_rows = pd.DataFrame(
            [
                ("Analysis Window", summary["cohorts_analyzed"]),
                ("Regional Directorates (AREFs)", summary["regional_directorates_count"]),
                ("2025-2026 Total Enrolled Students", summary["latest_year_enrolled"]),
                ("2025-2026 Annual Student Dropouts", summary["latest_year_dropouts"]),
                ("2020-2021 Baseline Dropout Rate (%)", summary["baseline_2020_dropout_rate_pct"]),
                ("2025-2026 National Dropout Rate (%)", summary["latest_2025_dropout_rate_pct"]),
                ("Highest Disparity Region", summary["highest_disparity_aref"]),
                ("Lowest Disparity Region", summary["lowest_disparity_aref"]),
                ("Primary Structural Dropout Driver", summary["top_dropout_driver"]),
                ("Multivariate Driver Model R²", summary["driver_model_r2"]),
            ],
            columns=["KPI Metric", "Value"],
        )
        kpi_rows.to_excel(writer, sheet_name="Executive_Summary", startrow=2, index=False)
        ws1 = writer.sheets["Executive_Summary"]
        ws1.write(
            "A1", "National Education Performance & Retention — Executive KPI Summary", title_fmt
        )
        for col_idx, col_name in enumerate(kpi_rows.columns):
            ws1.write(2, col_idx, col_name, header_fmt)
        ws1.set_column("A:A", 42)
        ws1.set_column("B:B", 34)

        # Sheet 2: Regional Disparity Ranking (2025-2026)
        latest_reg = regional[regional["academic_year"] == "2025-2026"].copy()
        latest_reg.to_excel(writer, sheet_name="Regional_Disparity", startrow=2, index=False)
        ws2 = writer.sheets["Regional_Disparity"]
        ws2.write(
            "A1",
            "Regional Directorate (AREF) Performance & Disparity Ranking (2025-2026)",
            title_fmt,
        )
        for col_idx, col_name in enumerate(latest_reg.columns):
            ws2.write(2, col_idx, col_name, header_fmt)
        ws2.set_column("A:A", 14)
        ws2.set_column("B:B", 12)
        ws2.set_column("C:C", 28)
        ws2.set_column("D:D", 16)
        ws2.set_column("E:F", 16, int_fmt)
        ws2.set_column("G:H", 18, pct_fmt)

        # Native Excel Bar Chart on Regional_Disparity
        chart = wb.add_chart({"type": "bar"})
        chart.add_series(
            {
                "name": "Weighted Dropout Rate (%)",
                "categories": ["Regional_Disparity", 3, 2, 14, 2],
                "values": ["Regional_Disparity", 3, 6, 14, 6],
                "fill": {"color": "#C0392B"},
            }
        )
        chart.set_title({"name": "2025-2026 Dropout Rate by Regional Directorate (%)"})
        chart.set_legend({"none": True})
        ws2.insert_chart("L3", chart, {"x_scale": 1.35, "y_scale": 1.35})

        # Sheet 3: Cycle & Urban-Rural Equity
        cycle_eq.to_excel(writer, sheet_name="Cycle_Urban_Rural", startrow=2, index=False)
        ws3 = writer.sheets["Cycle_Urban_Rural"]
        ws3.write("A1", "School Cycle Bottleneck & Urban-Rural Equity Breakdown", title_fmt)
        for col_idx, col_name in enumerate(cycle_eq.columns):
            ws3.write(2, col_idx, col_name, header_fmt)
        ws3.set_column("A:G", 22)

        # Sheet 4: Statistical Dropout Drivers
        drivers.to_excel(writer, sheet_name="Dropout_Drivers", startrow=2, index=False)
        ws4 = writer.sheets["Dropout_Drivers"]
        ws4.write("A1", "Standardized Regression Drivers of Student Dropout", title_fmt)
        for col_idx, col_name in enumerate(drivers.columns):
            ws4.write(2, col_idx, col_name, header_fmt)
        ws4.set_column("A:E", 32)

    return excel_path


def generate_dashboard_visuals() -> list[Path]:
    proc_dir = ROOT_DIR / "data" / "processed"
    assets_dir = ROOT_DIR / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    regional = pd.read_csv(proc_dir / "regional_disparity_kpis.csv")
    cycle_eq = pd.read_csv(proc_dir / "cycle_equity_breakdown.csv")
    drivers = pd.read_csv(proc_dir / "dropout_drivers_ranked.csv")

    sns.set_theme(style="whitegrid")

    # Visual 1: Executive Overview (6-Year National Trajectory + Cycle/Area Equity)
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.2))

    yearly = regional.groupby("academic_year", as_index=False).agg(
        total_enrolled=("total_enrolled", "sum"), total_dropouts=("total_dropouts", "sum")
    )
    yearly["national_dropout_pct"] = yearly["total_dropouts"] * 100.0 / yearly["total_enrolled"]

    axes[0].plot(
        yearly["academic_year"],
        yearly["national_dropout_pct"],
        marker="o",
        linewidth=2.6,
        color="#1B365D",
    )
    for idx, row in yearly.iterrows():
        axes[0].annotate(
            f"{row['national_dropout_pct']:.2f}%",
            (idx, row["national_dropout_pct"]),
            textcoords="offset points",
            xytext=(0, 8),
            ha="center",
            fontsize=9,
            fontweight="bold",
        )
    axes[0].set_title("National Weighted Dropout Trajectory (2020–2026)", fontweight="bold")
    axes[0].set_ylabel("Dropout Rate (%)")
    axes[0].set_ylim(
        yearly["national_dropout_pct"].min() - 0.5, yearly["national_dropout_pct"].max() + 0.6
    )
    axes[0].tick_params(axis="x", rotation=20)

    sns.barplot(
        data=cycle_eq,
        x="cycle_name",
        y="dropout_rate_pct",
        hue="area_type",
        palette={"Urban": "#2E86AB", "Rural": "#D9534F"},
        ax=axes[1],
    )
    axes[1].set_title("2025–2026 Dropout Rate by School Cycle & Area Type", fontweight="bold")
    axes[1].set_xlabel("Education Cycle")
    axes[1].set_ylabel("Dropout Rate (%)")
    axes[1].legend(title="Area Type")

    plt.tight_layout()
    p1 = assets_dir / "executive_kpi_dashboard.png"
    fig.savefig(p1, dpi=180)
    plt.close(fig)

    # Visual 2: Regional Disparity Ranking + Standardized Dropout Drivers
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))

    latest_reg = regional[regional["academic_year"] == "2025-2026"].sort_values(
        "weighted_dropout_pct", ascending=True
    )
    axes[0].barh(latest_reg["aref_name"], latest_reg["weighted_dropout_pct"], color="#34495E")
    axes[0].set_title(
        "Regional Directorate (AREF) Dropout Disparity (2025–2026)", fontweight="bold"
    )
    axes[0].set_xlabel("Weighted Dropout Rate (%)")

    drivers_sorted = drivers.sort_values("standardized_beta", ascending=True)
    colors = ["#2E7D32" if val < 0 else "#C0392B" for val in drivers_sorted["standardized_beta"]]
    axes[1].barh(drivers_sorted["driver_name"], drivers_sorted["standardized_beta"], color=colors)
    axes[1].axvline(0, color="#333333", linewidth=1)
    axes[1].set_title("Standardized Drivers of Student Dropout (Beta Impact)", fontweight="bold")
    axes[1].set_xlabel("Standardized Effect on Dropout Rate (pct pts per SD)")

    plt.tight_layout()
    p2 = assets_dir / "dropout_drivers_disparity.png"
    fig.savefig(p2, dpi=180)
    plt.close(fig)

    # Write Power BI DAX Measures file
    dax_code = """-- Power BI DAX Measures for National Education Performance & Retention Analytics

Total Enrolled Students = SUM(fact_cohort_retention[enrolled_students])

Total Student Dropouts = SUM(fact_cohort_retention[dropouts_total])

Total Retained Students = SUM(fact_cohort_retention[retained_students])

Weighted Dropout Rate (%) =
DIVIDE([Total Student Dropouts], [Total Enrolled Students], 0) * 100

Cohort Retention Rate (%) =
DIVIDE([Total Retained Students], [Total Enrolled Students], 0) * 100

Reintegration Recovery Rate (%) =
DIVIDE(SUM(fact_cohort_retention[reintegrated_students]), [Total Student Dropouts], 0) * 100

YoY Dropout Delta (pp) =
VAR CurrentRate = [Weighted Dropout Rate (%)]
VAR PrevRate =
    CALCULATE(
        [Weighted Dropout Rate (%)],
        FILTER(
            ALL(dim_academic_year),
            dim_academic_year[cohort_seq] = MAX(dim_academic_year[cohort_seq]) - 1
        )
    )
RETURN
IF(ISBLANK(PrevRate), BLANK(), CurrentRate - PrevRate)

Regional Disparity Index =
DIVIDE(
    [Weighted Dropout Rate (%)],
    CALCULATE([Weighted Dropout Rate (%)], ALL(dim_directorate)),
    1
)
"""
    (ROOT_DIR / "dashboards" / "powerbi" / "measures.dax").write_text(dax_code, encoding="utf-8")
    return [p1, p2]


if __name__ == "__main__":
    summary = run_analytics_pipeline()
    xlsx = generate_excel_workbook()
    imgs = generate_dashboard_visuals()
    print(f"Built Excel workbook: {xlsx.name}, charts: {[p.name for p in imgs]}")
