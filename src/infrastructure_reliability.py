"""Synthetic facility infrastructure, utilities reliability and resilience analytics.

All infrastructure attributes and interruption events are simulated. This module
is a portfolio scenario, not a facility inspection, utility-provider record,
engineering assessment or evidence of clinical service disruption.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REQUIRED_FACILITY_COLUMNS = [
    "Facility_ID", "Facility_Name", "District", "Facility_Type",
    "Urban_Rural", "Catchment_Population",
]

POWER_SOURCES = ["Grid", "Solar + battery", "Grid + generator", "Solar + generator"]
WATER_SOURCES = ["Piped supply", "Borehole", "Protected well", "Mixed supply"]
CONNECTIVITY_TYPES = ["Mobile broadband", "Fixed broadband", "Mobile network (basic)", "Intermittent mobile"]

INFRASTRUCTURE_UPGRADES = [
    {"Upgrade": "Backup power package", "Domain": "Power", "Cost_Credits": 900, "Power_Reduction_Factor": 0.45, "Water_Reduction_Factor": 1.0, "Connectivity_Reduction_Factor": 1.0},
    {"Upgrade": "Water storage package", "Domain": "Water", "Cost_Credits": 650, "Power_Reduction_Factor": 1.0, "Water_Reduction_Factor": 0.40, "Connectivity_Reduction_Factor": 1.0},
    {"Upgrade": "Connectivity resilience package", "Domain": "Connectivity", "Cost_Credits": 500, "Power_Reduction_Factor": 1.0, "Water_Reduction_Factor": 1.0, "Connectivity_Reduction_Factor": 0.35},
    {"Upgrade": "Integrated resilience package", "Domain": "Integrated", "Cost_Credits": 1750, "Power_Reduction_Factor": 0.45, "Water_Reduction_Factor": 0.40, "Connectivity_Reduction_Factor": 0.35},
]


def _validate_facilities(facilities: pd.DataFrame) -> pd.DataFrame:
    missing = sorted(set(REQUIRED_FACILITY_COLUMNS) - set(facilities.columns))
    if missing:
        raise ValueError(f"Facility dimension missing required columns: {missing}")
    result = facilities[REQUIRED_FACILITY_COLUMNS].copy()
    if result.empty:
        raise ValueError("Facility dimension must contain at least one facility")
    result["Facility_ID"] = result["Facility_ID"].astype("string").str.strip()
    if result["Facility_ID"].isna().any() or result["Facility_ID"].eq("").any():
        raise ValueError("Facility_ID must be populated for every facility")
    if result["Facility_ID"].duplicated().any():
        raise ValueError("Facility_ID values must be unique")
    for column in ["Facility_Name", "District", "Facility_Type", "Urban_Rural"]:
        result[column] = result[column].fillna("Unknown").astype(str).str.strip()
    result["Catchment_Population"] = pd.to_numeric(result["Catchment_Population"], errors="coerce").fillna(0).clip(lower=0)
    return result


def build_infrastructure_profiles(
    facilities: pd.DataFrame,
    periods: int = 60,
    start_month: str = "2021-01-01",
    seed: int = 42,
    equipment_monthly: pd.DataFrame | None = None,
    budget_credits: int = 50000,
) -> dict[str, pd.DataFrame]:
    """Create facility profiles, facility-month interruption records and upgrade scenarios."""
    if isinstance(periods, bool) or not isinstance(periods, (int, np.integer)) or periods < 1:
        raise ValueError("periods must be a positive integer")
    if (isinstance(budget_credits, bool)
            or not isinstance(budget_credits, (int, np.integer))
            or budget_credits < 0):
        raise ValueError("budget_credits must be a non-negative integer")
    fac = _validate_facilities(facilities)
    months = pd.date_range(pd.Timestamp(start_month).to_period("M").to_timestamp(), periods=periods, freq="MS")
    rng = np.random.default_rng(seed)
    profile_rows: list[dict[str, Any]] = []
    monthly_rows: list[dict[str, Any]] = []

    for facility in fac.to_dict("records"):
        rural = str(facility["Urban_Rural"]).lower() == "rural"
        power_source = rng.choice(POWER_SOURCES, p=[0.30, 0.24, 0.30, 0.16] if rural else [0.48, 0.12, 0.30, 0.10])
        water_source = rng.choice(WATER_SOURCES, p=[0.16, 0.44, 0.18, 0.22] if rural else [0.52, 0.15, 0.08, 0.25])
        connectivity = rng.choice(CONNECTIVITY_TYPES, p=[0.16, 0.18, 0.24, 0.42] if rural else [0.31, 0.29, 0.16, 0.24])
        backup_hours = float(rng.uniform(2, 18) if power_source in {"Grid + generator", "Solar + generator"} else rng.uniform(0, 10))
        water_storage_days = float(rng.uniform(0.5, 4.0) if water_source in {"Borehole", "Mixed supply"} else rng.uniform(0.2, 2.5))
        profile_rows.append({
            **facility,
            "Primary_Power_Configuration": power_source,
            "Primary_Water_Source": water_source,
            "Connectivity_Modality": connectivity,
            "Illustrative_Backup_Power_Hours": round(backup_hours, 2),
            "Illustrative_Water_Storage_Days": round(water_storage_days, 2),
            "Synthetic_Data": True,
        })

        power_factor = 1.25 if rural else 0.85
        water_factor = 1.20 if rural else 0.90
        connectivity_factor = 1.30 if rural else 0.80
        if power_source == "Solar + battery":
            power_factor *= 0.72
        elif power_source == "Grid + generator":
            power_factor *= 0.78
        elif power_source == "Solar + generator":
            power_factor *= 0.62
        if water_source in {"Borehole", "Mixed supply"}:
            water_factor *= 0.78
        if connectivity in {"Intermittent mobile", "Mobile network (basic)"}:
            connectivity_factor *= 1.25

        for month in months:
            calendar_hours = int((month + pd.offsets.MonthEnd(1)).day * 24)
            power_events = int(rng.poisson(2.2 * power_factor))
            water_events = int(rng.poisson(1.4 * water_factor))
            connectivity_events = int(rng.poisson(3.0 * connectivity_factor))
            power_outage_hours = min(float(rng.gamma(1.8, 2.4, power_events).sum()), calendar_hours * 0.65) if power_events else 0.0
            water_shortage_hours = min(float(rng.gamma(1.7, 3.0, water_events).sum()), calendar_hours * 0.55) if water_events else 0.0
            connectivity_downtime = min(float(rng.gamma(2.0, 1.8, connectivity_events).sum()), calendar_hours * 0.70) if connectivity_events else 0.0
            power_backup_hours = min(power_outage_hours, backup_hours * 30.0, power_outage_hours * float(rng.uniform(0.35, 0.95)))
            unserved_power_hours = max(0.0, power_outage_hours - power_backup_hours)
            water_buffered_hours = min(water_shortage_hours, water_storage_days * 24 * float(rng.uniform(0.25, 0.8)))
            unserved_water_hours = max(0.0, water_shortage_hours - water_buffered_hours)
            power_availability = 100 * (calendar_hours - unserved_power_hours) / calendar_hours
            water_availability = 100 * (calendar_hours - unserved_water_hours) / calendar_hours
            connectivity_availability = 100 * (calendar_hours - connectivity_downtime) / calendar_hours
            resilience = (
                0.40 * power_availability + 0.30 * water_availability
                + 0.20 * connectivity_availability
                + 0.10 * min(100, backup_hours / 18 * 100)
            )
            monthly_rows.append({
                "Facility_ID": facility["Facility_ID"],
                "Facility_Name": facility["Facility_Name"],
                "District": facility["District"],
                "Month": month,
                "Calendar_Hours": calendar_hours,
                "Power_Interruption_Events": power_events,
                "Power_Interruption_Hours": round(power_outage_hours, 2),
                "Backup_Power_Hours_Provided": round(power_backup_hours, 2),
                "Unserved_Power_Interruption_Hours": round(unserved_power_hours, 2),
                "Water_Interruption_Events": water_events,
                "Water_Shortage_Hours": round(water_shortage_hours, 2),
                "Water_Buffered_Hours": round(water_buffered_hours, 2),
                "Unserved_Water_Shortage_Hours": round(unserved_water_hours, 2),
                "Connectivity_Interruption_Events": connectivity_events,
                "Connectivity_Downtime_Hours": round(connectivity_downtime, 2),
                "Power_Availability_Pct": round(power_availability, 2),
                "Water_Availability_Pct": round(water_availability, 2),
                "Connectivity_Availability_Pct": round(connectivity_availability, 2),
                "Infrastructure_Resilience_Score": round(resilience, 2),
                "Synthetic_Data": True,
            })

    profiles = pd.DataFrame(profile_rows)
    monthly = pd.DataFrame(monthly_rows)
    latest_month = monthly["Month"].max()
    latest = monthly.loc[monthly["Month"].eq(latest_month)].merge(
        profiles[["Facility_ID", "Primary_Power_Configuration", "Primary_Water_Source", "Connectivity_Modality",
                  "Illustrative_Backup_Power_Hours", "Illustrative_Water_Storage_Days"]],
        on="Facility_ID", how="left", validate="one_to_one",
    )
    latest["Infrastructure_Risk_Band"] = pd.cut(
        latest["Infrastructure_Resilience_Score"],
        bins=[-0.01, 70, 85, 100.01], labels=["High", "Moderate", "Lower"],
    ).astype(str)
    latest = latest.sort_values(["Infrastructure_Resilience_Score", "Facility_ID"]).reset_index(drop=True)

    association = pd.DataFrame()
    if equipment_monthly is not None and not equipment_monthly.empty:
        required = {"Facility_ID", "Month", "Mean_Operational_Uptime_Pct"}
        if required.issubset(equipment_monthly.columns):
            equipment = equipment_monthly[list(required)].copy()
            equipment["Month"] = pd.to_datetime(equipment["Month"], errors="coerce").dt.to_period("M").dt.to_timestamp()
            paired = monthly.merge(equipment, on=["Facility_ID", "Month"], how="inner", validate="one_to_one")
            if not paired.empty:
                paired["Power_Interruption_Band"] = pd.cut(
                    paired["Unserved_Power_Interruption_Hours"],
                    bins=[-0.01, 2, 8, float("inf")], labels=["0–2 hours", "2–8 hours", "8+ hours"],
                ).astype(str)
                association = paired.groupby("Power_Interruption_Band", as_index=False, observed=False).agg(
                    Facility_Months=("Facility_ID", "size"),
                    Mean_Unserved_Power_Hours=("Unserved_Power_Interruption_Hours", "mean"),
                    Mean_Operational_Uptime_Pct=("Mean_Operational_Uptime_Pct", "mean"),
                    Mean_Resilience_Score=("Infrastructure_Resilience_Score", "mean"),
                )
                association["Interpretation"] = "Descriptive association only; not causal evidence."
                paired.attrs["correlation_power_hours_uptime"] = (
                    float(paired["Unserved_Power_Interruption_Hours"].corr(paired["Mean_Operational_Uptime_Pct"]))
                    if paired["Unserved_Power_Interruption_Hours"].nunique() > 1 and paired["Mean_Operational_Uptime_Pct"].nunique() > 1 else None
                )
                association.attrs["paired_facility_months"] = len(paired)
                association.attrs["correlation_power_hours_uptime"] = paired.attrs["correlation_power_hours_uptime"]

    # Scenario table: each facility is evaluated under each illustrative package.
    scenario_rows: list[dict[str, Any]] = []
    for row in latest.to_dict("records"):
        for upgrade in INFRASTRUCTURE_UPGRADES:
            power_gain = row["Unserved_Power_Interruption_Hours"] * upgrade["Power_Reduction_Factor"]
            water_gain = row["Unserved_Water_Shortage_Hours"] * upgrade["Water_Reduction_Factor"]
            connectivity_gain = row["Connectivity_Downtime_Hours"] * upgrade["Connectivity_Reduction_Factor"]
            avoided = power_gain + water_gain + connectivity_gain
            scenario_rows.append({
                "Facility_ID": row["Facility_ID"], "Facility_Name": row["Facility_Name"],
                "District": row["District"], "Upgrade": upgrade["Upgrade"], "Domain": upgrade["Domain"],
                "Synthetic_Cost_Credits": upgrade["Cost_Credits"],
                "Baseline_Unserved_Interruption_Hours": round(
                    row["Unserved_Power_Interruption_Hours"] + row["Unserved_Water_Shortage_Hours"] + row["Connectivity_Downtime_Hours"], 2
                ),
                "Illustrative_Avoided_Interruption_Hours": round(avoided, 2),
                "Avoided_Hours_Per_100_Credits": round(avoided / upgrade["Cost_Credits"] * 100, 3),
                "Synthetic_Data": True,
            })
    scenarios = pd.DataFrame(scenario_rows).sort_values(
        ["Avoided_Hours_Per_100_Credits", "Facility_ID"], ascending=[False, True]
    ).reset_index(drop=True)
    scenarios["Selected_Package_For_Facility"] = False
    best_indices = scenarios.groupby("Facility_ID")["Avoided_Hours_Per_100_Credits"].idxmax()
    best_indices = scenarios.loc[best_indices].sort_values(
        "Avoided_Hours_Per_100_Credits", ascending=False
    ).index
    scenarios.loc[best_indices, "Selected_Package_For_Facility"] = True
    scenarios["Within_Illustrative_Budget"] = False
    remaining = int(budget_credits)
    for idx in best_indices:
        row = scenarios.loc[idx]
        cost = int(row["Synthetic_Cost_Credits"])
        if cost <= remaining:
            scenarios.loc[idx, "Within_Illustrative_Budget"] = True
            remaining -= cost
    scenarios["Budget_Credits_Available"] = int(budget_credits)
    scenarios["Budget_Credits_Unallocated"] = remaining
    return {
        "facility_profiles": profiles,
        "monthly_reliability": monthly,
        "latest_resilience": latest,
        "equipment_association": association,
        "upgrade_scenarios": scenarios,
    }


def run_infrastructure_planning(
    facility_path: Path,
    output_dir: Path,
    periods: int = 60,
    start_month: str = "2021-01-01",
    seed: int = 42,
    budget_credits: int = 50000,
    equipment_monthly_path: Path | None = None,
) -> dict[str, Any]:
    facility_path, output_dir = Path(facility_path), Path(output_dir)
    facilities = pd.read_csv(facility_path)
    equipment = pd.read_csv(equipment_monthly_path) if equipment_monthly_path and Path(equipment_monthly_path).exists() else None
    result = build_infrastructure_profiles(facilities, periods, start_month, seed, equipment, budget_credits)
    filenames = {
        "facility_infrastructure_profiles": "facility_infrastructure_profiles.csv",
        "monthly_infrastructure_reliability": "facility_monthly_infrastructure_reliability.csv",
        "latest_infrastructure_resilience": "facility_latest_infrastructure_resilience.csv",
        "equipment_infrastructure_association": "equipment_infrastructure_association.csv",
        "infrastructure_upgrade_scenarios": "infrastructure_upgrade_scenarios.csv",
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    for key, filename in filenames.items():
        result[key].to_csv(output_dir / filename, index=False)
    latest = result["latest_resilience"]
    report = {
        "synthetic_data": True,
        "facilities": int(facilities["Facility_ID"].nunique()),
        "facility_month_records": int(len(result["monthly_reliability"])),
        "latest_high_risk_facilities": int(latest["Infrastructure_Risk_Band"].eq("High").sum()),
        "latest_mean_resilience_score": round(float(latest["Infrastructure_Resilience_Score"].mean()), 2),
        "equipment_association_facility_months": int(result["equipment_association"].attrs.get("paired_facility_months", 0)),
        "power_interruption_uptime_correlation": result["equipment_association"].attrs.get("correlation_power_hours_uptime"),
        "upgrade_scenarios_within_budget": int(result["upgrade_scenarios"]["Within_Illustrative_Budget"].sum()),
        "limitations": [
            "All utility configurations, interruption events, backup capacities and availability metrics are synthetic.",
            "No utility-provider, sensor, generator-log, water-quality or connectivity telemetry is represented.",
            "Infrastructure availability is not verified clinical service availability and does not establish patient impact.",
            "Upgrade costs and avoided-hour factors are abstract scenario assumptions; credits are not MWK.",
            "Equipment comparisons are descriptive associations, not causal estimates.",
            "Risk bands and weights are illustrative review aids, not engineering or national standards.",
        ],
        "outputs": list(filenames.values()),
    }
    (output_dir / "infrastructure_planning_report.json").write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--facilities", type=Path, default=Path("data/warehouse/raw/facility_dimension.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/warehouse/analytics"))
    parser.add_argument("--periods", type=int, default=60)
    parser.add_argument("--start-month", default="2021-01-01")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--budget-credits", type=int, default=50000)
    parser.add_argument("--equipment-monthly", type=Path, default=Path("data/warehouse/analytics/facility_equipment_monthly_summary.csv"))
    args = parser.parse_args()
    print(json.dumps(run_infrastructure_planning(
        args.facilities, args.output_dir, args.periods, args.start_month,
        args.seed, args.budget_credits, args.equipment_monthly,
    ), indent=2))


if __name__ == "__main__":
    main()
