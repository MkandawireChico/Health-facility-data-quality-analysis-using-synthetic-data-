"""Staging, schema enforcement and quality profiling for the health data platform.

This pipeline separates structural rejection from analytical quality flags:
records with broken identity, facility relationships or reporting periods are
quarantined; records with measurable quality defects remain staged for analysis.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

FACT_REQUIRED = [
    "Record_ID", "Facility_ID", "Month", "Programme", "Indicator",
    "Reported_Value", "Target_Value", "Data_Source", "Paper_Value",
    "EMR_Value", "DHIS2_Value", "Submission_Date", "Deadline_Date",
]
FACILITY_REQUIRED = [
    "Facility_ID", "Facility_Name", "District", "Facility_Type",
    "Urban_Rural", "Ownership", "Catchment_Population",
]
NUMERIC_FIELDS = [
    "Reported_Value", "Target_Value", "Paper_Value", "EMR_Value", "DHIS2_Value",
]
SOURCE_VALUES = {"Paper Register", "EMR", "DHIS2"}
NATURAL_KEY = ["Facility_ID", "Month", "Programme", "Indicator"]


def _blank(series: pd.Series) -> pd.Series:
    return series.isna() | series.astype("string").str.strip().eq("").fillna(True)


def stage_reporting_data(
    fact: pd.DataFrame, facilities: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Normalize source tables, quarantine structural failures and profile quality."""
    missing_fact = sorted(set(FACT_REQUIRED) - set(fact.columns))
    missing_facilities = sorted(set(FACILITY_REQUIRED) - set(facilities.columns))
    if missing_fact:
        raise ValueError(f"Fact table missing required columns: {missing_fact}")
    if missing_facilities:
        raise ValueError(f"Facility table missing required columns: {missing_facilities}")
    if facilities.empty:
        raise ValueError("Facility dimension cannot be empty")
    dimension = facilities.copy()
    dimension["Facility_ID"] = dimension["Facility_ID"].astype("string").str.strip()
    if dimension["Facility_ID"].isna().any() or dimension["Facility_ID"].eq("").any():
        raise ValueError("Facility_ID must be populated in the facility dimension")
    if dimension["Facility_ID"].duplicated().any():
        raise ValueError("Facility_ID must be unique in the facility dimension")

    work = fact.copy().reset_index(drop=True)
    for column in ["Record_ID", "Facility_ID", "Programme", "Indicator", "Data_Source"]:
        work[column] = work[column].astype("string").str.strip()

    work["Month"] = pd.to_datetime(work["Month"], format="mixed", errors="coerce")
    work["Month"] = work["Month"].dt.to_period("M").dt.to_timestamp()
    for column in ["Submission_Date", "Deadline_Date"]:
        work[column] = pd.to_datetime(work[column], format="mixed", errors="coerce")
    for column in NUMERIC_FIELDS:
        work[column] = pd.to_numeric(work[column], errors="coerce")

    # Bring authoritative facility attributes from the dimension, not duplicated source text.
    facility_lookup = dimension.set_index("Facility_ID")
    known_facilities = work["Facility_ID"].isin(facility_lookup.index)
    work["Facility_Name"] = work["Facility_ID"].map(facility_lookup["Facility_Name"])
    work["District"] = work["Facility_ID"].map(facility_lookup["District"])
    work["Facility_Type"] = work["Facility_ID"].map(facility_lookup["Facility_Type"])
    work["Urban_Rural"] = work["Facility_ID"].map(facility_lookup["Urban_Rural"])
    work["Ownership"] = work["Facility_ID"].map(facility_lookup["Ownership"])

    structural = pd.DataFrame(index=work.index)
    structural["missing_record_id"] = _blank(work["Record_ID"])
    structural["duplicate_record_id"] = work["Record_ID"].duplicated(keep=False) & ~_blank(work["Record_ID"])
    structural["missing_facility_id"] = _blank(work["Facility_ID"])
    structural["unknown_facility_id"] = ~known_facilities & ~_blank(work["Facility_ID"])
    structural["invalid_reporting_month"] = work["Month"].isna()
    for column in ["Programme", "Indicator"]:
        structural[f"blank_{column.lower()}"] = _blank(work[column])

    # Duplicate natural keys are structurally ambiguous; quarantine all members.
    duplicate_natural_key = work.duplicated(NATURAL_KEY, keep=False)
    structural["duplicate_natural_key"] = duplicate_natural_key
    structural["structural_error_count"] = structural.sum(axis=1)
    quarantine_mask = structural["structural_error_count"].gt(0)

    work["Quality_Invalid_Numeric_Count"] = 0
    work["Quality_Negative_Value_Count"] = 0
    for column in NUMERIC_FIELDS:
        invalid = fact[column].notna().reset_index(drop=True) & work[column].isna()
        negative = work[column].lt(0)
        work["Quality_Invalid_Numeric_Count"] += invalid.astype(int)
        work["Quality_Negative_Value_Count"] += negative.astype(int)

    work["Quality_Missing_Reported_Value"] = work["Reported_Value"].isna()
    work["Quality_Invalid_Source_Label"] = ~work["Data_Source"].isin(SOURCE_VALUES)
    work["Quality_Missing_Submission_Date"] = work["Submission_Date"].isna()
    work["Quality_Missing_Deadline_Date"] = work["Deadline_Date"].isna()
    work["Quality_Late_Submission"] = (
        work["Submission_Date"].notna()
        & work["Deadline_Date"].notna()
        & work["Submission_Date"].gt(work["Deadline_Date"])
    )
    source_count = work[["Paper_Value", "EMR_Value", "DHIS2_Value"]].notna().sum(axis=1)
    work["Quality_Insufficient_Source_Count"] = source_count.lt(2)
    source_max = work[["Paper_Value", "EMR_Value", "DHIS2_Value"]].max(axis=1)
    source_min = work[["Paper_Value", "EMR_Value", "DHIS2_Value"]].min(axis=1)
    work["Quality_Source_Spread"] = source_max - source_min
    work["Quality_Source_Discrepancy"] = (
        source_count.ge(2) & work["Quality_Source_Spread"].gt(5)
        & (
            source_min.le(0)
            | ((source_max - source_min) / source_min.where(source_min.gt(0)) > 0.20)
        )
    )

    for column in structural.columns:
        work[f"Structural_{column}"] = structural[column].astype(bool)
    work["Structural_Error_Count"] = structural["structural_error_count"].astype(int)
    staged = work.loc[~quarantine_mask].copy()
    quarantine = work.loc[quarantine_mask].copy()
    issue_columns = [c for c in staged.columns if c.startswith("Quality_")]
    summary = {
        "source_fact_rows": int(len(fact)),
        "facility_dimension_rows": int(len(dimension)),
        "staged_rows": int(len(staged)),
        "quarantined_rows": int(len(quarantine)),
        "staging_yield_pct": round(100 * len(staged) / len(fact), 2) if len(fact) else 0.0,
        "duplicate_facility_keys": int(fact["Facility_ID"].isin(
            dimension.loc[dimension["Facility_ID"].duplicated(keep=False), "Facility_ID"]
        ).sum()),
        "quality_issue_counts": {
            column: int(staged[column].sum()) for column in issue_columns
        },
        "quality_issue_rows": int(staged[issue_columns].any(axis=1).sum()) if issue_columns else 0,
        "structural_rejection_reasons": {
            column: int(structural[column].sum())
            for column in structural.columns if column != "structural_error_count"
        },
        "synthetic_data": bool(
            "Is_Synthetic" in dimension.columns and dimension["Is_Synthetic"].fillna(False).all()
        ),
        "ground_truth_fields_excluded_from_quality_rules": True,
    }
    return staged, quarantine, summary


def run_pipeline(
    fact_path: Path, facility_path: Path, output_dir: Path
) -> dict[str, Any]:
    """Run CSV ingestion, staging and quality profiling; persist reproducible outputs."""
    fact = pd.read_csv(fact_path)
    facilities = pd.read_csv(facility_path)
    staged, quarantine, summary = stage_reporting_data(fact, facilities)
    output_dir.mkdir(parents=True, exist_ok=True)
    staged.to_csv(output_dir / "facility_reporting_staged.csv", index=False)
    quarantine.to_csv(output_dir / "facility_reporting_quarantine.csv", index=False)
    (output_dir / "staging_quality_report.json").write_text(json.dumps(summary, indent=2))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fact", type=Path, default=Path("data/warehouse/raw/facility_reporting_fact.csv"))
    parser.add_argument("--facilities", type=Path, default=Path("data/warehouse/raw/facility_dimension.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/warehouse/staged"))
    args = parser.parse_args()
    print(json.dumps(run_pipeline(args.fact, args.facilities, args.output_dir), indent=2))


if __name__ == "__main__":
    main()
