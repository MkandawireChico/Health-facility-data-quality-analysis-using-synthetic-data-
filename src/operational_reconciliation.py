"""Cross-domain reconciliation checks for synthetic operational planning outputs."""
from __future__ import annotations

import numpy as np
import pandas as pd


def _numeric(frame: pd.DataFrame, columns: list[str], label: str) -> pd.DataFrame:
    out = frame.copy()
    missing = sorted(set(columns) - set(out.columns))
    if missing:
        raise RuntimeError(f"{label} is missing reconciliation columns: {missing}")
    for column in columns:
        values = pd.to_numeric(out[column], errors="coerce")
        if values.isna().any() or not np.isfinite(values.to_numpy(dtype=float)).all():
            raise RuntimeError(f"{label} contains invalid numeric values in {column}")
        out[column] = values
    return out


def _close(left, right, label: str, tolerance: float = 0.03) -> None:
    if not np.allclose(np.asarray(left, dtype=float), np.asarray(right, dtype=float),
                       rtol=0, atol=tolerance):
        raise RuntimeError(f"{label} does not reconcile")


def validate_resource_allocations(capacity: pd.DataFrame, scenarios: pd.DataFrame,
                                  resource_pool: int = 120) -> dict[str, int]:
    base_cols = ["Facility_ID", "Illustrative_Requirement_Units",
                 "Synthetic_Available_Units", "Baseline_Gap_Units"]
    base = _numeric(capacity, base_cols, "Resource capacity")
    if base.empty or base["Facility_ID"].isna().any() or base["Facility_ID"].duplicated().any():
        raise RuntimeError("Resource capacity facility keys must be populated and unique")
    if (base[base_cols[1:]] < 0).any().any():
        raise RuntimeError("Resource capacity units cannot be negative")
    expected_gap = (base["Illustrative_Requirement_Units"] -
                    base["Synthetic_Available_Units"]).clip(lower=0)
    _close(base["Baseline_Gap_Units"], expected_gap, "Resource baseline gap", 0)
    cols = ["Facility_ID", "Scenario", "Allocated_Units", "Residual_Gap_Units",
            "Post_Allocation_Coverage_Pct"]
    plan = _numeric(scenarios, cols, "Resource allocation scenarios")
    if plan[["Facility_ID", "Scenario"]].isna().any().any() or plan.duplicated(["Facility_ID", "Scenario"]).any():
        raise RuntimeError("Resource allocation facility-scenario keys must be unique and populated")
    expected_scenarios = {"gap_priority", "equity", "equal"}
    if set(plan["Scenario"].astype(str)) != expected_scenarios:
        raise RuntimeError("Resource allocation strategies do not match the expected set")
    base_ids = set(base["Facility_ID"].astype(str))
    for scenario, group in plan.groupby("Scenario"):
        if set(group["Facility_ID"].astype(str)) != base_ids:
            raise RuntimeError(f"Resource scenario {scenario} does not cover every facility")
        joined = group.merge(base, on="Facility_ID", validate="one_to_one")
        if (joined["Allocated_Units"] < 0).any() or (joined["Allocated_Units"] > joined["Baseline_Gap_Units"]).any():
            raise RuntimeError(f"Resource scenario {scenario} allocates beyond facility gaps")
        _close(joined["Residual_Gap_Units"],
               joined["Baseline_Gap_Units"] - joined["Allocated_Units"],
               f"Resource scenario {scenario} residual gap", 0)
        expected_coverage = 100 * (
            joined["Synthetic_Available_Units"] + joined["Allocated_Units"]
        ) / joined["Illustrative_Requirement_Units"]
        _close(joined["Post_Allocation_Coverage_Pct"], expected_coverage,
               f"Resource scenario {scenario} post-allocation coverage", 0.03)
        if group["Allocated_Units"].sum() > resource_pool:
            raise RuntimeError(f"Resource scenario {scenario} exceeds its pool")
    return {"facilities": len(base), "scenarios": len(expected_scenarios),
            "scenario_rows": len(plan)}


def validate_stock_ledger(stock: pd.DataFrame) -> dict[str, int]:
    keys = ["Facility_ID", "Commodity_ID", "Month"]
    required = keys + ["Opening_Stock_Units", "Receipts_Units", "Demand_Units",
        "Fulfilled_Consumption_Units", "Unmet_Demand_Units", "Closing_Stock_Units",
        "Stockout_Days", "Stockout_Flag"]
    data = _numeric(stock, [c for c in required if c != "Stockout_Flag"], "Commodity stock ledger")
    if data[keys].isna().any().any() or data.duplicated(keys).any():
        raise RuntimeError("Commodity stock ledger keys must be populated and unique")
    if (data[required[3:-1]] < 0).any().any():
        raise RuntimeError("Commodity stock ledger quantities cannot be negative")
    _close(data["Opening_Stock_Units"] + data["Receipts_Units"],
           data["Fulfilled_Consumption_Units"] + data["Closing_Stock_Units"],
           "Commodity stock balance", 0)
    _close(data["Demand_Units"],
           data["Fulfilled_Consumption_Units"] + data["Unmet_Demand_Units"],
           "Commodity demand fulfilment", 0)
    if not data["Stockout_Flag"].isin([True, False, 0, 1]).all():
        raise RuntimeError("Commodity Stockout_Flag must be Boolean")
    expected_flag = data["Stockout_Days"].gt(0)
    if not data["Stockout_Flag"].astype(bool).equals(expected_flag):
        raise RuntimeError("Commodity stockout flag does not reconcile with stockout days")
    data["Month"] = pd.to_datetime(data["Month"], errors="coerce").dt.to_period("M")
    if data["Month"].isna().any():
        raise RuntimeError("Commodity stock ledger contains invalid months")
    if (data["Stockout_Days"] > data["Month"].map(lambda m: m.days_in_month)).any():
        raise RuntimeError("Commodity stockout days exceed calendar days in the month")
    data = data.sort_values(keys)
    previous = data.groupby(["Facility_ID", "Commodity_ID"])["Closing_Stock_Units"].shift()
    has_previous = previous.notna()
    _close(data.loc[has_previous, "Opening_Stock_Units"], previous[has_previous],
           "Commodity opening-to-prior-closing continuity", 0)
    return {"ledger_rows": len(data),
            "facility_commodity_pairs": int(data.groupby(["Facility_ID", "Commodity_ID"]).ngroups)}


def validate_cold_chain_ledger(batch: pd.DataFrame, risk: pd.DataFrame) -> dict[str, int]:
    keys = ["Batch_ID", "Month"]
    numeric = ["Opening_Stock_Units", "Receipts_Units", "Fulfilled_Consumption_Units",
               "Expired_Units", "Closing_Stock_Units"]
    data = _numeric(batch, numeric, "Cold-chain batch ledger")
    if data[keys].isna().any().any() or data.duplicated(keys).any():
        raise RuntimeError("Cold-chain batch-month keys must be populated and unique")
    if (data[numeric] < 0).any().any():
        raise RuntimeError("Cold-chain batch quantities cannot be negative")
    _close(data["Opening_Stock_Units"] + data["Receipts_Units"],
           data["Fulfilled_Consumption_Units"] + data["Expired_Units"] + data["Closing_Stock_Units"],
           "Cold-chain batch stock balance", 0)
    data["Month"] = pd.to_datetime(data["Month"], errors="coerce").dt.to_period("M")
    if data["Month"].isna().any():
        raise RuntimeError("Cold-chain batch ledger contains invalid months")
    data = data.sort_values(["Batch_ID", "Month"])
    previous = data.groupby("Batch_ID")["Closing_Stock_Units"].shift()
    has_previous = previous.notna()
    _close(data.loc[has_previous, "Opening_Stock_Units"], previous[has_previous],
           "Cold-chain batch opening-to-prior-closing continuity", 0)

    risk_keys = ["Facility_ID", "Commodity_ID", "Month"]
    risk_data = _numeric(risk, ["Expired_Units", "Closing_Stock_Units",
        "Near_Expiry_90_Day_Units", "Demand_Units", "Fulfilled_Consumption_Units",
        "Unmet_Demand_Units"], "Cold-chain risk summary")
    if risk_data[risk_keys].isna().any().any() or risk_data.duplicated(risk_keys).any():
        raise RuntimeError("Cold-chain risk summary keys must be populated and unique")
    risk_data["Month"] = pd.to_datetime(risk_data["Month"], errors="coerce").dt.to_period("M")
    if risk_data["Month"].isna().any():
        raise RuntimeError("Cold-chain risk summary contains invalid months")
    grouped = data.groupby(["Facility_ID", "Commodity_ID", "Month"], as_index=False).agg(
        Expired_Units=("Expired_Units", "sum"),
        Closing_Stock_Units=("Closing_Stock_Units", "sum"),
        Near_Expiry_90_Day_Units=("Near_Expiry_90_Days", "sum"),
        Fulfilled_Consumption_Units=("Fulfilled_Consumption_Units", "sum"),
    )
    joined = risk_data.merge(grouped, on=risk_keys, how="outer", suffixes=("_summary", "_batch"),
                             validate="one_to_one", indicator=True)
    if not joined["_merge"].eq("both").all():
        raise RuntimeError("Cold-chain risk summary does not cover the batch ledger population")
    for column in ["Expired_Units", "Closing_Stock_Units",
                   "Near_Expiry_90_Day_Units", "Fulfilled_Consumption_Units"]:
        _close(joined[f"{column}_summary"], joined[f"{column}_batch"],
               f"Cold-chain {column} summary", 0)
    _close(risk_data["Demand_Units"],
           risk_data["Fulfilled_Consumption_Units"] + risk_data["Unmet_Demand_Units"],
           "Cold-chain demand fulfilment", 0)
    return {"batch_month_rows": len(data), "risk_summary_rows": len(risk_data)}


def validate_equipment_ledger(performance: pd.DataFrame, work_orders: pd.DataFrame) -> dict[str, int]:
    keys = ["Asset_ID", "Month"]
    numeric = ["Calendar_Hours", "Unplanned_Downtime_Hours",
        "Planned_Maintenance_Downtime_Hours", "Total_Downtime_Hours",
        "Service_Availability_Pct", "Operational_Uptime_Pct",
        "Maintenance_Cost_Credits", "Breakdown_Count"]
    data = _numeric(performance, numeric, "Equipment asset-month performance")
    if data[keys].isna().any().any() or data.duplicated(keys).any():
        raise RuntimeError("Equipment asset-month keys must be populated and unique")
    if (data[numeric] < 0).any().any() or (data["Calendar_Hours"] <= 0).any():
        raise RuntimeError("Equipment downtime and cost measures must be non-negative")
    _close(data["Total_Downtime_Hours"],
           data["Unplanned_Downtime_Hours"] + data["Planned_Maintenance_Downtime_Hours"],
           "Equipment total downtime", 0.11)
    _close(data["Service_Availability_Pct"],
           100 * (data["Calendar_Hours"] - data["Unplanned_Downtime_Hours"]) / data["Calendar_Hours"],
           "Equipment service availability", 0.03)
    _close(data["Operational_Uptime_Pct"],
           100 * (data["Calendar_Hours"] - data["Total_Downtime_Hours"]) / data["Calendar_Hours"],
           "Equipment operational uptime", 0.03)
    if data["Total_Downtime_Hours"].gt(data["Calendar_Hours"] + 0.11).any():
        raise RuntimeError("Equipment downtime exceeds calendar hours")
    wo = work_orders.copy()
    if wo.empty:
        wo = pd.DataFrame(columns=["Asset_ID", "Month", "Cost_Credits"])
    if not {"Asset_ID", "Month", "Cost_Credits"}.issubset(wo.columns):
        raise RuntimeError("Maintenance work orders are missing reconciliation fields")
    wo["Cost_Credits"] = pd.to_numeric(wo["Cost_Credits"], errors="coerce")
    if wo["Cost_Credits"].isna().any() or not np.isfinite(wo["Cost_Credits"]).all() or wo["Cost_Credits"].lt(0).any():
        raise RuntimeError("Maintenance work-order costs are invalid")
    if not wo.empty:
        if "Downtime_Hours" not in wo.columns or "Work_Order_ID" not in wo.columns:
            raise RuntimeError("Maintenance work orders are missing downtime or unique identifiers")
        if wo["Work_Order_ID"].isna().any() or wo["Work_Order_ID"].duplicated().any():
            raise RuntimeError("Maintenance work-order identifiers must be populated and unique")
        wo["Downtime_Hours"] = pd.to_numeric(wo["Downtime_Hours"], errors="coerce")
        if wo["Downtime_Hours"].isna().any() or not np.isfinite(wo["Downtime_Hours"]).all() or wo["Downtime_Hours"].lt(0).any():
            raise RuntimeError("Maintenance work-order downtime is invalid")
        wo["Month"] = pd.to_datetime(wo["Month"], errors="coerce").dt.to_period("M")
        if wo["Month"].isna().any():
            raise RuntimeError("Maintenance work orders contain invalid months")
        totals = wo.groupby(["Asset_ID", "Month"], as_index=False).agg(
            Cost_Credits=("Cost_Credits", "sum"),
            Downtime_Hours=("Downtime_Hours", "sum"),
        )
        base = data.assign(Month=pd.to_datetime(data["Month"]).dt.to_period("M"))
        joined = base.merge(totals, on=keys, how="left", validate="one_to_one")
        _close(joined["Maintenance_Cost_Credits"], joined["Cost_Credits"].fillna(0),
               "Equipment maintenance cost versus work orders", 0)
        _close(joined["Total_Downtime_Hours"], joined["Downtime_Hours"].fillna(0),
               "Equipment downtime versus maintenance work orders", 0.11)
    elif data["Maintenance_Cost_Credits"].gt(0).any() or data["Total_Downtime_Hours"].gt(0).any():
        raise RuntimeError("Equipment maintenance activity exists without work orders")
    return {"asset_month_rows": len(data), "work_order_rows": len(work_orders)}


def validate_infrastructure_ledger(monthly: pd.DataFrame, profiles: pd.DataFrame | None = None) -> dict[str, int]:
    numeric = ["Calendar_Hours", "Power_Interruption_Hours", "Backup_Power_Hours_Provided",
        "Unserved_Power_Interruption_Hours", "Water_Shortage_Hours", "Water_Buffered_Hours",
        "Unserved_Water_Shortage_Hours", "Connectivity_Downtime_Hours",
        "Power_Availability_Pct", "Water_Availability_Pct",
        "Connectivity_Availability_Pct", "Infrastructure_Resilience_Score"]
    data = _numeric(monthly, numeric, "Infrastructure monthly reliability")
    if not {"Facility_ID", "Month"}.issubset(data.columns) or data[["Facility_ID", "Month"]].isna().any().any():
        raise RuntimeError("Infrastructure facility-month keys must be populated")
    if data.duplicated(["Facility_ID", "Month"]).any():
        raise RuntimeError("Infrastructure facility-month keys must be unique")
    if (data[numeric] < 0).any().any() or (data["Calendar_Hours"] <= 0).any():
        raise RuntimeError("Infrastructure hours and measures must be non-negative")
    _close(data["Power_Interruption_Hours"],
           data["Backup_Power_Hours_Provided"] + data["Unserved_Power_Interruption_Hours"],
           "Infrastructure power interruption balance", 0.03)
    _close(data["Water_Shortage_Hours"],
           data["Water_Buffered_Hours"] + data["Unserved_Water_Shortage_Hours"],
           "Infrastructure water interruption balance", 0.03)
    for column, hours in [("Power_Availability_Pct", "Unserved_Power_Interruption_Hours"),
                          ("Water_Availability_Pct", "Unserved_Water_Shortage_Hours"),
                          ("Connectivity_Availability_Pct", "Connectivity_Downtime_Hours")]:
        expected = 100 * (data["Calendar_Hours"] - data[hours]) / data["Calendar_Hours"]
        _close(data[column], expected, f"Infrastructure {column}", 0.03)
        if not data[column].between(0, 100).all():
            raise RuntimeError(f"Infrastructure {column} is outside 0–100")
    expected_score = (0.40 * data["Power_Availability_Pct"] +
                      0.30 * data["Water_Availability_Pct"] +
                      0.20 * data["Connectivity_Availability_Pct"])
    if profiles is not None:
        if not {"Facility_ID", "Illustrative_Backup_Power_Hours"}.issubset(profiles.columns):
            raise RuntimeError("Infrastructure facility profiles are missing backup-power assumptions")
        backup = pd.to_numeric(profiles["Illustrative_Backup_Power_Hours"], errors="coerce")
        if backup.isna().any() or not np.isfinite(backup).all() or backup.lt(0).any():
            raise RuntimeError("Infrastructure backup-power assumptions are invalid")
        if profiles["Facility_ID"].isna().any() or profiles["Facility_ID"].duplicated().any():
            raise RuntimeError("Infrastructure facility profiles must have unique facility IDs")
        data = data.merge(profiles[["Facility_ID"]].assign(_backup=backup.to_numpy()),
                          on="Facility_ID", how="left", validate="many_to_one")
        if data["_backup"].isna().any():
            raise RuntimeError("Infrastructure monthly records reference missing facility profiles")
        expected_score = (0.40 * data["Power_Availability_Pct"] +
                          0.30 * data["Water_Availability_Pct"] +
                          0.20 * data["Connectivity_Availability_Pct"] +
                          0.10 * np.minimum(100, data["_backup"] / 18 * 100))
        _close(data["Infrastructure_Resilience_Score"], expected_score,
               "Infrastructure resilience score", 0.04)
    if not data["Infrastructure_Resilience_Score"].between(0, 100).all():
        raise RuntimeError("Infrastructure resilience score is outside 0–100")
    if (data["Unserved_Power_Interruption_Hours"] > data["Calendar_Hours"]).any() or (data["Unserved_Water_Shortage_Hours"] > data["Calendar_Hours"]).any() or (data["Connectivity_Downtime_Hours"] > data["Calendar_Hours"]).any():
        raise RuntimeError("Infrastructure unserved hours exceed calendar hours")
    return {"facility_month_rows": len(data)}


def validate_workforce_ledger(monthly: pd.DataFrame) -> dict[str, int]:
    numeric = ["Illustrative_Establishment", "Filled_Positions", "Vacant_Positions",
        "Absent_Positions", "Available_On_Duty_Positions", "Workforce_Coverage_Pct",
        "Absence_Rate_Pct", "Synthetic_Workload_Demand_Proxy",
        "Weighted_Available_Capacity", "Workforce_Pressure_Index"]
    data = _numeric(monthly, numeric, "Workforce monthly capacity")
    if not {"Facility_ID", "Month"}.issubset(data.columns) or data[["Facility_ID", "Month"]].isna().any().any():
        raise RuntimeError("Workforce facility-month keys must be populated")
    if data.duplicated(["Facility_ID", "Month"]).any():
        raise RuntimeError("Workforce facility-month keys must be unique")
    count_cols = ["Illustrative_Establishment", "Filled_Positions", "Vacant_Positions",
                  "Absent_Positions", "Available_On_Duty_Positions"]
    if (data[count_cols] < 0).any().any() or not np.equal(data[count_cols], np.floor(data[count_cols])).all().all():
        raise RuntimeError("Workforce position counts must be non-negative integers")
    if (data["Filled_Positions"] > data["Illustrative_Establishment"]).any() or (data["Absent_Positions"] > data["Filled_Positions"]).any():
        raise RuntimeError("Workforce filled or absent positions exceed their valid bounds")
    _close(data["Vacant_Positions"],
           data["Illustrative_Establishment"] - data["Filled_Positions"],
           "Workforce vacancy count", 0)
    _close(data["Available_On_Duty_Positions"],
           data["Filled_Positions"] - data["Absent_Positions"],
           "Workforce on-duty count", 0)
    expected_coverage = 100 * data["Filled_Positions"] / data["Illustrative_Establishment"].clip(lower=1)
    _close(data["Workforce_Coverage_Pct"], expected_coverage, "Workforce coverage", 0.03)
    expected_absence = 100 * data["Absent_Positions"] / data["Filled_Positions"].clip(lower=1)
    _close(data["Absence_Rate_Pct"], expected_absence, "Workforce absence rate", 0.03)
    expected_pressure = 100 * np.minimum(2.0,
        data["Synthetic_Workload_Demand_Proxy"] / data["Weighted_Available_Capacity"].clip(lower=1))
    _close(data["Workforce_Pressure_Index"], expected_pressure, "Workforce pressure index", 0.03)
    return {"facility_month_rows": len(data)}
