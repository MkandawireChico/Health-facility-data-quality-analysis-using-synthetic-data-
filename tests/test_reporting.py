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
    data["Month"] = data["Month"].astype(object)
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



def test_source_consistency_requires_at_least_two_available_sources():
    from data_quality import DataQualityAssessor

    data = pd.DataFrame({
        "Paper_Value": [100, np.nan, np.nan],
        "EMR_Value": [105, 105, np.nan],
        "DHIS2_Value": [102, np.nan, np.nan],
    })
    result = DataQualityAssessor(data).assess_source_consistency()
    assert result["Consistency_Flag"].tolist() == [
        "Consistent", "Unknown Sources", "Unknown Sources"
    ]
    assert result["Consistency_Flag_Baseline"].tolist() == [
        "Consistent", "Unknown Sources", "Unknown Sources"
    ]


def test_real_submission_and_deadline_dates_override_simulated_timeliness():
    data = sample_data()
    data["Submission_Date"] = pd.to_datetime([
        "2025-01-10", "2025-02-20", "2025-03-10",
        "2025-04-10", None, "2025-06-10",
    ])
    data["Deadline_Date"] = pd.to_datetime(["2025-01-15"] * 6)
    assessed = assess_dataset(data)
    assert assessed.loc[0, "Calculated_Timeliness"] == "On Time"
    assert assessed.loc[1, "Calculated_Timeliness"] == "Late"
    assert assessed.loc[4, "Calculated_Timeliness"] == "Unknown"



def test_facility_consistency_rate_excludes_unknown_source_records():
    data = sample_data()
    data.loc[0, ["Paper_Value", "DHIS2_Value"]] = np.nan
    assessed = assess_dataset(data)
    summary = facility_summary(assessed).set_index("Facility")
    facility_a = assessed[assessed["Facility"] == "A"]
    known = facility_a["Consistency_Flag"].isin(["Consistent", "Review Required", "Inconsistent"])
    expected = facility_a.loc[known, "Consistency_Flag"].eq("Consistent").mean()
    assert summary.loc["A", "Consistency_Rate"] == expected



def test_duplicate_reporting_keys_are_reported_not_removed():
    data = sample_data()
    duplicated = pd.concat([data, data.iloc[[0]]], ignore_index=True)
    result = validate_dataset(duplicated)
    assert result["duplicate_rows"] == 2
    assert result["row_count"] == len(data) + 1



def test_insufficient_source_evidence_is_included_in_follow_up_register():
    data = sample_data()
    data.loc[0, ["Paper_Value", "DHIS2_Value"]] = np.nan
    assessed = assess_dataset(data)
    register = build_issue_register(assessed)
    assert bool(register.loc[0, "Issue_Insufficient_Sources"])
    assert register.loc[0, "Primary_Issue"] == "Insufficient Source Data"
    assert bool(register.loc[0, "Requires_Follow_Up"])
