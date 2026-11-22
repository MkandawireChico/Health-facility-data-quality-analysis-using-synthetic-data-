from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_streamlit_dashboard_renders_without_runtime_exception(tmp_path, monkeypatch):
    monkeypatch.setenv("HEALTH_DATA_ACTION_DB", str(tmp_path / "test-actions.sqlite"))
    app_path = Path(__file__).resolve().parents[1] / "dashboard" / "streamlit_app.py"
    app = AppTest.from_file(str(app_path), default_timeout=30).run()

    assert not app.exception
