from __future__ import annotations

import io
import json
import sys
import zipfile
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from management_export import build_management_review_archive


def test_management_review_archive_contains_summary_and_every_table():
    tables = {
        "district_action_performance.csv": pd.DataFrame([{"District": "North", "tracked": 2}]),
        "integrated_facility_priority_register.csv": pd.DataFrame([{"Facility_ID": "F-001"}]),
    }
    summary = {"synthetic_data": True, "saved_actions": 2}

    payload = build_management_review_archive(tables, summary)

    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        assert set(archive.namelist()) == {
            "management_summary.json",
            "district_action_performance.csv",
            "integrated_facility_priority_register.csv",
        }
        assert json.loads(archive.read("management_summary.json")) == summary
        exported = pd.read_csv(archive.open("district_action_performance.csv"))
        assert exported.to_dict(orient="records") == [{"District": "North", "tracked": 2}]


def test_management_review_archive_rejects_path_traversal_filename():
    with pytest.raises(ValueError, match="Invalid management export filename"):
        build_management_review_archive(
            {"../actions.csv": pd.DataFrame()},
            {"synthetic_data": True},
        )


def test_management_review_archive_rejects_reserved_summary_filename_case_insensitively():
    for filename in ("management_summary.csv", "MANAGEMENT_SUMMARY.CSV"):
        with pytest.raises(ValueError, match="Invalid management export filename"):
            build_management_review_archive(
                {filename: pd.DataFrame()},
                {"synthetic_data": True},
            )


def test_management_review_archive_rejects_case_insensitive_duplicate_names():
    with pytest.raises(ValueError, match="Duplicate management export filename"):
        build_management_review_archive(
            {
                "Actions.csv": pd.DataFrame(),
                "actions.csv": pd.DataFrame(),
            },
            {"synthetic_data": True},
        )


def test_management_review_archive_rejects_non_dataframe_table():
    with pytest.raises(ValueError, match="must be a DataFrame"):
        build_management_review_archive(
            {"actions.csv": [{"Record_ID": "A-1"}]},
            {"synthetic_data": True},
        )


def test_management_review_archive_escapes_formula_like_text_but_preserves_numbers():
    frame = pd.DataFrame(
        {
            "Owner_Note": ["=HYPERLINK(\"https://example.invalid\")", "  +SUM(1,2)", "@cmd", "ordinary"],
            "Units": [-4, 0, 2, 3],
        }
    )
    payload = build_management_review_archive({"actions.csv": frame}, {"synthetic_data": True})

    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        exported = pd.read_csv(archive.open("actions.csv"), keep_default_na=False)
    assert exported["Owner_Note"].tolist() == [
        "'=HYPERLINK(\"https://example.invalid\")",
        "'  +SUM(1,2)",
        "'@cmd",
        "ordinary",
    ]
    assert exported["Units"].tolist() == [-4, 0, 2, 3]


def test_management_review_archive_rejects_non_finite_summary_numbers():
    with pytest.raises(ValueError, match="not valid JSON"):
        build_management_review_archive(
            {"actions.csv": pd.DataFrame()},
            {"synthetic_data": True, "invalid_metric": float("nan")},
        )


def test_management_review_archive_is_byte_for_byte_deterministic():
    tables = {"actions.csv": pd.DataFrame([{"Record_ID": "A-1", "status": "Open"}])}
    summary = {"synthetic_data": True, "saved_actions": 1}

    first = build_management_review_archive(tables, summary)
    second = build_management_review_archive(tables, summary)

    assert first == second
