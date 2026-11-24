"""Cross-facility executive briefing and management attention queue."""
from __future__ import annotations

from typing import Any

import pandas as pd

from facility_management_view import extract_facility_id

REQUIRED_PRIORITY = {
    "Facility_ID", "Facility_Name", "District", "Priority_Band",
    "Integrated_Priority_Rank", "Integrated_Priority_Score",
    "Data_Quality_Priority_Score", "Resource_Gap_Priority_Score",
    "Operational_Priority_Score", "Supply_Cold_Chain_Priority_Score",
    "Review_Domains",
}
REQUIRED_ACTIONS = {
    "Record_ID", "Facility", "Month", "Status", "Assigned owner", "Due date",
}
COMPONENTS = {
    "Data quality": "Data_Quality_Priority_Score",
    "Resource capacity": "Resource_Gap_Priority_Score",
    "Operational resilience": "Operational_Priority_Score",
    "Supply and cold chain": "Supply_Cold_Chain_Priority_Score",
}
ALLOWED_BANDS = {"High review", "Focused review", "Routine review"}
ALLOWED_STATUSES = {"Open", "In progress", "Resolved", "Escalated"}


def build_executive_management_briefing(
    priority_register: pd.DataFrame,
    action_register: pd.DataFrame,
    as_of: Any = None,
    top_n: int = 12,
) -> dict[str, Any]:
    """Summarise synthetic cross-facility priorities and saved action accountability."""
    missing_priority = sorted(REQUIRED_PRIORITY - set(priority_register.columns))
    if missing_priority:
        raise ValueError(f"Priority register is missing columns: {missing_priority}")
    missing_actions = sorted(REQUIRED_ACTIONS - set(action_register.columns))
    if missing_actions:
        raise ValueError(f"Action register is missing columns: {missing_actions}")
    if isinstance(top_n, bool) or not isinstance(top_n, int) or top_n < 1:
        raise ValueError("top_n must be a positive integer")

    priority = priority_register.copy()
    priority["Facility_ID"] = priority["Facility_ID"].astype("string").str.strip()
    for column in ["Facility_ID", "Facility_Name", "District", "Priority_Band"]:
        if priority[column].isna().any() or priority[column].astype(str).str.strip().eq("").any():
            raise ValueError(f"Priority register contains missing {column}")
    if priority["Facility_ID"].duplicated().any():
        raise ValueError("Priority register contains duplicate facility identifiers")
    if not priority["Priority_Band"].isin(ALLOWED_BANDS).all():
        raise ValueError("Priority register contains unsupported priority bands")
    for column in ["Integrated_Priority_Score", *COMPONENTS.values()]:
        values = pd.to_numeric(priority[column], errors="coerce")
        if values.isna().any() or not values.between(0, 100).all():
            raise ValueError(f"Priority register contains invalid {column} values")
        priority[column] = values
    priority["Integrated_Priority_Rank"] = pd.to_numeric(
        priority["Integrated_Priority_Rank"], errors="coerce"
    )
    if (
        priority["Integrated_Priority_Rank"].isna().any()
        or priority["Integrated_Priority_Rank"].lt(1).any()
        or priority["Integrated_Priority_Rank"].duplicated().any()
    ):
        raise ValueError("Priority register contains invalid or duplicate ranks")
    expected_score = priority[list(COMPONENTS.values())].mean(axis=1).round(2)
    score_difference = (
        expected_score - priority["Integrated_Priority_Score"].round(2)
    ).abs()
    if score_difference.gt(0.01).any():
        raise ValueError("Integrated priority scores do not reconcile with component scores")

    expected_band = pd.Series(
        pd.Series("Routine review", index=priority.index)
        .mask(priority["Integrated_Priority_Score"].ge(25), "Focused review")
        .mask(priority["Integrated_Priority_Score"].ge(50), "High review"),
        index=priority.index,
    )
    if not priority["Priority_Band"].reset_index(drop=True).equals(
        expected_band.reset_index(drop=True)
    ):
        raise ValueError("Priority bands do not reconcile with the documented score thresholds")
    ranks = priority["Integrated_Priority_Rank"]
    if (
        ranks.isna().any()
        or ranks.lt(1).any()
        or not (ranks % 1).eq(0).all()
        or set(ranks.astype(int)) != set(range(1, len(priority) + 1))
    ):
        raise ValueError("Priority ranks must be contiguous positive integers")
    expected_order = priority.sort_values(
        ["Integrated_Priority_Score", "Facility_ID"],
        ascending=[False, True],
    )["Facility_ID"].tolist()
    actual_order = priority.sort_values("Integrated_Priority_Rank")["Facility_ID"].tolist()
    if actual_order != expected_order:
        raise ValueError("Priority ranks do not follow descending score and facility-ID tie-break order")

    actions = action_register.copy()
    reference = pd.Timestamp(as_of if as_of is not None else pd.Timestamp.now().date())
    if pd.isna(reference) or reference.tzinfo is not None:
        raise ValueError("Management reference date must be a valid timezone-naive date")
    reference = reference.normalize()
    if actions.empty:
        actions["Facility_ID"] = pd.Series(dtype="string")
        actions["Overdue"] = pd.Series(dtype=bool)
    else:
        actions["Facility_ID"] = actions["Facility"].map(extract_facility_id)
        if not actions["Facility_ID"].isin(priority["Facility_ID"]).all():
            raise ValueError("Action register references facility identifiers absent from the priority register")
        action_district = actions["Facility"].astype(str).str.extract(
            r"\(([^()]*)\)\s*\[[^]]+\]\s*$", expand=False
        ).str.strip()
        canonical_district = actions["Facility_ID"].map(
            priority.set_index("Facility_ID")["District"]
        ).astype(str).str.strip()
        if action_district.isna().any() or action_district.eq("").any():
            raise ValueError("Action facility labels must include a district before [Facility_ID]")
        if not action_district.reset_index(drop=True).equals(
            canonical_district.reset_index(drop=True)
        ):
            raise ValueError("Action facility district does not match the canonical priority register")
        if actions["Record_ID"].isna().any() or actions["Record_ID"].astype(str).str.strip().eq("").any():
            raise ValueError("Action register contains missing record identifiers")
        if actions["Record_ID"].duplicated().any():
            raise ValueError("Action register contains duplicate record identifiers")
        if not actions["Status"].isin(ALLOWED_STATUSES).all():
            raise ValueError("Action register contains unsupported statuses")
        due_text = actions["Due date"].fillna("").astype(str).str.strip()
        due = pd.to_datetime(
            due_text.where(due_text.ne(""), pd.NA),
            format="%Y-%m-%d",
            errors="coerce",
        )
        if (due_text.ne("") & due.isna()).any():
            raise ValueError("Action register contains invalid due dates")
        action_month = pd.to_datetime(
            actions["Month"], format="%Y-%m-%d", errors="coerce"
        )
        if action_month.isna().any():
            raise ValueError("Action register contains invalid reporting months")
        actions["Overdue"] = actions["Status"].ne("Resolved") & due.notna() & due.lt(reference)

    status_counts = actions.groupby("Facility_ID")["Status"].value_counts().unstack(fill_value=0)
    overdue_counts = actions.groupby("Facility_ID")["Overdue"].sum()
    tracked_counts = actions.groupby("Facility_ID").size()
    queue = priority.copy()
    queue["actions_tracked"] = queue["Facility_ID"].map(tracked_counts).fillna(0).astype(int)
    queue["overdue_actions"] = queue["Facility_ID"].map(overdue_counts).fillna(0).astype(int)
    for status in ["Open", "In progress", "Resolved", "Escalated"]:
        queue[status.lower().replace(" ", "_") + "_actions"] = (
            queue["Facility_ID"].map(status_counts[status]).fillna(0).astype(int)
            if status in status_counts.columns else 0
        )
    queue["action_resolution_rate_pct"] = (
        100
        * queue["resolved_actions"].div(
            queue["actions_tracked"].where(queue["actions_tracked"].ne(0))
        )
    ).fillna(0).round(2)

    def recommendation(row: pd.Series) -> str:
        domains = [
            label for label, column in COMPONENTS.items()
            if float(row[column]) > 0
        ]
        if row["Priority_Band"] == "High review":
            text = "Convene a facility review and validate the highest-scoring synthetic domains"
        elif row["Priority_Band"] == "Focused review":
            text = "Review flagged domains and confirm whether an action is warranted"
        else:
            text = "Maintain routine monitoring and check for new exceptions"
        if domains:
            text += ": " + ", ".join(domains)
        if row["overdue_actions"]:
            text += f"; follow up {int(row['overdue_actions'])} overdue unresolved action(s)"
        elif row["actions_tracked"] == 0:
            text += "; assign an accountable owner if follow-up is confirmed"
        elif row["resolved_actions"] < row["actions_tracked"]:
            text += "; review remaining open or in-progress actions"
        return text

    queue["Management_Follow_Up"] = queue.apply(recommendation, axis=1)
    queue = queue.sort_values(
        ["Integrated_Priority_Score", "overdue_actions", "Integrated_Priority_Rank"],
        ascending=[False, False, True],
    ).reset_index(drop=True)

    district = queue.groupby("District", as_index=False).agg(
        facilities=("Facility_ID", "nunique"),
        mean_priority_score=("Integrated_Priority_Score", "mean"),
        high_review=("Priority_Band", lambda x: int(x.eq("High review").sum())),
        focused_review=("Priority_Band", lambda x: int(x.eq("Focused review").sum())),
        routine_review=("Priority_Band", lambda x: int(x.eq("Routine review").sum())),
        tracked_actions=("actions_tracked", "sum"),
        overdue_actions=("overdue_actions", "sum"),
        open_actions=("open_actions", "sum"),
        in_progress_actions=("in_progress_actions", "sum"),
        resolved_actions=("resolved_actions", "sum"),
        escalated_actions=("escalated_actions", "sum"),
    )
    district["resolution_rate_pct"] = (
        100
        * district["resolved_actions"].div(
            district["tracked_actions"].where(district["tracked_actions"].ne(0))
        )
    ).fillna(0).round(2)
    district["mean_priority_score"] = district["mean_priority_score"].round(2)
    district = district.sort_values(
        ["mean_priority_score", "high_review", "District"],
        ascending=[False, False, True],
    ).reset_index(drop=True)

    domain_rows = []
    for label, column in COMPONENTS.items():
        domain_rows.append({
            "Domain": label,
            "facilities_flagged": int(priority[column].gt(0).sum()),
            "mean_component_score": round(float(priority[column].mean()), 2),
        })
    domain_summary = pd.DataFrame(domain_rows).sort_values(
        ["facilities_flagged", "mean_component_score"], ascending=[False, False]
    ).reset_index(drop=True)

    band_counts = priority["Priority_Band"].value_counts()
    total = len(priority)
    kpis = {
        "facilities": total,
        "high_review": int(band_counts.get("High review", 0)),
        "focused_review": int(band_counts.get("Focused review", 0)),
        "routine_review": int(band_counts.get("Routine review", 0)),
        "mean_priority_score": round(float(priority["Integrated_Priority_Score"].mean()), 2),
        "tracked_actions": int(len(actions)),
        "overdue_actions": int(actions["Overdue"].sum()) if not actions.empty else 0,
        "action_resolution_rate_pct": round(
            100 * int(actions["Status"].eq("Resolved").sum()) / len(actions), 2
        ) if not actions.empty else 0.0,
    }
    return {
        "kpis": kpis,
        "district": district,
        "domains": domain_summary,
        "management_queue": queue.head(top_n).copy(),
        "all_facilities": queue,
        "as_of": reference.date().isoformat(),
        "synthetic_scope": (
            "Synthetic facility and action records only. Priority inputs have mixed time scopes; "
            "the register is a screening aid, not an official performance or clinical rating."
        ),
    }
