"""Tests for facility corrective-action performance summaries."""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from action_performance import build_action_performance


def action_frame():
    return pd.DataFrame([
        {"Facility": "Alpha Clinic (North) [F-001]", "Month": "2026-09-01",
         "Status": "Resolved", "Due date": "2026-09-20"},
        {"Facility": "Beta Clinic (North) [F-002]", "Month": "2026-09-01",
         "Status": "Open", "Due date": "2026-09-25"},
        {"Facility": "Gamma Clinic (South) [F-003]", "Month": "2026-10-01",
         "Status": "In progress", "Due date": "2026-11-01"},
        {"Facility": "Delta Clinic (South) [F-004]", "Month": "2026-10-01",
         "Status": "Escalated", "Due date": ""},
    ])


def test_action_performance_calculates_portfolio_kpis_and_overdue():
    result = build_action_performance(action_frame(), as_of="2026-10-01")
    assert result["kpis"] == {
        "tracked": 4, "resolved": 1, "resolution_rate_pct": 25.0,
        "overdue": 1, "open": 1, "in_progress": 1, "escalated": 1,
    }


def test_action_performance_summarises_district_workload_and_resolution():
    result = build_action_performance(action_frame(), as_of="2026-10-01")
    north = result["district"].set_index("District").loc["North"]
    south = result["district"].set_index("District").loc["South"]
    assert north["tracked_actions"] == 2
    assert north["resolution_rate_pct"] == 50.0
    assert south["tracked_actions"] == 2
    assert south["resolution_rate_pct"] == 0.0


def test_action_performance_groups_monthly_progress():
    result = build_action_performance(action_frame(), as_of="2026-10-01")
    monthly = result["monthly"].set_index("Month")
    assert monthly.loc["2026-09", "tracked_actions"] == 2
    assert monthly.loc["2026-09", "resolution_rate_pct"] == 50.0
    assert monthly.loc["2026-10", "resolved_actions"] == 0


def test_action_performance_empty_register_returns_zero_kpis():
    result = build_action_performance(
        pd.DataFrame(columns=["Facility", "Month", "Status", "Due date"]),
        as_of="2026-10-01",
    )
    assert result["kpis"]["tracked"] == 0
    assert result["district"].empty


@pytest.mark.parametrize("status", ["Pending", "Closed", ""])
def test_action_performance_rejects_unsupported_status(status):
    data = action_frame()
    data.loc[0, "Status"] = status
    with pytest.raises(ValueError, match="unsupported statuses"):
        build_action_performance(data, as_of="2026-10-01")


def test_action_performance_rejects_malformed_facility_identity():
    data = action_frame()
    data.loc[0, "Facility"] = "Alpha Clinic"
    with pytest.raises(ValueError, match="facility labels"):
        build_action_performance(data, as_of="2026-10-01")
