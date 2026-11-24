"""Pure filtering helpers shared by the Streamlit dashboard and tests."""
from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime

import pandas as pd


ISSUE_FILTER_COLUMNS = {
    "Requires follow-up": "Requires_Follow_Up",
    "Missing values": "Issue_Missing_Value",
    "Late reports": "Issue_Late_Report",
    "Insufficient source data": "Issue_Insufficient_Sources",
    "Source discrepancies": "Issue_Source_Discrepancy",
    "Potential outliers": "Issue_Potential_Outlier",
    "Low completeness": "Issue_Low_Completeness",
}


def apply_dashboard_filters(
    records: pd.DataFrame,
    *,
    selected_facilities: Sequence[str],
    selected_programmes: Sequence[str],
    date_range: Sequence[date | datetime] | date | datetime | None,
    issue_filter: str,
) -> pd.DataFrame:
    """Apply the dashboard's facility, programme, period and issue filters."""
    required = {"Facility", "Programme", "Month"}
    missing = required.difference(records.columns)
    if missing:
        raise ValueError(f"Dashboard filter input is missing columns: {sorted(missing)}")

    filtered = records[
        records["Facility"].astype(str).isin([str(value) for value in selected_facilities])
        & records["Programme"].astype(str).isin([str(value) for value in selected_programmes])
    ].copy()

    if date_range is not None:
        if isinstance(date_range, (date, datetime)):
            bounds = [date_range]
        else:
            bounds = list(date_range)
        month_values = pd.to_datetime(filtered["Month"], errors="coerce")
        if len(bounds) == 2:
            start, end = pd.Timestamp(bounds[0]), pd.Timestamp(bounds[1])
            if start > end:
                raise ValueError("Dashboard reporting-period start must not exceed its end")
            filtered = filtered.loc[month_values.between(start, end)].copy()
        elif len(bounds) == 1:
            selected_day = pd.Timestamp(bounds[0]).date()
            filtered = filtered.loc[month_values.dt.date == selected_day].copy()
        elif len(bounds) != 0:
            raise ValueError("Dashboard reporting period must contain zero, one or two dates")

    if issue_filter in ISSUE_FILTER_COLUMNS:
        issue_column = ISSUE_FILTER_COLUMNS[issue_filter]
        if issue_column not in filtered.columns:
            raise ValueError(f"Dashboard filter input is missing issue column: {issue_column}")
        filtered = filtered.loc[filtered[issue_column].fillna(False).astype(bool)].copy()

    return filtered
