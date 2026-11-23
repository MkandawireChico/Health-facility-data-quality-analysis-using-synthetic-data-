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


def test_monthly_analytics_population_reconciles_across_all_views():
    import pandas as pd
    from build_platform import _validate_monthly_analytics_population

    quality = pd.DataFrame({
        "Month": ["2024-01-01", "2024-02-01"], "records": [12, 15],
    })
    monitoring = pd.DataFrame({
        "Month": ["2024-01-01", "2024-02-01"], "Records": [12, 15],
    })
    attainment = pd.DataFrame({
        "Month": ["2024-01-01", "2024-02-01"], "reporting_records": [12, 15],
    })

    assert _validate_monthly_analytics_population(
        quality, monitoring, attainment
    ) == {"months_reconciled": 2, "monthly_reporting_records": 27}


def test_monthly_analytics_population_rejects_denominator_drift():
    import pandas as pd
    import pytest
    from build_platform import _validate_monthly_analytics_population

    quality = pd.DataFrame({"Month": ["2024-01-01"], "records": [12]})
    monitoring = pd.DataFrame({"Month": ["2024-01-01"], "Records": [11]})
    attainment = pd.DataFrame({"Month": ["2024-01-01"], "reporting_records": [12]})

    with pytest.raises(RuntimeError, match="Monthly reporting population mismatch"):
        _validate_monthly_analytics_population(quality, monitoring, attainment)


def test_monthly_analytics_population_rejects_duplicate_month_rows():
    import pandas as pd
    import pytest
    from build_platform import _validate_monthly_analytics_population

    quality = pd.DataFrame({
        "Month": ["2024-01-01", "2024-01-15"], "records": [6, 6],
    })
    monitoring = pd.DataFrame({"Month": ["2024-01-01"], "Records": [12]})
    attainment = pd.DataFrame({"Month": ["2024-01-01"], "reporting_records": [12]})

    with pytest.raises(RuntimeError, match="duplicate month rows"):
        _validate_monthly_analytics_population(quality, monitoring, attainment)

def test_monthly_analytics_population_rejects_fractional_and_boolean_counts():
    import pandas as pd
    import pytest
    from build_platform import _validate_monthly_analytics_population

    quality = pd.DataFrame({"Month": ["2024-01-01"], "records": [12]})
    monitoring = pd.DataFrame({"Month": ["2024-01-01"], "Records": [12]})
    attainment = pd.DataFrame({
        "Month": ["2024-01-01"], "reporting_records": [12],
    })

    fractional = quality.copy()
    fractional.loc[0, "records"] = 12.5
    with pytest.raises(RuntimeError, match="invalid record counts"):
        _validate_monthly_analytics_population(
            fractional, monitoring, attainment
        )

    boolean = monitoring.copy()
    boolean["Records"] = [True]
    with pytest.raises(RuntimeError, match="invalid record counts"):
        _validate_monthly_analytics_population(
            quality, boolean, attainment
        )

def test_quality_profile_population_reconciles_across_dimensions():
    import pandas as pd
    from build_platform import _validate_quality_profile_population

    staged = pd.DataFrame({
        "Facility_ID": ["F1", "F1", "F2", "F2"],
        "District": ["North", "North", "South", "South"],
        "Programme": ["HIV", "TB", "HIV", "TB"],
        "Indicator": ["A", "B", "A", "B"],
    })
    facility = pd.DataFrame({
        "Facility_ID": ["F1", "F2"], "records": [2, 2],
    })
    district = pd.DataFrame({
        "District": ["North", "South"], "records": [2, 2],
    })
    programme = pd.DataFrame({
        "Programme": ["HIV", "TB"], "Indicator": ["A", "B"],
        "records": [2, 2],
    })

    assert _validate_quality_profile_population(
        staged, facility, district, programme
    ) == {
        "staged_records": 4,
        "facilities_reconciled": 2,
        "districts_reconciled": 2,
        "programme_indicator_groups_reconciled": 2,
    }


def test_quality_profile_population_rejects_record_count_drift():
    import pandas as pd
    import pytest
    from build_platform import _validate_quality_profile_population

    staged = pd.DataFrame({
        "Facility_ID": ["F1", "F1", "F2"],
        "District": ["North", "North", "South"],
        "Programme": ["HIV", "TB", "HIV"],
        "Indicator": ["A", "B", "A"],
    })
    facility = pd.DataFrame({
        "Facility_ID": ["F1", "F2"], "records": [1, 1],
    })
    district = pd.DataFrame({
        "District": ["North", "South"], "records": [2, 1],
    })
    programme = pd.DataFrame({
        "Programme": ["HIV", "TB"], "Indicator": ["A", "B"],
        "records": [2, 1],
    })

    with pytest.raises(RuntimeError, match="facility quality profile population"):
        _validate_quality_profile_population(staged, facility, district, programme)


def test_quality_profile_population_rejects_missing_groups_and_boolean_counts():
    import pandas as pd
    import pytest
    from build_platform import _validate_quality_profile_population

    staged = pd.DataFrame({
        "Facility_ID": ["F1", "F2"],
        "District": ["North", "South"],
        "Programme": ["HIV", "TB"],
        "Indicator": ["A", "B"],
    })
    facility = pd.DataFrame({
        "Facility_ID": ["F1", "F2"], "records": [True, 1],
    })
    district = pd.DataFrame({
        "District": ["North", "South"], "records": [1, 1],
    })
    programme = pd.DataFrame({
        "Programme": ["HIV", "TB"], "Indicator": ["A", "B"],
        "records": [1, 1],
    })

    with pytest.raises(RuntimeError, match="invalid record counts"):
        _validate_quality_profile_population(staged, facility, district, programme)
\n

def _planning_population_samples():
    import pandas as pd

    facilities = pd.DataFrame({
        "Facility_ID": ["F1", "F2"],
        "Facility_Name": ["Alpha", "Beta"],
        "District": ["North", "South"],
    })
    resource = facilities.copy()
    resource_scenarios = pd.concat([
        facilities.assign(Scenario=scenario)
        for scenario in ["gap_priority", "equity", "equal"]
    ], ignore_index=True)
    establishment = pd.DataFrame([
        {"Facility_ID": facility, "Role": role}
        for facility in ["F1", "F2"]
        for role in ["Nurse", "Clinician"]
    ])
    monthly = pd.DataFrame([
        {"Facility_ID": facility, "Month": month}
        for facility in ["F1", "F2"]
        for month in ["2024-01-01", "2024-02-01"]
    ])
    latest = facilities.assign(Month="2024-02-01")
    return facilities, resource, resource_scenarios, establishment, monthly, latest


def test_operational_planning_population_reconciles_resource_and_workforce_outputs():
    from build_platform import _validate_operational_planning_population

    samples = _planning_population_samples()
    assert _validate_operational_planning_population(*samples, 2) == {
        "facilities_reconciled": 2,
        "resource_scenarios_reconciled": 3,
        "workforce_roles_reconciled": 2,
        "workforce_months_reconciled": 2,
        "workforce_facility_month_rows": 4,
    }


def test_operational_planning_population_rejects_missing_resource_facility():
    import pytest
    from build_platform import _validate_operational_planning_population

    samples = list(_planning_population_samples())
    samples[1] = samples[1].iloc[:1].copy()
    with pytest.raises(RuntimeError, match="resource capacity facility population"):
        _validate_operational_planning_population(*samples, 2)


def test_operational_planning_population_rejects_incomplete_workforce_month_grid():
    import pytest
    from build_platform import _validate_operational_planning_population

    samples = list(_planning_population_samples())
    samples[4] = samples[4].iloc[:-1].copy()
    with pytest.raises(RuntimeError, match="facility-month grid"):
        _validate_operational_planning_population(*samples, 2)


def test_operational_planning_population_rejects_duplicate_resource_scenario_rows():
    import pandas as pd
    import pytest
    from build_platform import _validate_operational_planning_population

    samples = list(_planning_population_samples())
    samples[2] = pd.concat([samples[2], samples[2].iloc[[0]]], ignore_index=True)
    with pytest.raises(RuntimeError, match="duplicate facility-scenario"):
        _validate_operational_planning_population(*samples, 2)


def test_operational_resilience_views_reconcile_all_three_domains(tmp_path):
    import pandas as pd
    from build_platform import _build_operational_resilience_views

    facilities = pd.DataFrame({"Facility_ID": ["F1", "F2"]})
    base = [{"Facility_ID": f, "Facility_Name": n, "District": d, "Month": m}
        for f, n, d in [("F1", "Alpha", "North"), ("F2", "Beta", "South")]
        for m in ["2024-01-01", "2024-02-01"]]
    equipment = pd.DataFrame([{**r, "Mean_Operational_Uptime_Pct": 96, "Total_Downtime_Hours": 2, "High_Risk_Assets": 1, "PM_Overdue": 0} for r in base])
    infrastructure = pd.DataFrame([{**r, "Infrastructure_Resilience_Score": 80, "Unserved_Power_Interruption_Hours": 1, "Unserved_Water_Shortage_Hours": 2, "Connectivity_Downtime_Hours": 3} for r in base])
    workforce = pd.DataFrame([{**r, "Workforce_Coverage_Pct": 60 if r["Facility_ID"] == "F2" else 90, "Workforce_Pressure_Index": 20, "Vacant_Positions": 2, "Absent_Positions": 1} for r in base])
    result = _build_operational_resilience_views(facilities, equipment, infrastructure, workforce, tmp_path)
    assert result == {"facility_month_records": 4, "facilities_reconciled": 2, "months_reconciled": 2, "latest_review_priority_facilities": 1}
    latest = pd.read_csv(tmp_path / "facility_latest_operational_resilience.csv")
    assert latest.loc[latest["Facility_ID"].eq("F2"), "Operational_Review_Domains"].iloc[0] == "workforce"


def test_operational_resilience_views_reject_domain_population_drift(tmp_path):
    import pandas as pd
    import pytest
    from build_platform import _build_operational_resilience_views

    facilities = pd.DataFrame({"Facility_ID": ["F1"]})
    base = {"Facility_ID": "F1", "Facility_Name": "Alpha", "District": "North", "Month": "2024-01-01"}
    equipment = pd.DataFrame([{**base, "Mean_Operational_Uptime_Pct": 98, "Total_Downtime_Hours": 1, "High_Risk_Assets": 0, "PM_Overdue": 0}])
    infrastructure = pd.DataFrame([{**base, "Infrastructure_Resilience_Score": 90, "Unserved_Power_Interruption_Hours": 0, "Unserved_Water_Shortage_Hours": 0, "Connectivity_Downtime_Hours": 0}])
    workforce = pd.DataFrame([{**base, "Workforce_Coverage_Pct": 90, "Workforce_Pressure_Index": 10, "Vacant_Positions": 0, "Absent_Positions": 0}])
    workforce.loc[0, "Facility_ID"] = "F2"
    with pytest.raises(RuntimeError, match="facility population"):
        _build_operational_resilience_views(facilities, equipment, infrastructure, workforce, tmp_path)


def test_supply_cold_chain_resilience_view_reconciles_monthly_facility_populations(tmp_path):
    import pandas as pd
    from build_platform import _build_supply_cold_chain_resilience_view

    facilities = pd.DataFrame({"Facility_ID": ["F1", "F2"]})
    rows = [{"Facility_ID": f, "Facility_Name": n, "District": d, "Month": m}
        for f, n, d in [("F1", "Alpha", "North"), ("F2", "Beta", "South")]
        for m in ["2024-01-01", "2024-02-01"]]
    stock = pd.DataFrame([{**r, "Commodity_ID": "COM-001", "Demand_Units": 10,
        "Unmet_Demand_Units": 2, "Closing_Stock_Units": 4, "Stockout_Days": 3,
        "Stockout_Flag": True} for r in rows])
    cold = pd.DataFrame([{**r, "Commodity_ID": "CC-001", "Expired_Units": 1,
        "Near_Expiry_90_Day_Units": 2, "Temperature_Excursion_Days": 1,
        "Cold_Chain_Risk_Score": 75.0, "Risk_Band": "High"} for r in rows])

    result = _build_supply_cold_chain_resilience_view(facilities, stock, cold, tmp_path)
    assert result == {"facility_month_records": 4, "facilities_reconciled": 2,
        "months_reconciled": 2, "latest_supply_review_facilities": 2}
    latest = pd.read_csv(tmp_path / "facility_latest_supply_cold_chain_resilience.csv")
    assert latest["Supply_Review_Flag"].all()
    assert latest["Stockout_Commodity_Pairs"].eq(1).all()
    assert latest["High_Cold_Chain_Risk_Pairs"].eq(1).all()


def test_supply_cold_chain_resilience_view_rejects_monthly_population_drift(tmp_path):
    import pandas as pd
    import pytest
    from build_platform import _build_supply_cold_chain_resilience_view

    facilities = pd.DataFrame({"Facility_ID": ["F1"]})
    base = {"Facility_ID": "F1", "Facility_Name": "Alpha", "District": "North",
        "Month": "2024-01-01"}
    stock = pd.DataFrame([{**base, "Commodity_ID": "COM-001", "Demand_Units": 10,
        "Unmet_Demand_Units": 0, "Closing_Stock_Units": 5, "Stockout_Days": 0,
        "Stockout_Flag": False}])
    cold = pd.DataFrame([{**base, "Commodity_ID": "CC-001", "Expired_Units": 0,
        "Near_Expiry_90_Day_Units": 0, "Temperature_Excursion_Days": 0,
        "Cold_Chain_Risk_Score": 10.0, "Risk_Band": "Low"}])
    cold.loc[0, "Month"] = "2024-02-01"

    with pytest.raises(RuntimeError, match="reporting months do not match"):
        _build_supply_cold_chain_resilience_view(facilities, stock, cold, tmp_path)


def test_integrated_facility_priority_register_ranks_cross_domain_pressures(tmp_path):
    import pandas as pd
    from build_platform import _build_integrated_facility_priority

    facilities = pd.DataFrame({"Facility_ID": ["F1", "F2"]})
    operational = pd.DataFrame([
        {"Facility_ID": "F1", "Facility_Name": "Alpha", "District": "North",
         "Mean_Operational_Uptime_Pct": 98, "Infrastructure_Resilience_Score": 90,
         "Workforce_Coverage_Pct": 90, "Operational_Review_Flag": False,
         "Operational_Review_Domains": "none"},
        {"Facility_ID": "F2", "Facility_Name": "Beta", "District": "South",
         "Mean_Operational_Uptime_Pct": 80, "Infrastructure_Resilience_Score": 50,
         "Workforce_Coverage_Pct": 55, "Operational_Review_Flag": True,
         "Operational_Review_Domains": "equipment;infrastructure;workforce"},
    ])
    supply = pd.DataFrame([
        {"Facility_ID": "F1", "Facility_Name": "Alpha", "District": "North",
         "Supply_Review_Flag": False, "Stockout_Commodity_Pairs": 0,
         "High_Cold_Chain_Risk_Pairs": 0, "Near_Expiry_90_Day_Units": 0,
         "Temperature_Excursion_Days": 0},
        {"Facility_ID": "F2", "Facility_Name": "Beta", "District": "South",
         "Supply_Review_Flag": True, "Stockout_Commodity_Pairs": 2,
         "High_Cold_Chain_Risk_Pairs": 1, "Near_Expiry_90_Day_Units": 5,
         "Temperature_Excursion_Days": 2},
    ])
    quality = pd.DataFrame([
        {"Facility_ID": "F1", "Facility": "Alpha", "District": "North",
         "records": 100, "detected_issue_records": 5, "detected_issue_rate_pct": 5,
         "missing_records": 1, "source_discrepancy_records": 2,
         "outlier_records": 1, "late_records": 1},
        {"Facility_ID": "F2", "Facility": "Beta", "District": "South",
         "records": 100, "detected_issue_records": 35, "detected_issue_rate_pct": 35,
         "missing_records": 10, "source_discrepancy_records": 10,
         "outlier_records": 10, "late_records": 5},
    ])
    resource = pd.DataFrame([
        {"Facility_ID": "F1", "Facility_Name": "Alpha", "District": "North",
         "Illustrative_Requirement_Units": 10, "Synthetic_Available_Units": 9,
         "Baseline_Gap_Units": 1, "Baseline_Capacity_Coverage_Pct": 90},
        {"Facility_ID": "F2", "Facility_Name": "Beta", "District": "South",
         "Illustrative_Requirement_Units": 10, "Synthetic_Available_Units": 5,
         "Baseline_Gap_Units": 5, "Baseline_Capacity_Coverage_Pct": 50},
    ])

    result = _build_integrated_facility_priority(
        facilities, operational, supply, quality, resource, tmp_path
    )
    register = pd.read_csv(tmp_path / "integrated_facility_priority_register.csv")
    assert result["facilities_prioritised"] == 2
    assert register.iloc[0]["Facility_ID"] == "F2"
    assert register.iloc[0]["Priority_Band"] == "High review"
    assert register.iloc[0]["Review_Domains"] == "data_quality;resource_capacity;operational_resilience;supply_cold_chain"


def test_integrated_facility_priority_register_rejects_domain_population_drift(tmp_path):
    import pandas as pd
    import pytest
    from build_platform import _build_integrated_facility_priority

    facilities = pd.DataFrame({"Facility_ID": ["F1"]})
    base = {"Facility_ID": "F1", "Facility_Name": "Alpha", "District": "North"}
    operational = pd.DataFrame([{**base, "Mean_Operational_Uptime_Pct": 98,
        "Infrastructure_Resilience_Score": 90, "Workforce_Coverage_Pct": 90,
        "Operational_Review_Flag": False, "Operational_Review_Domains": "none"}])
    supply = pd.DataFrame([{**base, "Supply_Review_Flag": False,
        "Stockout_Commodity_Pairs": 0, "High_Cold_Chain_Risk_Pairs": 0,
        "Near_Expiry_90_Day_Units": 0, "Temperature_Excursion_Days": 0}])
    quality = pd.DataFrame([{**base, "records": 10, "detected_issue_records": 0,
        "detected_issue_rate_pct": 0, "missing_records": 0,
        "source_discrepancy_records": 0, "outlier_records": 0, "late_records": 0}])
    resource = pd.DataFrame([{**base, "Illustrative_Requirement_Units": 10,
        "Synthetic_Available_Units": 10, "Baseline_Gap_Units": 0,
        "Baseline_Capacity_Coverage_Pct": 100}])
    supply.loc[0, "Facility_ID"] = "F2"
    with pytest.raises(RuntimeError, match="facility population"):
        _build_integrated_facility_priority(
            facilities, operational, supply, quality, resource, tmp_path
        )
