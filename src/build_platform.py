"""One-command end-to-end build for the expanded synthetic health data platform."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scale_data_generator import ScaledHealthDataGenerator
from etl_pipeline import run_pipeline
from quality_analytics import run_quality_analytics
from statistical_monitoring import run_statistical_monitoring
from target_attainment import run_target_attainment
from resource_planning import run_resource_planning
from supply_chain_planning import run_supply_chain_planning


def build_platform(
    output_dir: Path = Path("data/warehouse"),
    seed: int = 42,
    facility_count: int = 120,
    start_month: str = "2021-01-01",
    periods: int = 60,
) -> dict[str, Any]:
    """Generate, stage, evaluate and statistically monitor a synthetic cohort."""
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

    if manifest["actual_record_count"] != generator.expected_record_count:
        raise RuntimeError("Generated record count does not match configured fact grain")
    if staging_report["staged_rows"] + staging_report["quarantined_rows"] != manifest["actual_record_count"]:
        raise RuntimeError("Staging row reconciliation failed")

    summary = {
        "synthetic_data": True,
        "seed": seed,
        "facility_count": facility_count,
        "period_count": periods,
        "programme_count": manifest["programme_count"],
        "indicator_count": manifest["indicator_count"],
        "expected_fact_records": generator.expected_record_count,
        "generated_fact_records": manifest["actual_record_count"],
        "staged_records": staging_report["staged_rows"],
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
        "supply_chain_assumptions": supply_report["limitations"],
        "months_monitored": statistical_report["months_monitored"],
        "ground_truth_used_for_operational_monitoring": False,
        "outputs": {
            "raw_fact": str(fact_path),
            "facility_dimension": str(facility_path),
            "staged_fact": str(staged_path),
            "quarantine": str(staged_dir / "facility_reporting_quarantine.csv"),
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
        },
    }
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
