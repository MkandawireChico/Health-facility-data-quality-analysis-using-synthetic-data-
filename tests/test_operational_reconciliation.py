"""Unit tests for operational planning ledger reconciliation."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd
import pytest

from operational_reconciliation import (
    validate_resource_allocations, validate_stock_ledger,
    validate_cold_chain_ledger, validate_equipment_ledger,
    validate_infrastructure_ledger, validate_workforce_ledger,
)


def test_resource_allocation_reconciles_gaps_coverage_and_scenario_pools():
    capacity = pd.DataFrame([
        {"Facility_ID": "F1", "Illustrative_Requirement_Units": 10,
         "Synthetic_Available_Units": 6, "Baseline_Gap_Units": 4},
    ])
    scenarios = pd.DataFrame([
        {"Facility_ID": "F1", "Scenario": scenario, "Allocated_Units": 2,
         "Residual_Gap_Units": 2, "Post_Allocation_Coverage_Pct": 80}
        for scenario in ["gap_priority", "equity", "equal"]
    ])
    assert validate_resource_allocations(capacity, scenarios, 2)["scenario_rows"] == 3


def test_resource_allocation_rejects_allocation_beyond_facility_gap():
    capacity = pd.DataFrame([{"Facility_ID": "F1",
        "Illustrative_Requirement_Units": 10, "Synthetic_Available_Units": 6,
        "Baseline_Gap_Units": 4}])
    scenarios = pd.DataFrame([
        {"Facility_ID": "F1", "Scenario": scenario, "Allocated_Units": 5,
         "Residual_Gap_Units": 0, "Post_Allocation_Coverage_Pct": 110}
        for scenario in ["gap_priority", "equity", "equal"]
    ])
    with pytest.raises(RuntimeError, match="beyond facility gaps"):
        validate_resource_allocations(capacity, scenarios, 10)


def test_stock_ledger_reconciles_movements_and_rejects_broken_balance():
    stock = pd.DataFrame([{
        "Facility_ID": "F1", "Commodity_ID": "C1", "Month": "2024-01-01",
        "Opening_Stock_Units": 5, "Receipts_Units": 4, "Demand_Units": 7,
        "Fulfilled_Consumption_Units": 7, "Unmet_Demand_Units": 0,
        "Closing_Stock_Units": 2, "Stockout_Days": 0, "Stockout_Flag": False,
    }])
    assert validate_stock_ledger(stock)["ledger_rows"] == 1
    stock.loc[0, "Closing_Stock_Units"] = 3
    with pytest.raises(RuntimeError, match="stock balance"):
        validate_stock_ledger(stock)


def _cold_chain_fixtures():
    batch = pd.DataFrame([{
        "Batch_ID": "B1", "Facility_ID": "F1", "Commodity_ID": "C1",
        "Month": "2024-01-01", "Opening_Stock_Units": 0, "Receipts_Units": 10,
        "Fulfilled_Consumption_Units": 8, "Expired_Units": 0,
        "Closing_Stock_Units": 2, "Near_Expiry_90_Days": True,
    }])
    risk = pd.DataFrame([{
        "Facility_ID": "F1", "Commodity_ID": "C1", "Month": "2024-01-01",
        "Expired_Units": 0, "Closing_Stock_Units": 2,
        "Near_Expiry_90_Day_Units": 2, "Demand_Units": 10,
        "Fulfilled_Consumption_Units": 8, "Unmet_Demand_Units": 2,
    }])
    return batch, risk


def test_cold_chain_batch_ledger_reconciles_to_risk_summary():
    batch, risk = _cold_chain_fixtures()
    assert validate_cold_chain_ledger(batch, risk)["batch_month_rows"] == 1
    risk.loc[0, "Closing_Stock_Units"] = 3
    with pytest.raises(RuntimeError, match="Closing_Stock_Units summary"):
        validate_cold_chain_ledger(batch, risk)


def test_equipment_downtime_and_cost_reconcile_to_work_orders():
    performance = pd.DataFrame([{
        "Asset_ID": "A1", "Month": "2024-01-01", "Calendar_Hours": 744,
        "Unplanned_Downtime_Hours": 4.0, "Planned_Maintenance_Downtime_Hours": 2.0,
        "Total_Downtime_Hours": 6.0, "Service_Availability_Pct": 99.46,
        "Operational_Uptime_Pct": 99.19, "Maintenance_Cost_Credits": 40,
        "Breakdown_Count": 1,
    }])
    work_orders = pd.DataFrame([
        {"Work_Order_ID": "W1", "Asset_ID": "A1", "Month": "2024-01-01",
         "Downtime_Hours": 2.0, "Cost_Credits": 10},
        {"Work_Order_ID": "W2", "Asset_ID": "A1", "Month": "2024-01-01",
         "Downtime_Hours": 4.0, "Cost_Credits": 30},
    ])
    assert validate_equipment_ledger(performance, work_orders)["work_order_rows"] == 2
    work_orders.loc[0, "Downtime_Hours"] = 1
    with pytest.raises(RuntimeError, match="downtime versus maintenance work orders"):
        validate_equipment_ledger(performance, work_orders)


def test_infrastructure_hours_availability_and_score_reconcile():
    profiles = pd.DataFrame([{"Facility_ID": "F1",
        "Illustrative_Backup_Power_Hours": 9.0}])
    monthly = pd.DataFrame([{
        "Facility_ID": "F1", "Month": "2024-01-01", "Calendar_Hours": 744,
        "Power_Interruption_Hours": 10, "Backup_Power_Hours_Provided": 4,
        "Unserved_Power_Interruption_Hours": 6,
        "Water_Shortage_Hours": 8, "Water_Buffered_Hours": 3,
        "Unserved_Water_Shortage_Hours": 5, "Connectivity_Downtime_Hours": 7,
        "Power_Availability_Pct": 99.19, "Water_Availability_Pct": 99.33,
        "Connectivity_Availability_Pct": 99.06,
        "Infrastructure_Resilience_Score": 94.29,
    }])
    assert validate_infrastructure_ledger(monthly, profiles)["facility_month_rows"] == 1
    monthly.loc[0, "Unserved_Power_Interruption_Hours"] = 7
    with pytest.raises(RuntimeError, match="power interruption balance"):
        validate_infrastructure_ledger(monthly, profiles)


def test_workforce_counts_and_rates_reconcile():
    monthly = pd.DataFrame([{
        "Facility_ID": "F1", "Month": "2024-01-01",
        "Illustrative_Establishment": 10, "Filled_Positions": 8,
        "Vacant_Positions": 2, "Absent_Positions": 1,
        "Available_On_Duty_Positions": 7, "Workforce_Coverage_Pct": 80,
        "Absence_Rate_Pct": 12.5, "Synthetic_Workload_Demand_Proxy": 5,
        "Weighted_Available_Capacity": 10,
        "Workforce_Pressure_Index": 50,
    }])
    assert validate_workforce_ledger(monthly)["facility_month_rows"] == 1
    monthly.loc[0, "Vacant_Positions"] = 1
    with pytest.raises(RuntimeError, match="vacancy count"):
        validate_workforce_ledger(monthly)



def test_cold_chain_zero_stock_month_can_have_no_batch_rows():
    batch = pd.DataFrame(columns=[
        "Batch_ID", "Facility_ID", "Commodity_ID", "Month",
        "Opening_Stock_Units", "Receipts_Units", "Fulfilled_Consumption_Units",
        "Expired_Units", "Closing_Stock_Units", "Near_Expiry_90_Days",
    ])
    risk = pd.DataFrame([{
        "Facility_ID": "F1", "Commodity_ID": "C1", "Month": "2024-01-01",
        "Expired_Units": 0, "Closing_Stock_Units": 0,
        "Near_Expiry_90_Day_Units": 0, "Demand_Units": 4,
        "Fulfilled_Consumption_Units": 0, "Unmet_Demand_Units": 4,
    }])
    assert validate_cold_chain_ledger(batch, risk)["batch_month_rows"] == 0



def test_cold_chain_near_expiry_reconciles_units_not_batch_flag_count():
    batch = pd.DataFrame([
        {"Batch_ID": "B1", "Facility_ID": "F1", "Commodity_ID": "C1",
         "Month": "2024-01-01", "Opening_Stock_Units": 0, "Receipts_Units": 5,
         "Fulfilled_Consumption_Units": 0, "Expired_Units": 0,
         "Closing_Stock_Units": 5, "Near_Expiry_90_Days": True},
        {"Batch_ID": "B2", "Facility_ID": "F1", "Commodity_ID": "C1",
         "Month": "2024-01-01", "Opening_Stock_Units": 0, "Receipts_Units": 4,
         "Fulfilled_Consumption_Units": 0, "Expired_Units": 0,
         "Closing_Stock_Units": 4, "Near_Expiry_90_Days": False},
    ])
    risk = pd.DataFrame([{
        "Facility_ID": "F1", "Commodity_ID": "C1", "Month": "2024-01-01",
        "Expired_Units": 0, "Closing_Stock_Units": 9,
        "Near_Expiry_90_Day_Units": 5, "Demand_Units": 0,
        "Fulfilled_Consumption_Units": 0, "Unmet_Demand_Units": 0,
    }])
    assert validate_cold_chain_ledger(batch, risk)["batch_month_rows"] == 2
