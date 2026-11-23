"""Tests for quality detector evaluation and operational profiling."""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from quality_analytics import (
    add_operational_predictions,
    build_operational_profiles,
    build_district_profiles,
    evaluate_detectors,
    run_quality_analytics,
)


def analytics_fixture():
    return pd.DataFrame({
        "Record_ID": ["r1", "r2", "r3", "r4", "r5", "r6"],
        "Facility_ID": ["f1", "f1", "f2", "f2", "f3", "f3"],
        "Facility": ["Facility 1", "Facility 1", "Facility 2", "Facility 2", "Facility 3", "Facility 3"],
        "District": ["North", "North", "Central", "Central", "South", "South"],
        "Month": pd.to_datetime(["2025-01-01", "2025-01-01", "2025-02-01", "2025-02-01", "2025-02-01", "2025-03-01"]),
        "Programme": ["HIV", "HIV", "TB", "TB", "HIV", "TB"],
        "Indicator": ["A", "A", "B", "B", "A", "B"],
        "Reported_Value": [None, 220, 10, 10, 15, 10],
        "Target_Value": [100, 100, 10, 10, 10, 10],
        "Quality_Missing_Reported_Value": [True, False, False, False, False, False],
        "Quality_Source_Discrepancy": [False, True, False, False, False, False],
        "Quality_Late_Submission": [False, False, True, False, False, False],
        "Ground_Truth_Missing": [True, False, False, False, False, False],
        "Ground_Truth_Source_Discrepancy": [False, True, False, False, False, False],
        "Ground_Truth_Outlier": [False, True, False, False, False, False],
        "Ground_Truth_Late": [False, False, True, False, False, False],
    })


def test_perfect_detector_confusion_metrics_and_outlier_rule():
    metrics = evaluate_detectors(analytics_fixture()).set_index("defect")
    assert metrics.loc["missing", "precision"] == 1
    assert metrics.loc["missing", "recall"] == 1
    assert metrics.loc["missing", "f1"] == 1
    assert metrics.loc["source_discrepancy", "false_positive"] == 0
    assert metrics.loc["outlier", "true_positive"] == 1
    assert metrics.loc["outlier", "false_positive"] == 0
    assert metrics.loc["late", "specificity"] == 1


def test_non_finite_values_do_not_create_operational_outlier_signals():
    data = analytics_fixture()
    data.loc[0, "Reported_Value"] = float("inf")
    data.loc[1, "Target_Value"] = float("inf")
    data.loc[2, "Reported_Value"] = float("1e308")
    data.loc[2, "Target_Value"] = float("1e-308")

    result = add_operational_predictions(data)

    assert not result.loc[[0, 1, 2], "Operational_Detected_Outlier"].any()
    assert result.loc[[0, 1, 2], "Operational_Outlier_Ratio"].isna().all()


def test_operational_predictions_do_not_depend_on_ground_truth():
    data = analytics_fixture()
    first = add_operational_predictions(data)
    changed = data.copy()
    for col in [c for c in changed if c.startswith("Ground_Truth_")]:
        changed[col] = ~changed[col]
    second = add_operational_predictions(changed)
    pd.testing.assert_series_equal(
        first["Operational_Any_Detected_Issue"],
        second["Operational_Any_Detected_Issue"],
    )
    pd.testing.assert_series_equal(
        first["Operational_Detected_Outlier"],
        second["Operational_Detected_Outlier"],
    )


def test_operational_profiles_are_volume_normalised_and_ground_truth_free():
    monthly, facility, programme = build_operational_profiles(analytics_fixture())
    assert monthly["records"].sum() == 6
    assert set(facility["Facility_ID"]) == {"f1", "f2", "f3"}
    assert facility.iloc[0]["detected_issue_rate_pct"] >= facility.iloc[-1]["detected_issue_rate_pct"]
    for frame in [monthly, facility, programme]:
        assert not any(c.startswith("Ground_Truth_") for c in frame.columns)
    assert programme["records"].sum() == 6


def test_missing_evaluation_labels_fail_clearly():
    data = analytics_fixture().drop(columns=["Ground_Truth_Late"])
    with pytest.raises(ValueError, match="Ground_Truth_Late"):
        evaluate_detectors(data)


def test_pipeline_writes_metrics_and_profiles(tmp_path):
    staged = tmp_path / "staged.csv"
    analytics_fixture().to_csv(staged, index=False)
    report = run_quality_analytics(staged, tmp_path / "analytics")
    assert report["input_records"] == 6
    for name in report["outputs"]:
        assert (tmp_path / "analytics" / name).exists()


def test_district_profiles_are_volume_normalised_and_ground_truth_free():
    district, district_monthly = build_district_profiles(analytics_fixture())
    assert set(district["District"]) == {"North", "Central", "South"}
    assert district["records"].sum() == 6
    assert district["facilities"].sum() == 3
    assert district_monthly["records"].sum() == 6
    assert district_monthly["detected_issue_rate_pct"].between(0, 100).all()
    for frame in (district, district_monthly):
        assert not any(column.startswith("Ground_Truth_") for column in frame.columns)


def test_district_profile_rejects_missing_dimensions():
    with pytest.raises(ValueError, match="district dimensions"):
        build_district_profiles(analytics_fixture().drop(columns=["District"]))
