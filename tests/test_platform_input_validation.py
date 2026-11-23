"""Tests for expanded dashboard upload validation."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from platform_input_validation import validate_platform_extract


def valid_extract():
    return pd.DataFrame({
        "Facility_ID": ["F1", "F1"],
        "Facility": ["Facility One", "Facility One"],
        "District": ["Lilongwe", "Lilongwe"],
        "Facility_Type": ["Health Centre", "Health Centre"],
        "Urban_Rural": ["Urban", "Urban"],
        "Catchment_Population": [12000, 12000],
        "Month": ["2025-01-01", "2025-02-01"],
        "Programme": ["HIV", "HIV"],
        "Indicator": ["ART", "ART"],
        "Reported_Value": [100, 110],
        "Target_Value": [120, 120],
        "Quality_Missing_Reported_Value": [False, False],
        "Quality_Source_Discrepancy": [False, False],
        "Quality_Late_Submission": [False, False],
    })


def test_valid_staged_extract_passes():
    assert validate_platform_extract(valid_extract()) == []


def test_empty_extract_is_rejected():
    assert "no reporting records" in validate_platform_extract(valid_extract().iloc[0:0])[0]


def test_missing_resource_planning_metadata_is_reported():
    data = valid_extract().drop(columns=["Catchment_Population", "Facility_Type"])
    errors = validate_platform_extract(data)
    assert len(errors) == 1
    assert "Catchment_Population" in errors[0]
    assert "Facility_Type" in errors[0]


def test_blank_facility_metadata_is_reported():
    data = valid_extract()
    data.loc[0, "Facility_Type"] = " "
    errors = validate_platform_extract(data)
    assert any("Facility_Type" in error for error in errors)


def test_non_numeric_infinite_and_negative_catchment_values_are_rejected():
    for invalid in ["unknown", float("inf"), -1]:
        data = valid_extract()
        data.loc[0, "Catchment_Population"] = invalid
        errors = validate_platform_extract(data)
        assert any("finite, non-negative numeric" in error for error in errors)
