"""Cross-artifact lineage checks for dashboard, executive and management outputs."""
from __future__ import annotations

from typing import Any

import pandas as pd


def _require_columns(frame: pd.DataFrame, columns: set[str], label: str) -> None:
    missing = sorted(columns - set(frame.columns))
    if missing:
        raise ValueError(f"{label} is missing lineage columns: {missing}")


def _same_counts(left: dict[str, int], right: dict[str, int]) -> bool:
    return left == right


def build_lineage_reconciliation_report(
    priority_register: pd.DataFrame,
    action_register: pd.DataFrame,
    action_performance: dict[str, Any],
    executive_briefing: dict[str, Any],
    export_tables: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """Verify that dashboard summaries and ZIP tables retain their canonical source rows."""
    _require_columns(priority_register, {"Facility_ID", "District", "Integrated_Priority_Score",
        "Integrated_Priority_Rank", "Priority_Band"}, "Priority register")
    if priority_register.empty or priority_register["Facility_ID"].isna().any():
        raise ValueError("Priority register must contain identified facility rows")
    if priority_register["Facility_ID"].astype(str).duplicated().any():
        raise ValueError("Priority register contains duplicate facility IDs")
    canonical_ids = set(priority_register["Facility_ID"].astype(str))

    executive_all = executive_briefing["all_facilities"]
    _require_columns(executive_all, {"Facility_ID", "District", "Integrated_Priority_Score",
        "Integrated_Priority_Rank", "Priority_Band"}, "Executive facility output")
    if executive_all["Facility_ID"].astype(str).duplicated().any():
        raise ValueError("Executive facility output contains duplicate facility IDs")
    if set(executive_all["Facility_ID"].astype(str)) != canonical_ids:
        raise ValueError("Executive facility output does not cover the canonical priority register")
    canonical = priority_register.set_index("Facility_ID").sort_index()
    executive = executive_all.set_index("Facility_ID").sort_index()
    for column in ["District", "Integrated_Priority_Score", "Integrated_Priority_Rank", "Priority_Band"]:
        left = canonical[column].astype(str)
        right = executive[column].astype(str)
        if not left.equals(right):
            raise ValueError(f"Executive facility output does not reconcile to priority register: {column}")

    if action_register.empty:
        source_action_ids: set[str] = set()
        source_status: dict[str, int] = {}
        source_district: dict[str, dict[str, int]] = {}
    else:
        _require_columns(action_register, {"Record_ID", "Facility", "Status"}, "Saved action register")
        if action_register["Record_ID"].isna().any() or action_register["Record_ID"].astype(str).duplicated().any():
            raise ValueError("Saved action register contains missing or duplicate Record_ID values")
        source_action_ids = set(action_register["Record_ID"].astype(str))
        source_status = action_register["Status"].astype(str).value_counts().to_dict()
        districts = action_register["Facility"].astype(str).str.extract(
            r"\(([^()]*)\)\s*\[[^]]+\]\s*$", expand=False
        )
        if districts.isna().any():
            raise ValueError("Saved action register contains an unparseable district label")
        source_district = {}
        for district, group in action_register.assign(_district=districts).groupby("_district"):
            source_district[str(district)] = {
                status: int(group["Status"].eq(status).sum())
                for status in ["Open", "In progress", "Resolved", "Escalated"]
            }

    performance_actions = action_performance["actions"]
    if not performance_actions.empty:
        _require_columns(performance_actions, {"Record_ID", "Status", "District", "Overdue"},
                         "Validated action-performance register")
        performance_ids = set(performance_actions["Record_ID"].astype(str))
        if performance_ids != source_action_ids:
            raise ValueError("Action-performance register Record_ID population differs from saved actions")
        if performance_actions["Record_ID"].astype(str).duplicated().any():
            raise ValueError("Action-performance register contains duplicate Record_ID values")
        performance_status = performance_actions["Status"].astype(str).value_counts().to_dict()
        if performance_status != source_status:
            raise ValueError("Action-performance status totals differ from saved action register")
        performance_district: dict[str, dict[str, int]] = {}
        for district, group in performance_actions.groupby("District"):
            performance_district[str(district)] = {
                status: int(group["Status"].eq(status).sum())
                for status in ["Open", "In progress", "Resolved", "Escalated"]
            }
        if performance_district != source_district:
            raise ValueError("Action-performance district/status totals differ from saved actions")
        if int(performance_actions["Overdue"].sum()) != int(action_performance["kpis"]["overdue"]):
            raise ValueError("Action-performance overdue KPI does not reconcile to its action rows")
    elif source_action_ids:
        raise ValueError("Action-performance register is empty while saved actions exist")

    expected_status = {
        "tracked": len(source_action_ids),
        "resolved": source_status.get("Resolved", 0),
        "open": source_status.get("Open", 0),
        "in_progress": source_status.get("In progress", 0),
        "escalated": source_status.get("Escalated", 0),
    }
    performance_kpis = action_performance["kpis"]
    for key, expected in expected_status.items():
        if int(performance_kpis[key]) != expected:
            raise ValueError(f"Action-performance KPI '{key}' differs from saved action register")
    if int(executive_briefing["kpis"]["tracked_actions"]) != len(source_action_ids):
        raise ValueError("Executive tracked-action KPI differs from saved action register")
    if int(executive_briefing["kpis"]["overdue_actions"]) != int(performance_kpis["overdue"]):
        raise ValueError("Executive overdue-action KPI differs from action-performance KPI")

    executive_district = executive_briefing["district"]
    performance_district_frame = action_performance["district"]
    if not executive_district.empty and not performance_district_frame.empty:
        left = executive_district.set_index("District").sort_index()
        right = performance_district_frame.set_index("District").sort_index()
        for column in ["tracked_actions", "resolved_actions", "overdue_actions",
                       "open_actions", "in_progress_actions", "escalated_actions"]:
            if column not in left or column not in right:
                raise ValueError(f"District reconciliation is missing {column}")
            if left[column].astype(int).to_dict() != right[column].astype(int).to_dict():
                raise ValueError(f"Executive and action-performance district totals differ: {column}")
    elif source_action_ids:
        raise ValueError("District summaries are missing while saved actions exist")

    monthly = action_performance["monthly"]
    if not monthly.empty and int(monthly["tracked_actions"].sum()) != len(source_action_ids):
        raise ValueError("Monthly action totals do not reconcile to saved action count")

    expected_exports = {
        "integrated_facility_priority_register.csv": priority_register,
        "integrated_facility_corrective_action_register.csv": action_register,
        "district_action_performance.csv": action_performance["district"],
        "monthly_action_performance.csv": action_performance["monthly"],
        "validated_action_performance_register.csv": action_performance["actions"],
        "executive_facility_management_briefing.csv": executive_briefing["all_facilities"],
        "executive_district_briefing.csv": executive_briefing["district"],
        "executive_domain_briefing.csv": executive_briefing["domains"],
        "executive_management_queue_top_n.csv": executive_briefing["management_queue"],
    }
    for filename, expected in expected_exports.items():
        actual = export_tables.get(filename)
        if not isinstance(actual, pd.DataFrame):
            raise ValueError(f"Management export is missing required lineage table: {filename}")
        if not actual.reset_index(drop=True).equals(expected.reset_index(drop=True)):
            raise ValueError(f"Management export table differs from dashboard source: {filename}")

    queue = executive_briefing["management_queue"]
    if queue["Facility_ID"].astype(str).duplicated().any():
        raise ValueError("Executive top-N queue contains duplicate facility IDs")
    if not set(queue["Facility_ID"].astype(str)).issubset(canonical_ids):
        raise ValueError("Executive top-N queue contains facilities outside the canonical register")
    if len(queue) > len(executive_all):
        raise ValueError("Executive top-N queue is larger than the full facility output")

    checks = [
        ("canonical_facility_population", len(canonical_ids)),
        ("executive_facility_population", len(executive_all)),
        ("saved_action_population", len(source_action_ids)),
        ("action_performance_population", len(performance_actions)),
        ("monthly_action_population", int(monthly["tracked_actions"].sum()) if not monthly.empty else 0),
        ("management_export_tables", len(expected_exports)),
        ("executive_queue_rows", len(queue)),
    ]
    return pd.DataFrame([
        {"check": name, "status": "PASS", "observed_value": value}
        for name, value in checks
    ])
