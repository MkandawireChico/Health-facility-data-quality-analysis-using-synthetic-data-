"""Facility-level management drill-down for synthetic priority and action records."""
from __future__ import annotations

import re
from typing import Any

import pandas as pd

FACILITY_ID_PATTERN = re.compile(r"\[([^\[\]]+)\]\s*$")
PRIORITY_COLUMNS = {
    "Facility_ID", "Facility_Name", "District", "Priority_Band",
    "Integrated_Priority_Rank", "Integrated_Priority_Score",
    "Data_Quality_Priority_Score", "Resource_Gap_Priority_Score",
    "Operational_Priority_Score", "Supply_Cold_Chain_Priority_Score",
    "Review_Domains",
}
ACTION_COLUMNS = {
    "Record_ID", "Facility", "Month", "Status", "Assigned owner",
    "Root cause", "Corrective action / notes", "Due date",
}


def extract_facility_id(label: Any) -> str:
    """Extract the canonical ID from 'Name (District) [Facility_ID]' labels."""
    if label is None or pd.isna(label):
        raise ValueError("Action facility label is missing")
    match = FACILITY_ID_PATTERN.search(str(label).strip())
    if not match or not match.group(1).strip():
        raise ValueError("Action facility labels must end with [Facility_ID]")
    return match.group(1).strip()


def build_facility_management_view(
    priority_register: pd.DataFrame,
    action_register: pd.DataFrame,
    facility_id: str,
    audit_history: pd.DataFrame | None = None,
    as_of: Any = None,
) -> dict[str, Any]:
    """Return validated priority context, actions, status progress and audit history."""
    missing_priority = sorted(PRIORITY_COLUMNS - set(priority_register.columns))
    if missing_priority:
        raise ValueError(f"Priority register is missing columns: {missing_priority}")
    missing_actions = sorted(ACTION_COLUMNS - set(action_register.columns))
    if missing_actions:
        raise ValueError(f"Action register is missing columns: {missing_actions}")
    selected_id = str(facility_id).strip()
    if not selected_id:
        raise ValueError("A facility identifier must be selected")
    priorities = priority_register.copy()
    priorities["Facility_ID"] = priorities["Facility_ID"].astype("string").str.strip()
    if priorities["Facility_ID"].isna().any() or priorities["Facility_ID"].eq("").any():
        raise ValueError("Priority register contains missing facility identifiers")
    if priorities["Facility_ID"].duplicated().any():
        raise ValueError("Priority register contains duplicate facility identifiers")
    score_columns = [
        "Integrated_Priority_Score", "Data_Quality_Priority_Score",
        "Resource_Gap_Priority_Score", "Operational_Priority_Score",
        "Supply_Cold_Chain_Priority_Score",
    ]
    for column in score_columns:
        values = pd.to_numeric(priorities[column], errors="coerce")
        if values.isna().any() or not values.between(0, 100).all():
            raise ValueError(f"Priority register contains invalid {column} values")
    selected_priority = priorities.loc[priorities["Facility_ID"].eq(selected_id)]
    if selected_priority.empty:
        raise ValueError(f"Unknown facility identifier: {selected_id}")
    if len(selected_priority) != 1:
        raise ValueError(f"Facility identifier is not unique: {selected_id}")
    priority = selected_priority.iloc[0].to_dict()

    actions = action_register.copy()
    if actions.empty:
        actions["Facility_ID"] = pd.Series(dtype="string")
    else:
        actions["Facility_ID"] = actions["Facility"].map(extract_facility_id)
        if not actions["Facility_ID"].isin(priorities["Facility_ID"]).all():
            raise ValueError("Action register references facility identifiers absent from the priority register")
        if actions["Record_ID"].isna().any() or actions["Record_ID"].astype(str).str.strip().eq("").any():
            raise ValueError("Action register contains missing record identifiers")
        if actions["Record_ID"].duplicated().any():
            raise ValueError("Action register contains duplicate record identifiers")
        allowed = {"Open", "In progress", "Resolved", "Escalated"}
        if not actions["Status"].isin(allowed).all():
            raise ValueError("Action register contains unsupported statuses")
        actions["Month"] = pd.to_datetime(actions["Month"], errors="coerce")
        if actions["Month"].isna().any():
            raise ValueError("Action register contains invalid reporting months")
    selected_actions = actions.loc[actions["Facility_ID"].eq(selected_id)].copy()
    selected_actions = selected_actions.sort_values(
        ["Month", "Due date", "Record_ID"], na_position="last"
    ).reset_index(drop=True)
    due = pd.to_datetime(selected_actions["Due date"], errors="coerce")
    reference = pd.Timestamp(as_of if as_of is not None else pd.Timestamp.now().date())
    if reference.tzinfo is not None:
        raise ValueError("Management reference date must be timezone-naive")
    selected_actions["Overdue"] = (
        selected_actions["Status"].ne("Resolved")
        & due.notna()
        & due.lt(reference.normalize())
    )
    status_counts = {
        status: int(selected_actions["Status"].eq(status).sum())
        for status in ["Open", "In progress", "Resolved", "Escalated"]
    }
    total = len(selected_actions)
    resolved = status_counts["Resolved"]
    progress = {
        "tracked": total,
        "resolved": resolved,
        "resolution_rate_pct": round(100 * resolved / total, 2) if total else 0.0,
        "overdue": int(selected_actions["Overdue"].sum()),
        **{status.lower().replace(" ", "_"): count for status, count in status_counts.items()},
    }
    if selected_actions.empty:
        monthly = pd.DataFrame(columns=[
            "Month", "tracked_actions", "resolved_actions", "overdue_actions",
            "resolution_rate_pct",
        ])
    else:
        selected_actions["Month_Period"] = selected_actions["Month"].dt.to_period("M").astype(str)
        monthly = selected_actions.groupby("Month_Period", as_index=False).agg(
            tracked_actions=("Record_ID", "size"),
            resolved_actions=("Status", lambda values: int(values.eq("Resolved").sum())),
            overdue_actions=("Overdue", "sum"),
        ).rename(columns={"Month_Period": "Month"})
        monthly["resolution_rate_pct"] = (
            100 * monthly["resolved_actions"] / monthly["tracked_actions"]
        ).round(2)
    history = (
        audit_history.copy()
        if audit_history is not None
        else pd.DataFrame(columns=["changed_at", "field_name", "old_value", "new_value"])
    )
    return {
        "facility": priority,
        "actions": selected_actions,
        "progress": progress,
        "monthly": monthly,
        "audit_history": history,
    }
