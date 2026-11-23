"""Tests for converting integrated facility priorities into action records."""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from priority_action_workflow import build_priority_action_rows


def priority_frame():
    return pd.DataFrame([
        {
            "Facility_ID": "F-001", "Facility_Name": "Alpha Clinic",
            "District": "North", "Priority_Band": "High review",
            "Integrated_Priority_Rank": 1, "Integrated_Priority_Score": 75.0,
            "Review_Domains": "data_quality;operational_resilience",
        },
        {
            "Facility_ID": "F-002", "Facility_Name": "Beta Clinic",
            "District": "South", "Priority_Band": "Routine review",
            "Integrated_Priority_Rank": 2, "Integrated_Priority_Score": 10.0,
            "Review_Domains": "resource_capacity",
        },
    ])


def test_priority_rows_create_one_stable_action_per_facility():
    first = build_priority_action_rows(priority_frame(), "2026-10-01")
    second = build_priority_action_rows(priority_frame().iloc[::-1], "2026-10-15")
    assert set(first["Record_ID"]) == set(second["Record_ID"])
    first_id = first.loc[first["Facility"].str.contains("F-001"), "Record_ID"].iloc[0]
    second_id = second.loc[second["Facility"].str.contains("F-001"), "Record_ID"].iloc[0]
    assert first_id == second_id
    assert first["Issue count"].tolist() == [2, 1]
    assert first.loc[0, "Status"] == "Open"
    assert first.loc[0, "Month"] == "2026-10-01"


def test_priority_action_rows_preserve_existing_assignments():
    initial = build_priority_action_rows(priority_frame(), "2026-10-01")
    record_id = initial.loc[0, "Record_ID"]
    saved = {
        record_id: {
            "Status": "In progress", "Assigned owner": "District data officer",
            "Root cause": "Delayed consolidation",
            "Corrective action / notes": "Introduce weekly verification",
            "Due date": "2026-11-15",
        }
    }
    refreshed = build_priority_action_rows(priority_frame(), "2026-10-01", saved)
    row = refreshed.loc[refreshed["Record_ID"].eq(record_id)].iloc[0]
    assert row["Status"] == "In progress"
    assert row["Assigned owner"] == "District data officer"
    assert row["Due date"] == "2026-11-15"


@pytest.mark.parametrize("bad_score", [-1, 101, float("nan")])
def test_priority_action_rows_reject_invalid_scores(bad_score):
    data = priority_frame()
    data.loc[0, "Integrated_Priority_Score"] = bad_score
    with pytest.raises(ValueError, match="scores"):
        build_priority_action_rows(data, "2026-10-01")


def test_priority_action_rows_reject_duplicate_facilities():
    data = pd.concat([priority_frame(), priority_frame().iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="duplicate"):
        build_priority_action_rows(data, "2026-10-01")


def test_priority_action_rows_reject_invalid_latest_month():
    with pytest.raises(ValueError, match="Latest simulated month"):
        build_priority_action_rows(priority_frame(), "not-a-date")


def test_priority_action_rows_reject_duplicate_ranks():
    data = priority_frame()
    data.loc[1, "Integrated_Priority_Rank"] = 1
    with pytest.raises(ValueError, match="unique positive"):
        build_priority_action_rows(data, "2026-10-01")


def test_priority_action_rows_reject_missing_review_domains():
    data = priority_frame()
    data.loc[0, "Review_Domains"] = None
    with pytest.raises(ValueError, match="missing review domains"):
        build_priority_action_rows(data, "2026-10-01")


def test_priority_action_rows_persist_through_audited_store(tmp_path):
    from action_store import ActionRegisterStore

    store = ActionRegisterStore(tmp_path / "priority-actions.sqlite")
    row = build_priority_action_rows(priority_frame(), "2026-10-01").iloc[0].to_dict()
    assert store.upsert_actions([row])["inserted"] == 1
    row["Status"] = "In progress"
    row["Assigned owner"] = "District coordinator"
    row["Root cause"] = "Delayed reporting consolidation"
    assert store.upsert_actions([row])["updated"] == 1
    loaded = store.get_actions([row["Record_ID"]])[row["Record_ID"]]
    assert loaded["Assigned owner"] == "District coordinator"
    history = store.history(row["Record_ID"])
    assert {"Status", "Assigned owner", "Root cause"}.issubset(set(history["field_name"]))
