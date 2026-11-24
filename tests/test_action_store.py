"""Tests for the SQLite corrective-action store."""
import sys
from pathlib import Path

import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from action_store import ActionRegisterStore, build_action_record_id


def sample_action(**updates):
    row = {
        "Record_ID": "facility-2024-01-HIV-ART",
        "Facility": "Synthetic Facility 0001",
        "Month": "2024-01-01",
        "Programme": "HIV",
        "Indicator": "ART clients",
        "Primary issue": "Late report",
        "Issue count": 1,
        "Status": "Open",
        "Assigned owner": "M&E Officer",
        "Root cause": "",
        "Corrective action / notes": "Confirm submission date",
        "Due date": "2024-02-15",
    }
    row.update(updates)
    return row


def test_action_register_persists_after_reopening(tmp_path):
    path = tmp_path / "actions.sqlite"
    first = ActionRegisterStore(path)
    assert first.upsert_actions([sample_action()]) == {
        "inserted": 1, "updated": 0, "unchanged": 0
    }
    second = ActionRegisterStore(path)
    loaded = second.get_actions(["facility-2024-01-HIV-ART"])
    assert loaded["facility-2024-01-HIV-ART"]["Assigned owner"] == "M&E Officer"
    assert loaded["facility-2024-01-HIV-ART"]["Due date"] == "2024-02-15"


def test_changes_create_field_level_audit_history(tmp_path):
    store = ActionRegisterStore(tmp_path / "actions.sqlite")
    store.upsert_actions([sample_action()])
    result = store.upsert_actions([sample_action(Status="In progress", **{"Root cause": "Late source collation"})])
    assert result["updated"] == 1
    history = store.history("facility-2024-01-HIV-ART")
    assert {"Status", "Root cause"}.issubset(set(history["field_name"]))
    assert history.loc[history["field_name"] == "Status", "new_value"].iloc[-1] == "In progress"


def test_unchanged_save_does_not_duplicate_history(tmp_path):
    store = ActionRegisterStore(tmp_path / "actions.sqlite")
    row = sample_action()
    store.upsert_actions([row])
    initial = len(store.history(row["Record_ID"]))
    result = store.upsert_actions([row])
    assert result["unchanged"] == 1
    assert len(store.history(row["Record_ID"])) == initial


def test_empty_record_ids_are_ignored(tmp_path):
    store = ActionRegisterStore(tmp_path / "actions.sqlite")
    assert store.upsert_actions([{"Record_ID": "  "}]) == {
        "inserted": 0, "updated": 0, "unchanged": 0
    }


def test_action_record_id_is_stable_across_row_order_and_date_formats():
    first = build_action_record_id(
        "cohort.csv", "Facility A", "2025-01-01", "HIV", "ART"
    )
    reordered = build_action_record_id(
        "cohort.csv", "Facility A", pd.Timestamp("2025-01-01"), "HIV", "ART"
    )
    other_source = build_action_record_id(
        "another.csv", "Facility A", "2025-01-01", "HIV", "ART"
    )
    assert first == reordered
    assert first != other_source
