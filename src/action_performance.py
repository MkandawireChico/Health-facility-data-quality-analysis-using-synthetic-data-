"""Summarise integrated facility corrective-action performance."""
from __future__ import annotations

import pandas as pd

REQUIRED_ACTION_COLUMNS = {"Facility", "Month", "Status", "Due date"}


def build_action_performance(
    actions: pd.DataFrame, as_of=None, priority_register: pd.DataFrame | None = None
) -> dict[str, pd.DataFrame | dict]:
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
    data["Month"] = pd.to_datetime(
        data["Month"], format="%Y-%m-%d", errors="coerce"
    )
    if data["Month"].isna().any():
        raise ValueError("Action register contains invalid reporting months")
    data["District"] = data["Facility"].str.extract(r"\(([^()]*)\)\s*\[[^]]+\]\s*$", expand=False)
    if data["District"].isna().any() or data["District"].str.strip().eq("").any():
        raise ValueError("Action facility labels must end with (District) [Facility_ID]")
    data["District"] = data["District"].str.strip()
    if priority_register is not None:
        required_priority = {"Facility_ID", "District"}
        missing_priority = sorted(required_priority - set(priority_register.columns))
        if missing_priority:
            raise ValueError(
                f"Priority register is missing columns for district reconciliation: {missing_priority}"
            )
        priority = priority_register[["Facility_ID", "District"]].copy()
        priority["Facility_ID"] = priority["Facility_ID"].astype("string").str.strip()
        priority["District"] = priority["District"].astype("string").str.strip()
        if (
            priority["Facility_ID"].isna().any()
            or priority["Facility_ID"].eq("").any()
            or priority["Facility_ID"].duplicated().any()
            or priority["District"].isna().any()
            or priority["District"].eq("").any()
        ):
            raise ValueError("Priority register contains invalid facility-to-district mappings")
        data["Facility_ID"] = data["Facility"].str.extract(
            r"\[([^]]+)\]\s*$", expand=False
        ).astype("string").str.strip()
        if data["Facility_ID"].isna().any() or not data["Facility_ID"].isin(
            priority["Facility_ID"]
        ).all():
            raise ValueError("Action register references facility IDs absent from the priority register")
        expected_district = data["Facility_ID"].map(
            priority.set_index("Facility_ID")["District"]
        )
        if not data["District"].reset_index(drop=True).equals(
            expected_district.reset_index(drop=True)
        ):
            raise ValueError("Action facility district does not match the canonical priority register")
    due_text = data["Due date"].fillna("").astype(str).str.strip()
    due = pd.to_datetime(
        due_text.where(due_text.ne(""), pd.NA),
        format="%Y-%m-%d",
        errors="coerce",
    )
    if (due_text.ne("") & due.isna()).any():
        raise ValueError("Action register contains invalid due dates")
    reference = pd.Timestamp(as_of if as_of is not None else pd.Timestamp.now().date())
    if pd.isna(reference) or reference.tzinfo is not None:
        raise ValueError("Performance reference date must be a valid timezone-naive date")
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
    data["Month_Period"] = data["Month"].dt.to_period("M").astype(str)
    monthly = (
        data.groupby("Month_Period", as_index=False)
        .agg(
            tracked_actions=("Status", "size"),
            resolved_actions=("Status", lambda values: int(values.eq("Resolved").sum())),
            overdue_actions=("Overdue", "sum"),
        )
        .rename(columns={"Month_Period": "Month"})
    )
    monthly["resolution_rate_pct"] = (
        100 * monthly["resolved_actions"] / monthly["tracked_actions"]
    ).round(2)
    return {"kpis": kpis, "district": district, "monthly": monthly, "actions": data}
