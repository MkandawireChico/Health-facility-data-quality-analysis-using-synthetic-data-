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
        "analytics/statistical_peer_anomalies.csv",
        "analytics/monthly_issue_control_chart.csv",
        "platform_build_summary.json",
    ]
    for relative in expected_files:
        assert (tmp_path / "warehouse" / relative).exists(), relative

    persisted = json.loads((tmp_path / "warehouse" / "platform_build_summary.json").read_text())
    assert persisted["generated_fact_records"] == 480
