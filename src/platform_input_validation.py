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
    errors = []
    if missing:
        errors.append("Missing required columns: " + ", ".join(missing))
        return errors

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

    population = pd.to_numeric(data["Catchment_Population"], errors="coerce")
    finite_population = np.isfinite(population.to_numpy(dtype=float))
    if population.isna().any() or not finite_population.all() or population.lt(0).any():
        errors.append(
            "Catchment_Population must contain finite, non-negative numeric values."
        )

    return errors
