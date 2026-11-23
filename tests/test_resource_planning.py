"""Tests for illustrative resource planning and allocation scenarios."""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from resource_planning import build_resource_planning_profiles, run_resource_planning


def facilities():
    return pd.DataFrame({
        "Facility_ID": ["F001", "F002", "F003", "F004"],
        "Facility_Name": ["One", "Two", "Three", "Four"],
        "District": ["North", "North", "South", "South"],
        "Facility_Type": ["Health Centre", "Community Hospital", "District Hospital", "Health Centre"],
        "Urban_Rural": ["Rural", "Urban", "Rural", "Peri-urban"],
        "Catchment_Population": [10000, 25000, 50000, 12000],
        "Is_Synthetic": [True] * 4,
    })


def test_scenarios_respect_pool_and_facility_gap_caps():
    result = build_resource_planning_profiles(facilities(), resource_pool=8, seed=7)
    allocations = result["scenario_allocations"]
    assert set(allocations["Scenario"]) == {"gap_priority", "equity", "equal"}
    for _, group in allocations.groupby("Scenario"):
        assert group["Allocated_Units"].sum() <= 8
        assert (group["Allocated_Units"] <= group["Baseline_Gap_Units"]).all()
        assert (group["Residual_Gap_Units"] >= 0).all()


def test_same_seed_is_reproducible_and_scenarios_are_comparable():
    a = build_resource_planning_profiles(facilities(), resource_pool=5, seed=17)
    b = build_resource_planning_profiles(facilities(), resource_pool=5, seed=17)
    pd.testing.assert_frame_equal(a["facility_capacity"], b["facility_capacity"])
    pd.testing.assert_frame_equal(a["scenario_allocations"], b["scenario_allocations"])
    assert a["scenario_summary"]["allocated_units"].nunique() == 1


def test_zero_pool_and_excess_pool_are_handled():
    zero = build_resource_planning_profiles(facilities(), resource_pool=0)
    assert zero["scenario_allocations"]["Allocated_Units"].sum() == 0
    excess = build_resource_planning_profiles(facilities(), resource_pool=10000)
    assert (excess["scenario_allocations"]["Residual_Gap_Units"] == 0).all()
    assert (excess["scenario_summary"]["unallocated_pool_units"] > 0).all()


def test_invalid_facility_dimension_and_parameters_fail_clearly():
    with pytest.raises(ValueError, match="Facility dimension missing"):
        build_resource_planning_profiles(facilities().drop(columns=["District"]))
    with pytest.raises(ValueError, match="resource_pool"):
        build_resource_planning_profiles(facilities(), resource_pool=-1)
    with pytest.raises(ValueError, match="resource_pool"):
        build_resource_planning_profiles(facilities(), resource_pool=True)
    with pytest.raises(ValueError, match="units_per_10000_population"):
        build_resource_planning_profiles(facilities(), units_per_10000_population=True)
    with pytest.raises(ValueError, match="units_per_10000_population"):
        build_resource_planning_profiles(facilities(), units_per_10000_population=float("inf"))
    with pytest.raises(ValueError, match="unique"):
        build_resource_planning_profiles(pd.concat([facilities(), facilities().iloc[[0]]]))
    with pytest.raises(ValueError, match="positive"):
        build_resource_planning_profiles(facilities(), units_per_10000_population=0)


def test_pipeline_writes_resource_outputs(tmp_path):
    path = tmp_path / "facilities.csv"
    facilities().to_csv(path, index=False)
    report = run_resource_planning(path, tmp_path / "analytics", resource_pool=6)
    assert report["synthetic_data"] is True
    for filename in report["outputs"]:
        assert (tmp_path / "analytics" / filename).exists()
    assert (tmp_path / "analytics" / "resource_planning_report.json").exists()

def test_invalid_catchment_population_is_rejected():
    for invalid_population in ["not-a-number", float("nan"), float("inf"), -1]:
        data = facilities().copy()
        data.loc[data.index[0], "Catchment_Population"] = invalid_population
        with pytest.raises(ValueError, match="Catchment_Population"):
            build_resource_planning_profiles(data)
