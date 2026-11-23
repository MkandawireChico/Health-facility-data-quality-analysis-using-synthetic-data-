"""Tests for the cross-facility executive management briefing."""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from executive_management_briefing import build_executive_management_briefing


def priority_rows():
    return pd.DataFrame([
        {"Facility_ID": "F-001", "Facility_Name": "Alpha", "District": "North",
         "Priority_Band": "High review", "Integrated_Priority_Rank": 1,
         "Integrated_Priority_Score": 75.0, "Data_Quality_Priority_Score": 20.0,
         "Resource_Gap_Priority_Score": 80.0, "Operational_Priority_Score": 100.0,
         "Supply_Cold_Chain_Priority_Score": 100.0, "Review_Domains": "multiple"},
        {"Facility_ID": "F-002", "Facility_Name": "Beta", "District": "South",
         "Priority_Band": "Routine review", "Integrated_Priority_Rank": 2,
         "Integrated_Priority_Score": 10.0, "Data_Quality_Priority_Score": 10.0,
         "Resource_Gap_Priority_Score": 30.0, "Operational_Priority_Score": 0.0,
         "Supply_Cold_Chain_Priority_Score": 0.0, "Review_Domains": "quality"},
        {"Facility_ID": "F-003", "Facility_Name": "Gamma", "District": "North",
         "Priority_Band": "Focused review", "Integrated_Priority_Rank": 3,
         "Integrated_Priority_Score": 30.0, "Data_Quality_Priority_Score": 20.0,
         "Resource_Gap_Priority_Score": 20.0, "Operational_Priority_Score": 40.0,
         "Supply_Cold_Chain_Priority_Score": 40.0, "Review_Domains": "several"},
    ])


def action_rows():
    return pd.DataFrame([
        {"Record_ID": "A1", "Facility": "Alpha (North) [F-001]", "Month": "2026-10-01",
         "Status": "Open", "Assigned owner": "Officer A", "Due date": "2026-10-10"},
        {"Record_ID": "A2", "Facility": "Alpha (North) [F-001]", "Month": "2026-10-01",
         "Status": "Resolved", "Assigned owner": "Officer A", "Due date": "2026-10-09"},
        {"Record_ID": "A3", "Facility": "Gamma (North) [F-003]", "Month": "2026-10-01",
         "Status": "Escalated", "Assigned owner": "Officer B", "Due date": "2026-10-11"},
    ])


def test_briefing_kpis_domain_counts_and_priority_order():
    result = build_executive_management_briefing(
        priority_rows(), action_rows(), as_of="2026-10-12"
    )
    assert result["kpis"]["facilities"] == 3
    assert result["kpis"]["high_review"] == 1
    assert result["kpis"]["overdue_actions"] == 2
    assert result["kpis"]["action_resolution_rate_pct"] == pytest.approx(33.33)
    assert result["management_queue"]["Facility_ID"].tolist() == ["F-001", "F-003", "F-002"]
    assert result["domains"].iloc[0]["facilities_flagged"] == 3


def test_district_summary_reconciles_facilities_and_actions():
    result = build_executive_management_briefing(
        priority_rows(), action_rows(), as_of="2026-10-12"
    )
    north = result["district"].set_index("District").loc["North"]
    south = result["district"].set_index("District").loc["South"]
    assert north["facilities"] == 2
    assert north["tracked_actions"] == 3
    assert north["overdue_actions"] == 2
    assert south["facilities"] == 1
    assert south["tracked_actions"] == 0


def test_empty_action_register_preserves_facility_comparison():
    empty = pd.DataFrame(columns=[
        "Record_ID", "Facility", "Month", "Status", "Assigned owner", "Due date"
    ])
    result = build_executive_management_briefing(priority_rows(), empty)
    assert result["kpis"]["tracked_actions"] == 0
    assert result["kpis"]["overdue_actions"] == 0
    assert len(result["district"]) == 2
    assert result["management_queue"]["actions_tracked"].sum() == 0


def test_unknown_action_facility_is_rejected():
    bad = action_rows()
    bad.loc[0, "Facility"] = "Unknown (West) [F-999]"
    with pytest.raises(ValueError, match="absent from the priority register"):
        build_executive_management_briefing(priority_rows(), bad)


def test_duplicate_facility_ids_are_rejected():
    bad = pd.concat([priority_rows(), priority_rows().iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="duplicate facility"):
        build_executive_management_briefing(bad, action_rows())


def test_invalid_priority_component_is_rejected():
    bad = priority_rows()
    bad.loc[0, "Operational_Priority_Score"] = 120
    with pytest.raises(ValueError, match="invalid Operational_Priority_Score"):
        build_executive_management_briefing(bad, action_rows())


def test_priority_score_must_reconcile_to_component_mean():
    bad = priority_rows()
    bad.loc[0, "Integrated_Priority_Score"] = 10
    with pytest.raises(ValueError, match="do not reconcile"):
        build_executive_management_briefing(bad, action_rows())


def test_invalid_top_n_is_rejected():
    with pytest.raises(ValueError, match="top_n"):
        build_executive_management_briefing(priority_rows(), action_rows(), top_n=0)


def test_recommendations_reflect_overdue_and_unassigned_action_gap():
    result = build_executive_management_briefing(
        priority_rows(), action_rows(), as_of="2026-10-12"
    )
    alpha = result["management_queue"].set_index("Facility_ID").loc["F-001"]
    beta = result["management_queue"].set_index("Facility_ID").loc["F-002"]
    assert "1 overdue" in alpha["Management_Follow_Up"]
    assert "assign an accountable owner" in beta["Management_Follow_Up"]


def test_integer_scores_reconcile_without_dtype_false_positive():
    integer_scores = priority_rows().copy()
    for column in [
        "Integrated_Priority_Score", "Data_Quality_Priority_Score",
        "Resource_Gap_Priority_Score", "Operational_Priority_Score",
        "Supply_Cold_Chain_Priority_Score",
    ]:
        integer_scores[column] = integer_scores[column].astype(int)
    result = build_executive_management_briefing(integer_scores, action_rows())
    assert result["kpis"]["facilities"] == 3


def test_malformed_nonempty_due_date_is_rejected():
    bad = action_rows()
    bad.loc[0, "Due date"] = "next Friday"
    with pytest.raises(ValueError, match="invalid due dates"):
        build_executive_management_briefing(priority_rows(), bad)


def test_invalid_action_month_is_rejected():
    bad = action_rows()
    bad.loc[0, "Month"] = "not-a-month"
    with pytest.raises(ValueError, match="invalid reporting months"):
        build_executive_management_briefing(priority_rows(), bad)
