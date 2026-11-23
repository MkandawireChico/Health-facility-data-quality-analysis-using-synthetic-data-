"""Illustrative resource-capacity planning and constrained allocation scenarios.

All resource units and capacity assumptions are synthetic planning abstractions.
They are not staffing norms, clinical standards, budgets, or recommendations.
Catchment population is used only as a configurable planning proxy, never as
observed patient volume or service coverage.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REQUIRED_FACILITY_COLUMNS = {
    "Facility_ID", "Facility_Name", "District", "Facility_Type",
    "Urban_Rural", "Catchment_Population",
}


def build_resource_planning_profiles(
    facilities: pd.DataFrame,
    resource_pool: int = 120,
    seed: int = 42,
    units_per_10000_population: float = 2.5,
) -> dict[str, pd.DataFrame | dict[str, Any]]:
    """Build facility capacity gaps and three constrained allocation scenarios.

    The baseline requirement is a transparent scenario assumption:
    population-scaled units plus a facility-type increment. Available units
    are synthetic and seeded. Allocation uses a deterministic one-unit-at-a-
    time priority rule and never allocates beyond a facility's calculated gap.
    """
    missing = REQUIRED_FACILITY_COLUMNS - set(facilities.columns)
    if missing:
        raise ValueError(f"Facility dimension missing required columns: {sorted(missing)}")
    if not isinstance(resource_pool, (int, np.integer)) or resource_pool < 0:
        raise ValueError("resource_pool must be a non-negative integer")
    if units_per_10000_population <= 0:
        raise ValueError("units_per_10000_population must be positive")

    frame = facilities[list(REQUIRED_FACILITY_COLUMNS)].copy()
    frame["Catchment_Population"] = pd.to_numeric(frame["Catchment_Population"], errors="coerce")
    if frame["Facility_ID"].isna().any() or frame["Facility_ID"].duplicated().any():
        raise ValueError("Facility_ID must be populated and unique")
    if frame["Catchment_Population"].isna().any() or frame["Catchment_Population"].lt(0).any():
        raise ValueError("Catchment_Population must contain non-negative numeric values")

    type_increment = {
        "Health Centre": 1,
        "Community Hospital": 2,
        "District Hospital": 4,
    }
    frame["Illustrative_Requirement_Units"] = (
        np.ceil(frame["Catchment_Population"] / 10000 * units_per_10000_population)
        + frame["Facility_Type"].map(type_increment).fillna(1)
    ).astype(int).clip(lower=1)

    rng = np.random.default_rng(seed)
    capacity_ratio = rng.uniform(0.55, 1.15, len(frame))
    frame["Synthetic_Available_Units"] = np.floor(
        frame["Illustrative_Requirement_Units"] * capacity_ratio
    ).astype(int)
    frame["Baseline_Gap_Units"] = (
        frame["Illustrative_Requirement_Units"] - frame["Synthetic_Available_Units"]
    ).clip(lower=0).astype(int)
    frame["Baseline_Capacity_Coverage_Pct"] = (
        100 * frame["Synthetic_Available_Units"]
        / frame["Illustrative_Requirement_Units"]
    ).round(2)

    def allocate(strategy: str) -> pd.DataFrame:
        result = frame[[
            "Facility_ID", "Facility_Name", "District", "Facility_Type",
            "Urban_Rural", "Catchment_Population",
            "Illustrative_Requirement_Units", "Synthetic_Available_Units",
            "Baseline_Gap_Units",
        ]].copy()
        result["Allocated_Units"] = 0
        remaining = int(resource_pool)
        rural = result["Urban_Rural"].astype("string").str.lower().eq("rural")
        for _ in range(remaining):
            residual = result["Baseline_Gap_Units"] - result["Allocated_Units"]
            eligible = residual.gt(0)
            if not eligible.any():
                break
            if strategy == "equal":
                score = pd.Series(1.0, index=result.index)
            elif strategy == "equity":
                score = pd.Series(np.where(rural, 1.25, 1.0), index=result.index)
            else:
                score = residual.astype(float)
            score = score.where(eligible, -1.0)
            chosen = sorted(
                result.index[eligible],
                key=lambda idx: (-float(score.loc[idx]), str(result.loc[idx, "Facility_ID"])),
            )[0]
            result.loc[chosen, "Allocated_Units"] += 1
        result["Residual_Gap_Units"] = (
            result["Baseline_Gap_Units"] - result["Allocated_Units"]
        ).clip(lower=0)
        result["Post_Allocation_Coverage_Pct"] = (
            100 * (result["Synthetic_Available_Units"] + result["Allocated_Units"])
            / result["Illustrative_Requirement_Units"]
        ).round(2)
        result["Scenario"] = strategy
        return result

    scenarios = pd.concat(
        [allocate("gap_priority"), allocate("equity"), allocate("equal")],
        ignore_index=True,
    )
    summary = (
        scenarios.groupby("Scenario", as_index=False)
        .agg(
            facilities=("Facility_ID", "nunique"),
            allocated_units=("Allocated_Units", "sum"),
            facilities_fully_covered=("Residual_Gap_Units", lambda x: int(x.eq(0).sum())),
            residual_gap_units=("Residual_Gap_Units", "sum"),
            mean_residual_gap_units=("Residual_Gap_Units", "mean"),
            mean_post_allocation_coverage_pct=("Post_Allocation_Coverage_Pct", "mean"),
        )
    )
    summary["resource_pool"] = int(resource_pool)
    summary["unallocated_pool_units"] = (
        summary["resource_pool"] - summary["allocated_units"]
    ).clip(lower=0)
    summary["synthetic_data"] = True
    return {
        "facility_capacity": frame,
        "scenario_allocations": scenarios,
        "scenario_summary": summary,
        "assumptions": {
            "synthetic_data": True,
            "resource_pool": int(resource_pool),
            "seed": int(seed),
            "units_per_10000_population": float(units_per_10000_population),
            "facility_type_increment_units": type_increment,
            "available_capacity_generation": "Illustrative requirement multiplied by seeded uniform ratio from 0.55 to 1.15, rounded down.",
            "allocation_rules": {
                "gap_priority": "Greedily allocates one unit to the facility with the largest remaining gap; Facility_ID breaks ties.",
                "equity": "Greedily allocates one unit using a 1.25 rural weighting and 1.0 otherwise; Facility_ID breaks ties.",
                "equal": "Greedily allocates one unit per eligible facility in stable Facility_ID order, repeating rounds.",
            },
            "limitations": [
                "Resource units are abstract and are not staff headcounts or monetary budgets.",
                "Requirements are illustrative scenario assumptions, not official Malawi staffing or service standards.",
                "Catchment population is only a planning proxy; it is not patient volume, unique people served, or coverage.",
                "Scenarios are deterministic heuristics, not validated optimal allocations or operational recommendations.",
            ],
        },
    }


def run_resource_planning(
    facility_path: Path,
    output_dir: Path,
    resource_pool: int = 120,
    seed: int = 42,
    units_per_10000_population: float = 2.5,
) -> dict[str, Any]:
    facilities = pd.read_csv(facility_path)
    result = build_resource_planning_profiles(
        facilities, resource_pool, seed, units_per_10000_population
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "facility_capacity": "facility_resource_capacity.csv",
        "scenario_allocations": "resource_allocation_scenarios.csv",
        "scenario_summary": "resource_allocation_scenario_summary.csv",
    }
    for key, filename in outputs.items():
        result[key].to_csv(output_dir / filename, index=False)
    report = {
        **result["assumptions"],
        "facility_count": int(len(result["facility_capacity"])),
        "outputs": list(outputs.values()),
    }
    (output_dir / "resource_planning_report.json").write_text(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--facilities", type=Path, default=Path("data/warehouse/raw/facility_dimension.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/warehouse/analytics"))
    parser.add_argument("--resource-pool", type=int, default=120)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--units-per-10000-population", type=float, default=2.5)
    args = parser.parse_args()
    print(json.dumps(run_resource_planning(
        args.facilities, args.output_dir, args.resource_pool, args.seed,
        args.units_per_10000_population,
    ), indent=2))
