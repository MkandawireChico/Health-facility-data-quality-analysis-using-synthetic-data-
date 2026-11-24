"""Tests for indicator-grain target attainment analytics."""
import sys
from pathlib import Path
import pandas as pd
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from target_attainment import build_target_attainment_profiles, run_target_attainment

def fixture():
    return pd.DataFrame({
        "Record_ID": ["r1", "r2", "r3", "r4", "r5", "r6"],
        "Facility_ID": ["f1", "f1", "f2", "f2", "f1", "f2"],
        "Facility": ["One", "One", "Two", "Two", "One", "Two"],
        "District": ["North", "North", "South", "South", "North", "South"],
        "Month": pd.to_datetime(["2025-01-01", "2025-02-01", "2025-01-01", "2025-02-01", "2025-01-01", "2025-02-01"]),
        "Programme": ["HIV", "HIV", "HIV", "HIV", "TB", "TB"],
        "Indicator": ["ART", "ART", "ART", "ART", "Screening", "Screening"],
        "Reported_Value": [80, 100, 60, None, 0, 15],
        "Target_Value": [100, 100, 100, 100, 0, 10],
        "Ground_Truth_Missing": [False, False, False, True, False, False],
    })

def test_attainment_is_pooled_at_matching_indicator_grain():
    result = build_target_attainment_profiles(fixture())
    district = result["district_indicator"].set_index(["District", "Programme", "Indicator"])
    assert district.loc[("North", "HIV", "ART"), "attainment_pct"] == 90
    assert district.loc[("South", "HIV", "ART"), "attainment_pct"] == 60
    assert district.loc[("North", "HIV", "ART"), "performance_band"] == "80–99.9% of target"
    assert district.loc[("South", "HIV", "ART"), "performance_band"] == "Below 80% of target"

def test_invalid_or_missing_values_do_not_enter_attainment_denominator():
    result = build_target_attainment_profiles(fixture())
    facility = result["facility_indicator"].set_index(["Facility_ID", "Programme", "Indicator"])
    row = facility.loc[("f1", "TB", "Screening")]
    assert pd.isna(row["attainment_pct"])
    assert row["valid_attainment_records"] == 0
    assert row["performance_band"] == "Insufficient valid target data"

def test_profiles_do_not_expose_ground_truth_and_keep_indicator_grain():
    result = build_target_attainment_profiles(fixture())
    for frame in result.values():
        assert not any(column.startswith("Ground_Truth_") for column in frame.columns)
    assert {"Programme", "Indicator", "Indicator_Key"}.issubset(result["district_indicator"].columns)
    assert set(result["district_indicator"]["Indicator_Key"]) == {"HIV|ART", "TB|Screening"}
    assert "Month" in result["monthly_indicator"].columns

def test_required_columns_are_validated():
    with pytest.raises(ValueError, match="Target attainment input missing"):
        build_target_attainment_profiles(fixture().drop(columns=["Target_Value"]))

def test_pipeline_writes_all_target_attainment_outputs(tmp_path):
    staged = tmp_path / "staged.csv"
    fixture().to_csv(staged, index=False)
    report = run_target_attainment(staged, tmp_path / "analytics")
    assert report["synthetic_data"] is True
    for name in report["outputs"]:
        assert (tmp_path / "analytics" / name).exists()
    assert (tmp_path / "analytics" / "target_attainment_report.json").exists()