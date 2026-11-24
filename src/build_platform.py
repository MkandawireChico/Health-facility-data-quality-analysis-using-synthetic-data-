"""One-command end-to-end build for the expanded synthetic health data platform."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from scale_data_generator import ScaledHealthDataGenerator
from etl_pipeline import run_pipeline
from quality_analytics import run_quality_analytics
from statistical_monitoring import run_statistical_monitoring
from target_attainment import run_target_attainment
from resource_planning import run_resource_planning
from supply_chain_planning import run_supply_chain_planning
from cold_chain_planning import run_cold_chain_planning
from equipment_maintenance import run_equipment_maintenance
from infrastructure_reliability import run_infrastructure_planning
from workforce_planning import run_workforce_planning
from operational_reconciliation import (
    validate_resource_allocations, validate_stock_ledger,
    validate_cold_chain_ledger, validate_equipment_ledger,
    validate_infrastructure_ledger, validate_workforce_ledger,
)




def _validate_generated_fact_grain(
    fact: pd.DataFrame,
    facilities: pd.DataFrame,
    expected_records: int,
    expected_periods: int,
    expected_indicator_pairs: set[tuple[str, str]] | None = None,
    expected_months: pd.DatetimeIndex | None = None,
) -> dict[str, int]:
    """Validate the complete facility × month × programme-indicator grid."""
    key = ["Facility_ID", "Month", "Programme", "Indicator"]
    missing = sorted(set(key) - set(fact.columns))
    if missing:
        raise RuntimeError(f"Generated fact is missing grain columns: {missing}")
    if fact.empty or len(fact) != expected_records:
        raise RuntimeError(
            f"Generated fact row count mismatch: expected {expected_records}, got {len(fact)}"
        )
    dimension_required = {"Facility_ID"}
    if not dimension_required.issubset(facilities.columns):
        raise RuntimeError("Generated facility dimension is missing Facility_ID")
    if facilities.empty or facilities["Facility_ID"].isna().any():
        raise RuntimeError("Generated facility dimension contains missing facility identifiers")
    if facilities["Facility_ID"].astype("string").str.strip().eq("").any():
        raise RuntimeError("Generated facility dimension contains blank facility identifiers")
    if facilities["Facility_ID"].duplicated().any():
        raise RuntimeError("Generated facility dimension contains duplicate facility identifiers")
    if fact[key].isna().any().any():
        raise RuntimeError("Generated fact contains null natural-key values")
    for column in ["Facility_ID", "Programme", "Indicator"]:
        if fact[column].astype("string").str.strip().eq("").any():
            raise RuntimeError(f"Generated fact contains blank {column} values")
    if fact.duplicated(key).any():
        raise RuntimeError("Generated fact contains duplicate facility-month-indicator keys")

    expected_facilities = set(facilities["Facility_ID"].astype(str))
    actual_facilities = set(fact["Facility_ID"].astype(str))
    if actual_facilities != expected_facilities:
        raise RuntimeError("Generated fact facility population does not match the dimension")

    months = pd.to_datetime(fact["Month"], errors="coerce")
    if months.isna().any():
        raise RuntimeError("Generated fact contains invalid reporting months")
    month_periods = months.dt.to_period("M")
    actual_months = set(month_periods.astype(str))
    if len(actual_months) != expected_periods:
        raise RuntimeError("Generated fact reporting-period count does not match configuration")
    if expected_months is not None:
        configured_months = set(pd.DatetimeIndex(expected_months).to_period("M").astype(str))
        if actual_months != configured_months:
            raise RuntimeError("Generated fact reporting months do not match configured periods")

    actual_pairs = set(zip(fact["Programme"].astype(str), fact["Indicator"].astype(str)))
    if expected_indicator_pairs is not None and actual_pairs != expected_indicator_pairs:
        raise RuntimeError("Generated fact programme-indicator catalogue does not match configuration")
    indicator_pairs = expected_indicator_pairs or actual_pairs
    expected_per_facility_month = len(indicator_pairs)
    expected_groups = len(expected_facilities) * expected_periods
    expected_grid = {
        (facility_id, month, programme, indicator)
        for facility_id in expected_facilities
        for month in actual_months
        for programme, indicator in indicator_pairs
    }
    actual_grid = set(zip(
        fact["Facility_ID"].astype(str),
        month_periods.astype(str),
        fact["Programme"].astype(str),
        fact["Indicator"].astype(str),
    ))
    if len(actual_grid) != expected_records or actual_grid != expected_grid:
        raise RuntimeError("Generated fact has incomplete or inconsistent indicator coverage by facility-month")

    metadata_columns = ["Facility_Name", "District"]
    if set(metadata_columns).issubset(facilities.columns):
        fact_name_column = (
            "Facility_Name" if "Facility_Name" in fact.columns
            else "Facility" if "Facility" in fact.columns
            else None
        )
        if fact_name_column is None or "District" not in fact.columns:
            raise RuntimeError("Generated fact is missing canonical facility metadata")
        canonical = facilities.set_index("Facility_ID")[metadata_columns]
        expected_names = fact["Facility_ID"].map(canonical["Facility_Name"])
        if not fact[fact_name_column].astype(str).equals(expected_names.astype(str)):
            raise RuntimeError("Generated fact facility name values do not match the facility dimension")
        expected_districts = fact["Facility_ID"].map(canonical["District"])
        if not fact["District"].astype(str).equals(expected_districts.astype(str)):
            raise RuntimeError("Generated fact District values do not match the facility dimension")

    return {
        "unique_facility_month_groups": expected_groups,
        "indicators_per_facility_month": expected_per_facility_month,
        "unique_natural_keys": int(len(actual_grid)),
        "unique_programme_indicator_pairs": len(indicator_pairs),
        "configured_months": len(actual_months),
    }



def _validate_monthly_analytics_population(
    quality_monthly: pd.DataFrame,
    control_chart: pd.DataFrame,
    attainment_monthly: pd.DataFrame,
) -> dict[str, int]:
    """Require monthly quality, monitoring and attainment views to share one population."""
    specifications = [
        (quality_monthly, "records", "quality analytics"),
        (control_chart, "Records", "statistical monitoring"),
        (attainment_monthly, "reporting_records", "target attainment"),
    ]
    monthly_counts: dict[str, dict[str, int]] = {}
    for frame, count_column, label in specifications:
        if not {"Month", count_column}.issubset(frame.columns):
            raise RuntimeError(f"{label} monthly output is missing Month or {count_column}")
        months = pd.to_datetime(frame["Month"], errors="coerce").dt.to_period("M")
        if months.isna().any():
            raise RuntimeError(f"{label} monthly output contains invalid reporting months")
        if months.duplicated().any():
            raise RuntimeError(f"{label} monthly output contains duplicate month rows")
        raw_counts = frame[count_column]
        contains_boolean = raw_counts.map(
            lambda value: isinstance(value, (bool, np.bool_))
        ).any()
        counts = pd.to_numeric(raw_counts, errors="coerce")
        if (
            contains_boolean
            or counts.isna().any()
            or counts.lt(0).any()
            or not np.isfinite(counts).all()
            or not np.equal(counts, np.floor(counts)).all()
        ):
            raise RuntimeError(
                f"{label} monthly output contains invalid record counts"
            )
        monthly_counts[label] = {
            str(month): int(count)
            for month, count in zip(months.astype(str), counts)
        }

    expected = monthly_counts["quality analytics"]
    for label, counts in monthly_counts.items():
        if counts != expected:
            raise RuntimeError(
                f"Monthly reporting population mismatch: quality analytics vs {label}"
            )
    return {
        "months_reconciled": len(expected),
        "monthly_reporting_records": int(sum(expected.values())),
    }


def _validate_quality_profile_population(
    staged: pd.DataFrame,
    facility_profile: pd.DataFrame,
    district_profile: pd.DataFrame,
    programme_profile: pd.DataFrame,
) -> dict[str, int]:
    """Reconcile disjoint quality profile totals back to the staged fact population."""
    if not {"Facility_ID", "District", "Programme", "Indicator"}.issubset(staged.columns):
        raise RuntimeError("Staged fact is missing quality profile reconciliation dimensions")

    expected_records = len(staged)
    expected_facilities = int(staged["Facility_ID"].nunique())
    expected_districts = int(staged["District"].nunique())
    expected_programme_indicators = int(
        staged[["Programme", "Indicator"]].drop_duplicates().shape[0]
    )
    specifications = [
        (facility_profile, "Facility_ID", "facility", expected_facilities),
        (district_profile, "District", "district", expected_districts),
        (
            programme_profile,
            None,
            "programme-indicator",
            expected_programme_indicators,
        ),
    ]
    for frame, dimension, label, expected_groups in specifications:
        required = {"records"} | ({dimension} if dimension else {"Programme", "Indicator"})
        if not required.issubset(frame.columns):
            raise RuntimeError(f"{label} quality profile is missing required columns")
        if frame.empty or frame["records"].isna().any():
            raise RuntimeError(f"{label} quality profile has missing record counts")
        raw_counts = frame["records"]
        if raw_counts.map(lambda value: isinstance(value, (bool, np.bool_))).any():
            raise RuntimeError(f"{label} quality profile has invalid record counts")
        counts = pd.to_numeric(raw_counts, errors="coerce")
        if (
            counts.isna().any()
            or counts.lt(0).any()
            or not np.isfinite(counts).all()
            or not np.equal(counts, np.floor(counts)).all()
        ):
            raise RuntimeError(f"{label} quality profile has invalid record counts")
        if int(counts.sum()) != expected_records:
            raise RuntimeError(
                f"{label} quality profile population does not reconcile with staged records"
            )
        if len(frame) != expected_groups:
            raise RuntimeError(
                f"{label} quality profile group count does not reconcile with staged facts"
            )
        if dimension and frame[dimension].duplicated().any():
            raise RuntimeError(f"{label} quality profile contains duplicate groups")
        if not dimension and frame[["Programme", "Indicator"]].duplicated().any():
            raise RuntimeError("programme-indicator quality profile contains duplicate groups")

    return {
        "staged_records": expected_records,
        "facilities_reconciled": expected_facilities,
        "districts_reconciled": expected_districts,
        "programme_indicator_groups_reconciled": expected_programme_indicators,
    }



def _validate_operational_planning_population(
    facilities: pd.DataFrame,
    resource_capacity: pd.DataFrame,
    resource_scenarios: pd.DataFrame,
    workforce_establishment: pd.DataFrame,
    workforce_monthly: pd.DataFrame,
    workforce_latest: pd.DataFrame,
    expected_periods: int,
) -> dict[str, int]:
    """Reconcile resource and workforce outputs to the canonical facility dimension."""
    required_facility = {"Facility_ID", "Facility_Name", "District"}
    if not required_facility.issubset(facilities.columns):
        raise RuntimeError("Canonical facility dimension is missing planning identity columns")
    if facilities.empty or facilities["Facility_ID"].isna().any():
        raise RuntimeError("Canonical facility dimension has missing facility identifiers")
    if facilities["Facility_ID"].astype("string").str.strip().eq("").any():
        raise RuntimeError("Canonical facility dimension has blank facility identifiers")
    if facilities["Facility_ID"].duplicated().any():
        raise RuntimeError("Canonical facility dimension contains duplicate facility identifiers")

    expected_ids = set(facilities["Facility_ID"].astype(str))
    metadata = facilities.set_index("Facility_ID")[["Facility_Name", "District"]]
    facility_outputs = [
        (resource_capacity, "resource capacity"),
        (workforce_latest, "latest workforce"),
    ]
    for frame, label in facility_outputs:
        required = {"Facility_ID", "Facility_Name", "District"}
        if not required.issubset(frame.columns):
            raise RuntimeError(f"{label} output is missing facility identity columns")
        if frame.empty or frame["Facility_ID"].isna().any():
            raise RuntimeError(f"{label} output has missing facility identifiers")
        if frame["Facility_ID"].duplicated().any():
            raise RuntimeError(f"{label} output contains duplicate facility rows")
        actual_ids = set(frame["Facility_ID"].astype(str))
        if actual_ids != expected_ids:
            raise RuntimeError(f"{label} facility population does not match canonical dimension")
        actual = frame.set_index("Facility_ID")[["Facility_Name", "District"]].sort_index()
        for column in ["Facility_Name", "District"]:
            if not actual[column].astype(str).equals(metadata[column].astype(str).sort_index()):
                raise RuntimeError(f"{label} {column} values do not match canonical dimension")

    if not {"Facility_ID", "Scenario"}.issubset(resource_scenarios.columns):
        raise RuntimeError("Resource scenario output is missing facility or scenario keys")
    if resource_scenarios[["Facility_ID", "Scenario"]].isna().any().any():
        raise RuntimeError("Resource scenario output contains missing natural keys")
    expected_scenarios = {"gap_priority", "equity", "equal"}
    if set(resource_scenarios["Scenario"].astype(str)) != expected_scenarios:
        raise RuntimeError("Resource scenario output does not contain the three expected strategies")
    if resource_scenarios.duplicated(["Facility_ID", "Scenario"]).any():
        raise RuntimeError("Resource scenario output contains duplicate facility-scenario rows")
    for scenario, group in resource_scenarios.groupby("Scenario"):
        if set(group["Facility_ID"].astype(str)) != expected_ids:
            raise RuntimeError(f"Resource scenario '{scenario}' facility population is incomplete")

    if not {"Facility_ID", "Role"}.issubset(workforce_establishment.columns):
        raise RuntimeError("Workforce establishment output is missing facility-role keys")
    if workforce_establishment[["Facility_ID", "Role"]].isna().any().any():
        raise RuntimeError("Workforce establishment output contains missing natural keys")
    if workforce_establishment.duplicated(["Facility_ID", "Role"]).any():
        raise RuntimeError("Workforce establishment output contains duplicate facility-role rows")
    roles = set(workforce_establishment["Role"].astype(str))
    if not roles:
        raise RuntimeError("Workforce establishment output contains no role definitions")
    for facility_id, group in workforce_establishment.groupby("Facility_ID"):
        if set(group["Role"].astype(str)) != roles:
            raise RuntimeError(f"Workforce establishment role coverage is incomplete for {facility_id}")
    if set(workforce_establishment["Facility_ID"].astype(str)) != expected_ids:
        raise RuntimeError("Workforce establishment facility population does not match canonical dimension")

    required_monthly = {"Facility_ID", "Month"}
    if not required_monthly.issubset(workforce_monthly.columns):
        raise RuntimeError("Monthly workforce output is missing facility-month keys")
    if workforce_monthly[list(required_monthly)].isna().any().any():
        raise RuntimeError("Monthly workforce output contains missing natural keys")
    if workforce_monthly.duplicated(["Facility_ID", "Month"]).any():
        raise RuntimeError("Monthly workforce output contains duplicate facility-month rows")
    months = pd.to_datetime(workforce_monthly["Month"], errors="coerce")
    if months.isna().any():
        raise RuntimeError("Monthly workforce output contains invalid reporting months")
    month_periods = months.dt.to_period("M")
    unique_months = set(month_periods.astype(str))
    if len(unique_months) != expected_periods:
        raise RuntimeError("Monthly workforce reporting-period count does not match build configuration")
    expected_pairs = {(facility_id, month) for facility_id in expected_ids for month in unique_months}
    actual_pairs = set(zip(workforce_monthly["Facility_ID"].astype(str), month_periods.astype(str)))
    if actual_pairs != expected_pairs:
        raise RuntimeError("Monthly workforce facility-month grid is incomplete or contains unknown facilities")
    latest_month = month_periods.max()
    latest_rows = workforce_latest.copy()
    if "Month" not in latest_rows.columns:
        raise RuntimeError("Latest workforce output is missing its reporting month")
    latest_dates = pd.to_datetime(latest_rows["Month"], errors="coerce").dt.to_period("M")
    if latest_dates.isna().any() or not latest_dates.eq(latest_month).all():
        raise RuntimeError("Latest workforce output does not represent the final configured month")

    return {
        "facilities_reconciled": len(expected_ids),
        "resource_scenarios_reconciled": len(expected_scenarios),
        "workforce_roles_reconciled": len(roles),
        "workforce_months_reconciled": len(unique_months),
        "workforce_facility_month_rows": len(workforce_monthly),
    }


def _build_operational_resilience_views(facilities, equipment_monthly, infrastructure_monthly, workforce_monthly, output_dir):
    """Create an auditable facility-month view across equipment, infrastructure and workforce."""
    key = ["Facility_ID", "Month"]
    identity = ["Facility_Name", "District"]
    expected_ids = set(facilities["Facility_ID"].astype(str))
    frames = [
        (equipment_monthly, "equipment", {"Mean_Operational_Uptime_Pct", "Total_Downtime_Hours", "High_Risk_Assets", "PM_Overdue"}),
        (infrastructure_monthly, "infrastructure", {"Infrastructure_Resilience_Score", "Unserved_Power_Interruption_Hours", "Unserved_Water_Shortage_Hours", "Connectivity_Downtime_Hours"}),
        (workforce_monthly, "workforce", {"Workforce_Coverage_Pct", "Workforce_Pressure_Index", "Vacant_Positions", "Absent_Positions"}),
    ]
    normalized = []
    reference_months = None
    for frame, label, measures in frames:
        required = set(key + identity) | measures
        if not required.issubset(frame.columns):
            raise RuntimeError(f"{label} operational output is missing required integration columns")
        data = frame[list(required)].copy()
        if data[key + identity].isna().any().any():
            raise RuntimeError(f"{label} operational output has missing facility-month identity")
        data["Facility_ID"] = data["Facility_ID"].astype(str).str.strip()
        if data["Facility_ID"].eq("").any() or data.duplicated(key).any():
            raise RuntimeError(f"{label} operational output has blank or duplicate facility-month keys")
        month = pd.to_datetime(data["Month"], errors="coerce")
        if month.isna().any():
            raise RuntimeError(f"{label} operational output has invalid reporting months")
        data["Month"] = month.dt.to_period("M").dt.to_timestamp()
        month_set = set(data["Month"])
        if reference_months is None:
            reference_months = month_set
        elif month_set != reference_months:
            raise RuntimeError(f"{label} operational reporting months do not match other domains")
        if set(data["Facility_ID"]) != expected_ids:
            raise RuntimeError(f"{label} operational facility population does not match canonical dimension")
        if len(data) != len(expected_ids) * len(reference_months):
            raise RuntimeError(f"{label} operational facility-month grid is incomplete")
        for column in measures:
            values = pd.to_numeric(data[column], errors="coerce")
            if values.isna().any() or not np.isfinite(values.to_numpy(dtype=float)).all():
                raise RuntimeError(f"{label} operational measure {column} contains invalid values")
            data[column] = values
        normalized.append(data.sort_values(key).reset_index(drop=True))

    base = normalized[0]
    for other, label in zip(normalized[1:], ["infrastructure", "workforce"]):
        joined = base[key + identity].merge(other[key + identity], on=key, how="outer",
            suffixes=("_base", "_other"), validate="one_to_one", indicator=True)
        if not joined["_merge"].eq("both").all():
            raise RuntimeError(f"{label} facility-month keys do not reconcile")
        for column in identity:
            if not joined[f"{column}_base"].astype(str).equals(joined[f"{column}_other"].astype(str)):
                raise RuntimeError(f"{label} facility metadata does not match equipment records")

    combined = base
    for other in normalized[1:]:
        combined = combined.merge(other.drop(columns=identity), on=key, how="inner", validate="one_to_one")
    combined["Operational_Review_Flag"] = (
        combined["Mean_Operational_Uptime_Pct"].lt(95)
        | combined["Infrastructure_Resilience_Score"].lt(70)
        | combined["Workforce_Coverage_Pct"].lt(65)
    )
    combined["Operational_Review_Domains"] = combined.apply(
        lambda row: ";".join(domain for domain, condition in [
            ("equipment", row["Mean_Operational_Uptime_Pct"] < 95),
            ("infrastructure", row["Infrastructure_Resilience_Score"] < 70),
            ("workforce", row["Workforce_Coverage_Pct"] < 65),
        ] if condition) or "none", axis=1)
    combined["Interpretation"] = "Synthetic scenario screening flag; not a verified facility risk rating."
    combined["Synthetic_Data"] = True
    combined = combined.sort_values(key).reset_index(drop=True)
    latest = combined.loc[combined["Month"].eq(combined["Month"].max())].copy()
    output_dir = Path(output_dir)
    combined.to_csv(output_dir / "facility_monthly_operational_resilience.csv", index=False)
    latest.to_csv(output_dir / "facility_latest_operational_resilience.csv", index=False)
    return {"facility_month_records": int(len(combined)),
        "facilities_reconciled": int(combined["Facility_ID"].nunique()),
        "months_reconciled": int(combined["Month"].nunique()),
        "latest_review_priority_facilities": int(latest["Operational_Review_Flag"].sum())}



def _build_supply_cold_chain_resilience_view(facilities, stock_ledger, cold_chain_risk, output_dir):
    """Aggregate commodity availability and cold-chain risk on a shared facility-month grain."""
    key = ["Facility_ID", "Month"]
    identity = ["Facility_Name", "District"]
    expected_ids = set(facilities["Facility_ID"].astype(str))
    specifications = [
        (stock_ledger, "stock", {"Demand_Units", "Unmet_Demand_Units", "Closing_Stock_Units", "Stockout_Days", "Stockout_Flag"}),
        (cold_chain_risk, "cold-chain", {"Expired_Units", "Near_Expiry_90_Day_Units", "Temperature_Excursion_Days", "Cold_Chain_Risk_Score", "Risk_Band"}),
    ]
    aggregates = []
    month_reference = None
    for frame, label, measures in specifications:
        required = set(key + identity + ["Commodity_ID"]) | measures
        if not required.issubset(frame.columns):
            raise RuntimeError(f"{label} source is missing required supply resilience columns")
        data = frame.copy()
        if data[key + identity].isna().any().any():
            raise RuntimeError(f"{label} source contains missing facility-month identity")
        if data["Commodity_ID"].isna().any():
            raise RuntimeError(f"{label} source contains missing commodity identifiers")
        data["Facility_ID"] = data["Facility_ID"].astype(str).str.strip()
        for column in identity:
            data[column] = data[column].astype(str).str.strip()
        data["Commodity_ID"] = data["Commodity_ID"].astype(str).str.strip()
        if data["Facility_ID"].eq("").any() or data["Commodity_ID"].eq("").any():
            raise RuntimeError(f"{label} source contains blank facility or commodity identifiers")
        if data[identity[0]].eq("").any() or data[identity[1:]].eq("").any().any():
            raise RuntimeError(f"{label} source contains blank facility metadata")
        data["Month"] = pd.to_datetime(data["Month"], errors="coerce").dt.to_period("M").dt.to_timestamp()
        if data["Month"].isna().any():
            raise RuntimeError(f"{label} source contains invalid reporting months")
        if set(data["Facility_ID"]) != expected_ids:
            raise RuntimeError(f"{label} facility population does not match canonical dimension")
        if data[identity].isna().any().any():
            raise RuntimeError(f"{label} source contains missing facility metadata")
        if data.groupby("Facility_ID")[identity].nunique().gt(1).any().any():
            raise RuntimeError(f"{label} source contains conflicting facility metadata")
        if data["Commodity_ID"].isna().any() or data["Commodity_ID"].astype(str).str.strip().eq("").any():
            raise RuntimeError(f"{label} source contains missing commodity identifiers")
        if data.duplicated(key + ["Commodity_ID"]).any():
            raise RuntimeError(f"{label} source contains duplicate facility-month-commodity keys")
        months = set(data["Month"])
        if month_reference is None:
            month_reference = months
        elif months != month_reference:
            raise RuntimeError(f"{label} reporting months do not match the other supply domain")
        if label == "stock":
            if not data["Stockout_Flag"].isin([True, False, 0, 1]).all():
                raise RuntimeError("Stockout_Flag must contain Boolean values")
            data["Stockout_Flag"] = data["Stockout_Flag"].astype(bool)
        else:
            if not data["Risk_Band"].isin(["Low", "Medium", "High", "Data Gap"]).all():
                raise RuntimeError("Cold-chain Risk_Band contains an unsupported category")
        for column in measures - {"Risk_Band", "Stockout_Flag"}:
            values = pd.to_numeric(data[column], errors="coerce")
            if column == "Cold_Chain_Risk_Score" and label == "cold-chain":
                data_gap = data["Risk_Band"].eq("Data Gap")
                if values[data_gap].notna().any() or values[~data_gap].isna().any():
                    raise RuntimeError("Cold-chain risk scores must be missing only for explicit data-gap rows")
                if not np.isfinite(values.dropna().to_numpy(dtype=float)).all():
                    raise RuntimeError("Cold-chain risk scores contain non-finite values")
            elif values.isna().any() or not np.isfinite(values.to_numpy(dtype=float)).all():
                raise RuntimeError(f"{label} measure {column} contains invalid values")
            if column != "Cold_Chain_Risk_Score" and values.lt(0).any():
                raise RuntimeError(f"{label} measure {column} cannot be negative")
            if column == "Cold_Chain_Risk_Score" and not values.dropna().between(0, 100).all():
                raise RuntimeError("Cold-chain risk scores must be between 0 and 100")
            data[column] = values
        grouped = data.groupby(key, as_index=False).agg(
            Facility_Name=("Facility_Name", "first"),
            District=("District", "first"),
            **({"Demand_Units": ("Demand_Units", "sum"),
                "Unmet_Demand_Units": ("Unmet_Demand_Units", "sum"),
                "Closing_Stock_Units": ("Closing_Stock_Units", "sum"),
                "Stockout_Days": ("Stockout_Days", "sum"),
                "Stockout_Commodity_Pairs": ("Stockout_Flag", "sum")}
               if label == "stock" else
               {"Expired_Units": ("Expired_Units", "sum"),
                "Near_Expiry_90_Day_Units": ("Near_Expiry_90_Day_Units", "sum"),
                "Temperature_Excursion_Days": ("Temperature_Excursion_Days", "sum"),
                "High_Cold_Chain_Risk_Pairs": ("Risk_Band", lambda values: values.eq("High").sum()),
                "Data_Gap_Cold_Chain_Pairs": ("Risk_Band", lambda values: values.eq("Data Gap").sum()),
                "Mean_Cold_Chain_Risk_Score": ("Cold_Chain_Risk_Score", "mean")}
        )
        )
        grouped["Facility_ID"] = grouped["Facility_ID"].astype(str)
        if grouped.duplicated(key).any():
            raise RuntimeError(f"{label} aggregation produced duplicate facility-month rows")
        if set(grouped["Facility_ID"]) != expected_ids or len(grouped) != len(expected_ids) * len(month_reference):
            raise RuntimeError(f"{label} facility-month grid is incomplete")
        aggregates.append(grouped.sort_values(key).reset_index(drop=True))

    stock, cold = aggregates
    joined = stock.merge(cold, on=key, how="outer", suffixes=("_stock", "_cold"),
        validate="one_to_one", indicator=True)
    if not joined["_merge"].eq("both").all():
        raise RuntimeError("Stock and cold-chain facility-month populations do not reconcile")
    for column in identity:
        if not joined[f"{column}_stock"].astype(str).equals(joined[f"{column}_cold"].astype(str)):
            raise RuntimeError(f"Stock and cold-chain {column} metadata do not reconcile")
    joined["Facility_Name"] = joined.pop("Facility_Name_stock")
    joined["District"] = joined.pop("District_stock")
    joined = joined.drop(columns=["Facility_Name_cold", "District_cold", "_merge"])
    joined["Supply_Review_Flag"] = (
        joined["Stockout_Commodity_Pairs"].gt(0)
        | joined["High_Cold_Chain_Risk_Pairs"].gt(0)
        | joined["Data_Gap_Cold_Chain_Pairs"].gt(0)
        | joined["Temperature_Excursion_Days"].gt(0)
        | joined["Near_Expiry_90_Day_Units"].gt(0)
    )
    joined["Interpretation"] = "Synthetic stock and cold-chain scenario screening; not live inventory or product disposition advice."
    joined["Synthetic_Data"] = True
    joined = joined.sort_values(key).reset_index(drop=True)
    latest = joined.loc[joined["Month"].eq(joined["Month"].max())].copy()
    output_dir = Path(output_dir)
    joined.to_csv(output_dir / "facility_monthly_supply_cold_chain_resilience.csv", index=False)
    latest.to_csv(output_dir / "facility_latest_supply_cold_chain_resilience.csv", index=False)
    return {
        "facility_month_records": int(len(joined)),
        "facilities_reconciled": int(joined["Facility_ID"].nunique()),
        "months_reconciled": int(joined["Month"].nunique()),
        "latest_supply_review_facilities": int(latest["Supply_Review_Flag"].sum()),
    }



def _build_integrated_facility_priority(
    facilities, operational_latest, supply_latest, quality_benchmark,
    resource_capacity, output_dir,
):
    """Build a transparent synthetic cross-domain facility review register."""
    identity = ["Facility_ID", "Facility_Name", "District"]
    expected_ids = set(facilities["Facility_ID"].astype(str).str.strip())
    sources = [
        (operational_latest, "operational", {
            "Mean_Operational_Uptime_Pct", "Infrastructure_Resilience_Score",
            "Workforce_Coverage_Pct", "Operational_Review_Flag",
            "Operational_Review_Domains",
        }),
        (supply_latest, "supply", {
            "Supply_Review_Flag", "Stockout_Commodity_Pairs",
            "High_Cold_Chain_Risk_Pairs", "Data_Gap_Cold_Chain_Pairs",
            "Near_Expiry_90_Day_Units", "Temperature_Excursion_Days",
        }),
        (quality_benchmark, "quality", {
            "records", "detected_issue_records", "detected_issue_rate_pct",
            "missing_records", "source_discrepancy_records", "outlier_records",
            "late_records",
        }),
        (resource_capacity, "resource", {
            "Illustrative_Requirement_Units", "Synthetic_Available_Units",
            "Baseline_Gap_Units", "Baseline_Capacity_Coverage_Pct",
        }),
    ]
    normalized = []
    for frame, label, measures in sources:
        if label == "quality" and "Facility_Name" not in frame.columns and "Facility" in frame.columns:
            frame = frame.rename(columns={"Facility": "Facility_Name"})
        required = set(identity) | measures
        if not required.issubset(frame.columns):
            raise RuntimeError(f"{label} priority source is missing required columns")
        data = frame[identity + sorted(measures)].copy()
        if data[identity].isna().any().any():
            raise RuntimeError(f"{label} priority source contains missing facility identity")
        data["Facility_ID"] = data["Facility_ID"].astype(str).str.strip()
        if data["Facility_ID"].eq("").any() or data["Facility_ID"].duplicated().any():
            raise RuntimeError(f"{label} priority source has blank or duplicate facilities")
        if set(data["Facility_ID"]) != expected_ids or len(data) != len(expected_ids):
            raise RuntimeError(f"{label} priority facility population does not match canonical dimension")
        if data.groupby("Facility_ID")[["Facility_Name", "District"]].nunique().gt(1).any().any():
            raise RuntimeError(f"{label} priority source contains conflicting facility metadata")
        for column in measures - {"Operational_Review_Flag", "Operational_Review_Domains", "Supply_Review_Flag"}:
            values = pd.to_numeric(data[column], errors="coerce")
            if values.isna().any() or not np.isfinite(values.to_numpy(dtype=float)).all():
                raise RuntimeError(f"{label} priority measure {column} contains invalid values")
            data[column] = values
        if label in {"operational", "supply"}:
            flag = "Operational_Review_Flag" if label == "operational" else "Supply_Review_Flag"
            if not data[flag].isin([True, False, 0, 1]).all():
                raise RuntimeError(f"{label} review flag must be Boolean")
            data[flag] = data[flag].astype(bool)
        normalized.append(data.sort_values("Facility_ID").reset_index(drop=True))

    base = normalized[0]
    for other, label in zip(normalized[1:], ["supply", "quality", "resource"]):
        joined = base[identity].merge(
            other[identity], on="Facility_ID", how="outer",
            suffixes=("_base", "_other"), validate="one_to_one", indicator=True,
        )
        if not joined["_merge"].eq("both").all():
            raise RuntimeError(f"{label} facility identities do not reconcile")
        for column in ["Facility_Name", "District"]:
            if not joined[f"{column}_base"].astype(str).equals(joined[f"{column}_other"].astype(str)):
                raise RuntimeError(f"{label} {column} metadata does not reconcile")

    combined = base
    for other in normalized[1:]:
        combined = combined.merge(other.drop(columns=["Facility_Name", "District"]),
            on="Facility_ID", how="inner", validate="one_to_one")

    if combined["records"].le(0).any():
        raise RuntimeError("Quality benchmark record counts must be positive")
    if combined["detected_issue_records"].lt(0).any() or combined["detected_issue_records"].gt(combined["records"]).any():
        raise RuntimeError("Quality benchmark issue counts are outside valid bounds")
    if not combined["detected_issue_rate_pct"].between(0, 100).all():
        raise RuntimeError("Quality benchmark issue rates must be between 0 and 100")
    if not combined["Baseline_Capacity_Coverage_Pct"].between(0, 200).all():
        raise RuntimeError("Resource capacity coverage must be between 0 and 200")
    if combined["Baseline_Gap_Units"].lt(0).any():
        raise RuntimeError("Resource baseline gaps cannot be negative")
    for column in ["Mean_Operational_Uptime_Pct", "Infrastructure_Resilience_Score", "Workforce_Coverage_Pct"]:
        if not combined[column].between(0, 100).all():
            raise RuntimeError(f"Operational measure {column} must be between 0 and 100")
    for column in ["Stockout_Commodity_Pairs", "High_Cold_Chain_Risk_Pairs",
                   "Data_Gap_Cold_Chain_Pairs", "Near_Expiry_90_Day_Units", "Temperature_Excursion_Days",
                   "missing_records", "source_discrepancy_records", "outlier_records",
                   "late_records", "Illustrative_Requirement_Units",
                   "Synthetic_Available_Units", "Baseline_Gap_Units"]:
        if combined[column].lt(0).any():
            raise RuntimeError(f"Priority measure {column} cannot be negative")
    expected_quality_rate = 100 * combined["detected_issue_records"] / combined["records"]
    if not np.allclose(expected_quality_rate, combined["detected_issue_rate_pct"], atol=0.02):
        raise RuntimeError("Quality benchmark issue rates do not reconcile with record counts")
    if not combined["Baseline_Gap_Units"].equals(
        (combined["Illustrative_Requirement_Units"] - combined["Synthetic_Available_Units"]).clip(lower=0)
    ):
        raise RuntimeError("Resource baseline gap does not reconcile with requirement and available units")

    combined["Data_Quality_Priority_Score"] = combined["detected_issue_rate_pct"].clip(0, 100)
    combined["Resource_Gap_Priority_Score"] = (100 - combined["Baseline_Capacity_Coverage_Pct"]).clip(0, 100)
    combined["Operational_Priority_Score"] = (
        100 * combined["Operational_Review_Flag"].astype(int)
    )
    combined["Supply_Cold_Chain_Priority_Score"] = (
        100 * combined["Supply_Review_Flag"].astype(int)
    )
    score_columns = [
        "Data_Quality_Priority_Score", "Resource_Gap_Priority_Score",
        "Operational_Priority_Score", "Supply_Cold_Chain_Priority_Score",
    ]
    combined["Integrated_Priority_Score"] = combined[score_columns].mean(axis=1).round(2)
    combined["Priority_Band"] = np.select(
        [combined["Integrated_Priority_Score"].ge(50), combined["Integrated_Priority_Score"].ge(25)],
        ["High review", "Focused review"], default="Routine review",
    )
    combined["Review_Domains"] = combined.apply(
        lambda row: ";".join(domain for domain, condition in [
            ("data_quality", row["Data_Quality_Priority_Score"] > 0),
            ("resource_capacity", row["Baseline_Gap_Units"] > 0),
            ("operational_resilience", bool(row["Operational_Review_Flag"])),
            ("supply_cold_chain", bool(row["Supply_Review_Flag"])),
        ] if condition) or "none", axis=1,
    )
    combined["Quality_Benchmark_Scope"] = "All reporting periods in the current synthetic build"
    combined["Interpretation"] = (
        "Illustrative synthetic cross-domain review score; equal-weighted screening, "
        "not a validated clinical, safety, facility-performance or resource-allocation rating."
    )
    combined["Synthetic_Data"] = True
    combined = combined.sort_values(
        ["Integrated_Priority_Score", "Facility_ID"], ascending=[False, True]
    ).reset_index(drop=True)
    combined["Integrated_Priority_Rank"] = np.arange(1, len(combined) + 1)
    output_dir = Path(output_dir)
    combined.to_csv(output_dir / "integrated_facility_priority_register.csv", index=False)
    return {
        "facilities_prioritised": int(len(combined)),
        "high_review_facilities": int(combined["Priority_Band"].eq("High review").sum()),
        "focused_review_facilities": int(combined["Priority_Band"].eq("Focused review").sum()),
        "routine_review_facilities": int(combined["Priority_Band"].eq("Routine review").sum()),
        "mean_integrated_priority_score": round(float(combined["Integrated_Priority_Score"].mean()), 2),
    }



def _build_artifact_manifest(outputs: dict[str, str], output_dir: Path) -> dict[str, dict[str, Any]]:
    """Validate build artifacts and return stable, relative integrity metadata."""
    root = Path(output_dir).resolve()
    manifest: dict[str, dict[str, Any]] = {}
    for name, raw_path in outputs.items():
        path = Path(raw_path).resolve()
        try:
            relative_path = path.relative_to(root)
        except ValueError as exc:
            raise RuntimeError(
                f"Platform artifact '{name}' is outside the output directory"
            ) from exc
        if not path.is_file():
            raise RuntimeError(f"Platform artifact '{name}' is missing: {relative_path}")
        size_bytes = path.stat().st_size
        if size_bytes <= 0:
            raise RuntimeError(f"Platform artifact '{name}' is empty: {relative_path}")
        digest = hashlib.sha256()
        with path.open("rb") as artifact_file:
            for chunk in iter(lambda: artifact_file.read(1024 * 1024), b""):
                digest.update(chunk)
        manifest[name] = {
            "path": relative_path.as_posix(),
            "size_bytes": size_bytes,
            "sha256": digest.hexdigest(),
        }
    return manifest


def build_platform(
    output_dir: Path = Path("data/warehouse"),
    seed: int = 42,
    facility_count: int = 120,
    start_month: str = "2021-01-01",
    periods: int = 60,
) -> dict[str, Any]:
    """Generate, stage, evaluate and statistically monitor a synthetic cohort."""
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise ValueError("seed must be a non-negative integer")
    if isinstance(facility_count, bool) or not isinstance(facility_count, int) or facility_count < 1:
        raise ValueError("facility_count must be a positive integer")
    if isinstance(periods, bool) or not isinstance(periods, int) or periods < 1:
        raise ValueError("periods must be a positive integer")
    try:
        parsed_start_month = pd.Timestamp(start_month)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("start_month must be a valid timezone-naive date") from exc
    if pd.isna(parsed_start_month) or parsed_start_month.tz is not None:
        raise ValueError("start_month must be a valid timezone-naive date")
    start_month = parsed_start_month.to_period("M").to_timestamp().strftime("%Y-%m-%d")

    output_dir = Path(output_dir)
    raw_dir = output_dir / "raw"
    staged_dir = output_dir / "staged"
    analytics_dir = output_dir / "analytics"
    for directory in (raw_dir, staged_dir, analytics_dir):
        directory.mkdir(parents=True, exist_ok=True)

    generator = ScaledHealthDataGenerator(
        seed=seed,
        facility_count=facility_count,
        start_month=start_month,
        periods=periods,
    )
    fact, facilities, manifest = generator.generate()
    expected_indicator_pairs = {
        (str(programme), str(indicator))
        for programme, indicators in generator.programmes.items()
        for indicator in indicators
    }
    grain_validation = _validate_generated_fact_grain(
        fact,
        facilities,
        generator.expected_record_count,
        periods,
        expected_indicator_pairs=expected_indicator_pairs,
        expected_months=generator.months,
    )
    fact_path = raw_dir / "facility_reporting_fact.csv"
    facility_path = raw_dir / "facility_dimension.csv"
    fact.to_csv(fact_path, index=False)
    facilities.to_csv(facility_path, index=False)
    (raw_dir / "generation_manifest.json").write_text(json.dumps(manifest, indent=2))

    staging_report = run_pipeline(fact_path, facility_path, staged_dir)
    staged_path = staged_dir / "facility_reporting_staged.csv"
    quality_report = run_quality_analytics(staged_path, analytics_dir)
    statistical_report = run_statistical_monitoring(staged_path, analytics_dir)
    attainment_report = run_target_attainment(staged_path, analytics_dir)
    resource_report = run_resource_planning(facility_path, analytics_dir, seed=seed)
    supply_report = run_supply_chain_planning(
        facility_path, analytics_dir, periods=periods, start_month=start_month, seed=seed
    )
    cold_chain_report = run_cold_chain_planning(
        facility_path, analytics_dir, periods=periods, start_month=start_month, seed=seed
    )
    equipment_report = run_equipment_maintenance(
        facility_path, analytics_dir, periods=periods, start_month=start_month, seed=seed
    )
    infrastructure_report = run_infrastructure_planning(
        facility_path, analytics_dir, periods=periods, start_month=start_month,
        seed=seed, equipment_monthly_path=analytics_dir / "facility_equipment_monthly_summary.csv",
    )
    workforce_report = run_workforce_planning(
        facility_path, analytics_dir, periods=periods, start_month=start_month, seed=seed,
    )


    supply_cold_chain_resilience = _build_supply_cold_chain_resilience_view(
        facilities,
        pd.read_csv(analytics_dir / "facility_commodity_stock_ledger.csv"),
        pd.read_csv(analytics_dir / "cold_chain_expiry_risk_summary.csv"),
        analytics_dir,
    )

    if manifest["actual_record_count"] != generator.expected_record_count:
        raise RuntimeError("Generated record count does not match configured fact grain")
    if manifest["facility_count"] != len(facilities):
        raise RuntimeError("Generated facility count does not match the facility dimension")
    if staging_report["staged_rows"] + staging_report["quarantined_rows"] != manifest["actual_record_count"]:
        raise RuntimeError("Staging row reconciliation failed")
    if staging_report["source_fact_rows"] != manifest["actual_record_count"]:
        raise RuntimeError("ETL source row count does not reconcile with the generated fact")
    if quality_report["input_records"] != staging_report["staged_rows"]:
        raise RuntimeError("Quality analytics input count does not reconcile with staged records")
    if statistical_report["staged_records"] != staging_report["staged_rows"]:
        raise RuntimeError("Statistical monitoring input count does not reconcile with staged records")
    if attainment_report["input_records"] != staging_report["staged_rows"]:
        raise RuntimeError("Target attainment input count does not reconcile with staged records")
    monthly_population = _validate_monthly_analytics_population(
        pd.read_csv(analytics_dir / "monthly_quality_trends.csv"),
        pd.read_csv(analytics_dir / "monthly_issue_control_chart.csv"),
        pd.read_csv(analytics_dir / "monthly_indicator_target_attainment.csv"),
    )

    quality_profile_population = _validate_quality_profile_population(
        pd.read_csv(staged_path),
        pd.read_csv(analytics_dir / "facility_quality_benchmark.csv").rename(columns={"Facility": "Facility_Name"}),
        pd.read_csv(analytics_dir / "district_quality_profile.csv"),
        pd.read_csv(analytics_dir / "programme_indicator_quality_profile.csv"),
    )


    operational_planning_population = _validate_operational_planning_population(
        facilities,
        pd.read_csv(analytics_dir / "facility_resource_capacity.csv"),
        pd.read_csv(analytics_dir / "resource_allocation_scenarios.csv"),
        pd.read_csv(analytics_dir / "facility_workforce_establishment.csv"),
        pd.read_csv(analytics_dir / "facility_monthly_workforce_capacity.csv"),
        pd.read_csv(analytics_dir / "facility_latest_workforce_capacity.csv"),
        periods,
    )


    operational_ledger_reconciliation = {
        "resource_allocation": validate_resource_allocations(
            pd.read_csv(analytics_dir / "facility_resource_capacity.csv"),
            pd.read_csv(analytics_dir / "resource_allocation_scenarios.csv"),
        ),
        "commodity_stock": validate_stock_ledger(
            pd.read_csv(analytics_dir / "facility_commodity_stock_ledger.csv"),
        ),
        "cold_chain_batches": validate_cold_chain_ledger(
            pd.read_csv(analytics_dir / "facility_commodity_batch_ledger.csv"),
            pd.read_csv(analytics_dir / "cold_chain_expiry_risk_summary.csv"),
        ),
        "equipment_maintenance": validate_equipment_ledger(
            pd.read_csv(analytics_dir / "equipment_asset_monthly_performance.csv"),
            pd.read_csv(analytics_dir / "equipment_maintenance_work_orders.csv"),
        ),
        "infrastructure": validate_infrastructure_ledger(
            pd.read_csv(analytics_dir / "facility_monthly_infrastructure_reliability.csv"),
        ),
        "workforce": validate_workforce_ledger(
            pd.read_csv(analytics_dir / "facility_monthly_workforce_capacity.csv"),
        ),
    }


    operational_resilience = _build_operational_resilience_views(
        facilities,
        pd.read_csv(analytics_dir / "facility_equipment_monthly_summary.csv"),
        pd.read_csv(analytics_dir / "facility_monthly_infrastructure_reliability.csv"),
        pd.read_csv(analytics_dir / "facility_monthly_workforce_capacity.csv"),
        analytics_dir,
    )


    integrated_facility_priority = _build_integrated_facility_priority(
        facilities,
        pd.read_csv(analytics_dir / "facility_latest_operational_resilience.csv"),
        pd.read_csv(analytics_dir / "facility_latest_supply_cold_chain_resilience.csv"),
        pd.read_csv(analytics_dir / "facility_quality_benchmark.csv"),
        pd.read_csv(analytics_dir / "facility_resource_capacity.csv"),
        analytics_dir,
    )

    summary = {
        "synthetic_data": True,
        "seed": seed,
        "facility_count": facility_count,
        "period_count": periods,
        "programme_count": manifest["programme_count"],
        "indicator_count": manifest["indicator_count"],
        "expected_fact_records": generator.expected_record_count,
        "generated_fact_records": manifest["actual_record_count"],
        "generated_fact_grain_validation": grain_validation,
        "staged_records": staging_report["staged_rows"],
        "monthly_analytics_population": monthly_population,
        "quality_profile_population": quality_profile_population,
        "operational_planning_population": operational_planning_population,
        "operational_ledger_reconciliation": operational_ledger_reconciliation,
        "operational_resilience": operational_resilience,
        "supply_cold_chain_resilience": supply_cold_chain_resilience,
        "integrated_facility_priority": integrated_facility_priority,
        "quarantined_records": staging_report["quarantined_rows"],
        "staging_yield_pct": staging_report["staging_yield_pct"],
        "detector_evaluation_scope": quality_report["evaluation_scope"],
        "peer_anomaly_records": statistical_report["peer_anomaly_records"],
        "target_attainment_outputs": attainment_report["outputs"],
        "target_attainment_method": attainment_report["method"],
        "resource_planning_outputs": resource_report["outputs"],
        "resource_planning_assumptions": resource_report["limitations"],
        "supply_chain_outputs": supply_report["outputs"],
        "supply_chain_inventory_records": supply_report["inventory_records"],
        "supply_chain_stockout_pairs": supply_report["facility_commodity_pairs_with_recent_stockout"],
        "supply_chain_requested_replenishment_units": supply_report["requested_replenishment_units"],
        "supply_chain_allocated_replenishment_units": supply_report["allocated_replenishment_units"],
        "supply_chain_unfunded_replenishment_units": supply_report["unfunded_replenishment_units"],
        "supply_chain_allocated_cost_credits": supply_report["allocated_cost_credits"],
        "supply_chain_assumptions": supply_report["limitations"],
        "cold_chain_outputs": cold_chain_report["outputs"],
        "cold_chain_temperature_records": cold_chain_report["temperature_monitoring_records"],
        "cold_chain_batch_records": cold_chain_report["batch_ledger_records"],
        "cold_chain_high_risk_pairs": cold_chain_report["latest_high_risk_facility_commodity_pairs"],
        "cold_chain_near_expiry_units": cold_chain_report["latest_near_expiry_90_day_units"],
        "cold_chain_expired_units": cold_chain_report["total_expired_units"],
        "cold_chain_assumptions": cold_chain_report["limitations"],
        "equipment_asset_count": equipment_report["assets"],
        "equipment_asset_month_records": equipment_report["asset_month_records"],
        "equipment_maintenance_work_orders": equipment_report["maintenance_work_orders"],
        "equipment_latest_high_risk_assets": equipment_report["latest_high_risk_assets"],
        "equipment_latest_mean_operational_uptime_pct": equipment_report["latest_mean_operational_uptime_pct"],
        "equipment_maintenance_assumptions": equipment_report["limitations"],
        "infrastructure_facility_month_records": infrastructure_report["facility_month_records"],
        "infrastructure_latest_high_risk_facilities": infrastructure_report["latest_high_risk_facilities"],
        "infrastructure_latest_mean_resilience_score": infrastructure_report["latest_mean_resilience_score"],
        "infrastructure_equipment_association_months": infrastructure_report["equipment_association_facility_months"],
        "infrastructure_assumptions": infrastructure_report["limitations"],
        "workforce_facility_month_records": workforce_report["facility_month_records"],
        "workforce_latest_mean_coverage_pct": workforce_report["latest_mean_coverage_pct"],
        "workforce_latest_high_risk_facilities": workforce_report["latest_high_review_priority_facilities"],
        "workforce_baseline_vacancies": workforce_report["total_baseline_vacancies"],
        "workforce_funded_recruitment_positions": workforce_report["funded_recruitment_positions"],
        "workforce_assumptions": workforce_report["limitations"],
        "months_monitored": statistical_report["months_monitored"],
        "ground_truth_used_for_operational_monitoring": False,
        "outputs": {
            "raw_fact": str(fact_path),
            "facility_dimension": str(facility_path),
            "staged_fact": str(staged_path),
            "staging_quality_report": str(staged_dir / "staging_quality_report.json"),
            "quarantine": str(staged_dir / "facility_reporting_quarantine.csv"),
            "quality_analytics_report": str(analytics_dir / "quality_analytics_report.json"),
            "statistical_monitoring_report": str(analytics_dir / "statistical_monitoring_report.json"),
            "target_attainment_report": str(analytics_dir / "target_attainment_report.json"),
            "detector_metrics": str(analytics_dir / "detector_evaluation_metrics.csv"),
            "monthly_trends": str(analytics_dir / "monthly_quality_trends.csv"),
            "facility_benchmark": str(analytics_dir / "facility_quality_benchmark.csv"),
            "programme_profile": str(analytics_dir / "programme_indicator_quality_profile.csv"),
            "district_profile": str(analytics_dir / "district_quality_profile.csv"),
            "district_monthly_trends": str(analytics_dir / "district_monthly_quality_trends.csv"),
            "peer_anomalies": str(analytics_dir / "statistical_peer_anomalies.csv"),
            "monthly_control_chart": str(analytics_dir / "monthly_issue_control_chart.csv"),
            "facility_indicator_attainment": str(analytics_dir / "facility_indicator_target_attainment.csv"),
            "district_indicator_attainment": str(analytics_dir / "district_indicator_target_attainment.csv"),
            "programme_indicator_attainment": str(analytics_dir / "programme_indicator_target_attainment.csv"),
            "monthly_indicator_attainment": str(analytics_dir / "monthly_indicator_target_attainment.csv"),
            "facility_resource_capacity": str(analytics_dir / "facility_resource_capacity.csv"),
            "resource_allocation_scenarios": str(analytics_dir / "resource_allocation_scenarios.csv"),
            "resource_allocation_summary": str(analytics_dir / "resource_allocation_scenario_summary.csv"),
            "resource_planning_report": str(analytics_dir / "resource_planning_report.json"),
            "commodity_catalog": str(analytics_dir / "commodity_catalog.csv"),
            "commodity_stock_ledger": str(analytics_dir / "facility_commodity_stock_ledger.csv"),
            "commodity_replenishment_plan": str(analytics_dir / "commodity_replenishment_plan.csv"),
            "commodity_replenishment_summary": str(analytics_dir / "commodity_replenishment_summary.csv"),
            "supply_chain_planning_report": str(analytics_dir / "supply_chain_planning_report.json"),
            "cold_chain_catalog": str(analytics_dir / "cold_chain_catalog.csv"),
            "cold_chain_temperature_monitoring": str(analytics_dir / "facility_cold_chain_temperature_monitoring.csv"),
            "cold_chain_batch_ledger": str(analytics_dir / "facility_commodity_batch_ledger.csv"),
            "cold_chain_expiry_risk_summary": str(analytics_dir / "cold_chain_expiry_risk_summary.csv"),
            "cold_chain_planning_report": str(analytics_dir / "cold_chain_planning_report.json"),
            "equipment_catalog": str(analytics_dir / "equipment_catalog.csv"),
            "equipment_asset_register": str(analytics_dir / "facility_equipment_asset_register.csv"),
            "equipment_asset_monthly_performance": str(analytics_dir / "equipment_asset_monthly_performance.csv"),
            "facility_equipment_monthly_summary": str(analytics_dir / "facility_equipment_monthly_summary.csv"),
            "equipment_maintenance_work_orders": str(analytics_dir / "equipment_maintenance_work_orders.csv"),
            "equipment_latest_asset_status": str(analytics_dir / "equipment_latest_asset_risk_status.csv"),
            "equipment_maintenance_report": str(analytics_dir / "equipment_maintenance_report.json"),
            "facility_infrastructure_profiles": str(analytics_dir / "facility_infrastructure_profiles.csv"),
            "monthly_infrastructure_reliability": str(analytics_dir / "facility_monthly_infrastructure_reliability.csv"),
            "latest_infrastructure_resilience": str(analytics_dir / "facility_latest_infrastructure_resilience.csv"),
            "equipment_infrastructure_association": str(analytics_dir / "equipment_infrastructure_association.csv"),
            "infrastructure_upgrade_scenarios": str(analytics_dir / "infrastructure_upgrade_scenarios.csv"),
            "infrastructure_planning_report": str(analytics_dir / "infrastructure_planning_report.json"),
            "workforce_establishment": str(analytics_dir / "facility_workforce_establishment.csv"),
            "monthly_workforce_capacity": str(analytics_dir / "facility_monthly_workforce_capacity.csv"),
            "latest_workforce_capacity": str(analytics_dir / "facility_latest_workforce_capacity.csv"),
            "monthly_operational_resilience": str(analytics_dir / "facility_monthly_operational_resilience.csv"),
            "latest_operational_resilience": str(analytics_dir / "facility_latest_operational_resilience.csv"),
            "monthly_supply_cold_chain_resilience": str(analytics_dir / "facility_monthly_supply_cold_chain_resilience.csv"),
            "latest_supply_cold_chain_resilience": str(analytics_dir / "facility_latest_supply_cold_chain_resilience.csv"),
            "integrated_facility_priority_register": str(analytics_dir / "integrated_facility_priority_register.csv"),
            "workforce_recruitment_scenario": str(analytics_dir / "workforce_recruitment_scenario.csv"),
            "workforce_planning_report": str(analytics_dir / "workforce_planning_report.json"),
        },
    }
    # Publish an integrity manifest only after every advertised artifact has
    # been verified as a non-empty file inside this build's output directory.
    summary["artifact_manifest"] = _build_artifact_manifest(
        summary["outputs"], output_dir
    )
    summary["artifact_count"] = len(summary["artifact_manifest"])
    summary["artifact_total_bytes"] = sum(
        item["size_bytes"] for item in summary["artifact_manifest"].values()
    )
    (output_dir / "platform_build_summary.json").write_text(json.dumps(summary, indent=2))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("data/warehouse"))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--facilities", type=int, default=120)
    parser.add_argument("--start-month", default="2021-01-01")
    parser.add_argument("--periods", type=int, default=60)
    args = parser.parse_args()
    print(json.dumps(build_platform(
        output_dir=args.output_dir,
        seed=args.seed,
        facility_count=args.facilities,
        start_month=args.start_month,
        periods=args.periods,
    ), indent=2))


if __name__ == "__main__":
    main()
