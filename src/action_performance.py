"""Summarise integrated facility corrective-action performance."""
from __future__ import annotations

import pandas as pd

REQUIRED_ACTION_COLUMNS = {"Facility", "Month", "Status", "Due date"}


def build_action_performance(actions: pd.DataFrame, as_of=None) -> dict[str, pd.DataFrame | dict]:
    """Return validated portfolio KPIs and district/month performance tables."""
    missing = sorted(REQUIRED_ACTION_COLUMNS - set(actions.columns))
    if missing:
        raise ValueError(f"Action register is missing columns: {missing}")
    data = actions.copy()
    if data.empty:
        empty = pd.DataFrame()
        return {
            "kpis": {"tracked": 0, "resolved": 0, "resolution_rate_pct": 0.0,
                     "overdue": 0, "open": 0, "in_progress": 0, "escalated": 0},
            "district": empty, "monthly": empty, "actions": data,
        }
    for column in ["Facility", "Month", "Status"]:
        if data[column].isna().any():
            raise ValueError(f"Action register contains missing {column}")
        data[column] = data[column].astype(str).str.strip()
        if data[column].eq("").any():
            raise ValueError(f"Action register contains blank {column}")
    allowed = {"Open", "In progress", "Resolved", "Escalated"}
    if not data["Status"].isin(allowed).all():
        raise ValueError("Action register contains unsupported statuses")
    data["Month"] = pd.to_datetime(data["Month"], errors="coerce")
    if data["Month"].isna().any():
        raise ValueError("Action register contains invalid reporting months")
    data["District"] = data["Facility"].str.extract(r"\(([^()]*)\)\s*\[[^]]+\]\s*$", expand=False)
    if data["District"].isna().any() or data["District"].str.strip().eq("").any():
        raise ValueError("Action facility labels must end with (District) [Facility_ID]")
    data["District"] = data["District"].str.strip()
    due = pd.to_datetime(data["Due date"], errors="coerce")
    reference = pd.Timestamp(as_of if as_of is not None else pd.Timestamp.now().date())
    if reference.tzinfo is not None:
        raise ValueError("Performance reference date must be timezone-naive")
    unresolved = data["Status"].ne("Resolved")
    data["Overdue"] = unresolved & due.notna() & due.lt(reference.normalize())
    data["Due date parsed"] = due
    total = len(data)
    resolved = int(data["Status"].eq("Resolved").sum())
    kpis = {
        "tracked": total,
        "resolved": resolved,
        "resolution_rate_pct": round(100 * resolved / total, 2),
        "overdue": int(data["Overdue"].sum()),
        "open": int(data["Status"].eq("Open").sum()),
        "in_progress": int(data["Status"].eq("In progress").sum()),
        "escalated": int(data["Status"].eq("Escalated").sum()),
    }
    district = (
        data.groupby("District", as_index=False)
        .agg(
            tracked_actions=("Status", "size"),
            resolved_actions=("Status", lambda values: int(values.eq("Resolved").sum())),
            overdue_actions=("Overdue", "sum"),
            open_actions=("Status", lambda values: int(values.eq("Open").sum())),
            in_progress_actions=("Status", lambda values: int(values.eq("In progress").sum())),
            escalated_actions=("Status", lambda values: int(values.eq("Escalated").sum())),
        )
    )
    district["resolution_rate_pct"] = (
        100 * district["resolved_actions"] / district["tracked_actions"]
    ).round(2)
    monthly = (
        data.groupby(data["Month"].dt.to_period("M"), as_index=False)
        .agg(
            tracked_actions=("Status", "size"),
            resolved_actions=("Status", lambda values: int(values.eq("Resolved").sum())),
            overdue_actions=("Overdue", "sum"),
        )
    )
    monthly["Month"] = monthly["Month"].astype(str)
    monthly["resolution_rate_pct"] = (
        100 * monthly["resolved_actions"] / monthly["tracked_actions"]
    ).round(2)
    return {"kpis": kpis, "district": district, "monthly": monthly, "actions": data}
