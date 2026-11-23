from pathlib import Path

from streamlit.testing.v1 import AppTest

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from action_store import ActionRegisterStore


def test_streamlit_dashboard_renders_without_runtime_exception(tmp_path, monkeypatch):
    monkeypatch.setenv("HEALTH_DATA_ACTION_DB", str(tmp_path / "test-actions.sqlite"))
    app_path = Path(__file__).resolve().parents[1] / "dashboard" / "streamlit_app.py"
    app = AppTest.from_file(str(app_path), default_timeout=30).run()

    assert not app.exception


def test_saved_action_portfolio_is_visible_without_matching_current_rows(tmp_path, monkeypatch):
    database = tmp_path / "persisted-actions.sqlite"
    monkeypatch.setenv("HEALTH_DATA_ACTION_DB", str(database))
    store = ActionRegisterStore(database)
    store.upsert_actions([{
        "Record_ID": "ACT-PERSISTED-TEST",
        "Facility": "Synthetic Facility 0001",
        "Month": "2025-01-01",
        "Programme": "HIV",
        "Indicator": "Test indicator",
        "Primary issue": "Late report",
        "Issue count": 1,
        "Status": "In progress",
        "Assigned owner": "M&E Officer",
        "Root cause": "Delayed source collation",
        "Corrective action / notes": "Confirm reporting timeline",
        "Due date": "2026-12-01",
    }])
    app_path = Path(__file__).resolve().parents[1] / "dashboard" / "streamlit_app.py"
    app = AppTest.from_file(str(app_path), default_timeout=30).run()

    assert not app.exception
    assert any("Action portfolio" in item.value for item in app.markdown)
