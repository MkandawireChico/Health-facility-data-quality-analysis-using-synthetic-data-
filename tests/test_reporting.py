import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from reporting import assess_dataset, build_issue_register, facility_summary, validate_dataset


def sample_data():
    return pd.DataFrame({
        "Facility": ["A", "A", "B", "B", "B", "A"],
        "Programme": ["HIV"] * 6,
        "Indicator": ["ART"] * 6,
        "Month": pd.date_range("2025-01-01", periods=6, freq="MS"),
        "Reported_Value": [100, 105, np.nan, 500, 90, 110],
        "Target_Value": [120] * 6,
        "Data_Source": ["DHIS2"] * 6,
        "Paper_Value": [100, 105, 100, 100, 90, 110],
        "EMR_Value": [101, 104, 100, 101, 90, 110],
        "DHIS2_Value": [100, 105, 100, 100, 90, 110],
        "Timeliness": ["On Time", "Late", "On Time", "On Time", "Late", "On Time"],
    })


def test_validate_dataset_reports_missing_columns_and_bad_values():
    data = sample_data()
    data.loc[0, "Month"] = "not-a-date"
    data.loc[1, "Reported_Value"] = "not-numeric"
    data.loc[2, "Target_Value"] = -2
    data.loc[3, "Facility"] = ""
    result = validate_dataset(data)
    assert result["valid"]
    assert result["invalid_months"] == 1
    assert result["invalid_numeric_values"]["Reported_Value"] == 1
    assert result["negative_values"]["Target_Value"] == 1
    assert result["blank_dimensions"]["Facility"] == 1


def test_validate_dataset_rejects_missing_required_columns():
    result = validate_dataset(pd.DataFrame({"Facility": ["A"]}))
    assert not result["valid"]
    assert "Month" in result["missing_columns"]


def test_assessment_pipeline_and_issue_register():
    assessed = assess_dataset(sample_data())
    assert {"Calculated_Completeness", "Consistency_Flag", "Outlier_Flag", "Primary_Issue"}.issubset(assessed.columns)
    register = build_issue_register(assessed)
    assert register["Requires_Follow_Up"].any()
    assert register["Issue_Count"].max() >= 1


def test_facility_risk_is_bounded_and_volume_normalised():
    assessed = assess_dataset(sample_data())
    summary = facility_summary(assessed)
    assert summary["Risk_Score"].between(0, 100).all()
    assert set(summary["Facility"]) == {"A", "B"}
