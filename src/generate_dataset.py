from pathlib import Path

import numpy as np
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent

AREFS = [
    ("AREF-01", "Tanger-Tetouan-Al Hoceima", "North", 0.44, 1.18),
    ("AREF-02", "Oriental", "Northeast", 0.41, 1.14),
    ("AREF-03", "Fes-Meknes", "Central-North", 0.43, 1.12),
    ("AREF-04", "Rabat-Sale-Kenitra", "Northwest", 0.30, 0.88),
    ("AREF-05", "Beni Mellal-Khenifra", "Central", 0.54, 1.24),
    ("AREF-06", "Casablanca-Settat", "Coastal-Central", 0.22, 0.82),
    ("AREF-07", "Marrakech-Safi", "Central-South", 0.56, 1.26),
    ("AREF-08", "Draa-Tafilalet", "Southeast", 0.64, 1.32),
    ("AREF-09", "Souss-Massa", "South-Central", 0.47, 1.10),
    ("AREF-10", "Guelmim-Oued Noun", "South", 0.38, 1.05),
    ("AREF-11", "Laayoune-Sakia El Hamra", "Sahara-North", 0.14, 0.78),
    ("AREF-12", "Dakhla-Oued Ed-Dahab", "Sahara-South", 0.16, 0.76),
]

ACADEMIC_YEARS = ["2020-2021", "2021-2022", "2022-2023", "2023-2024", "2024-2025", "2025-2026"]
CYCLES = [
    ("PRIM", "Primary", 0.021, 0.55),
    ("LSEC", "Lower Secondary", 0.078, 0.23),
    ("USEC", "Upper Secondary", 0.049, 0.22),
]


def build_longitudinal_dataset(seed: int = 2026) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []

    for year_idx, academic_year in enumerate(ACADEMIC_YEARS):
        # Gradual national policy improvement over 6 academic cohorts
        reform_factor = 1.0 - (year_idx * 0.022)

        for aref_code, aref_name, macro_zone, rural_share, disparity_mult in AREFS:
            base_students = rng.integers(140_000, 980_000)
            if aref_code in {"AREF-06", "AREF-04", "AREF-07", "AREF-01", "AREF-03"}:
                base_students = int(base_students * 1.45)

            for cycle_code, cycle_name, base_dropout, _ in CYCLES:
                for area_type in ["Urban", "Rural"]:
                    area_weight = rural_share if area_type == "Rural" else (1.0 - rural_share)
                    cycle_weight = {"PRIM": 0.54, "LSEC": 0.27, "USEC": 0.19}[cycle_code]
                    enrolled = max(4_500, int(base_students * area_weight * cycle_weight))

                    # Operational drivers
                    rural_penalty = 1.48 if area_type == "Rural" else 0.72
                    avg_commute_km = round(
                        float(rng.normal(7.8 if area_type == "Rural" else 2.1, 1.4)), 2
                    )
                    avg_commute_km = max(0.8, avg_commute_km)

                    student_classroom_ratio = round(
                        float(rng.normal(34.5 if area_type == "Urban" else 29.0, 3.2)), 1
                    )
                    grade_repetition_pct = round(
                        float(
                            np.clip(
                                rng.normal(
                                    13.5 if cycle_code == "LSEC" else 7.2,
                                    2.1,
                                )
                                * disparity_mult,
                                2.5,
                                24.0,
                            )
                        ),
                        2,
                    )
                    boarding_transport_coverage_pct = round(
                        float(
                            np.clip(
                                (48.0 + year_idx * 4.5) / disparity_mult + rng.normal(0, 4.0),
                                18.0,
                                92.0,
                            )
                        ),
                        2,
                    )
                    exam_pass_rate_pct = round(
                        float(
                            np.clip(
                                (84.0 - (disparity_mult - 1.0) * 18.0 + year_idx * 1.1)
                                + rng.normal(0, 2.3),
                                52.0,
                                96.5,
                            )
                        ),
                        2,
                    )

                    # Dropout rate model driven by cycle bottleneck, rural access, and repetition
                    raw_rate = (
                        base_dropout
                        * disparity_mult
                        * rural_penalty
                        * reform_factor
                        * (1.0 + 0.018 * (grade_repetition_pct - 8.0))
                        * (1.0 - 0.003 * (boarding_transport_coverage_pct - 50.0))
                    )
                    dropout_rate = float(np.clip(raw_rate + rng.normal(0, 0.003), 0.008, 0.165))
                    dropouts_total = int(round(enrolled * dropout_rate))
                    retained_students = enrolled - dropouts_total
                    reintegrated_students = int(round(dropouts_total * rng.uniform(0.18, 0.25)))

                    rows.append(
                        {
                            "academic_year": academic_year,
                            "cohort_seq": year_idx + 1,
                            "aref_code": aref_code,
                            "aref_name": aref_name,
                            "macro_zone": macro_zone,
                            "cycle_code": cycle_code,
                            "cycle_name": cycle_name,
                            "area_type": area_type,
                            "enrolled_students": enrolled,
                            "retained_students": retained_students,
                            "dropouts_total": dropouts_total,
                            "reintegrated_students": reintegrated_students,
                            "dropout_rate_pct": round((dropouts_total / enrolled) * 100, 2),
                            "retention_rate_pct": round((retained_students / enrolled) * 100, 2),
                            "reintegration_rate_pct": round(
                                (reintegrated_students / max(1, dropouts_total)) * 100, 2
                            ),
                            "avg_commute_km": avg_commute_km,
                            "student_classroom_ratio": student_classroom_ratio,
                            "grade_repetition_pct": grade_repetition_pct,
                            "boarding_transport_coverage_pct": boarding_transport_coverage_pct,
                            "exam_pass_rate_pct": exam_pass_rate_pct,
                        }
                    )

    df = pd.DataFrame(rows)
    raw_dir = ROOT_DIR / "data" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(raw_dir / "regional_education_cohorts_2020_2026.csv", index=False)
    return df


if __name__ == "__main__":
    dataset = build_longitudinal_dataset()
    print(
        f"Generated {len(dataset)} cohort records across {dataset['aref_code'].nunique()} AREFs."
    )
