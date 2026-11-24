"""Target-attainment intelligence at comparable programme-indicator grain.

All values are synthetic. Attainment is calculated only where reported and target
values are numeric, reported values are non-negative, and targets are positive.
No catchment-population coverage is inferred from service counts.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import numpy as np
import pandas as pd

REQUIRED = {"Facility_ID", "Facility", "District", "Month", "Programme", "Indicator", "Reported_Value", "Target_Value"}

def _prepare(data: pd.DataFrame) -> pd.DataFrame:
    missing = sorted(REQUIRED - set(data.columns))
    if missing:
        raise ValueError(f"Target attainment input missing required columns: {missing}")
    frame = data.copy()
    frame["Month"] = pd.to_datetime(frame["Month"], errors="coerce").dt.to_period("M").dt.to_timestamp()
    frame["Reported_Value"] = pd.to_numeric(frame["Reported_Value"], errors="coerce")
    frame["Target_Value"] = pd.to_numeric(frame["Target_Value"], errors="coerce")
    frame["Valid_Attainment_Record"] = (
        frame["Month"].notna() & frame["Reported_Value"].notna()
        & frame["Reported_Value"].ge(0) & frame["Target_Value"].notna()
        & frame["Target_Value"].gt(0)
    )
    frame["Attainment_Contribution"] = frame["Reported_Value"].where(frame["Valid_Attainment_Record"], 0)
    frame["Target_Contribution"] = frame["Target_Value"].where(frame["Valid_Attainment_Record"], 0)
    return frame

def _summarise(frame: pd.DataFrame, dimensions: list[str]) -> pd.DataFrame:
    result = frame.groupby(dimensions, dropna=False).agg(
        reporting_records=("Facility_ID", "size"),
        valid_attainment_records=("Valid_Attainment_Record", "sum"),
        reported_total=("Attainment_Contribution", "sum"),
        target_total=("Target_Contribution", "sum"),
        facilities=("Facility_ID", "nunique"),
    ).reset_index()
    result["attainment_pct"] = (
        100 * result["reported_total"] / result["target_total"].where(result["target_total"].gt(0))
    ).round(2)
    result["Indicator_Key"] = result["Programme"].astype("string") + "|" + result["Indicator"].astype("string")
    result["performance_band"] = np.select(
        [result["attainment_pct"].lt(80), result["attainment_pct"].lt(100)],
        ["Below 80% of target", "80–99.9% of target"],
        default="At or above target",
    )
    result.loc[result["attainment_pct"].isna(), "performance_band"] = "Insufficient valid target data"
    result["valid_data_pct"] = (
        100 * result["valid_attainment_records"] / result["reporting_records"].replace(0, np.nan)
    ).round(2)
    return result

def build_target_attainment_profiles(data: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Build comparable indicator-grain performance profiles and monthly trends."""
    frame = _prepare(data)
    outputs = {
        "facility_indicator": _summarise(frame, ["Facility_ID", "Facility", "District", "Programme", "Indicator"]),
        "district_indicator": _summarise(frame, ["District", "Programme", "Indicator"]),
        "programme_indicator": _summarise(frame, ["Programme", "Indicator"]),
        "monthly_indicator": _summarise(frame.dropna(subset=["Month"]), ["Month", "Programme", "Indicator"]),
    }
    for output in outputs.values():
        if any(column.startswith("Ground_Truth_") for column in output.columns):
            raise AssertionError("Ground-truth fields must not enter operational performance profiles")
    return outputs

def run_target_attainment(staged_path: Path, output_dir: Path) -> dict[str, Any]:
    data = pd.read_csv(staged_path)
    profiles = build_target_attainment_profiles(data)
    output_dir.mkdir(parents=True, exist_ok=True)
    filenames = {
        "facility_indicator": "facility_indicator_target_attainment.csv",
        "district_indicator": "district_indicator_target_attainment.csv",
        "programme_indicator": "programme_indicator_target_attainment.csv",
        "monthly_indicator": "monthly_indicator_target_attainment.csv",
    }
    for key, filename in filenames.items():
        profiles[key].to_csv(output_dir / filename, index=False)
    report = {
        "synthetic_data": True,
        "input_records": int(len(data)),
        "method": "Pooled reported-value total divided by pooled target total at matching programme-indicator grain.",
        "valid_record_rule": "Valid month, numeric non-negative reported value, and positive numeric target.",
        "performance_bands": {"below_target_review": "<80%", "near_target": "80–99.9%", "at_or_above_target": ">=100%"},
        "not_coverage": "These are reported-to-target attainment measures, not population coverage or unique people served.",
        "outputs": list(filenames.values()),
    }
    (output_dir / "target_attainment_report.json").write_text(json.dumps(report, indent=2))
    return report

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staged", type=Path, default=Path("data/warehouse/staged/facility_reporting_staged.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/warehouse/analytics"))
    args = parser.parse_args()
    print(json.dumps(run_target_attainment(args.staged, args.output_dir), indent=2))