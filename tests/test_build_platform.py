"""End-to-end tests for the platform build orchestrator."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from build_platform import build_platform


def test_small_end_to_end_platform_build(tmp_path):
    summary = build_platform(
        output_dir=tmp_path / "warehouse",
        seed=21,
        facility_count=6,
        start_month="2024-01-01",
        periods=2,
    )
    assert summary["synthetic_data"] is True
    assert summary["expected_fact_records"] == 6 * 2 * 40
    assert summary["generated_fact_records"] == 480
    assert summary["staged_records"] + summary["quarantined_records"] == 480
    assert summary["ground_truth_used_for_operational_monitoring"] is False
    assert summary["artifact_count"] == len(summary["outputs"])
    assert summary["artifact_total_bytes"] > 0
    assert summary["cold_chain_temperature_records"] == 6 * 2
    assert summary["cold_chain_batch_records"] > 0
    assert summary["cold_chain_high_risk_pairs"] >= 0
    assert summary["cold_chain_expired_units"] >= 0
    assert summary["equipment_asset_count"] > 0
    assert summary["equipment_asset_month_records"] == summary["equipment_asset_count"] * 2
    assert summary["equipment_maintenance_work_orders"] >= 0
    assert 0 <= summary["equipment_latest_mean_operational_uptime_pct"] <= 100
    assert summary["infrastructure_facility_month_records"] == 6 * 2
    assert summary["infrastructure_latest_high_risk_facilities"] >= 0
    assert 0 <= summary["infrastructure_latest_mean_resilience_score"] <= 100
    assert summary["infrastructure_equipment_association_months"] == 6 * 2
    assert summary["workforce_facility_month_records"] == 6 * 2
    assert 0 <= summary["workforce_latest_mean_coverage_pct"] <= 100
    assert summary["workforce_latest_high_risk_facilities"] >= 0
    assert summary["workforce_baseline_vacancies"] >= 0
    assert summary["workforce_funded_recruitment_positions"] >= 0

    expected_files = [
        "raw/facility_reporting_fact.csv",
        "raw/facility_dimension.csv",
        "raw/generation_manifest.json",
        "staged/facility_reporting_staged.csv",
        "staged/facility_reporting_quarantine.csv",
        "analytics/detector_evaluation_metrics.csv",
        "analytics/monthly_quality_trends.csv",
        "analytics/facility_quality_benchmark.csv",
        "analytics/programme_indicator_quality_profile.csv",
        "analytics/district_quality_profile.csv",
        "analytics/district_monthly_quality_trends.csv",
        "analytics/statistical_peer_anomalies.csv",
        "analytics/monthly_issue_control_chart.csv",
        "analytics/facility_indicator_target_attainment.csv",
        "analytics/district_indicator_target_attainment.csv",
        "analytics/programme_indicator_target_attainment.csv",
        "analytics/monthly_indicator_target_attainment.csv",
        "analytics/target_attainment_report.json",
        "analytics/facility_resource_capacity.csv",
        "analytics/resource_allocation_scenarios.csv",
        "analytics/resource_allocation_scenario_summary.csv",
        "analytics/resource_planning_report.json",
        "analytics/commodity_catalog.csv",
        "analytics/facility_commodity_stock_ledger.csv",
        "analytics/commodity_replenishment_plan.csv",
        "analytics/commodity_replenishment_summary.csv",
        "analytics/supply_chain_planning_report.json",
        "analytics/cold_chain_catalog.csv",
        "analytics/facility_cold_chain_temperature_monitoring.csv",
        "analytics/facility_commodity_batch_ledger.csv",
        "analytics/cold_chain_expiry_risk_summary.csv",
        "analytics/cold_chain_planning_report.json",
        "analytics/equipment_catalog.csv",
        "analytics/facility_equipment_asset_register.csv",
        "analytics/equipment_asset_monthly_performance.csv",
        "analytics/facility_equipment_monthly_summary.csv",
        "analytics/equipment_maintenance_work_orders.csv",
        "analytics/equipment_latest_asset_risk_status.csv",
        "analytics/equipment_maintenance_report.json",
        "analytics/facility_infrastructure_profiles.csv",
        "analytics/facility_monthly_infrastructure_reliability.csv",
        "analytics/facility_latest_infrastructure_resilience.csv",
        "analytics/equipment_infrastructure_association.csv",
        "analytics/infrastructure_upgrade_scenarios.csv",
        "analytics/infrastructure_planning_report.json",
        "analytics/facility_workforce_establishment.csv",
        "analytics/facility_monthly_workforce_capacity.csv",
        "analytics/facility_latest_workforce_capacity.csv",
        "analytics/workforce_recruitment_scenario.csv",
        "analytics/workforce_planning_report.json",
        "platform_build_summary.json",
    ]
    for relative in expected_files:
        assert (tmp_path / "warehouse" / relative).exists(), relative

    # Every artifact advertised by the platform manifest must exist on disk.
    for artifact_name, artifact_path in summary["outputs"].items():
        assert Path(artifact_path).exists(), artifact_name

    expected_report_keys = {
        "staging_quality_report",
        "quality_analytics_report",
        "statistical_monitoring_report",
        "target_attainment_report",
    }
    assert expected_report_keys.issubset(summary["outputs"])

    persisted = json.loads((tmp_path / "warehouse" / "platform_build_summary.json").read_text())
    assert persisted["generated_fact_records"] == 480


def test_build_configuration_is_rejected_before_creating_output(tmp_path):
    import pytest

    output_dir = tmp_path / "must-not-exist"
    invalid_options = [
        {"facility_count": 0},
        {"facility_count": True},
        {"periods": 0},
        {"periods": True},
        {"seed": True},
        {"seed": -1},
        {"start_month": "not-a-date"},
        {"start_month": ""},
        {"start_month": "2024-01-01T00:00:00+02:00"},
    ]
    for options in invalid_options:
        with pytest.raises(ValueError):
            build_platform(output_dir=output_dir, **options)
    assert not output_dir.exists()


def test_build_reconciles_every_advertised_artifact(tmp_path):
    summary = build_platform(
        output_dir=tmp_path / "warehouse",
        seed=8,
        facility_count=3,
        start_month="2024-01-01",
        periods=1,
    )
    assert summary["artifact_count"] == len(summary["outputs"])
    assert all(Path(path).is_file() for path in summary["outputs"].values())
    assert summary["artifact_total_bytes"] == sum(
        Path(path).stat().st_size for path in summary["outputs"].values()
    )



def test_artifact_manifest_records_relative_paths_sizes_and_sha256(tmp_path):
    import hashlib
    from build_platform import _build_artifact_manifest

    artifact = tmp_path / "warehouse" / "analytics" / "sample.csv"
    artifact.parent.mkdir(parents=True)
    payload = b"facility_id,value\nF001,12\n"
    artifact.write_bytes(payload)

    manifest = _build_artifact_manifest(
        {"sample": str(artifact)}, tmp_path / "warehouse"
    )

    assert manifest["sample"]["path"] == "analytics/sample.csv"
    assert manifest["sample"]["size_bytes"] == len(payload)
    assert manifest["sample"]["sha256"] == hashlib.sha256(payload).hexdigest()


def test_artifact_manifest_rejects_missing_empty_and_external_files(tmp_path):
    import pytest
    from build_platform import _build_artifact_manifest

    root = tmp_path / "warehouse"
    root.mkdir()
    missing = root / "missing.csv"
    with pytest.raises(RuntimeError, match="missing"):
        _build_artifact_manifest({"missing": str(missing)}, root)

    empty = root / "empty.csv"
    empty.touch()
    with pytest.raises(RuntimeError, match="empty"):
        _build_artifact_manifest({"empty": str(empty)}, root)

    outside = tmp_path / "outside.csv"
    outside.write_text("data\n1\n")
    with pytest.raises(RuntimeError, match="outside the output directory"):
        _build_artifact_manifest({"outside": str(outside)}, root)


def test_build_summary_contains_complete_artifact_integrity_manifest(tmp_path):
    import hashlib

    summary = build_platform(
        output_dir=tmp_path / "warehouse",
        seed=12,
        facility_count=3,
        start_month="2024-01-01",
        periods=1,
    )
    manifest = summary["artifact_manifest"]
    assert set(manifest) == set(summary["outputs"])
    for name, details in manifest.items():
        artifact = tmp_path / "warehouse" / details["path"]
        assert artifact.is_file()
        assert details["size_bytes"] == artifact.stat().st_size
        assert details["sha256"] == hashlib.sha256(artifact.read_bytes()).hexdigest()
    assert summary["artifact_total_bytes"] == sum(
        details["size_bytes"] for details in manifest.values()
    )



def test_generated_fact_grain_accepts_complete_unique_facility_month_indicator_grid():
    import pandas as pd
    from build_platform import _validate_generated_fact_grain

    facilities = pd.DataFrame({"Facility_ID": ["F1", "F2"]})
    fact = pd.DataFrame([
        {"Facility_ID": facility, "Month": month, "Programme": "HIV", "Indicator": indicator}
        for facility in ["F1", "F2"]
        for month in ["2024-01-01", "2024-02-01"]
        for indicator in ["A", "B"]
    ])
    result = _validate_generated_fact_grain(fact, facilities, 8, 2)
    assert result == {
        "unique_facility_month_groups": 4,
        "indicators_per_facility_month": 2,
        "unique_natural_keys": 8,
    }


def test_generated_fact_grain_rejects_duplicate_natural_key():
    import pandas as pd
    import pytest
    from build_platform import _validate_generated_fact_grain

    facilities = pd.DataFrame({"Facility_ID": ["F1"]})
    fact = pd.DataFrame([
        {"Facility_ID": "F1", "Month": "2024-01-01", "Programme": "HIV", "Indicator": "A"},
        {"Facility_ID": "F1", "Month": "2024-01-01", "Programme": "HIV", "Indicator": "A"},
    ])
    with pytest.raises(RuntimeError, match="duplicate facility-month-indicator"):
        _validate_generated_fact_grain(fact, facilities, 2, 1)


def test_generated_fact_grain_rejects_incomplete_facility_month_grid():
    import pandas as pd
    import pytest
    from build_platform import _validate_generated_fact_grain

    facilities = pd.DataFrame({"Facility_ID": ["F1", "F2"]})
    fact = pd.DataFrame([
        {"Facility_ID": "F1", "Month": "2024-01-01", "Programme": "HIV", "Indicator": "A"},
        {"Facility_ID": "F2", "Month": "2024-01-01", "Programme": "HIV", "Indicator": "A"},
        {"Facility_ID": "F1", "Month": "2024-02-01", "Programme": "HIV", "Indicator": "A"},
    ])
    with pytest.raises(RuntimeError, match="row count mismatch"):
        _validate_generated_fact_grain(fact, facilities, 4, 2)


def test_generated_fact_grain_rejects_unknown_facility():
    import pandas as pd
    import pytest
    from build_platform import _validate_generated_fact_grain

    facilities = pd.DataFrame({"Facility_ID": ["F1"]})
    fact = pd.DataFrame([
        {"Facility_ID": "F2", "Month": "2024-01-01", "Programme": "HIV", "Indicator": "A"},
    ])
    with pytest.raises(RuntimeError, match="absent from the dimension"):
        _validate_generated_fact_grain(fact, facilities, 1, 1)
