"""Synthetic cold-chain monitoring, batch traceability and expiry-risk analytics.

All facilities, lots, temperature readings, receipts, consumption and wastage are
synthetic. Temperature limits, shelf lives and alert thresholds are illustrative
modelling assumptions, not Malawi Ministry of Health standards or product labels.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

COLD_CHAIN_CATALOG = [
    {"Commodity_ID": "CC-001", "Commodity": "Illustrative vaccine product A", "Programme": "Child Health", "Unit": "dose", "Monthly_Demand_per_10000": 52, "Shelf_Life_Days": 540, "Synthetic_Unit_Cost_Credits": 7},
    {"Commodity_ID": "CC-002", "Commodity": "Illustrative vaccine product B", "Programme": "Immunisation", "Unit": "dose", "Monthly_Demand_per_10000": 34, "Shelf_Life_Days": 365, "Synthetic_Unit_Cost_Credits": 9},
    {"Commodity_ID": "CC-003", "Commodity": "Illustrative temperature-sensitive medicine", "Programme": "Maternal Health", "Unit": "unit", "Monthly_Demand_per_10000": 18, "Shelf_Life_Days": 270, "Synthetic_Unit_Cost_Credits": 12},
    {"Commodity_ID": "CC-004", "Commodity": "Illustrative diagnostic reagent", "Programme": "Laboratory", "Unit": "test", "Monthly_Demand_per_10000": 26, "Shelf_Life_Days": 180, "Synthetic_Unit_Cost_Credits": 5},
]
REQUIRED_FACILITY_COLUMNS = {
    "Facility_ID", "Facility_Name", "District", "Facility_Type",
    "Urban_Rural", "Catchment_Population",
}
TEMPERATURE_MIN_C = 2.0
TEMPERATURE_MAX_C = 8.0


def _temperature_month(
    rng: np.random.Generator, month: pd.Timestamp,
    temperature_min_c: float, temperature_max_c: float,
) -> dict[str, Any]:
    """Create daily synthetic sensor observations for one facility-month."""
    days = int(month.days_in_month)
    observed_mask = rng.random(days) >= 0.04
    observed_days = int(observed_mask.sum())
    if observed_days:
        daily_mean = rng.normal(5.0, 0.85, days)
        daily_min = daily_mean - rng.uniform(0.3, 1.3, days)
        daily_max = daily_mean + rng.uniform(0.3, 1.3, days)
        # Occasional controlled excursions create review examples.
        if rng.random() < 0.12:
            excursion_index = int(rng.integers(0, days))
            if rng.random() < 0.5:
                daily_min[excursion_index] = rng.uniform(-0.5, 1.8)
            else:
                daily_max[excursion_index] = rng.uniform(8.3, 12.0)
        excursion = observed_mask & (
            (daily_min < temperature_min_c) | (daily_max > temperature_max_c)
        )
        observed_mean = daily_mean[observed_mask]
        observed_min = np.minimum(daily_min, daily_max)[observed_mask]
        observed_max = np.maximum(daily_min, daily_max)[observed_mask]
        excursion_days = int(excursion.sum())
        excursion_hours = int(sum(rng.integers(1, 9) for _ in range(excursion_days)))
        mean_c = float(np.mean(observed_mean))
        min_c = float(np.min(observed_min))
        max_c = float(np.max(observed_max))
    else:
        excursion_days = excursion_hours = 0
        mean_c = min_c = max_c = float("nan")
    coverage = observed_days / days
    return {
        "Sensor_ID": None,
        "Days_In_Month": days,
        "Observed_Days": observed_days,
        "Temperature_Data_Coverage_Pct": round(coverage * 100, 2),
        "Mean_Temperature_C": round(mean_c, 2) if pd.notna(mean_c) else np.nan,
        "Minimum_Temperature_C": round(min_c, 2) if pd.notna(min_c) else np.nan,
        "Maximum_Temperature_C": round(max_c, 2) if pd.notna(max_c) else np.nan,
        "Excursion_Days": excursion_days,
        "Estimated_Excursion_Hours": excursion_hours,
        "Temperature_Excursion_Flag": bool(excursion_days > 0),
        "Temperature_Data_Status": (
            "Missing" if observed_days == 0 else
            "Incomplete" if coverage < 0.80 else "Sufficient"
        ),
    }


def build_cold_chain_profiles(
    facilities: pd.DataFrame,
    periods: int = 24,
    start_month: str = "2025-01-01",
    seed: int = 42,
    temperature_min_c: float = TEMPERATURE_MIN_C,
    temperature_max_c: float = TEMPERATURE_MAX_C,
) -> dict[str, pd.DataFrame | dict[str, Any]]:
    """Simulate facility sensors and FEFO-managed batch inventories."""
    missing = REQUIRED_FACILITY_COLUMNS - set(facilities.columns)
    if missing:
        raise ValueError(f"Facility dimension missing required columns: {sorted(missing)}")
    if not isinstance(periods, (int, np.integer)) or periods < 1:
        raise ValueError("periods must be a positive integer")
    if not np.isfinite(temperature_min_c) or not np.isfinite(temperature_max_c) or temperature_min_c >= temperature_max_c:
        raise ValueError("Temperature bounds must be finite and minimum must be below maximum")

    fac = facilities[list(REQUIRED_FACILITY_COLUMNS)].copy()
    if fac.empty:
        raise ValueError("Facility dimension must contain at least one facility")
    fac["Catchment_Population"] = pd.to_numeric(fac["Catchment_Population"], errors="coerce")
    if fac["Facility_ID"].isna().any() or fac["Facility_ID"].duplicated().any():
        raise ValueError("Facility_ID must be populated and unique")
    if fac["Catchment_Population"].isna().any() or fac["Catchment_Population"].lt(0).any():
        raise ValueError("Catchment_Population must contain non-negative numeric values")

    catalog = pd.DataFrame(COLD_CHAIN_CATALOG)
    months = pd.date_range(start=start_month, periods=periods, freq="MS")
    rng = np.random.default_rng(seed)
    type_factor = fac["Facility_Type"].map({
        "Health Centre": 0.75, "Community Hospital": 1.15,
        "District Hospital": 1.45,
    }).fillna(1.0).to_numpy(dtype=float)

    temperature_rows: list[dict[str, Any]] = []
    batch_rows: list[dict[str, Any]] = []
    risk_rows: list[dict[str, Any]] = []
    inventory_state: dict[tuple[str, str], list[dict[str, Any]]] = {}

    for facility_index, facility in fac.reset_index(drop=True).iterrows():
        facility_id = str(facility["Facility_ID"])
        sensor_id = f"SENSOR-{facility_id}"
        population_factor = max(float(facility["Catchment_Population"]), 0.0) / 10000
        for month in months:
            temp = _temperature_month(rng, month, temperature_min_c, temperature_max_c)
            temp["Sensor_ID"] = sensor_id
            temp.update({
                "Facility_ID": facility_id,
                "Facility_Name": facility["Facility_Name"],
                "District": facility["District"],
                "Month": month,
                "Synthetic_Data": True,
                "Assumed_Minimum_Temperature_C": temperature_min_c,
                "Assumed_Maximum_Temperature_C": temperature_max_c,
            })
            temperature_rows.append(temp)

            for commodity in COLD_CHAIN_CATALOG:
                commodity_id = commodity["Commodity_ID"]
                base_demand = (
                    commodity["Monthly_Demand_per_10000"]
                    * population_factor * type_factor[facility_index]
                )
                demand = int(rng.poisson(max(base_demand, 0)))
                receipt_qty = int(rng.poisson(max(base_demand * 1.15, 0)))
                lots: list[dict[str, Any]] = []
                # Keep a lot-level inventory state for this facility and commodity.
                state_key = (facility_id, commodity_id)
                lots = inventory_state.setdefault(state_key, [])

                month_start = month
                month_end = month + pd.offsets.MonthEnd(0)
                current_lots: list[dict[str, Any]] = []
                monthly_expired = 0
                # Expire lots whose expiry date was before the current month.
                for lot in lots:
                    opening = int(lot["closing_units"])
                    if pd.Timestamp(lot["expiry_date"]) < month_start:
                        expired = opening
                        monthly_expired += expired
                        batch_rows.append({
                            **lot["identity"],
                            "Month": month,
                            "Opening_Stock_Units": opening,
                            "Receipts_Units": 0,
                            "Fulfilled_Consumption_Units": 0,
                            "Expired_Units": expired,
                            "Closing_Stock_Units": 0,
                            "Days_To_Expiry_At_Month_End": int((pd.Timestamp(lot["expiry_date"]) - month_end).days),
                            "Near_Expiry_30_Days": False,
                            "Near_Expiry_60_Days": False,
                            "Near_Expiry_90_Days": False,
                            "Temperature_Excursion_Days": temp["Excursion_Days"],
                            "Temperature_Excursion_Flag": temp["Temperature_Excursion_Flag"],
                            "Temperature_Data_Status": temp["Temperature_Data_Status"],
                            "Synthetic_Data": True,
                        })
                    else:
                        lot["opening_units"] = opening
                        lot["receipts_units"] = 0
                        lot["consumed_units"] = 0
                        lot["expired_units"] = 0
                        current_lots.append(lot)

                if receipt_qty > 0:
                    lot_number = len([x for x in current_lots if x["identity"]["Receipt_Month"] == month.strftime("%Y-%m")]) + 1
                    receipt_date = month_start + pd.Timedelta(days=int(rng.integers(0, max(month.days_in_month, 1))))
                    shelf_life = int(commodity["Shelf_Life_Days"] * rng.uniform(0.80, 1.20))
                    expiry_date = receipt_date + pd.Timedelta(days=shelf_life)
                    manufacture_date = receipt_date - pd.Timedelta(days=int(rng.integers(30, 181)))
                    batch_id = f"{facility_id}-{commodity_id}-{month:%Y%m}-{lot_number:02d}"
                    identity = {
                        "Batch_ID": batch_id,
                        "Facility_ID": facility_id,
                        "Facility_Name": facility["Facility_Name"],
                        "District": facility["District"],
                        "Commodity_ID": commodity_id,
                        "Commodity": commodity["Commodity"],
                        "Programme": commodity["Programme"],
                        "Unit": commodity["Unit"],
                        "Synthetic_Supplier_ID": f"SUP-{int(rng.integers(1, 8)):03d}",
                        "Manufacture_Date": manufacture_date,
                        "Receipt_Date": receipt_date,
                        "Receipt_Month": month.strftime("%Y-%m"),
                        "Expiry_Date": expiry_date,
                        "Synthetic_Unit_Cost_Credits": commodity["Synthetic_Unit_Cost_Credits"],
                    }
                    current_lots.append({
                        "identity": identity, "closing_units": receipt_qty,
                        "opening_units": 0, "receipts_units": receipt_qty,
                        "consumed_units": 0, "expired_units": 0,
                    })

                # FEFO: consume lots with the earliest expiry date first.
                remaining_demand = demand
                for lot in sorted(current_lots, key=lambda item: (item["identity"]["Expiry_Date"], item["identity"]["Batch_ID"])):
                    available = int(lot["opening_units"] + lot["receipts_units"])
                    consumed = min(available, remaining_demand)
                    lot["consumed_units"] = consumed
                    lot["closing_units"] = available - consumed
                    remaining_demand -= consumed

                next_lots: list[dict[str, Any]] = []
                fulfilled = demand - remaining_demand
                near_expiry_30 = near_expiry_60 = near_expiry_90 = 0
                closing_total = 0
                expiry_risk_90 = 0
                min_days_to_expiry: int | None = None
                for lot in current_lots:
                    expiry_date = pd.Timestamp(lot["identity"]["Expiry_Date"])
                    days_to_expiry = int((expiry_date - month_end).days)
                    expired = 0
                    closing = int(lot["closing_units"])
                    if expiry_date <= month_end:
                        expired = closing
                        closing = 0
                        monthly_expired += expired
                    lot["closing_units"] = closing
                    if closing > 0:
                        closing_total += closing
                        min_days_to_expiry = days_to_expiry if min_days_to_expiry is None else min(min_days_to_expiry, days_to_expiry)
                        if 0 < days_to_expiry <= 30:
                            near_expiry_30 += closing
                        if 0 < days_to_expiry <= 60:
                            near_expiry_60 += closing
                        if 0 < days_to_expiry <= 90:
                            near_expiry_90 += closing
                        if 0 < days_to_expiry <= 90:
                            expiry_risk_90 += closing

                    batch_rows.append({
                        **lot["identity"],
                        "Month": month,
                        "Opening_Stock_Units": int(lot["opening_units"]),
                        "Receipts_Units": int(lot["receipts_units"]),
                        "Fulfilled_Consumption_Units": int(lot["consumed_units"]),
                        "Expired_Units": int(expired),
                        "Closing_Stock_Units": closing,
                        "Days_To_Expiry_At_Month_End": days_to_expiry,
                        "Near_Expiry_30_Days": bool(closing > 0 and 0 < days_to_expiry <= 30),
                        "Near_Expiry_60_Days": bool(closing > 0 and 0 < days_to_expiry <= 60),
                        "Near_Expiry_90_Days": bool(closing > 0 and 0 < days_to_expiry <= 90),
                        "Temperature_Excursion_Days": temp["Excursion_Days"],
                        "Temperature_Excursion_Flag": temp["Temperature_Excursion_Flag"],
                        "Temperature_Data_Status": temp["Temperature_Data_Status"],
                        "Synthetic_Data": True,
                    })
                    if closing > 0:
                        next_lots.append(lot)

                unmet = int(remaining_demand)
                coverage = temp["Temperature_Data_Coverage_Pct"]
                temperature_status = temp["Temperature_Data_Status"]
                excursion_rate = (
                    temp["Excursion_Days"] / temp["Observed_Days"]
                    if temp["Observed_Days"] else np.nan
                )
                expiry_share = expiry_risk_90 / closing_total if closing_total else 0.0
                score = (
                    50 * excursion_rate + 50 * expiry_share
                    if pd.notna(excursion_rate) else np.nan
                )
                if pd.isna(score):
                    risk_band = "Data Gap"
                elif temp["Excursion_Days"] >= 2 or expiry_share >= 0.50:
                    risk_band = "High"
                elif temp["Excursion_Days"] > 0 or expiry_risk_90 > 0:
                    risk_band = "Medium"
                else:
                    risk_band = "Low"
                risk_rows.append({
                    "Facility_ID": facility_id,
                    "Facility_Name": facility["Facility_Name"],
                    "District": facility["District"],
                    "Month": month,
                    "Commodity_ID": commodity_id,
                    "Commodity": commodity["Commodity"],
                    "Programme": commodity["Programme"],
                    "Demand_Units": demand,
                    "Fulfilled_Consumption_Units": fulfilled,
                    "Unmet_Demand_Units": unmet,
                    "Expired_Units": monthly_expired,
                    "Closing_Stock_Units": closing_total,
                    "Near_Expiry_30_Day_Units": near_expiry_30,
                    "Near_Expiry_60_Day_Units": near_expiry_60,
                    "Near_Expiry_90_Day_Units": near_expiry_90,
                    "Days_To_Nearest_Expiry": min_days_to_expiry,
                    "Temperature_Excursion_Days": temp["Excursion_Days"],
                    "Estimated_Excursion_Hours": temp["Estimated_Excursion_Hours"],
                    "Temperature_Data_Coverage_Pct": coverage,
                    "Temperature_Data_Status": temperature_status,
                    "Temperature_Excursion_Flag": temp["Temperature_Excursion_Flag"],
                    "Expiry_Risk_Share_Pct": round(expiry_share * 100, 2),
                    "Cold_Chain_Risk_Score": round(float(score), 2) if pd.notna(score) else np.nan,
                    "Risk_Band": risk_band,
                    "Synthetic_Data": True,
                })
                inventory_state[state_key] = next_lots

    temperature = pd.DataFrame(temperature_rows)
    batch_ledger = pd.DataFrame(batch_rows)
    risk_summary = pd.DataFrame(risk_rows)
    assumptions = {
        "synthetic_data": True,
        "commodity_count": len(catalog),
        "temperature_min_c_assumption": temperature_min_c,
        "temperature_max_c_assumption": temperature_max_c,
        "near_expiry_windows_days": [30, 60, 90],
        "fefo_consumption": True,
        "temperature_observation_frequency": "Synthetic daily minimum and maximum readings, aggregated to facility-month",
        "risk_score_method": "50% monthly observed excursion-day rate + 50% share of closing stock expiring within 90 days",
        "limitations": [
            "All facilities, sensors, batches, suppliers, temperature readings, receipts, demand, consumption and expiry events are synthetic.",
            "The 2–8°C monitoring band is an illustrative generic scenario, not a universal product-specific storage instruction or an official Malawi standard.",
            "Shelf lives and near-expiry windows are synthetic assumptions; actual product labels and national guidance must govern real storage.",
            "Monthly excursion summaries do not represent continuous calibrated logger data or validated excursion disposition.",
            "The simulation does not model power failures, refrigerator mapping, vaccine vial monitors, freeze indicators, batch quarantine, product stability decisions or inter-facility transfers.",
            "FEFO consumption is a modelling convention; real dispensing and stock-card practices require verification.",
            "Risk scores are prioritisation prompts, not clinical safety determinations or procurement recommendations.",
        ],
    }
    return {
        "cold_chain_catalog": catalog,
        "temperature_monitoring": temperature,
        "batch_ledger": batch_ledger,
        "expiry_risk_summary": risk_summary,
        "assumptions": assumptions,
    }


def run_cold_chain_planning(
    facility_path: Path,
    output_dir: Path,
    periods: int = 24,
    start_month: str = "2025-01-01",
    seed: int = 42,
    temperature_min_c: float = TEMPERATURE_MIN_C,
    temperature_max_c: float = TEMPERATURE_MAX_C,
) -> dict[str, Any]:
    facilities = pd.read_csv(facility_path)
    result = build_cold_chain_profiles(
        facilities, periods, start_month, seed, temperature_min_c, temperature_max_c
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "cold_chain_catalog": "cold_chain_catalog.csv",
        "temperature_monitoring": "facility_cold_chain_temperature_monitoring.csv",
        "batch_ledger": "facility_commodity_batch_ledger.csv",
        "expiry_risk_summary": "cold_chain_expiry_risk_summary.csv",
    }
    for key, filename in outputs.items():
        result[key].to_csv(output_dir / filename, index=False)
    summary = result["expiry_risk_summary"]
    latest_month = summary["Month"].max()
    latest = summary.loc[summary["Month"].eq(latest_month)]
    report = {
        **result["assumptions"],
        "facility_count": int(facilities["Facility_ID"].nunique()),
        "temperature_monitoring_records": int(len(result["temperature_monitoring"])),
        "batch_ledger_records": int(len(result["batch_ledger"])),
        "risk_summary_records": int(len(summary)),
        "latest_snapshot_month": str(latest_month),
        "latest_high_risk_facility_commodity_pairs": int(latest["Risk_Band"].eq("High").sum()),
        "latest_pairs_with_temperature_excursions": int(latest["Temperature_Excursion_Flag"].sum()),
        "latest_near_expiry_90_day_units": int(latest["Near_Expiry_90_Day_Units"].sum()),
        "total_expired_units": int(summary["Expired_Units"].sum()),
        "outputs": list(outputs.values()),
    }
    (output_dir / "cold_chain_planning_report.json").write_text(json.dumps(report, indent=2, default=str))
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Build synthetic cold-chain, batch and expiry analytics")
    parser.add_argument("--facility-file", type=Path, default=Path("data/warehouse/raw/facility_dimension.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/warehouse/analytics"))
    parser.add_argument("--periods", type=int, default=24)
    parser.add_argument("--start-month", default="2025-01-01")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--temperature-min-c", type=float, default=TEMPERATURE_MIN_C)
    parser.add_argument("--temperature-max-c", type=float, default=TEMPERATURE_MAX_C)
    args = parser.parse_args()
    report = run_cold_chain_planning(
        args.facility_file, args.output_dir, args.periods, args.start_month,
        args.seed, args.temperature_min_c, args.temperature_max_c,
    )
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
