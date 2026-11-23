"""Robust peer-group anomaly detection and monthly process monitoring.

This module is deliberately separate from deterministic quality rules. It
identifies statistically unusual reported values within comparable
programme/indicator/district cohorts and monitors monthly issue rates.
Synthetic ground-truth columns are never used.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REQUIRED = {
    "Month", "District", "Programme", "Indicator", "Reported_Value",
    "Facility_ID", "Quality_Missing_Reported_Value",
    "Quality_Source_Discrepancy", "Quality_Late_Submission",
}


def _as_bool(series: pd.Series) -> pd.Series:
    """Parse boolean flags safely, including values loaded from CSV text."""
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False)
    if pd.api.types.is_numeric_dtype(series):
        return series.fillna(0).ne(0)
    return series.astype("string").str.strip().str.lower().isin(
        {"true", "1", "yes", "y"}
    )


def detect_peer_anomalies(data: pd.DataFrame, min_group_size: int = 8,
                          robust_z_threshold: float = 3.5) -> pd.DataFrame:
    """Flag extreme values using MAD, with IQR fallback for zero-MAD groups."""
    missing = REQUIRED - set(data.columns)
    if missing:
        raise ValueError(f"Staged data missing columns: {sorted(missing)}")
    if (isinstance(min_group_size, bool)
            or not isinstance(min_group_size, (int, np.integer))
            or min_group_size < 4
            or isinstance(robust_z_threshold, bool)
            or not isinstance(robust_z_threshold, (int, float, np.integer, np.floating))
            or not np.isfinite(robust_z_threshold)
            or robust_z_threshold <= 0):
        raise ValueError("min_group_size must be an integer >= 4 and threshold must be finite and positive")
    out = data.copy()
    out["Statistical_Anomaly"] = False
    out["Statistical_Anomaly_Score"] = np.nan
    out["Statistical_Method"] = "Insufficient peer observations"
    out["Peer_Group_Size"] = 0
    values = pd.to_numeric(out["Reported_Value"], errors="coerce")
    # Compare facilities within the same reporting month and like-for-like
    # district/programme/indicator cohort. This avoids mixing seasonal or
    # secular changes across the full five-year reporting window.
    out["Month"] = pd.to_datetime(out["Month"], errors="coerce").dt.to_period("M").dt.to_timestamp()
    keys = ["Month", "District", "Programme", "Indicator"]
    for _, indexes in out.groupby(keys, dropna=False, sort=False).groups.items():
        valid_idx = [i for i in indexes if pd.notna(values.loc[i]) and np.isfinite(values.loc[i])]
        sample = values.loc[valid_idx]
        n = len(sample)
        out.loc[indexes, "Peer_Group_Size"] = n
        if n < min_group_size:
            continue
        median = float(sample.median())
        mad = float((sample - median).abs().median())
        if mad > 0:
            scores = 0.67448975 * (sample - median) / mad
            method = "MAD robust z-score"
            flags = scores.abs() > robust_z_threshold
        else:
            q1, q3 = sample.quantile([0.25, 0.75])
            iqr = float(q3 - q1)
            if iqr <= 0:
                # Degenerate IQR: use a scale-aware tolerance around the median.
                scale = max(abs(median) * 0.05, 1.0)
                lower, upper = median - scale, median + scale
                scores = (sample - median) / scale
                flags = (sample < lower) | (sample > upper)
            else:
                lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
                scores = (sample - median) / iqr
                flags = (sample < lower) | (sample > upper)
            method = "IQR fallback"
        out.loc[valid_idx, "Statistical_Anomaly_Score"] = scores.astype(float)
        out.loc[valid_idx, "Statistical_Anomaly"] = flags.astype(bool)
        out.loc[valid_idx, "Statistical_Method"] = method
    return out


def build_monthly_control_chart(data: pd.DataFrame, min_baseline_months: int = 6) -> pd.DataFrame:
    """Create descriptive 3-sigma limits for monthly operational issue rates.

    The operational definition aligns with the quality analytics profile:
    missing values, source discrepancies, outliers (>1.5x target) and late
    submissions. Limits use the full observed period, so this is retrospective
    monitoring rather than a prospective alerting/control-chart service.
    """
    required = {
        "Month", "Reported_Value", "Target_Value",
        "Quality_Missing_Reported_Value", "Quality_Source_Discrepancy",
        "Quality_Late_Submission",
    }
    missing = required - set(data.columns)
    if missing:
        raise ValueError(f"Staged data missing control-chart inputs: {sorted(missing)}")
    if min_baseline_months < 2:
        raise ValueError("min_baseline_months must be at least 2")
    work = data.copy()
    work["Month"] = pd.to_datetime(work["Month"], errors="coerce").dt.to_period("M").dt.to_timestamp()
    flag_cols = [
        "Quality_Missing_Reported_Value",
        "Quality_Source_Discrepancy",
        "Quality_Late_Submission",
    ]
    for col in flag_cols:
        work[col] = _as_bool(work[col])
    reported = pd.to_numeric(work["Reported_Value"], errors="coerce")
    target = pd.to_numeric(work["Target_Value"], errors="coerce")
    work["Operational_Detected_Outlier"] = (
        (reported / target.where(target.gt(0))).gt(1.5).fillna(False)
    )
    issue_cols = flag_cols + ["Operational_Detected_Outlier"]
    work["Any_Detected_Issue"] = work[issue_cols].any(axis=1)
    monthly = (
        work.dropna(subset=["Month"])
        .groupby("Month")
        .agg(
            Records=("Any_Detected_Issue", "size"),
            Issue_Records=("Any_Detected_Issue", "sum"),
            Missing_Records=("Quality_Missing_Reported_Value", "sum"),
            Source_Discrepancy_Records=("Quality_Source_Discrepancy", "sum"),
            Outlier_Records=("Operational_Detected_Outlier", "sum"),
            Late_Records=("Quality_Late_Submission", "sum"),
        )
        .reset_index()
    )
    monthly["Issue_Rate"] = monthly["Issue_Records"] / monthly["Records"].replace(0, np.nan)
    if len(monthly) >= min_baseline_months:
        # Use a pooled proportion and month-specific binomial standard errors.
        # This avoids giving a low-volume month the same weight as a high-volume month
        # and widens descriptive limits when the monthly denominator is small.
        centre = float(monthly["Issue_Records"].sum() / monthly["Records"].sum())
        standard_error = np.sqrt(
            centre * (1 - centre) / monthly["Records"].clip(lower=1)
        )
        monthly["Centre_Line"] = centre
        monthly["Lower_Control_Limit"] = np.maximum(0.0, centre - 3 * standard_error)
        monthly["Upper_Control_Limit"] = np.minimum(1.0, centre + 3 * standard_error)
        monthly["Outside_Descriptive_Limits"] = (
            (monthly["Issue_Rate"] < monthly["Lower_Control_Limit"])
            | (monthly["Issue_Rate"] > monthly["Upper_Control_Limit"])
        )
        monthly["Control_Status"] = "Within descriptive limits"
        monthly.loc[monthly["Outside_Descriptive_Limits"], "Control_Status"] = "Review signal"
    else:
        for col in ["Centre_Line", "Lower_Control_Limit", "Upper_Control_Limit"]:
            monthly[col] = np.nan
        monthly["Outside_Descriptive_Limits"] = False
        monthly["Control_Status"] = "Insufficient baseline"
    return monthly


def run_statistical_monitoring(staged_path: Path, output_dir: Path) -> dict[str, Any]:
    data = pd.read_csv(staged_path)
    anomalies = detect_peer_anomalies(data)
    control = build_monthly_control_chart(data)
    output_dir.mkdir(parents=True, exist_ok=True)
    anomalies.to_csv(output_dir / "statistical_peer_anomalies.csv", index=False)
    control.to_csv(output_dir / "monthly_issue_control_chart.csv", index=False)
    summary = {
        "synthetic_data": True,
        "staged_records": int(len(data)),
        "peer_anomaly_records": int(anomalies["Statistical_Anomaly"].sum()),
        "peer_anomaly_method_counts": anomalies.loc[
            anomalies["Statistical_Anomaly"], "Statistical_Method"
        ].value_counts().to_dict(),
        "months_monitored": int(len(control)),
        "months_outside_descriptive_limits": int(control["Outside_Descriptive_Limits"].sum()),
        "control_chart_issue_types": [
            "missing reported values", "source discrepancies",
            "reported values above 1.5x target", "late submissions",
        ],
        "control_limits_are_retrospective": True,
        "ground_truth_fields_used": False,
        "caution": "Statistical signals are review prompts, not proof of reporting error or clinical risk."
    }
    (output_dir / "statistical_monitoring_report.json").write_text(json.dumps(summary, indent=2))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staged", type=Path, default=Path("data/warehouse/staged/facility_reporting_staged.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/warehouse/analytics"))
    args = parser.parse_args()
    print(json.dumps(run_statistical_monitoring(args.staged, args.output_dir), indent=2))


if __name__ == "__main__":
    main()
