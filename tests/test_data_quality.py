"""
Automated tests for data quality rules and metrics.

This test suite validates the data quality calculations implemented in
the health data quality analysis notebook.
"""

import pandas as pd
import numpy as np
import pytest


def test_completeness_calculation():
    """Test that completeness is calculated correctly based on field presence."""
    # Create test data with known completeness
    test_data = pd.DataFrame({
        "Facility": ["A", "A", "B"],
        "Programme": ["HIV", "HIV", "TB"],
        "Indicator": ["I1", "I2", "I3"],
        "Reporting_Date": pd.to_datetime(["2024-01-15", "2024-01-15", "2024-01-15"]),
        "Reported_Value": [100, np.nan, 50],  # One missing
        "Target_Value": [120, 80, 60],
        "Data_Source": ["DHIS2", "DHIS2", "DHIS2"],
        "Source_1": [100, 95, 50],
        "Source_2": [105, 85, 52],
        "Source_3": [98, 90, 48]
    })
    
    # Calculate completeness based on field presence
    required_fields = ["Reported_Value", "Target_Value", "Data_Source"]
    test_data["Calculated_Completeness"] = test_data[required_fields].notna().mean(axis=1)
    
    # Expected: row 0 = 1.0 (all present), row 1 = 0.67 (missing Reported_Value), row 2 = 1.0
    expected_completeness = [1.0, 2/3, 1.0]
    
    assert list(test_data["Calculated_Completeness"].round(2)) == [round(x, 2) for x in expected_completeness]


def test_timeliness_calculation():
    """Test that timeliness is calculated correctly based on reporting dates."""
    # Create test data with known reporting dates
    test_data = pd.DataFrame({
        "Reporting_Date": pd.to_datetime(["2024-01-10", "2024-01-25", "2024-02-05"]),
        "Month": pd.to_datetime(["2024-01-01", "2024-01-01", "2024-02-01"])
    })
    
    # Assume due date is 15th of each month
    test_data["Due_Date"] = test_data["Month"] + pd.offsets.MonthBegin(0) + pd.Timedelta(days=14)
    test_data["Calculated_Timeliness"] = np.where(
        test_data["Reporting_Date"] <= test_data["Due_Date"],
        "On Time",
        "Late"
    )
    
    # Expected: row 0 = On Time (Jan 10), row 1 = Late (Jan 25), row 2 = On Time (Feb 5)
    expected_timeliness = ["On Time", "Late", "On Time"]
    
    assert list(test_data["Calculated_Timeliness"]) == expected_timeliness


def test_consistency_threshold():
    """Test that the improved consistency threshold (20% relative + 5 absolute) works correctly."""
    test_data = pd.DataFrame({
        "Source_Max": [100, 100, 10, 10],
        "Source_Min": [85, 70, 8, 4],
        "Reported_Value": [90, 85, 9, 7]
    })
    
    # Calculate discrepancy percentage
    test_data["Source_Discrepancy_Pct"] = (
        (test_data["Source_Max"] - test_data["Source_Min"]) / test_data["Source_Max"] * 100
    )
    
    # Apply improved threshold: 20% relative OR 5 absolute
    test_data["Consistency_Flag_Improved"] = np.where(
        (test_data["Source_Discrepancy_Pct"] <= 20) | 
        (test_data["Source_Max"] - test_data["Source_Min"] <= 5),
        "Consistent",
        "Inconsistent"
    )
    
    # Expected: 
    # Row 0: 15% diff, 15 absolute -> Consistent (15% <= 20%)
    # Row 1: 30% diff, 30 absolute -> Inconsistent (both thresholds exceeded)
    # Row 2: 20% diff, 2 absolute -> Consistent (2 <= 5 absolute)
    # Row 3: 60% diff, 6 absolute -> Inconsistent (both exceeded)
    expected = ["Consistent", "Inconsistent", "Consistent", "Inconsistent"]
    
    assert list(test_data["Consistency_Flag_Improved"]) == expected


def test_outlier_detection_iqr():
    """Test that IQR-based outlier detection works correctly."""
    # Create test data with known outliers
    np.random.seed(42)
    normal_values = np.random.normal(100, 10, 20)  # 20 normal values around 100
    outlier_values = [200, 250]  # 2 clear outliers
    test_values = np.concatenate([normal_values, outlier_values])
    
    test_data = pd.DataFrame({
        "Indicator": ["Test"] * 22,
        "Reported_Value": test_values
    })
    
    # Calculate IQR bounds
    q1 = test_data["Reported_Value"].quantile(0.25)
    q3 = test_data["Reported_Value"].quantile(0.75)
    iqr = q3 - q1
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr
    
    test_data["Outlier_Flag"] = (
        (test_data["Reported_Value"] < lower_bound) | 
        (test_data["Reported_Value"] > upper_bound)
    )
    
    # Should detect at least the two clear outliers
    outlier_count = test_data["Outlier_Flag"].sum()
    assert outlier_count >= 2, f"Expected at least 2 outliers, found {outlier_count}"


def test_facility_risk_score_normalization():
    """Test that facility risk scores are normalized by volume (using rates)."""
    test_data = pd.DataFrame({
        "Facility": ["A", "A", "B", "B", "C", "C"],
        "Reported_Value_Missing": [True, False, True, True, False, False],
        "Consistency_Flag": ["Inconsistent", "Consistent", "Inconsistent", "Inconsistent", "Consistent", "Consistent"],
        "Calculated_Timeliness": ["Late", "On Time", "Late", "Late", "On Time", "On Time"],
        "Outlier_Flag": [True, False, True, False, False, False],
        "Calculated_Completeness": [0.8, 1.0, 0.6, 0.7, 1.0, 1.0]
    })
    
    # Calculate risk scores using rates
    facility_metrics = []
    for facility in ["A", "B", "C"]:
        facility_subset = test_data[test_data["Facility"] == facility]
        missing_rate = facility_subset["Reported_Value_Missing"].mean()
        inconsistent_rate = (facility_subset["Consistency_Flag"] == "Inconsistent").mean()
        late_rate = (facility_subset["Calculated_Timeliness"] == "Late").mean()
        outlier_rate = facility_subset["Outlier_Flag"].mean()
        avg_completeness = facility_subset["Calculated_Completeness"].mean()
        
        risk_score = (
            missing_rate * 20 +
            inconsistent_rate * 20 +
            late_rate * 20 +
            outlier_rate * 20 +
            (1 - avg_completeness) * 20
        )
        
        facility_metrics.append({"Facility": facility, "Risk_Score": risk_score})
    
    risk_df = pd.DataFrame(facility_metrics)
    
    # Facility B should have highest risk (more issues)
    assert risk_df.loc[risk_df["Facility"] == "B", "Risk_Score"].values[0] > \
           risk_df.loc[risk_df["Facility"] == "A", "Risk_Score"].values[0]
    assert risk_df.loc[risk_df["Facility"] == "B", "Risk_Score"].values[0] > \
           risk_df.loc[risk_df["Facility"] == "C", "Risk_Score"].values[0]


def test_trend_aggregation_uses_rates():
    """Test that trend analysis uses rates instead of raw counts."""
    # Create test data with different volumes per month
    test_data = pd.DataFrame({
        "Month": ["2024-01", "2024-01", "2024-02", "2024-02", "2024-02"],
        "Reported_Value_Missing": [True, False, True, False, False],
        "Calculated_Timeliness": ["Late", "On Time", "Late", "On Time", "On Time"]
    })
    
    # Calculate rates by month
    monthly_rates = test_data.groupby("Month").agg({
        "Reported_Value_Missing": "mean",
        "Calculated_Timeliness": lambda x: (x == "Late").mean()
    })
    
    # January: 1 missing out of 2 = 50%, 1 late out of 2 = 50%
    # February: 1 missing out of 3 = 33%, 1 late out of 3 = 33%
    assert monthly_rates.loc["2024-01", "Reported_Value_Missing"] == 0.5
    assert monthly_rates.loc["2024-02", "Reported_Value_Missing"] == pytest.approx(1/3)
    assert monthly_rates.loc["2024-01", "Calculated_Timeliness"] == 0.5
    assert monthly_rates.loc["2024-02", "Calculated_Timeliness"] == pytest.approx(1/3)


if __name__ == "__main__":
    # Run tests
    test_completeness_calculation()
    print("✓ Completeness calculation test passed")
    
    test_timeliness_calculation()
    print("✓ Timeliness calculation test passed")
    
    test_consistency_threshold()
    print("✓ Consistency threshold test passed")
    
    test_outlier_detection_iqr()
    print("✓ Outlier detection test passed")
    
    test_facility_risk_score_normalization()
    print("✓ Facility risk score normalization test passed")
    
    test_trend_aggregation_uses_rates()
    print("✓ Trend aggregation test passed")
    
    print("\nAll tests passed!")


def test_production_consistency_rule_uses_hybrid_threshold():
    """The production flag uses the hybrid rule; the 10% baseline remains diagnostic."""
    from pathlib import Path
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from data_quality import DataQualityAssessor

    data = pd.DataFrame({
        "Paper_Value": [100, 10, 100],
        "EMR_Value": [110, 13, 100],
        "DHIS2_Value": [105, 12, 130],
    })
    assessed = DataQualityAssessor(data).assess_source_consistency()

    # A 10% difference is tolerated by the 20% hybrid rule.
    # A low-volume absolute difference of 3 is within the 5-unit tolerance.
    # A 30% difference at higher volume is flagged for review.
    assert assessed["Consistency_Flag"].tolist() == [
        "Consistent", "Consistent", "Review Required"
    ]
    assert assessed["Consistency_Flag_Baseline"].tolist() == [
        "Consistent", "Review Required", "Review Required"
    ]
