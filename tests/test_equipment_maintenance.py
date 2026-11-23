"""Tests for synthetic equipment maintenance and uptime intelligence."""
from pathlib import Path
import sys

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from equipment_maintenance import build_equipment_maintenance_profiles, run_equipment_maintenance


def facilities():
    return pd.DataFrame({
        "Facility_ID": ["F001", "F002", "F003"],
        "Facility_Name": ["One", "Two", "Three"],
        "District": ["North", "North", "South"],
        "Facility_Type": ["Health Centre", "Health Centre", "District Hospital"],
        "Urban_Rural": ["Rural", "Urban", "Rural"],
        "Catchment_Population": [12000, 26000, 51000],
    })


def test_asset_register_and_monthly_grains_are_unique():
    result = build_equipment_maintenance_profiles(facilities(), periods=6, seed=9)
    assets = result["asset_register"]
    monthly = result["asset_monthly_performance"]
    assert len(assets) == 4 * 2 + 7
    assert assets["Asset_ID"].is_unique
    assert len(monthly) == len(assets) * 6
    assert not monthly.duplicated(["Asset_ID", "Month"]).any()
    assert assets["Synthetic_Data"].all()
    assert monthly["Synthetic_Data"].all()
    assert result["latest_asset_status"]["Asset_ID"].is_unique


def test_uptime_pm_and_downtime_relationships_are_valid():
    result = build_equipment_maintenance_profiles(facilities(), periods=12, seed=13)
    monthly = result["asset_monthly_performance"]
    assert monthly["Service_Availability_Pct"].between(0, 100).all()
    assert monthly["Operational_Uptime_Pct"].between(0, 100).all()
    assert (monthly["Operational_Uptime_Pct"] <= monthly["Service_Availability_Pct"]).all()
    assert (
        monthly["Total_Downtime_Hours"]
        == monthly["Unplanned_Downtime_Hours"] + monthly["Planned_Maintenance_Downtime_Hours"]
    ).all()
    assert (monthly["Total_Downtime_Hours"] <= monthly["Calendar_Hours"]).all()
    assert (monthly["Preventive_Maintenance_Completed"] <= monthly["Preventive_Maintenance_Due"]).all()
    assert (
        monthly["Preventive_Maintenance_Overdue"]
        == (monthly["Preventive_Maintenance_Due"] & ~monthly["Preventive_Maintenance_Completed"])
    ).all()
    assert monthly["Equipment_Risk_Score"].between(0, 100).all()


def test_work_orders_reconcile_to_monthly_costs_and_event_counts():
    result = build_equipment_maintenance_profiles(facilities(), periods=24, seed=22)
    work = result["maintenance_work_orders"]
    monthly = result["asset_monthly_performance"]
    assert work["Work_Order_ID"].is_unique
    assert work["Synthetic_Data"].all()
    assert set(work["Work_Order_Type"]).issubset({"Preventive Maintenance", "Corrective Maintenance"})
    costs = work.groupby(["Asset_ID", "Month"])["Cost_Credits"].sum()
    expected = monthly.set_index(["Asset_ID", "Month"])["Maintenance_Cost_Credits"]
    pd.testing.assert_series_equal(costs.reindex(expected.index, fill_value=0), expected, check_names=False)
    corrective = work.loc[work["Work_Order_Type"].eq("Corrective Maintenance")]
    assert len(corrective) == int(monthly["Breakdown_Count"].sum())


def test_facility_month_summary_aggregates_asset_metrics():
    result = build_equipment_maintenance_profiles(facilities(), periods=4, seed=7)
    summary = result["facility_monthly_summary"]
    monthly = result["asset_monthly_performance"]
    assert len(summary) == 3 * 4
    assert not summary.duplicated(["Facility_ID", "Month"]).any()
    assert summary["Active_Assets"].gt(0).all()
    assert summary["Breakdown_Events"].sum() == monthly["Breakdown_Count"].sum()
    assert summary["Maintenance_Cost_Credits"].sum() == monthly["Maintenance_Cost_Credits"].sum()
    assert summary["PM_Completion_Pct"].dropna().between(0, 100).all()


def test_reproducibility_and_invalid_inputs():
    a = build_equipment_maintenance_profiles(facilities(), periods=5, seed=17)
    b = build_equipment_maintenance_profiles(facilities(), periods=5, seed=17)
    pd.testing.assert_frame_equal(a["asset_register"], b["asset_register"])
    pd.testing.assert_frame_equal(a["asset_monthly_performance"], b["asset_monthly_performance"])
    pd.testing.assert_frame_equal(a["maintenance_work_orders"], b["maintenance_work_orders"])
    with pytest.raises(ValueError, match="missing required columns"):
        build_equipment_maintenance_profiles(facilities().drop(columns=["District"]))
    with pytest.raises(ValueError, match="at least one facility"):
        build_equipment_maintenance_profiles(facilities().iloc[0:0])
    with pytest.raises(ValueError, match="periods"):
        build_equipment_maintenance_profiles(facilities(), periods=0)
    with pytest.raises(ValueError, match="unique"):
        build_equipment_maintenance_profiles(pd.concat([facilities(), facilities().iloc[[0]]]))


def test_pipeline_writes_complete_outputs(tmp_path: Path):
    facility_path = tmp_path / "facilities.csv"
    facilities().to_csv(facility_path, index=False)
    report = run_equipment_maintenance(
        facility_path, tmp_path / "analytics", periods=3, seed=8
    )
    assert report["synthetic_data"] is True
    assert report["facilities"] == 3
    assert report["assets"] == 17
    assert report["asset_month_records"] == 51
    assert report["latest_high_risk_assets"] >= 0
    for filename in report["outputs"]:
        assert (tmp_path / "analytics" / filename).exists()
    assert (tmp_path / "analytics" / "equipment_maintenance_report.json").exists()
