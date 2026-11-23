"""Synthetic commodity availability, stockout monitoring and replenishment planning.

All stock-card observations, demand, receipts and unit costs are synthetic.
They are not Ministry of Health inventory data, procurement prices, clinical
consumption standards or operational supply recommendations.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

COMMODITIES = [
    {"Commodity_ID": "COM-001", "Commodity": "Malaria rapid diagnostic test kits", "Programme": "Outpatient", "Unit": "test kit", "Monthly_Demand_per_10000": 190, "Synthetic_Unit_Cost_Credits": 3, "Essentiality_Weight": 1.00},
    {"Commodity_ID": "COM-002", "Commodity": "HIV testing kits", "Programme": "HIV", "Unit": "test kit", "Monthly_Demand_per_10000": 85, "Synthetic_Unit_Cost_Credits": 5, "Essentiality_Weight": 1.00},
    {"Commodity_ID": "COM-003", "Commodity": "TB sputum collection containers", "Programme": "Tuberculosis", "Unit": "container", "Monthly_Demand_per_10000": 24, "Synthetic_Unit_Cost_Credits": 2, "Essentiality_Weight": 0.95},
    {"Commodity_ID": "COM-004", "Commodity": "ANC screening test kits", "Programme": "Maternal Health", "Unit": "test kit", "Monthly_Demand_per_10000": 32, "Synthetic_Unit_Cost_Credits": 4, "Essentiality_Weight": 0.90},
    {"Commodity_ID": "COM-005", "Commodity": "Penta vaccine doses", "Programme": "Child Health", "Unit": "dose", "Monthly_Demand_per_10000": 48, "Synthetic_Unit_Cost_Credits": 6, "Essentiality_Weight": 1.00},
    {"Commodity_ID": "COM-006", "Commodity": "Vitamin A capsules", "Programme": "Nutrition", "Unit": "capsule", "Monthly_Demand_per_10000": 42, "Synthetic_Unit_Cost_Credits": 2, "Essentiality_Weight": 0.85},
    {"Commodity_ID": "COM-007", "Commodity": "Family planning implant kits", "Programme": "Family Planning", "Unit": "kit", "Monthly_Demand_per_10000": 7, "Synthetic_Unit_Cost_Credits": 18, "Essentiality_Weight": 0.80},
    {"Commodity_ID": "COM-008", "Commodity": "Examination gloves", "Programme": "Outpatient", "Unit": "pair", "Monthly_Demand_per_10000": 360, "Synthetic_Unit_Cost_Credits": 1, "Essentiality_Weight": 0.90},
]
REQUIRED_FACILITY_COLUMNS = {
    "Facility_ID", "Facility_Name", "District", "Facility_Type",
    "Urban_Rural", "Catchment_Population",
}


def build_supply_chain_profiles(
    facilities: pd.DataFrame,
    periods: int = 24,
    start_month: str = "2025-01-01",
    seed: int = 42,
    budget_credits: int = 50000,
    lead_time_days: int = 30,
    buffer_days: int = 15,
) -> dict[str, pd.DataFrame | dict[str, Any]]:
    """Create a reproducible stock ledger and constrained replenishment plan."""
    missing = REQUIRED_FACILITY_COLUMNS - set(facilities.columns)
    if missing:
        raise ValueError(f"Facility dimension missing required columns: {sorted(missing)}")
    for name, value in (("periods", periods), ("lead_time_days", lead_time_days)):
        if not isinstance(value, (int, np.integer)) or value < 1:
            raise ValueError(f"{name} must be a positive integer")
    if not isinstance(buffer_days, (int, np.integer)) or buffer_days < 0:
        raise ValueError("buffer_days must be a non-negative integer")
    if not isinstance(budget_credits, (int, np.integer)) or budget_credits < 0:
        raise ValueError("budget_credits must be a non-negative integer")

    fac = facilities[list(REQUIRED_FACILITY_COLUMNS)].copy()
    fac["Catchment_Population"] = pd.to_numeric(fac["Catchment_Population"], errors="coerce")
    if fac["Facility_ID"].isna().any() or fac["Facility_ID"].duplicated().any():
        raise ValueError("Facility_ID must be populated and unique")
    if fac["Catchment_Population"].isna().any() or fac["Catchment_Population"].lt(0).any():
        raise ValueError("Catchment_Population must contain non-negative numeric values")

    catalog = pd.DataFrame(COMMODITIES)
    months = pd.date_range(start=start_month, periods=periods, freq="MS")
    rng = np.random.default_rng(seed)
    type_factor = fac["Facility_Type"].map({
        "Health Centre": 0.75, "Community Hospital": 1.15, "District Hospital": 1.65
    }).fillna(1.0).to_numpy()
    records: list[dict[str, Any]] = []
    for fpos, facility in fac.reset_index(drop=True).iterrows():
        population_scale = max(float(facility["Catchment_Population"]) / 10000, 0.05)
        for commodity in COMMODITIES:
            demand_mean = max(
                1.0,
                population_scale * float(commodity["Monthly_Demand_per_10000"]) * type_factor[fpos],
            )
            opening = int(rng.poisson(demand_mean * rng.uniform(0.8, 1.8)))
            for month in months:
                receipts = int(rng.poisson(demand_mean * rng.uniform(0.55, 1.05)))
                demand = int(rng.poisson(demand_mean))
                available = opening + receipts
                fulfilled = min(available, demand)
                unmet = max(0, demand - available)
                closing = available - fulfilled
                days_in_month = int(month.days_in_month)
                stockout_days = (
                    min(days_in_month, int(np.ceil((unmet / max(demand, 1)) * days_in_month)))
                    if unmet else 0
                )
                records.append({
                    "Facility_ID": facility["Facility_ID"],
                    "Facility_Name": facility["Facility_Name"],
                    "District": facility["District"],
                    "Facility_Type": facility["Facility_Type"],
                    "Urban_Rural": facility["Urban_Rural"],
                    "Month": month,
                    "Commodity_ID": commodity["Commodity_ID"],
                    "Commodity": commodity["Commodity"],
                    "Programme": commodity["Programme"],
                    "Unit": commodity["Unit"],
                    "Synthetic_Unit_Cost_Credits": commodity["Synthetic_Unit_Cost_Credits"],
                    "Essentiality_Weight": commodity["Essentiality_Weight"],
                    "Opening_Stock_Units": opening,
                    "Receipts_Units": receipts,
                    "Demand_Units": demand,
                    "Fulfilled_Consumption_Units": fulfilled,
                    "Unmet_Demand_Units": unmet,
                    "Closing_Stock_Units": closing,
                    "Stockout_Days": stockout_days,
                    "Stockout_Flag": bool(stockout_days > 0),
                    "Synthetic_Data": True,
                })
                opening = closing

    ledger = pd.DataFrame(records)
    ledger["Month"] = pd.to_datetime(ledger["Month"])
    ledger = ledger.sort_values(["Facility_ID", "Commodity_ID", "Month"]).reset_index(drop=True)

    latest_month = ledger["Month"].max()
    plans: list[dict[str, Any]] = []
    for (facility_id, commodity_id), group in ledger.groupby(["Facility_ID", "Commodity_ID"], sort=True):
        group = group.sort_values("Month")
        last = group.iloc[-1]
        recent = group.tail(min(3, len(group)))
        average_monthly_demand = float(recent["Demand_Units"].mean())
        daily_demand = average_monthly_demand / 30.0
        days_cover = float(last["Closing_Stock_Units"] / daily_demand) if daily_demand > 0 else float("inf")
        target_units = int(np.ceil(daily_demand * (lead_time_days + buffer_days)))
        requested = max(0, target_units - int(last["Closing_Stock_Units"]))
        risk = max(0.0, (lead_time_days - days_cover) / max(lead_time_days, 1))
        stockout_recent = int(recent["Stockout_Days"].sum())
        priority = float(last["Essentiality_Weight"]) * (1.0 + risk + min(stockout_recent / 30.0, 1.0))
        plans.append({
            "Facility_ID": facility_id,
            "Facility_Name": last["Facility_Name"],
            "District": last["District"],
            "Urban_Rural": last["Urban_Rural"],
            "Commodity_ID": commodity_id,
            "Commodity": last["Commodity"],
            "Programme": last["Programme"],
            "Unit": last["Unit"],
            "Snapshot_Month": latest_month,
            "Closing_Stock_Units": int(last["Closing_Stock_Units"]),
            "Average_Monthly_Demand_Units": round(average_monthly_demand, 2),
            "Estimated_Days_of_Cover": round(days_cover, 2) if np.isfinite(days_cover) else np.nan,
            "Lead_Time_Days_Assumption": int(lead_time_days),
            "Buffer_Days_Assumption": int(buffer_days),
            "Target_Stock_Units": target_units,
            "Requested_Replenishment_Units": requested,
            "Synthetic_Unit_Cost_Credits": int(last["Synthetic_Unit_Cost_Credits"]),
            "Requested_Cost_Credits": requested * int(last["Synthetic_Unit_Cost_Credits"]),
            "Recent_Stockout_Days": stockout_recent,
            "Priority_Score": round(priority, 4),
            "Synthetic_Data": True,
        })
    plan = pd.DataFrame(plans)
    plan["Allocated_Replenishment_Units"] = 0
    remaining_budget = int(budget_credits)
    plan["Priority_Per_Credit"] = (
        plan["Priority_Score"] / plan["Synthetic_Unit_Cost_Credits"].clip(lower=1)
    )
    # Deterministic one-unit allocation, with stable keys for ties.
    eligible = plan.index[plan["Requested_Replenishment_Units"].gt(0)].tolist()
    eligible.sort(key=lambda idx: (
        -float(plan.loc[idx, "Priority_Per_Credit"]),
        str(plan.loc[idx, "Facility_ID"]),
        str(plan.loc[idx, "Commodity_ID"]),
    ))
    for idx in eligible:
        unit_cost = int(plan.loc[idx, "Synthetic_Unit_Cost_Credits"])
        requested = int(plan.loc[idx, "Requested_Replenishment_Units"])
        affordable = min(requested, remaining_budget // unit_cost)
        if affordable:
            plan.loc[idx, "Allocated_Replenishment_Units"] = affordable
            remaining_budget -= affordable * unit_cost
    plan["Allocated_Cost_Credits"] = (
        plan["Allocated_Replenishment_Units"] * plan["Synthetic_Unit_Cost_Credits"]
    )
    plan["Unfunded_Replenishment_Units"] = (
        plan["Requested_Replenishment_Units"] - plan["Allocated_Replenishment_Units"]
    )
    plan["Post_Allocation_Stock_Units"] = (
        plan["Closing_Stock_Units"] + plan["Allocated_Replenishment_Units"]
    )
    plan["Post_Allocation_Days_of_Cover"] = np.where(
        plan["Average_Monthly_Demand_Units"] > 0,
        30 * plan["Post_Allocation_Stock_Units"] / plan["Average_Monthly_Demand_Units"],
        np.nan,
    ).round(2)
    plan["Priority_Per_Credit"] = plan["Priority_Per_Credit"].round(5)

    summary = pd.DataFrame([{
        "snapshot_month": latest_month,
        "facilities": int(plan["Facility_ID"].nunique()),
        "facility_commodity_pairs": int(len(plan)),
        "pairs_with_zero_closing_stock": int(plan["Closing_Stock_Units"].eq(0).sum()),
        "pairs_with_recent_stockout": int(plan["Recent_Stockout_Days"].gt(0).sum()),
        "requested_replenishment_units": int(plan["Requested_Replenishment_Units"].sum()),
        "allocated_replenishment_units": int(plan["Allocated_Replenishment_Units"].sum()),
        "unfunded_replenishment_units": int(plan["Unfunded_Replenishment_Units"].sum()),
        "requested_cost_credits": int(plan["Requested_Cost_Credits"].sum()),
        "allocated_cost_credits": int(plan["Allocated_Cost_Credits"].sum()),
        "budget_credits": int(budget_credits),
        "unspent_budget_credits": int(remaining_budget),
        "synthetic_data": True,
    }])
    assumptions = {
        "synthetic_data": True,
        "commodity_count": int(len(catalog)),
        "periods": int(periods),
        "seed": int(seed),
        "budget_credits": int(budget_credits),
        "lead_time_days": int(lead_time_days),
        "buffer_days": int(buffer_days),
        "consumption_model": "Poisson demand using synthetic monthly rates per 10,000 catchment population and illustrative facility-type multipliers.",
        "replenishment_model": "Three-month average demand multiplied by lead time plus buffer days; deterministic priority-per-credit budget allocation.",
        "limitations": [
            "All inventory, consumption, receipts, unit costs and stockout observations are synthetic.",
            "Commodity names are illustrative examples, not an approved Malawi essential medicines or commodities list.",
            "Demand rates and facility multipliers are modelling assumptions, not clinical consumption standards.",
            "Unit costs are abstract budget credits, not MWK procurement prices.",
            "Receipts are modelled at the start of each reporting month; actual delivery timing and expiry are not modelled.",
            "This is not a live inventory system or an operational procurement recommendation.",
        ],
    }
    return {
        "commodity_catalog": catalog,
        "inventory_ledger": ledger,
        "replenishment_plan": plan,
        "scenario_summary": summary,
        "assumptions": assumptions,
    }


def run_supply_chain_planning(
    facility_path: Path,
    output_dir: Path,
    periods: int = 24,
    start_month: str = "2025-01-01",
    seed: int = 42,
    budget_credits: int = 50000,
    lead_time_days: int = 30,
    buffer_days: int = 15,
) -> dict[str, Any]:
    facilities = pd.read_csv(facility_path)
    result = build_supply_chain_profiles(
        facilities, periods, start_month, seed, budget_credits, lead_time_days, buffer_days
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "commodity_catalog": "commodity_catalog.csv",
        "inventory_ledger": "facility_commodity_stock_ledger.csv",
        "replenishment_plan": "commodity_replenishment_plan.csv",
        "scenario_summary": "commodity_replenishment_summary.csv",
    }
    for key, filename in outputs.items():
        result[key].to_csv(output_dir / filename, index=False)
    summary = result["scenario_summary"].iloc[0]
    plan = result["replenishment_plan"]
    report = {
        **result["assumptions"],
        "facility_count": int(facilities["Facility_ID"].nunique()),
        "inventory_records": int(len(result["inventory_ledger"])),
        "latest_snapshot_month": str(summary["snapshot_month"]),
        "facility_commodity_pairs_with_recent_stockout": int(plan["Recent_Stockout_Days"].gt(0).sum()),
        "requested_replenishment_units": int(summary["requested_replenishment_units"]),
        "allocated_replenishment_units": int(summary["allocated_replenishment_units"]),
        "unfunded_replenishment_units": int(summary["unfunded_replenishment_units"]),
        "allocated_cost_credits": int(summary["allocated_cost_credits"]),
        "unspent_budget_credits": int(summary["unspent_budget_credits"]),
        "outputs": list(outputs.values()),
    }
    (output_dir / "supply_chain_planning_report.json").write_text(json.dumps(report, indent=2, default=str))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--facilities", type=Path, default=Path("data/warehouse/raw/facility_dimension.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/warehouse/analytics"))
    parser.add_argument("--periods", type=int, default=24)
    parser.add_argument("--start-month", default="2025-01-01")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--budget-credits", type=int, default=50000)
    parser.add_argument("--lead-time-days", type=int, default=30)
    parser.add_argument("--buffer-days", type=int, default=15)
    args = parser.parse_args()
    print(json.dumps(run_supply_chain_planning(
        args.facilities, args.output_dir, args.periods, args.start_month, args.seed,
        args.budget_credits, args.lead_time_days, args.buffer_days,
    ), indent=2, default=str))
