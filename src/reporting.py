"""Reusable preparation and validation functions for health-facility reporting data."""
from __future__ import annotations

from typing import Any
import pandas as pd

REQUIRED_COLUMNS = [
    "Facility", "Programme", "Indicator", "Month", "Reported_Value",
    "Target_Value", "Data_Source", "Paper_Value", "EMR_Value", "DHIS2_Value",
]
NUMERIC_COLUMNS = [
    "Reported_Value", "Target_Value", "Paper_Value", "EMR_Value", "DHIS2_Value",
]
KEY_COLUMNS = ["Facility", "Month", "Programme", "Indicator"]


def validate_dataset(df: pd.DataFrame) -> dict[str, Any]:
    """Return actionable schema and data checks without mutating the input."""
    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    result: dict[str, Any] = {
        "valid": not missing and not df.empty,
        "missing_columns": missing,
        "row_count": int(len(df)),
        "duplicate_rows": 0,
        "invalid_months": 0,
        "invalid_numeric_values": {},
        "negative_values": {},
        "blank_dimensions": {},
        "warnings": [],
    }
    if missing:
        result["warnings"].append("The file is missing required columns.")
        return result
    if df.empty:
        result["warnings"].append("The uploaded file contains no records.")
        return result

    months = pd.to_datetime(df["Month"], errors="coerce")
    result["invalid_months"] = int(months.isna().sum())
    keys = df[KEY_COLUMNS].copy()
    keys["Month"] = months
    result["duplicate_rows"] = int(keys.duplicated(keep=False).sum())

    for column in NUMERIC_COLUMNS:
        values = pd.to_numeric(df[column], errors="coerce")
        invalid = df[column].notna() & values.isna()
        result["invalid_numeric_values"][column] = int(invalid.sum())
        result["negative_values"][column] = int((values < 0).sum())

    for column in ["Facility", "Programme", "Indicator", "Data_Source"]:
        result["blank_dimensions"][column] = int(
            df[column].isna().sum() + df[column].astype("string").str.strip().eq("").sum()
        )

    if result["invalid_months"]:
        result["warnings"].append("Some reporting periods are blank or cannot be parsed.")
    if result["duplicate_rows"]:
        result["warnings"].append("Duplicate facility-month-programme-indicator keys were found.")
    if any(result["invalid_numeric_values"].values()):
        result["warnings"].append("Some numeric fields contain non-numeric text.")
    if any(result["negative_values"].values()):
        result["warnings"].append("Negative values require review; they are not automatically changed.")
    if any(result["blank_dimensions"].values()):
        result["warnings"].append("Some facility or reporting dimensions are blank.")
    return result


def assess_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize types and run the shared production quality rules."""
    from data_quality import DataQualityAssessor

    work = df.copy()
    work["Month"] = pd.to_datetime(work["Month"], errors="coerce")
    for column in NUMERIC_COLUMNS:
        work[column] = pd.to_numeric(work[column], errors="coerce")
    for column in ["Facility", "Programme", "Indicator", "Data_Source"]:
        work[column] = work[column].astype("string").str.strip()

    assessor = DataQualityAssessor(work)
    assessor.calculate_field_completeness()
    if {"Submission_Date", "Deadline_Date"}.issubset(work.columns):
        assessor.calculate_timeliness_from_dates("Submission_Date", "Deadline_Date")
    else:
        assessor.calculate_timeliness_from_dates()
    assessor.assess_source_consistency(
        baseline_threshold=0.10,
        improved_threshold=0.20,
        absolute_tolerance=5,
    )
    assessor.detect_outliers_iqr(groupby_cols=["Programme", "Indicator"])
    assessor.assign_primary_issue()
    assessed = assessor.df
    assessed["Reported_Value_Missing"] = assessed["Reported_Value"].isna()
    return assessed


def facility_summary(assessed: pd.DataFrame) -> pd.DataFrame:
    """Build volume-normalised facility indicators and a transparent risk index."""
    from data_quality import DataQualityAssessor

    risk = DataQualityAssessor(assessed).calculate_facility_risk().reset_index()
    risk["On_Time_Rate"] = 1 - risk["Late_Rate"]
    grouped = assessed.groupby("Facility")["Consistency_Flag"]
    known = grouped.apply(lambda values: values.isin(["Consistent", "Review Required", "Inconsistent"]).sum())
    consistent = grouped.apply(lambda values: values.eq("Consistent").sum())
    risk["Consistency_Rate"] = consistent.div(known.replace(0, float("nan")))
    return risk.sort_values("Risk_Score", ascending=False)


def build_issue_register(assessed: pd.DataFrame) -> pd.DataFrame:
    """Create one row per record and a separate flag column for every issue type."""
    work = assessed.copy()
    work["Issue_Missing_Value"] = work["Reported_Value"].isna()
    work["Issue_Late_Report"] = work["Calculated_Timeliness"].eq("Late")
    work["Issue_Source_Discrepancy"] = work["Consistency_Flag"].eq("Review Required")
    work["Issue_Potential_Outlier"] = work["Outlier_Flag"].fillna(False).astype(bool)
    work["Issue_Low_Completeness"] = work["Calculated_Completeness"].lt(0.80)
    flag_columns = [
        "Issue_Missing_Value", "Issue_Late_Report", "Issue_Source_Discrepancy",
        "Issue_Potential_Outlier", "Issue_Low_Completeness",
    ]
    work["Issue_Count"] = work[flag_columns].sum(axis=1)
    work["Requires_Follow_Up"] = work["Issue_Count"].gt(0)
    return work
