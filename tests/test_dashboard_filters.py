from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from dashboard_filters import apply_dashboard_filters


@pytest.fixture
def dashboard_records():
    return pd.DataFrame(
        [
            {"Facility": "A", "Programme": "HIV", "Month": "2025-01-01", "Requires_Follow_Up": True, "Issue_Late_Report": False},
            {"Facility": "A", "Programme": "HIV", "Month": "2025-02-01", "Requires_Follow_Up": False, "Issue_Late_Report": True},
            {"Facility": "B", "Programme": "Malaria", "Month": "2025-02-01", "Requires_Follow_Up": True, "Issue_Late_Report": False},
        ]
    )


def test_dashboard_filters_combine_facility_programme_date_and_issue(dashboard_records):
    result = apply_dashboard_filters(
        dashboard_records,
        selected_facilities=["A"],
        selected_programmes=["HIV"],
        date_range=(date(2025, 1, 1), date(2025, 2, 1)),
        issue_filter="Requires follow-up",
    )
    assert result.index.tolist() == [0]


def test_dashboard_filters_return_empty_for_empty_facility_selection(dashboard_records):
    result = apply_dashboard_filters(
        dashboard_records,
        selected_facilities=[],
        selected_programmes=["HIV", "Malaria"],
        date_range=None,
        issue_filter="All records",
    )
    assert result.empty
    assert list(result.columns) == list(dashboard_records.columns)


def test_dashboard_filters_support_single_day_selection(dashboard_records):
    result = apply_dashboard_filters(
        dashboard_records,
        selected_facilities=["A", "B"],
        selected_programmes=["HIV", "Malaria"],
        date_range=(date(2025, 2, 1),),
        issue_filter="All records",
    )
    assert result.index.tolist() == [1, 2]


def test_dashboard_filters_reject_reversed_date_range(dashboard_records):
    with pytest.raises(ValueError, match="must not exceed"):
        apply_dashboard_filters(
            dashboard_records,
            selected_facilities=["A"],
            selected_programmes=["HIV"],
            date_range=(date(2025, 2, 1), date(2025, 1, 1)),
            issue_filter="All records",
        )


def test_dashboard_filters_reject_more_than_two_dates(dashboard_records):
    with pytest.raises(ValueError, match="zero, one or two"):
        apply_dashboard_filters(
            dashboard_records,
            selected_facilities=["A"],
            selected_programmes=["HIV"],
            date_range=(date(2025, 1, 1), date(2025, 2, 1), date(2025, 3, 1)),
            issue_filter="All records",
        )


def test_dashboard_filters_ignore_unknown_issue_filter(dashboard_records):
    result = apply_dashboard_filters(
        dashboard_records,
        selected_facilities=["A"],
        selected_programmes=["HIV"],
        date_range=None,
        issue_filter="All records",
    )
    assert result.index.tolist() == [0, 1]


def test_dashboard_filter_single_mask_matches_expected_rows_at_288k_scale():
    facilities = [f"F{i:03d}" for i in range(120)]
    programmes = ["HIV", "TB", "Maternal"]
    months = pd.date_range("2021-01-01", periods=60, freq="MS")
    frame = pd.DataFrame({
        "Facility": [facilities[i % 120] for i in range(288_000)],
        "Programme": [programmes[(i // 120) % 3] for i in range(288_000)],
        "Month": [months[(i // 360) % 60] for i in range(288_000)],
        "Requires_Follow_Up": [i % 7 == 0 for i in range(288_000)],
    })
    result = apply_dashboard_filters(
        frame,
        selected_facilities=["F001", "F002"],
        selected_programmes=["HIV"],
        date_range=(date(2022, 1, 1), date(2022, 12, 1)),
        issue_filter="Requires follow-up",
    )
    expected = frame[
        frame["Facility"].isin(["F001", "F002"])
        & frame["Programme"].eq("HIV")
        & pd.to_datetime(frame["Month"]).between("2022-01-01", "2022-12-01")
        & frame["Requires_Follow_Up"]
    ]
    pd.testing.assert_frame_equal(result, expected)
