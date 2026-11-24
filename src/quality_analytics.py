"""Evaluate quality-rule detection against synthetic ground truth and profile trends.

Ground-truth labels are consumed only by evaluation functions. They are never
used to construct operational predictions, issue rates, facility rankings or
monthly monitoring outputs.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

TRUTH_TO_PREDICTION = {
    "missing": ("Ground_Truth_Missing", "Quality_Missing_Reported_Value"),
    "source_discrepancy": ("Ground_Truth_Source_Discrepancy", "Quality_Source_Discrepancy"),
    "outlier": ("Ground_Truth_Outlier", "Operational_Detected_Outlier"),
    "late": ("Ground_Truth_Late", "Quality_Late_Submission"),
}


def _as_bool(series: pd.Series) -> pd.Series:
    if series.dtype == object or str(series.dtype).startswith("string"):
        return series.astype("string").str.lower().isin({"true", "1", "yes"})
    return series.fillna(False).astype(bool)


def add_operational_predictions(data: pd.DataFrame) -> pd.DataFrame:
    """Create detector outputs without reading any Ground_Truth columns."""
    required = {
        "Reported_Value", "Target_Value", "Quality_Missing_Reported_Value",
        "Quality_Source_Discrepancy", "Quality_Late_Submission",
    }
    missing = sorted(required - set(data.columns))
    if missing:
        raise ValueError(f"Staged data missing detector inputs: {missing}")
    result = data.copy()
    reported = pd.to_numeric(result["Reported_Value"], errors="coerce")
    target = pd.to_numeric(result["Target_Value"], errors="coerce")
    ratio = reported / target.where(target.gt(0))
    # Generator outliers are injected at 2–3x target. The 1.5x threshold
    # intentionally leaves a margin above normal synthetic variation.
    result["Operational_Detected_Outlier"] = ratio.gt(1.5).fillna(False)
    result["Operational_Outlier_Ratio"] = ratio
    result["Operational_Any_Detected_Issue"] = (
        _as_bool(result["Quality_Missing_Reported_Value"])
        | _as_bool(result["Quality_Source_Discrepancy"])
        | _as_bool(result["Operational_Detected_Outlier"])
        | _as_bool(result["Quality_Late_Submission"])
    )
    return result


def _binary_metrics(truth: pd.Series, prediction: pd.Series) -> dict[str, Any]:
    y = _as_bool(truth)
    p = _as_bool(prediction)
    tp = int((y & p).sum())
    fp = int((~y & p).sum())
    fn = int((y & ~p).sum())
    tn = int((~y & ~p).sum())
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    specificity = tn / (tn + fp) if tn + fp else None
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision is not None and recall is not None and precision + recall
        else (0.0 if precision == 0 or recall == 0 else None)
    )
    total = tp + fp + fn + tn
    return {
        "true_positive": tp, "false_positive": fp,
        "false_negative": fn, "true_negative": tn,
        "precision": precision, "recall": recall, "f1": f1,
        "specificity": specificity,
        "false_positive_rate": fp / (fp + tn) if fp + tn else None,
        "accuracy": (tp + tn) / total if total else None,
        "support": tp + fn,
        "predicted_positive": tp + fp,
    }


def evaluate_detectors(data: pd.DataFrame) -> pd.DataFrame:
    """Return class-level confusion metrics using labels only in this function."""
    predictions = add_operational_predictions(data)
    rows = []
    for defect, (truth_col, prediction_col) in TRUTH_TO_PREDICTION.items():
        if truth_col not in predictions:
            raise ValueError(f"Evaluation requires synthetic label: {truth_col}")
        metrics = _binary_metrics(predictions[truth_col], predictions[prediction_col])
        rows.append({"defect": defect, **metrics})
    return pd.DataFrame(rows)


def build_operational_profiles(data: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Build monthly, facility and programme profiles without ground-truth fields."""
    predicted = add_operational_predictions(data)
    required = {"Month", "Facility_ID", "District", "Programme", "Indicator"}
    missing = sorted(required - set(predicted.columns))
    if missing:
        raise ValueError(f"Staged data missing profile dimensions: {missing}")

    issue_cols = [
        "Quality_Missing_Reported_Value", "Quality_Source_Discrepancy",
        "Operational_Detected_Outlier", "Quality_Late_Submission",
    ]
    for col in issue_cols:
        predicted[col] = _as_bool(predicted[col])
    predicted["Operational_Issue_Count"] = predicted[issue_cols].sum(axis=1)
    predicted["Operational_Any_Detected_Issue"] = predicted[issue_cols].any(axis=1)
    predicted["Month"] = pd.to_datetime(predicted["Month"], errors="coerce").dt.to_period("M").dt.to_timestamp()

    monthly = predicted.groupby("Month", dropna=False).agg(
        records=("Facility_ID", "size"),
        facilities=("Facility_ID", "nunique"),
        detected_issue_records=("Operational_Any_Detected_Issue", "sum"),
        issue_events=("Operational_Issue_Count", "sum"),
        missing_records=("Quality_Missing_Reported_Value", "sum"),
        source_discrepancy_records=("Quality_Source_Discrepancy", "sum"),
        outlier_records=("Operational_Detected_Outlier", "sum"),
        late_records=("Quality_Late_Submission", "sum"),
    ).reset_index()
    monthly["detected_issue_rate_pct"] = (
        100 * monthly["detected_issue_records"] / monthly["records"].replace(0, np.nan)
    ).round(2)

    facility = predicted.groupby(["Facility_ID", "Facility", "District"], dropna=False).agg(
        records=("Facility_ID", "size"),
        detected_issue_records=("Operational_Any_Detected_Issue", "sum"),
        issue_events=("Operational_Issue_Count", "sum"),
        missing_records=("Quality_Missing_Reported_Value", "sum"),
        source_discrepancy_records=("Quality_Source_Discrepancy", "sum"),
        outlier_records=("Operational_Detected_Outlier", "sum"),
        late_records=("Quality_Late_Submission", "sum"),
    ).reset_index()
    facility["detected_issue_rate_pct"] = (
        100 * facility["detected_issue_records"] / facility["records"].replace(0, np.nan)
    ).round(2)
    facility = facility.sort_values(
        ["detected_issue_rate_pct", "detected_issue_records", "Facility_ID"],
        ascending=[False, False, True],
    ).reset_index(drop=True)
    facility["follow_up_rank"] = np.arange(1, len(facility) + 1)

    programme = predicted.groupby(["Programme", "Indicator"], dropna=False).agg(
        records=("Facility_ID", "size"),
        detected_issue_records=("Operational_Any_Detected_Issue", "sum"),
        issue_events=("Operational_Issue_Count", "sum"),
        missing_records=("Quality_Missing_Reported_Value", "sum"),
        source_discrepancy_records=("Quality_Source_Discrepancy", "sum"),
        outlier_records=("Operational_Detected_Outlier", "sum"),
        late_records=("Quality_Late_Submission", "sum"),
    ).reset_index()
    programme["detected_issue_rate_pct"] = (
        100 * programme["detected_issue_records"] / programme["records"].replace(0, np.nan)
    ).round(2)
    programme = programme.sort_values(
        ["detected_issue_rate_pct", "Programme", "Indicator"],
        ascending=[False, True, True],
    ).reset_index(drop=True)

    # Explicitly project operational outputs: no Ground_Truth columns survive.
    for frame in (monthly, facility, programme):
        assert not any(column.startswith("Ground_Truth_") for column in frame.columns)
    return monthly, facility, programme



def build_district_profile(data: pd.DataFrame) -> pd.DataFrame:
    """Build district-level operational issue rates without ground-truth labels."""
    predicted = add_operational_predictions(data)
    required = {"District", "Facility_ID"}
    missing = sorted(required - set(predicted.columns))
    if missing:
        raise ValueError(f"Staged data missing district dimensions: {missing}")

    issue_columns = [
        "Quality_Missing_Reported_Value",
        "Quality_Source_Discrepancy",
        "Operational_Detected_Outlier",
        "Quality_Late_Submission",
    ]
    for column in issue_columns:
        predicted[column] = _as_bool(predicted[column])
    predicted["Operational_Issue_Count"] = predicted[issue_columns].sum(axis=1)
    predicted["Operational_Any_Detected_Issue"] = predicted[issue_columns].any(axis=1)

    district = predicted.groupby("District", dropna=False).agg(
        facilities=("Facility_ID", "nunique"),
        records=("Facility_ID", "size"),
        detected_issue_records=("Operational_Any_Detected_Issue", "sum"),
        issue_events=("Operational_Issue_Count", "sum"),
        missing_records=("Quality_Missing_Reported_Value", "sum"),
        source_discrepancy_records=("Quality_Source_Discrepancy", "sum"),
        outlier_records=("Operational_Detected_Outlier", "sum"),
        late_records=("Quality_Late_Submission", "sum"),
    ).reset_index()
    district["detected_issue_rate_pct"] = (
        100 * district["detected_issue_records"]
        / district["records"].replace(0, np.nan)
    ).round(2)
    district["issue_events_per_100_records"] = (
        100 * district["issue_events"]
        / district["records"].replace(0, np.nan)
    ).round(2)
    district = district.sort_values(
        ["detected_issue_rate_pct", "records", "District"],
        ascending=[False, False, True],
        na_position="last",
    ).reset_index(drop=True)
    district["follow_up_rank"] = np.arange(1, len(district) + 1)
    assert not any(column.startswith("Ground_Truth_") for column in district.columns)
    return district

def run_quality_analytics(staged_path: Path, output_dir: Path) -> dict[str, Any]:
    """Evaluate synthetic detector performance and write operational profiles."""
    data = pd.read_csv(staged_path)
    metrics = evaluate_detectors(data)
    monthly, facility, programme = build_operational_profiles(data)
    district = build_district_profile(data)
    output_dir.mkdir(parents=True, exist_ok=True)
    metrics.to_csv(output_dir / "detector_evaluation_metrics.csv", index=False)
    monthly.to_csv(output_dir / "monthly_quality_trends.csv", index=False)
    facility.to_csv(output_dir / "facility_quality_benchmark.csv", index=False)
    programme.to_csv(output_dir / "programme_indicator_quality_profile.csv", index=False)
    district.to_csv(output_dir / "district_quality_benchmark.csv", index=False)
    report = {
        "input_records": int(len(data)),
        "evaluation_scope": "Synthetic ground-truth labels; not real-world detector validation",
        "outlier_rule": "Reported_Value / Target_Value > 1.5",
        "metrics": metrics.replace({np.nan: None}).to_dict(orient="records"),
        "operational_profiles_exclude_ground_truth": True,
        "outputs": [
            "detector_evaluation_metrics.csv", "monthly_quality_trends.csv",
            "facility_quality_benchmark.csv", "programme_indicator_quality_profile.csv",
            "district_quality_benchmark.csv",
        ],
    }
    (output_dir / "quality_analytics_report.json").write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staged", type=Path, default=Path("data/warehouse/staged/facility_reporting_staged.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/warehouse/analytics"))
    args = parser.parse_args()
    report = run_quality_analytics(args.staged, args.output_dir)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
