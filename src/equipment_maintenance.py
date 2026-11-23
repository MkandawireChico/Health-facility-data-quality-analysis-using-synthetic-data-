"""Synthetic health-facility equipment, maintenance and uptime intelligence.

All assets, acquisition dates, failures, maintenance events, downtime and costs are
simulated. This is a portfolio scenario, not a verified equipment inventory,
engineering assessment, maintenance standard or operational safety register.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

EQUIPMENT_CATALOG = [
    {"Equipment_Type": "Vaccine refrigerator", "Category": "Cold chain", "Criticality": "Critical", "Base_Monthly_Failure_Probability": 0.025, "PM_Interval_Months": 3, "Expected_Life_Years": 10, "Synthetic_Replacement_Cost_Credits": 1200},
    {"Equipment_Type": "Standby generator", "Category": "Power", "Criticality": "Critical", "Base_Monthly_Failure_Probability": 0.045, "PM_Interval_Months": 1, "Expected_Life_Years": 12, "Synthetic_Replacement_Cost_Credits": 2500},
    {"Equipment_Type": "Solar power system", "Category": "Power", "Criticality": "High", "Base_Monthly_Failure_Probability": 0.025, "PM_Interval_Months": 3, "Expected_Life_Years": 15, "Synthetic_Replacement_Cost_Credits": 3000},
    {"Equipment_Type": "Autoclave", "Category": "Sterilisation", "Criticality": "High", "Base_Monthly_Failure_Probability": 0.035, "PM_Interval_Months": 3, "Expected_Life_Years": 10, "Synthetic_Replacement_Cost_Credits": 1800},
    {"Equipment_Type": "Oxygen concentrator", "Category": "Clinical support", "Criticality": "Critical", "Base_Monthly_Failure_Probability": 0.04, "PM_Interval_Months": 2, "Expected_Life_Years": 8, "Synthetic_Replacement_Cost_Credits": 900},
    {"Equipment_Type": "Ultrasound scanner", "Category": "Diagnostics", "Criticality": "High", "Base_Monthly_Failure_Probability": 0.03, "PM_Interval_Months": 3, "Expected_Life_Years": 10, "Synthetic_Replacement_Cost_Credits": 4500},
    {"Equipment_Type": "Laboratory microscope", "Category": "Diagnostics", "Criticality": "Medium", "Base_Monthly_Failure_Probability": 0.02, "PM_Interval_Months": 6, "Expected_Life_Years": 12, "Synthetic_Replacement_Cost_Credits": 600},
]

REQUIRED_FACILITY_COLUMNS = [
    "Facility_ID", "Facility_Name", "District", "Facility_Type",
    "Urban_Rural", "Catchment_Population",
]


def _facility_asset_types(facility_type: str) -> list[str]:
    base = [
        "Vaccine refrigerator", "Standby generator",
        "Solar power system", "Autoclave",
    ]
    if "Hospital" in str(facility_type):
        return base + ["Oxygen concentrator", "Ultrasound scanner", "Laboratory microscope"]
    return base + ["Oxygen concentrator"]


def _validate_facilities(facilities: pd.DataFrame) -> pd.DataFrame:
    missing = sorted(set(REQUIRED_FACILITY_COLUMNS) - set(facilities.columns))
    if missing:
        raise ValueError(f"Facility dimension missing required columns: {missing}")
    fac = facilities[REQUIRED_FACILITY_COLUMNS].copy()
    if fac.empty:
        raise ValueError("Facility dimension must contain at least one facility")
    fac["Facility_ID"] = fac["Facility_ID"].astype("string").str.strip()
    if fac["Facility_ID"].isna().any() or fac["Facility_ID"].eq("").any():
        raise ValueError("Facility_ID must be populated for every facility")
    if fac["Facility_ID"].duplicated().any():
        raise ValueError("Facility_ID values must be unique")
    fac["Catchment_Population"] = pd.to_numeric(fac["Catchment_Population"], errors="coerce")
    fac["Catchment_Population"] = fac["Catchment_Population"].fillna(0).clip(lower=0)
    for column in ["Facility_Name", "District", "Facility_Type", "Urban_Rural"]:
        fac[column] = fac[column].fillna("Unknown").astype(str).str.strip()
    return fac


def build_equipment_maintenance_profiles(
    facilities: pd.DataFrame,
    periods: int = 60,
    start_month: str = "2021-01-01",
    seed: int = 42,
) -> dict[str, Any]:
    """Build synthetic asset register, monthly performance and maintenance events."""
    if not isinstance(periods, int) or periods < 1:
        raise ValueError("periods must be a positive integer")
    fac = _validate_facilities(facilities)
    months = pd.date_range(pd.Timestamp(start_month).to_period("M").to_timestamp(), periods=periods, freq="MS")
    rng = np.random.default_rng(seed)
    catalog = pd.DataFrame(EQUIPMENT_CATALOG)
    catalog_by_type = catalog.set_index("Equipment_Type").to_dict("index")

    assets: list[dict[str, Any]] = []
    monthly_rows: list[dict[str, Any]] = []
    work_orders: list[dict[str, Any]] = []
    asset_number = 0

    for facility in fac.to_dict("records"):
        for equipment_type in _facility_asset_types(facility["Facility_Type"]):
            spec = catalog_by_type[equipment_type]
            asset_number += 1
            asset_id = f"AST-{asset_number:06d}"
            age_at_start = int(rng.integers(1, spec["Expected_Life_Years"] + 3))
            install_date = months[0] - pd.DateOffset(years=age_at_start) - pd.DateOffset(days=int(rng.integers(0, 365)))
            condition_start = float(rng.uniform(58, 99))
            asset = {
                "Asset_ID": asset_id,
                "Facility_ID": facility["Facility_ID"],
                "Facility_Name": facility["Facility_Name"],
                "District": facility["District"],
                "Facility_Type": facility["Facility_Type"],
                "Urban_Rural": facility["Urban_Rural"],
                "Equipment_Type": equipment_type,
                "Category": spec["Category"],
                "Criticality": spec["Criticality"],
                "Install_Date": install_date.date().isoformat(),
                "Age_At_Start_Years": round((months[0] - install_date).days / 365.25, 1),
                "Expected_Life_Years_Assumption": spec["Expected_Life_Years"],
                "PM_Interval_Months_Assumption": spec["PM_Interval_Months"],
                "Synthetic_Replacement_Cost_Credits": spec["Synthetic_Replacement_Cost_Credits"],
                "Initial_Condition_Score": round(condition_start, 1),
                "Asset_Status": "Active",
                "Synthetic_Data": True,
            }
            assets.append(asset)
            condition = condition_start
            pm_offset = int(rng.integers(0, spec["PM_Interval_Months"]))
            for period_index, month in enumerate(months):
                days = int(month.days_in_month)
                calendar_hours = days * 24
                age_years = (month - install_date).days / 365.25
                age_factor = 1 + max(0.0, age_years - 3) * 0.025
                condition_factor = 1 + max(0.0, 75 - condition) / 100
                failure_probability = min(
                    0.35,
                    spec["Base_Monthly_Failure_Probability"] * age_factor * condition_factor,
                )
                breakdown = bool(rng.random() < failure_probability)
                breakdown_count = int(breakdown)
                breakdown_hours = float(rng.uniform(3, min(72, calendar_hours * 0.7))) if breakdown else 0.0
                pm_due = ((period_index + pm_offset + 1) % spec["PM_Interval_Months"]) == 0
                pm_completed = bool(pm_due and rng.random() < 0.84)
                pm_hours = float(rng.uniform(1, 6)) if pm_completed else 0.0
                planned_downtime = min(pm_hours, max(0.0, calendar_hours - breakdown_hours))
                total_downtime = min(calendar_hours, breakdown_hours + planned_downtime)
                service_availability = max(0.0, 100 * (calendar_hours - breakdown_hours) / calendar_hours)
                operational_uptime = max(0.0, 100 * (calendar_hours - total_downtime) / calendar_hours)
                pm_overdue = bool(pm_due and not pm_completed)
                if breakdown:
                    condition -= float(rng.uniform(3, 11))
                if pm_completed:
                    condition += float(rng.uniform(1, 4))
                elif pm_overdue:
                    condition -= float(rng.uniform(1, 3))
                condition = float(np.clip(condition, 10, 100))
                age_ratio = min(1.0, age_years / spec["Expected_Life_Years"])
                downtime_risk = min(100.0, breakdown_hours / max(1.0, calendar_hours) * 100 * 5)
                pm_risk = 100.0 if pm_overdue else 0.0
                age_risk = age_ratio * 100
                criticality_weight = {"Critical": 1.0, "High": 0.85, "Medium": 0.65}.get(spec["Criticality"], 0.5)
                risk_score = float(np.clip(
                    (0.40 * downtime_risk + 0.35 * pm_risk + 0.25 * age_risk) * (0.75 + 0.25 * criticality_weight),
                    0, 100,
                ))
                risk_band = "High" if risk_score >= 65 else "Medium" if risk_score >= 35 else "Low"
                pm_cost = int(rng.integers(10, 90)) if pm_completed else 0
                corrective_cost = int(rng.integers(25, 180)) if breakdown else 0
                maintenance_cost = pm_cost + corrective_cost
                record = {
                    "Asset_ID": asset_id,
                    "Facility_ID": facility["Facility_ID"],
                    "Facility_Name": facility["Facility_Name"],
                    "District": facility["District"],
                    "Facility_Type": facility["Facility_Type"],
                    "Urban_Rural": facility["Urban_Rural"],
                    "Equipment_Type": equipment_type,
                    "Category": spec["Category"],
                    "Criticality": spec["Criticality"],
                    "Month": month,
                    "Asset_Age_Years": round(age_years, 2),
                    "Calendar_Hours": calendar_hours,
                    "Breakdown_Count": breakdown_count,
                    "Unplanned_Downtime_Hours": round(breakdown_hours, 1),
                    "Planned_Maintenance_Downtime_Hours": round(planned_downtime, 1),
                    "Total_Downtime_Hours": round(total_downtime, 1),
                    "Service_Availability_Pct": round(service_availability, 2),
                    "Operational_Uptime_Pct": round(operational_uptime, 2),
                    "Preventive_Maintenance_Due": bool(pm_due),
                    "Preventive_Maintenance_Completed": bool(pm_completed),
                    "Preventive_Maintenance_Overdue": pm_overdue,
                    "Condition_Score": round(condition, 1),
                    "Maintenance_Cost_Credits": maintenance_cost,
                    "Equipment_Risk_Score": round(risk_score, 2),
                    "Risk_Band": risk_band,
                    "Synthetic_Data": True,
                }
                monthly_rows.append(record)
                if pm_due:
                    status = "Closed" if pm_completed else ("In Progress" if rng.random() < 0.25 else "Open")
                    work_orders.append({
                        "Work_Order_ID": f"WO-{asset_number:06d}-{month:%Y%m}-PM",
                        "Asset_ID": asset_id,
                        "Facility_ID": facility["Facility_ID"],
                        "Facility_Name": facility["Facility_Name"],
                        "District": facility["District"],
                        "Equipment_Type": equipment_type,
                        "Month": month,
                        "Work_Order_Type": "Preventive Maintenance",
                        "Priority": "High" if spec["Criticality"] == "Critical" else "Routine",
                        "Status": status,
                        "Due_Date": (month + pd.offsets.MonthEnd(0)).date().isoformat(),
                        "Downtime_Hours": round(planned_downtime, 1),
                        "Cost_Credits": pm_cost,
                        "Synthetic_Data": True,
                    })
                if breakdown:
                    work_orders.append({
                        "Work_Order_ID": f"WO-{asset_number:06d}-{month:%Y%m}-CM",
                        "Asset_ID": asset_id,
                        "Facility_ID": facility["Facility_ID"],
                        "Facility_Name": facility["Facility_Name"],
                        "District": facility["District"],
                        "Equipment_Type": equipment_type,
                        "Month": month,
                        "Work_Order_Type": "Corrective Maintenance",
                        "Priority": "Critical" if spec["Criticality"] == "Critical" else "High",
                        "Status": "Closed" if breakdown_hours < 12 or rng.random() < 0.55 else "In Progress",
                        "Due_Date": (month + pd.offsets.MonthEnd(0)).date().isoformat(),
                        "Downtime_Hours": round(breakdown_hours, 1),
                        "Cost_Credits": corrective_cost,
                        "Synthetic_Data": True,
                    })

    asset_register = pd.DataFrame(assets)
    performance = pd.DataFrame(monthly_rows)
    work_order_frame = pd.DataFrame(work_orders)
    if work_order_frame.empty:
        work_order_frame = pd.DataFrame(columns=[
            "Work_Order_ID", "Asset_ID", "Facility_ID", "Facility_Name", "District",
            "Equipment_Type", "Month", "Work_Order_Type", "Priority", "Status",
            "Due_Date", "Downtime_Hours", "Cost_Credits", "Synthetic_Data",
        ])

    facility_monthly = performance.groupby(
        ["Facility_ID", "Facility_Name", "District", "Month"], as_index=False
    ).agg(
        Active_Assets=("Asset_ID", "nunique"),
        Breakdown_Events=("Breakdown_Count", "sum"),
        Unplanned_Downtime_Hours=("Unplanned_Downtime_Hours", "sum"),
        Planned_Maintenance_Downtime_Hours=("Planned_Maintenance_Downtime_Hours", "sum"),
        Total_Downtime_Hours=("Total_Downtime_Hours", "sum"),
        Mean_Service_Availability_Pct=("Service_Availability_Pct", "mean"),
        Mean_Operational_Uptime_Pct=("Operational_Uptime_Pct", "mean"),
        PM_Due=("Preventive_Maintenance_Due", "sum"),
        PM_Completed=("Preventive_Maintenance_Completed", "sum"),
        PM_Overdue=("Preventive_Maintenance_Overdue", "sum"),
        High_Risk_Assets=("Risk_Band", lambda x: int(x.eq("High").sum())),
        Maintenance_Cost_Credits=("Maintenance_Cost_Credits", "sum"),
    )
    facility_monthly["PM_Completion_Pct"] = np.where(
        facility_monthly["PM_Due"].gt(0),
        100 * facility_monthly["PM_Completed"] / facility_monthly["PM_Due"],
        np.nan,
    )
    facility_monthly["Synthetic_Data"] = True

    latest_month = performance["Month"].max()
    latest_asset_status = performance.loc[performance["Month"].eq(latest_month)].copy()
    latest_asset_status = latest_asset_status.merge(
        asset_register[["Asset_ID", "Install_Date", "Expected_Life_Years_Assumption", "Synthetic_Replacement_Cost_Credits"]],
        on="Asset_ID", how="left", validate="one_to_one",
    )
    latest_asset_status = latest_asset_status.sort_values(
        ["Risk_Band", "Equipment_Risk_Score", "Unplanned_Downtime_Hours"],
        ascending=[False, False, False],
    )

    assumptions = {
        "synthetic_data": True,
        "seed": seed,
        "periods": periods,
        "start_month": str(months[0].date()),
        "end_month": str(months[-1].date()),
        "equipment_types": len(EQUIPMENT_CATALOG),
        "asset_count": int(len(asset_register)),
        "asset_month_records": int(len(performance)),
        "maintenance_work_orders": int(len(work_order_frame)),
        "limitations": [
            "All assets, acquisition dates, failures, maintenance events, downtime and costs are synthetic.",
            "Failure probabilities, expected lives, maintenance intervals, criticality and risk weights are illustrative assumptions, not official equipment standards.",
            "Abstract maintenance credits are not MWK and are not supplier quotations.",
            "No sensor telemetry, engineering inspection, service logs, spare-parts records or verified asset inventory is represented.",
            "Uptime is a generated scenario metric and must not be interpreted as verified clinical service availability.",
        ],
    }
    return {
        "equipment_catalog": catalog,
        "asset_register": asset_register,
        "asset_monthly_performance": performance,
        "facility_monthly_summary": facility_monthly,
        "maintenance_work_orders": work_order_frame,
        "latest_asset_status": latest_asset_status,
        "assumptions": assumptions,
    }


def run_equipment_maintenance(
    facility_path: Path,
    output_dir: Path,
    periods: int = 60,
    start_month: str = "2021-01-01",
    seed: int = 42,
) -> dict[str, Any]:
    """Read facility dimension, generate profiles and write CSV/JSON outputs."""
    facility_path = Path(facility_path)
    output_dir = Path(output_dir)
    if not facility_path.exists():
        raise FileNotFoundError(f"Facility dimension not found: {facility_path}")
    facilities = pd.read_csv(facility_path)
    profiles = build_equipment_maintenance_profiles(
        facilities, periods=periods, start_month=start_month, seed=seed
    )
    output_names = {
        "equipment_catalog": "equipment_catalog.csv",
        "asset_register": "facility_equipment_asset_register.csv",
        "asset_monthly_performance": "equipment_asset_monthly_performance.csv",
        "facility_monthly_summary": "facility_equipment_monthly_summary.csv",
        "maintenance_work_orders": "equipment_maintenance_work_orders.csv",
        "latest_asset_status": "equipment_latest_asset_risk_status.csv",
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    for key, filename in output_names.items():
        profiles[key].to_csv(output_dir / filename, index=False)
    report = {
        "synthetic_data": True,
        "facilities": int(facilities["Facility_ID"].nunique()),
        "assets": int(len(profiles["asset_register"])),
        "asset_month_records": int(len(profiles["asset_monthly_performance"])),
        "maintenance_work_orders": int(len(profiles["maintenance_work_orders"])),
        "latest_high_risk_assets": int(profiles["latest_asset_status"]["Risk_Band"].eq("High").sum()),
        "latest_mean_operational_uptime_pct": round(float(profiles["latest_asset_status"]["Operational_Uptime_Pct"].mean()), 2),
        "outputs": list(output_names.values()),
        "limitations": profiles["assumptions"]["limitations"],
    }
    (output_dir / "equipment_maintenance_report.json").write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--facility-path", type=Path, default=Path("data/warehouse/raw/facility_dimension.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/warehouse/analytics"))
    parser.add_argument("--periods", type=int, default=60)
    parser.add_argument("--start-month", default="2021-01-01")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    print(json.dumps(run_equipment_maintenance(
        args.facility_path, args.output_dir, periods=args.periods,
        start_month=args.start_month, seed=args.seed,
    ), indent=2))


if __name__ == "__main__":
    main()
