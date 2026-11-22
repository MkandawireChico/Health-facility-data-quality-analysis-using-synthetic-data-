"""Tests for the staging and data quality pipeline."""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from etl_pipeline import run_pipeline, stage_reporting_data
from scale_data_generator import ScaledHealthDataGenerator


def sample_tables():
    generator = ScaledHealthDataGenerator(
        seed=19, facility_count=4, periods=2,
        districts=("North", "Central"),
        programmes={"HIV": {"ART clients": (50, 100), "New starts": (2, 20)}},
    )
    fact, facilities, _ = generator.generate({
        "missing": 0, "source_discrepancy": 0, "outlier": 0, "late": 0,
    })
    return fact, facilities


def test_staging_preserves_valid_grain_and_joins_authoritative_facility_dimension():
    fact, facilities = sample_tables()
    staged, quarantine, report = stage_reporting_data(fact, facilities)
    assert len(staged) == len(fact)
    assert quarantine.empty
    assert staged["Facility_Name"].notna().all()
    assert staged["District"].notna().all()
    assert staged["Month"].dt.day.eq(1).all()
    assert report["staged_rows"] == len(fact)
    assert report["quarantined_rows"] == 0


def test_structural_failures_are_quarantined_with_reasons():
    fact, facilities = sample_tables()
    fact.loc[0, "Facility_ID"] = "UNKNOWN-FACILITY"
    fact["Month"] = fact["Month"].astype("object")
    fact.loc[1, "Month"] = "not-a-date"
    fact.loc[2, "Programme"] = " "
    staged, quarantine, report = stage_reporting_data(fact, facilities)
    assert len(quarantine) == 3
    assert len(staged) == len(fact) - 3
    assert quarantine["Structural_unknown_facility_id"].any()
    assert quarantine["Structural_invalid_reporting_month"].any()
    assert quarantine["Structural_blank_programme"].any()
    assert report["quarantined_rows"] == 3


def test_duplicate_natural_keys_quarantine_every_duplicate():
    fact, facilities = sample_tables()
    fact.loc[1, ["Facility_ID", "Month", "Programme", "Indicator"]] = fact.loc[
        0, ["Facility_ID", "Month", "Programme", "Indicator"]
    ].values
    _, quarantine, _ = stage_reporting_data(fact, facilities)
    assert len(quarantine) == 2
    assert quarantine["Structural_duplicate_natural_key"].all()


def test_analytical_quality_defects_are_flagged_not_quarantined():
    fact, facilities = sample_tables()
    fact.loc[0, "Reported_Value"] = None
    fact.loc[1, "Reported_Value"] = -9
    fact.loc[2, "Data_Source"] = "Unrecognised Source"
    fact.loc[3, "Submission_Date"] = pd.Timestamp("2025-03-30")
    fact.loc[3, "Deadline_Date"] = pd.Timestamp("2025-03-20")
    staged, quarantine, report = stage_reporting_data(fact, facilities)
    assert quarantine.empty
    assert len(staged) == len(fact)
    assert staged["Quality_Missing_Reported_Value"].sum() == 1
    assert staged["Quality_Negative_Value_Count"].sum() == 1
    assert staged["Quality_Invalid_Source_Label"].sum() == 1
    assert staged["Quality_Late_Submission"].sum() == 1
    assert report["quality_issue_rows"] >= 4


def test_required_schema_and_duplicate_facility_keys_are_enforced():
    fact, facilities = sample_tables()
    with pytest.raises(ValueError, match="Fact table missing"):
        stage_reporting_data(fact.drop(columns=["Record_ID"]), facilities)
    duplicated = pd.concat([facilities, facilities.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="Facility_ID must be unique"):
        stage_reporting_data(fact, duplicated)


def test_pipeline_persists_staged_quarantine_and_quality_report(tmp_path):
    fact, facilities = sample_tables()
    fact_path, facility_path = tmp_path / "fact.csv", tmp_path / "facilities.csv"
    fact.to_csv(fact_path, index=False)
    facilities.to_csv(facility_path, index=False)
    report = run_pipeline(fact_path, facility_path, tmp_path / "output")
    assert report["staged_rows"] == len(fact)
    assert (tmp_path / "output/facility_reporting_staged.csv").exists()
    assert (tmp_path / "output/facility_reporting_quarantine.csv").exists()
    assert (tmp_path / "output/staging_quality_report.json").exists()
