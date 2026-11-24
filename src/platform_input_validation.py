"""Validation for expanded Streamlit platform-analysis uploads."""
from __future__ import annotations

import numpy as np
import pandas as pd

PLATFORM_REQUIRED_COLUMNS = {
    "Facility_ID", "Facility", "District", "Facility_Type", "Urban_Rural",
    "Catchment_Population", "Month", "Programme", "Indicator",
    "Reported_Value", "Target_Value", "Quality_Missing_Reported_Value",
    "Quality_Source_Discrepancy", "Quality_Late_Submission",
}


def validate_platform_extract(data: pd.DataFrame) -> list[str]:
    """Return actionable input errors before running the expanded analytics."""
    if data.empty:
        return ["The staged extract contains no reporting records."]

    missing = sorted(PLATFORM_REQUIRED_COLUMNS - set(data.columns))
    if missing:
        return ["Missing required columns: " + ", ".join(missing)]

    errors: list[str] = []
    valid_months = pd.to_datetime(data["Month"], errors="coerce")
    if valid_months.isna().any():
        errors.append("Month must contain valid reporting periods for every record.")

    facility_dimensions = [
        "Facility_ID", "Facility", "District", "Facility_Type", "Urban_Rural",
    ]
    blank_dimensions = [
        column for column in facility_dimensions
        if data[column].isna().any()
        or data[column].astype("string").str.strip().eq("").any()
    ]
    if blank_dimensions:
        errors.append(
            "Facility metadata contains blank values in: "
            + ", ".join(blank_dimensions)
        )

    inconsistent = []
    if not blank_dimensions:
        for column in facility_dimensions[1:]:
            counts = data.groupby("Facility_ID", dropna=False)[column].nunique(dropna=False)
            if counts.gt(1).any():
                inconsistent.append(column)
    if inconsistent:
        errors.append(
            "Facility_ID values map to conflicting metadata in: "
            + ", ".join(inconsistent)
        )

    population = pd.to_numeric(data["Catchment_Population"], errors="coerce")
    finite_population = np.isfinite(population.to_numpy(dtype=float))
    if population.isna().any() or not finite_population.all() or population.lt(0).any():
        errors.append(
            "Catchment_Population must contain finite, non-negative numeric values."
        )

    for column in ["Reported_Value", "Target_Value"]:
        values = pd.to_numeric(data[column], errors="coerce")
        if values.isna().any() or not np.isfinite(values.to_numpy(dtype=float)).all():
            errors.append(f"{column} must contain finite numeric values.")

    for column in [
        "Quality_Missing_Reported_Value",
        "Quality_Source_Discrepancy",
        "Quality_Late_Submission",
    ]:
        if data[column].isna().any():
            errors.append(f"{column} must not contain missing flags.")

    return errors
