"""Tests for synthetic commodity stockout and replenishment planning."""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from supply_chain_planning import build_supply_chain_profiles, run_supply_chain_planning


def facility_dimension():
    return pd.DataFrame({
        "Facility_ID": ["F001", "F002", "F003"],
        "Facility_Name": ["One", "Two", "Three"],
        "District": ["North", "North", "South"],
        "Facility_Type": ["Health Centre", "Community Hospital", "District Hospital"],
        "Urban_Rural": ["Rural", "Urban", "Rural"],
        "Catchment_Population": [12000, 26000, 51000],
    })


def test_ledger_has_complete_grain_and_stock_balance():
    result = build_supply_chain_profiles(facility_dimension(), periods=4, seed=9)
    ledger = result["inventory_ledger"]
    assert len(ledger) == 3 * 4 * 8
    assert not ledger.duplicated(["Facility_ID", "Commodity_ID", "Month"]).any()
    assert (
        ledger["Opening_Stock_Units"] + ledger["Receipts_Units"]
        - ledger["Fulfilled_Consumption_Units"] == ledger["Closing_Stock_Units"]
    ).all()
    assert (ledger["Fulfilled_Consumption_Units"] <= ledger["Demand_Units"]).all()
    assert (ledger["Unmet_Demand_Units"] >= 0).all()
    assert ledger["Synthetic_Data"].all()


def test_budget_constraint_and_replenishment_request_caps():
    result = build_supply_chain_profiles(facility_dimension(), periods=5, seed=3, budget_credits=100)
    plan = result["replenishment_plan"]
    summary = result["scenario_summary"].iloc[0]
    assert plan["Allocated_Cost_Credits"].sum() <= 100
    assert (plan["Allocated_Replenishment_Units"] <= plan["Requested_Replenishment_Units"]).all()
    assert (plan["Unfunded_Replenishment_Units"] >= 0).all()
    assert summary["allocated_cost_credits"] <= summary["budget_credits"]
    assert summary["requested_replenishment_units"] >= summary["allocated_replenishment_units"]


def test_reproducible_and_zero_budget():
    a = build_supply_chain_profiles(facility_dimension(), periods=3, seed=17, budget_credits=0)
    b = build_supply_chain_profiles(facility_dimension(), periods=3, seed=17, budget_credits=0)
    pd.testing.assert_frame_equal(a["inventory_ledger"], b["inventory_ledger"])
    pd.testing.assert_frame_equal(a["replenishment_plan"], b["replenishment_plan"])
    assert a["replenishment_plan"]["Allocated_Replenishment_Units"].sum() == 0


def test_invalid_inputs_fail_clearly():
    with pytest.raises(ValueError, match="Facility dimension missing"):
        build_supply_chain_profiles(facility_dimension().drop(columns=["District"]))
    with pytest.raises(ValueError, match="periods"):
        build_supply_chain_profiles(facility_dimension(), periods=0)
    with pytest.raises(ValueError, match="budget_credits"):
        build_supply_chain_profiles(facility_dimension(), budget_credits=-1)
    with pytest.raises(ValueError, match="unique"):
        build_supply_chain_profiles(pd.concat([facility_dimension(), facility_dimension().iloc[[0]]]))


def test_pipeline_writes_all_outputs(tmp_path):
    path = tmp_path / "facilities.csv"
    facility_dimension().to_csv(path, index=False)
    report = run_supply_chain_planning(path, tmp_path / "analytics", periods=2, budget_credits=200)
    assert report["synthetic_data"] is True
    assert report["inventory_records"] == 3 * 2 * 8
    for filename in report["outputs"]:
        assert (tmp_path / "analytics" / filename).exists()
    assert (tmp_path / "analytics" / "supply_chain_planning_report.json").exists()
