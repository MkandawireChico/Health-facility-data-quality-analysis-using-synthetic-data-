"""Tests for release-readiness integrity checks."""
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from release_readiness import build_release_readiness_report


def priorities():
    return pd.DataFrame([
        {"Facility_ID": "F1", "Facility_Name": "Alpha", "District": "North",
         "Priority_Band": "High review", "Integrated_Priority_Rank": 1,
         "Integrated_Priority_Score": 75, "Data_Quality_Priority_Score": 20,
         "Resource_Gap_Priority_Score": 80, "Operational_Priority_Score": 100,
         "Supply_Cold_Chain_Priority_Score": 100},
        {"Facility_ID": "F2", "Facility_Name": "Beta", "District": "South",
         "Priority_Band": "Routine review", "Integrated_Priority_Rank": 2,
         "Integrated_Priority_Score": 10, "Data_Quality_Priority_Score": 10,
         "Resource_Gap_Priority_Score": 30, "Operational_Priority_Score": 0,
         "Supply_Cold_Chain_Priority_Score": 0},
    ])


def actions():
    return pd.DataFrame([
        {"Record_ID": "A1", "Facility": "Alpha (North) [F1]", "Month": "2026-10-01",
         "Status": "Open", "Due date": "2026-10-30"},
    ])


def test_valid_registers_pass_and_no_claims_of_external_qa():
    result = build_release_readiness_report(priorities(), actions())
    assert result["readiness"] == "WARNING" or result["readiness"] == "CONDITIONAL"
    assert result["failed"] == 0
    assert result["passed"] >= 7
    assert "Power BI refresh" in result["scope"]


def test_duplicate_facility_identifier_blocks_release():
    bad = pd.concat([priorities(), priorities().iloc[[0]]], ignore_index=True)
    result = build_release_readiness_report(bad, actions())
    assert result["readiness"] == "BLOCKED"
    assert result["failed"] >= 1


def test_priority_score_mismatch_blocks_release():
    bad = priorities()
    bad.loc[0, "Integrated_Priority_Score"] = 20
    result = build_release_readiness_report(bad, actions())
    assert result["readiness"] == "BLOCKED"


def test_unknown_action_facility_blocks_release():
    bad = actions()
    bad.loc[0, "Facility"] = "Unknown [F999]"
    result = build_release_readiness_report(priorities(), bad)
    assert result["readiness"] == "BLOCKED"


def test_empty_action_register_is_valid():
    empty = pd.DataFrame(columns=["Record_ID", "Facility", "Month", "Status", "Due date"])
    result = build_release_readiness_report(priorities(), empty)
    assert result["failed"] == 0
    assert "PASS" in result["checks"]["status"].tolist()


def test_missing_build_summary_is_warning_not_pass(tmp_path):
    result = build_release_readiness_report(priorities(), actions(), tmp_path)
    row = result["checks"].set_index("check").loc["Build artifact manifest"]
    assert row["status"] == "WARNING"
    assert result["readiness"] == "CONDITIONAL"


def test_artifact_hash_mismatch_is_blocking(tmp_path):
    artifact = tmp_path / "analytics.csv"
    artifact.write_text("a,b\n1,2\n", encoding="utf-8")
    summary = {"artifact_manifest": {"sample": {
        "path": "analytics.csv", "size_bytes": artifact.stat().st_size,
        "sha256": "wrong-hash",
    }}}
    (tmp_path / "platform_build_summary.json").write_text(json.dumps(summary), encoding="utf-8")
    result = build_release_readiness_report(priorities(), actions(), tmp_path)
    assert result["readiness"] == "BLOCKED"
    assert "hash/size mismatches" in result["checks"].set_index("check").loc["Build artifact manifest", "detail"]


def test_valid_artifact_manifest_passes(tmp_path):
    import hashlib
    artifact = tmp_path / "analytics.csv"
    content = "a,b\n1,2\n"
    artifact.write_text(content, encoding="utf-8")
    summary = {"artifact_manifest": {"sample": {
        "path": "analytics.csv", "size_bytes": len(content.encode()),
        "sha256": hashlib.sha256(content.encode()).hexdigest(),
    }}}
    (tmp_path / "platform_build_summary.json").write_text(json.dumps(summary), encoding="utf-8")
    result = build_release_readiness_report(priorities(), actions(), tmp_path)
    assert result["checks"].set_index("check").loc["Build artifact manifest", "status"] == "PASS"


def test_path_traversal_in_manifest_is_rejected(tmp_path):
    result = build_release_readiness_report(priorities(), actions(), tmp_path)
    summary = {"artifact_manifest": {"escape": {
        "path": "../outside.csv", "size_bytes": 2, "sha256": "bad",
    }}}
    (tmp_path / "platform_build_summary.json").write_text(json.dumps(summary), encoding="utf-8")
    result = build_release_readiness_report(priorities(), actions(), tmp_path)
    assert result["readiness"] == "BLOCKED"
