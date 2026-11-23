from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from cold_chain_planning import build_cold_chain_profiles, run_cold_chain_planning


def facility_dimension():
    return pd.DataFrame({
        "Facility_ID": ["F001", "F002", "F003"],
        "Facility_Name": ["One", "Two", "Three"],
        "District": ["North", "North", "South"],
        "Facility_Type": ["Health Centre", "Community Hospital", "District Hospital"],
        "Urban_Rural": ["Rural", "Urban", "Rural"],
        "Catchment_Population": [12000, 26000, 51000],
    })


def test_monitoring_and_batch_grains_are_complete_and_unique():
    result = build_cold_chain_profiles(facility_dimension(), periods=4, seed=9)
    temperature = result["temperature_monitoring"]
    risk = result["expiry_risk_summary"]
    ledger = result["batch_ledger"]

    assert len(temperature) == 3 * 4
    assert not temperature.duplicated(["Facility_ID", "Month"]).any()
    assert len(risk) == 3 * 4 * 4
    assert not risk.duplicated(["Facility_ID", "Commodity_ID", "Month"]).any()
    assert not ledger.duplicated(["Facility_ID", "Commodity_ID", "Batch_ID", "Month"]).any()
    assert temperature["Synthetic_Data"].all()
    assert ledger["Synthetic_Data"].all()
    assert risk["Synthetic_Data"].all()
    assert set(temperature["Temperature_Data_Status"]).issubset({"Sufficient", "Incomplete", "Missing"})


def test_batch_stock_equation_and_expiry_flags():
    result = build_cold_chain_profiles(facility_dimension(), periods=8, seed=13)
    ledger = result["batch_ledger"]
    assert (
        ledger["Opening_Stock_Units"] + ledger["Receipts_Units"]
        - ledger["Fulfilled_Consumption_Units"] - ledger["Expired_Units"]
        == ledger["Closing_Stock_Units"]
    ).all()
    assert (ledger["Fulfilled_Consumption_Units"] >= 0).all()
    assert (ledger["Expired_Units"] >= 0).all()
    assert (ledger["Closing_Stock_Units"] >= 0).all()
    assert (ledger["Near_Expiry_30_Days"] <= ledger["Near_Expiry_60_Days"]).all()
    assert (ledger["Near_Expiry_60_Days"] <= ledger["Near_Expiry_90_Days"]).all()
    assert ledger.loc[ledger["Closing_Stock_Units"].eq(0), [
        "Near_Expiry_30_Days", "Near_Expiry_60_Days", "Near_Expiry_90_Days"
    ]].eq(False).all().all()


def test_fefo_consumption_prioritises_earliest_expiry():
    result = build_cold_chain_profiles(facility_dimension(), periods=12, seed=22)
    ledger = result["batch_ledger"]
    for _, group in ledger.groupby(["Facility_ID", "Commodity_ID", "Month"]):
        available = group.loc[
            pd.to_datetime(group["Expiry_Date"]) >= pd.to_datetime(group["Month"]),
            ["Expiry_Date", "Fulfilled_Consumption_Units", "Opening_Stock_Units", "Receipts_Units", "Expired_Units"],
        ].copy()
        available = available.sort_values("Expiry_Date")
        for index in range(1, len(available)):
            earlier = available.iloc[:index]
            later = available.iloc[index:]
            if later["Fulfilled_Consumption_Units"].gt(0).any():
                earlier_available = (
                    earlier["Opening_Stock_Units"] + earlier["Receipts_Units"]
                    - earlier["Fulfilled_Consumption_Units"] - earlier["Expired_Units"]
                )
                assert earlier_available.eq(0).all()


def test_temperature_thresholds_and_reproducibility():
    a = build_cold_chain_profiles(facility_dimension(), periods=5, seed=17)
    b = build_cold_chain_profiles(facility_dimension(), periods=5, seed=17)
    pd.testing.assert_frame_equal(a["temperature_monitoring"], b["temperature_monitoring"])
    pd.testing.assert_frame_equal(a["batch_ledger"], b["batch_ledger"])
    custom = build_cold_chain_profiles(
        facility_dimension(), periods=2, seed=17, temperature_min_c=3.0, temperature_max_c=7.0
    )
    assert custom["assumptions"]["temperature_min_c_assumption"] == 3.0
    assert custom["assumptions"]["temperature_max_c_assumption"] == 7.0
    assert custom["temperature_monitoring"]["Excursion_Days"].sum() >= a["temperature_monitoring"]["Excursion_Days"].sum()
    assert a["expiry_risk_summary"]["Risk_Band"].isin(["Low", "Medium", "High", "Data Gap"]).all()


def test_invalid_inputs_fail_clearly():
    with pytest.raises(ValueError, match="Facility dimension missing"):
        build_cold_chain_profiles(facility_dimension().drop(columns=["District"]))
    with pytest.raises(ValueError, match="at least one facility"):
        build_cold_chain_profiles(facility_dimension().iloc[0:0])
    with pytest.raises(ValueError, match="periods"):
        build_cold_chain_profiles(facility_dimension(), periods=0)
    with pytest.raises(ValueError, match="Temperature bounds"):
        build_cold_chain_profiles(facility_dimension(), temperature_min_c=8, temperature_max_c=2)
    with pytest.raises(ValueError, match="unique"):
        build_cold_chain_profiles(pd.concat([facility_dimension(), facility_dimension().iloc[[0]]]))


def test_pipeline_writes_all_outputs(tmp_path: Path):
    path = tmp_path / "facilities.csv"
    facility_dimension().to_csv(path, index=False)
    report = run_cold_chain_planning(path, tmp_path / "analytics", periods=3, seed=8)
    assert report["synthetic_data"] is True
    assert report["temperature_monitoring_records"] == 3 * 3
    assert report["risk_summary_records"] == 3 * 3 * 4
    assert report["latest_high_risk_facility_commodity_pairs"] >= 0
    for filename in report["outputs"]:
        assert (tmp_path / "analytics" / filename).exists()
    assert (tmp_path / "analytics" / "cold_chain_planning_report.json").exists()
