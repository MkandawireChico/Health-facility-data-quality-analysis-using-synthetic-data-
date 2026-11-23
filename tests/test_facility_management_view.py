"""Tests for facility-level management drill-downs."""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from facility_management_view import build_facility_management_view, extract_facility_id


def priorities():
    return pd.DataFrame([
        {"Facility_ID": "F-001", "Facility_Name": "Alpha", "District": "North",
         "Priority_Band": "High review", "Integrated_Priority_Rank": 1,
         "Integrated_Priority_Score": 75.0, "Data_Quality_Priority_Score": 20.0,
         "Resource_Gap_Priority_Score": 80.0, "Operational_Priority_Score": 100.0,
         "Supply_Cold_Chain_Priority_Score": 100.0, "Review_Domains": "workforce; supply"},
        {"Facility_ID": "F-002", "Facility_Name": "Beta", "District": "South",
         "Priority_Band": "Routine review", "Integrated_Priority_Rank": 2,
         "Integrated_Priority_Score": 10.0, "Data_Quality_Priority_Score": 10.0,
         "Resource_Gap_Priority_Score": 30.0, "Operational_Priority_Score": 0.0,
         "Supply_Cold_Chain_Priority_Score": 0.0, "Review_Domains": "data quality"},
    ])


def actions():
    return pd.DataFrame([
        {"Record_ID": "A1", "Facility": "Alpha (North) [F-001]", "Month": "2026-09-01",
         "Status": "Resolved", "Assigned owner": "Officer A", "Root cause": "Cause",
         "Corrective action / notes": "Completed", "Due date": "2026-09-20"},
        {"Record_ID": "A2", "Facility": "Alpha (North) [F-001]", "Month": "2026-10-01",
         "Status": "Open", "Assigned owner": "Officer B", "Root cause": "",
         "Corrective action / notes": "", "Due date": "2026-09-25"},
        {"Record_ID": "A3", "Facility": "Beta (South) [F-002]", "Month": "2026-10-01",
         "Status": "In progress", "Assigned owner": "", "Root cause": "",
         "Corrective action / notes": "", "Due date": ""},
    ])


def test_extracts_canonical_facility_id():
    assert extract_facility_id("Alpha Clinic (North) [F-001]") == "F-001"


def test_filters_action_history_and_calculates_progress_for_one_facility():
    result = build_facility_management_view(
        priorities(), actions(), "F-001",
        audit_history=pd.DataFrame([{"field_name": "Status", "old_value": "Open", "new_value": "Resolved"}]),
        as_of="2026-10-01",
    )
    assert result["facility"]["Facility_ID"] == "F-001"
    assert result["actions"]["Record_ID"].tolist() == ["A1", "A2"]
    assert result["progress"]["tracked"] == 2
    assert result["progress"]["resolved"] == 1
    assert result["progress"]["resolution_rate_pct"] == 50.0
    assert result["progress"]["overdue"] == 1
    assert len(result["audit_history"]) == 1
    assert result["monthly"]["Month"].tolist() == ["2026-09", "2026-10"]


def test_unknown_facility_is_rejected():
    with pytest.raises(ValueError, match="Unknown facility"):
        build_facility_management_view(priorities(), actions(), "F-999")


def test_empty_action_register_keeps_priority_context_and_zero_progress():
    empty = pd.DataFrame(columns=[
        "Record_ID", "Facility", "Month", "Status", "Assigned owner",
        "Root cause", "Corrective action / notes", "Due date",
    ])
    result = build_facility_management_view(priorities(), empty, "F-002")
    assert result["facility"]["Facility_ID"] == "F-002"
    assert result["actions"].empty
    assert result["progress"]["tracked"] == 0
    assert result["progress"]["resolution_rate_pct"] == 0.0


def test_malformed_action_facility_label_is_rejected():
    bad = actions()
    bad.loc[0, "Facility"] = "Alpha Clinic"
    with pytest.raises(ValueError, match=r"end with \[Facility_ID\]"):
        build_facility_management_view(priorities(), bad, "F-001")


def test_duplicate_priority_facility_ids_are_rejected():
    bad = pd.concat([priorities(), priorities().iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="duplicate facility"):
        build_facility_management_view(bad, actions(), "F-001")
