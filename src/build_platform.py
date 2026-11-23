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




def _validate_generated_fact_grain(
    fact: pd.DataFrame, facilities: pd.DataFrame, expected_records: int,
    expected_periods: int,
) -> dict[str, int]:
    """Fail fast when generated facts violate the facility-month-indicator grain."""
    key = ["Facility_ID", "Month", "Programme", "Indicator"]
    missing = sorted(set(key) - set(fact.columns))
    if missing:
        raise RuntimeError(f"Generated fact is missing grain columns: {missing}")
    if fact.empty or len(fact) != expected_records:
        raise RuntimeError(
            f"Generated fact row count mismatch: expected {expected_records}, got {len(fact)}"
        )
    if facilities.empty or facilities["Facility_ID"].isna().any():
        raise RuntimeError("Generated facility dimension contains missing facility identifiers")
    if facilities["Facility_ID"].duplicated().any():
        raise RuntimeError("Generated facility dimension contains duplicate facility identifiers")
    if fact[key].isna().any().any():
        raise RuntimeError("Generated fact contains null natural-key values")
    for column in ["Facility_ID", "Programme", "Indicator"]:
        if fact[column].astype("string").str.strip().eq("").any():
            raise RuntimeError(f"Generated fact contains blank {column} values")
    if fact.duplicated(key).any():
        raise RuntimeError("Generated fact contains duplicate facility-month-indicator keys")
    if not fact["Facility_ID"].isin(facilities["Facility_ID"]).all():
        raise RuntimeError("Generated fact references facilities absent from the dimension")

    months = pd.to_datetime(fact["Month"], errors="coerce")
    if months.isna().any():
        raise RuntimeError("Generated fact contains invalid reporting months")
    month_periods = months.dt.to_period("M")
    if month_periods.nunique() != expected_periods:
        raise RuntimeError("Generated fact reporting-period count does not match configuration")
    indicators = fact[["Programme", "Indicator"]].drop_duplicates()
    expected_per_facility_month = len(indicators)
    counts = fact.assign(_month=month_periods).groupby(
        ["Facility_ID", "_month"], observed=True
    ).size()
    expected_groups = len(facilities) * expected_periods
    if len(counts) != expected_groups or not counts.eq(expected_per_facility_month).all():
        raise RuntimeError("Generated fact has incomplete facility-month indicator coverage")
    return {
        "unique_facility_month_groups": int(len(counts)),
        "indicators_per_facility_month": int(expected_per_facility_month),
        "unique_natural_keys": int(len(fact)),
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
        counts = pd.to_numeric(frame[count_column], errors="coerce")
        if counts.isna().any() or counts.lt(0).any() or not np.isfinite(counts).all():
            raise RuntimeError(f"{label} monthly output contains invalid record counts")
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
    grain_validation = _validate_generated_fact_grain(
        fact, facilities, generator.expected_record_count, periods
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
