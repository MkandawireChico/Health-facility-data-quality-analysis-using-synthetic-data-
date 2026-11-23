"""Tests for statistical quality monitoring."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from statistical_monitoring import detect_peer_anomalies, build_monthly_control_chart


def peer_data(values, monthly=True):
    n = len(values)
    months = pd.date_range("2024-01-01", periods=n, freq="MS") if monthly else [pd.Timestamp("2024-01-01")] * n
    return pd.DataFrame({
        "Month": months,
        "District": ["Lilongwe"] * n, "Programme": ["HIV"] * n,
        "Indicator": ["ART clients"] * n, "Reported_Value": values,
        "Target_Value": [100] * n,
        "Facility_ID": [f"F{i}" for i in range(n)],
        "Quality_Missing_Reported_Value": [False] * n,
        "Quality_Source_Discrepancy": [False] * n,
        "Quality_Late_Submission": [False] * n,
    })


def test_mad_detector_flags_extreme_peer_value():
    result = detect_peer_anomalies(peer_data([100, 102, 99, 101, 98, 103, 100, 101, 900], monthly=False))
    assert result["Statistical_Anomaly"].sum() == 1
    assert result.loc[result["Statistical_Anomaly"], "Reported_Value"].iloc[0] == 900
    assert result["Statistical_Method"].eq("MAD robust z-score").all()


def test_non_finite_peer_values_are_excluded_from_peer_statistics():
    data = peer_data([100, 101, 99, 102, 98, 100, 101, 99, float("inf")], monthly=False)
    result = detect_peer_anomalies(data)
    assert result["Peer_Group_Size"].eq(8).all()
    assert not result.loc[8, "Statistical_Anomaly"]
    assert pd.isna(result.loc[8, "Statistical_Anomaly_Score"])


def test_non_finite_reported_value_is_not_counted_as_operational_outlier():
    data = peer_data([100] * 12)
    data.loc[0, "Reported_Value"] = float("inf")
    result = build_monthly_control_chart(data)
    assert result.loc[0, "Outlier_Records"] == 0
    assert result.loc[0, "Issue_Records"] == 0


def test_monitoring_parameters_reject_non_finite_or_boolean_values():
    with pytest.raises(ValueError, match="threshold must be finite"):
        detect_peer_anomalies(peer_data([10] * 8, monthly=False), robust_z_threshold=float("inf"))
    with pytest.raises(ValueError, match="min_group_size"):
        detect_peer_anomalies(peer_data([10] * 8, monthly=False), min_group_size=True)
    with pytest.raises(ValueError, match="min_baseline_months"):
        build_monthly_control_chart(peer_data([10] * 12), min_baseline_months=True)


def test_insufficient_peer_group_is_not_flagged():
    result = detect_peer_anomalies(peer_data([10, 11, 12, 100], monthly=False), min_group_size=8)
    assert not result["Statistical_Anomaly"].any()
    assert result["Statistical_Method"].eq("Insufficient peer observations").all()


def test_iqr_fallback_when_mad_is_zero():
    result = detect_peer_anomalies(peer_data([10, 10, 10, 10, 10, 10, 10, 10, 100], monthly=False))
    assert result["Statistical_Method"].eq("IQR fallback").all()
    assert result["Statistical_Anomaly"].sum() == 1


def test_monthly_control_chart_has_descriptive_limits():
    data = peer_data([10] * 12)
    data.loc[0, "Quality_Late_Submission"] = True
    result = build_monthly_control_chart(data)
    assert len(result) == 12
    assert result["Centre_Line"].notna().all()
    assert result["Control_Status"].isin(["Within descriptive limits", "Review signal"]).all()


def test_monthly_control_chart_includes_outlier_detector():
    data = peer_data([100] * 12)
    data.loc[0, "Reported_Value"] = 180
    result = build_monthly_control_chart(data)
    assert result.loc[0, "Outlier_Records"] == 1
    assert result.loc[0, "Issue_Records"] == 1
    assert result.loc[0, "Issue_Rate"] == pytest.approx(1.0)


def test_monthly_control_chart_parses_csv_boolean_strings():
    data = peer_data([100] * 12)
    data["Quality_Late_Submission"] = ["False"] * 12
    data.loc[0, "Quality_Late_Submission"] = "True"
    result = build_monthly_control_chart(data)
    assert result.loc[0, "Late_Records"] == 1
    assert result["Late_Records"].sum() == 1


def test_short_history_does_not_create_limits():
    result = build_monthly_control_chart(peer_data([10] * 5))
    assert result["Centre_Line"].isna().all()
    assert result["Control_Status"].eq("Insufficient baseline").all()


def test_ground_truth_columns_are_not_required_or_used():
    data = peer_data([100, 101, 99, 102, 98, 100, 101, 99, 500], monthly=False)
    data["Ground_Truth_Outlier"] = [False] * 8 + [True]
    a = detect_peer_anomalies(data)
    data["Ground_Truth_Outlier"] = False
    b = detect_peer_anomalies(data)
    pd.testing.assert_series_equal(a["Statistical_Anomaly"], b["Statistical_Anomaly"])


def test_peer_groups_are_scoped_to_reporting_month():
    data = peer_data([100, 101, 99, 102, 98, 100, 101, 99, 500], monthly=False)
    data.loc[8, "Month"] = pd.Timestamp("2024-02-01")
    result = detect_peer_anomalies(data)
    assert result.loc[:7, "Peer_Group_Size"].eq(8).all()
    assert result.loc[8, "Peer_Group_Size"] == 1
    assert not result.loc[8, "Statistical_Anomaly"]



def test_control_limits_use_pooled_rate_and_month_specific_denominators():
    sizes = [1, 2, 3, 4, 5, 6]
    data = peer_data([100] * sum(sizes), monthly=False)
    months = []
    for month, size in enumerate(sizes, start=1):
        months.extend([pd.Timestamp(2024, month, 1)] * size)
    data["Month"] = months
    # One flagged record in each month: pooled rate is 6 / 21.
    data.loc[data.groupby("Month").head(1).index, "Quality_Late_Submission"] = True

    result = build_monthly_control_chart(data)
    pooled_rate = 6 / 21
    expected_se = np.sqrt(pooled_rate * (1 - pooled_rate) / result["Records"])

    np.testing.assert_allclose(result["Centre_Line"], pooled_rate)
    np.testing.assert_allclose(
        result["Upper_Control_Limit"],
        np.minimum(1.0, pooled_rate + 3 * expected_se),
    )
    assert result.loc[0, "Upper_Control_Limit"] > result.loc[5, "Upper_Control_Limit"]


def test_control_chart_rejects_invalid_baseline_length():
    with pytest.raises(ValueError, match="at least 2"):
        build_monthly_control_chart(peer_data([10] * 12), min_baseline_months=1)



def test_control_chart_ignores_non_finite_and_overflowed_outlier_ratios():
    data = peer_data([100] * 12)
    data.loc[0, "Reported_Value"] = float("inf")
    data.loc[1, "Target_Value"] = float("inf")
    data.loc[2, "Reported_Value"] = float("1e308")
    data.loc[2, "Target_Value"] = float("1e-308")

    result = build_monthly_control_chart(data)

    assert result["Outlier_Records"].sum() == 0
    assert result["Issue_Records"].sum() == 0
