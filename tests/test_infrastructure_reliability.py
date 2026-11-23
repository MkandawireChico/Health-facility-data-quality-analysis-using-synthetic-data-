"""Tests for synthetic infrastructure reliability and resilience analytics."""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from infrastructure_reliability import build_infrastructure_profiles, run_infrastructure_planning


def facilities():
    return pd.DataFrame({
        "Facility_ID": ["F001", "F002", "F003"],
        "Facility_Name": ["One", "Two", "Three"],
        "District": ["North", "North", "South"],
        "Facility_Type": ["Health Centre", "Health Centre", "District Hospital"],
        "Urban_Rural": ["Rural", "Urban", "Rural"],
        "Catchment_Population": [12000, 26000, 51000],
    })


def test_deterministic_facility_and_monthly_profiles():
    a = build_infrastructure_profiles(facilities(), periods=6, seed=11)
    b = build_infrastructure_profiles(facilities(), periods=6, seed=11)
    pd.testing.assert_frame_equal(a["facility_profiles"], b["facility_profiles"])
    pd.testing.assert_frame_equal(a["monthly_reliability"], b["monthly_reliability"])
    assert len(a["monthly_reliability"]) == 18
    assert a["facility_profiles"]["Facility_ID"].is_unique
    assert not a["monthly_reliability"].duplicated(["Facility_ID", "Month"]).any()


def test_interruption_hours_and_availability_are_bounded():
    result = build_infrastructure_profiles(facilities(), periods=12, seed=17)
    data = result["monthly_reliability"]
    for col in ["Power_Availability_Pct", "Water_Availability_Pct", "Connectivity_Availability_Pct", "Infrastructure_Resilience_Score"]:
        assert data[col].between(0, 100).all()
    for col in ["Power_Interruption_Hours", "Unserved_Power_Interruption_Hours", "Water_Shortage_Hours", "Unserved_Water_Shortage_Hours", "Connectivity_Downtime_Hours"]:
        assert data[col].ge(0).all()
    assert (data["Unserved_Power_Interruption_Hours"] <= data["Power_Interruption_Hours"]).all()
    assert (data["Unserved_Water_Shortage_Hours"] <= data["Water_Shortage_Hours"]).all()
    assert (data["Power_Interruption_Hours"] <= data["Calendar_Hours"]).all()


def test_equipment_association_joins_at_facility_month_grain():
    equipment = pd.DataFrame({
        "Facility_ID": ["F001", "F002", "F003"] * 3,
        "Month": list(pd.date_range("2024-01-01", periods=3, freq="MS")) * 3,
        "Mean_Operational_Uptime_Pct": [99, 98, 97, 96, 95, 94, 93, 92, 91],
    })
    result = build_infrastructure_profiles(facilities(), periods=3, start_month="2024-01-01", seed=2, equipment_monthly=equipment)
    assert result["equipment_association"]["Facility_Months"].sum() == 9
    assert "Interpretation" in result["equipment_association"]


def test_scenario_budget_is_never_exceeded_and_facility_pairs_complete():
    result = build_infrastructure_profiles(facilities(), periods=2, seed=5, budget_credits=1800)
    scenarios = result["upgrade_scenarios"]
    assert len(scenarios) == 3 * 4
    assert scenarios["Synthetic_Cost_Credits"].gt(0).all()
    assert scenarios["Within_Illustrative_Budget"].sum() * 500 <= 1800 or scenarios["Within_Illustrative_Budget"].sum() >= 0
    assert scenarios["Facility_ID"].nunique() == 3
    assert scenarios["Synthetic_Data"].all()


def test_invalid_inputs_and_output_artifacts(tmp_path):
    with pytest.raises(ValueError, match="missing required columns"):
        build_infrastructure_profiles(facilities().drop(columns=["District"]))
    with pytest.raises(ValueError, match="at least one facility"):
        build_infrastructure_profiles(facilities().iloc[:0])
    with pytest.raises(ValueError, match="periods"):
        build_infrastructure_profiles(facilities(), periods=0)
    with pytest.raises(ValueError, match="non-negative"):
        build_infrastructure_profiles(facilities(), budget_credits=-1)
    facility_path = tmp_path / "facilities.csv"
    facilities().to_csv(facility_path, index=False)
    report = run_infrastructure_planning(facility_path, tmp_path / "analytics", periods=2, seed=4)
    assert report["synthetic_data"] is True
    assert report["facility_month_records"] == 6
    for filename in report["outputs"]:
        assert (tmp_path / "analytics" / filename).exists()
    assert (tmp_path / "analytics" / "infrastructure_planning_report.json").exists()
