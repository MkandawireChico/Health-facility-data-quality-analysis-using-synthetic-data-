"""End-to-end reconciliation tests across dashboard and management artefacts."""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from action_performance import build_action_performance
from executive_management_briefing import build_executive_management_briefing
from lineage_audit import build_lineage_reconciliation_report


def _fixtures():
    priority = pd.DataFrame([
        {"Facility_ID":"F-001","Facility_Name":"Alpha","District":"North","Priority_Band":"High review",
         "Integrated_Priority_Rank":1,"Integrated_Priority_Score":75.0,
         "Data_Quality_Priority_Score":20.0,"Resource_Gap_Priority_Score":80.0,
         "Operational_Priority_Score":100.0,"Supply_Cold_Chain_Priority_Score":100.0,"Review_Domains":"multiple"},
        {"Facility_ID":"F-002","Facility_Name":"Beta","District":"South","Priority_Band":"Routine review",
         "Integrated_Priority_Rank":3,"Integrated_Priority_Score":10.0,
         "Data_Quality_Priority_Score":10.0,"Resource_Gap_Priority_Score":30.0,
         "Operational_Priority_Score":0.0,"Supply_Cold_Chain_Priority_Score":0.0,"Review_Domains":"quality"},
        {"Facility_ID":"F-003","Facility_Name":"Gamma","District":"North","Priority_Band":"Focused review",
         "Integrated_Priority_Rank":2,"Integrated_Priority_Score":30.0,
         "Data_Quality_Priority_Score":20.0,"Resource_Gap_Priority_Score":20.0,
         "Operational_Priority_Score":40.0,"Supply_Cold_Chain_Priority_Score":40.0,"Review_Domains":"several"},
    ])
    actions = pd.DataFrame([
        {"Record_ID":"A1","Facility":"Alpha (North) [F-001]","Month":"2026-10-01","Status":"Open",
         "Assigned owner":"Officer A","Due date":"2026-10-10"},
        {"Record_ID":"A2","Facility":"Alpha (North) [F-001]","Month":"2026-10-01","Status":"Resolved",
         "Assigned owner":"Officer A","Due date":"2026-10-09"},
        {"Record_ID":"A3","Facility":"Gamma (North) [F-003]","Month":"2026-10-01","Status":"Escalated",
         "Assigned owner":"Officer B","Due date":"2026-10-11"},
    ])
    performance = build_action_performance(actions, as_of="2026-10-12", priority_register=priority)
    executive = build_executive_management_briefing(priority, actions, as_of="2026-10-12")
    exports = {
        "integrated_facility_priority_register.csv": priority,
        "integrated_facility_corrective_action_register.csv": actions,
        "district_action_performance.csv": performance["district"],
        "monthly_action_performance.csv": performance["monthly"],
        "validated_action_performance_register.csv": performance["actions"],
        "executive_facility_management_briefing.csv": executive["all_facilities"],
        "executive_district_briefing.csv": executive["district"],
        "executive_domain_briefing.csv": executive["domains"],
        "executive_management_queue_top_n.csv": executive["management_queue"],
    }
    return priority, actions, performance, executive, exports


def test_dashboard_and_management_exports_share_one_canonical_lineage():
    priority, actions, performance, executive, exports = _fixtures()
    report = build_lineage_reconciliation_report(priority, actions, performance, executive, exports)
    assert report["status"].eq("PASS").all()
    assert report.set_index("check").loc["canonical_facility_population", "observed_value"] == 3
    assert report.set_index("check").loc["saved_action_population", "observed_value"] == 3


def test_lineage_rejects_action_export_missing_a_saved_record():
    priority, actions, performance, executive, exports = _fixtures()
    exports["integrated_facility_corrective_action_register.csv"] = actions.iloc[:-1].copy()
    with pytest.raises(ValueError, match="differs from dashboard source"):
        build_lineage_reconciliation_report(priority, actions, performance, executive, exports)


def test_lineage_rejects_executive_facility_population_drift():
    priority, actions, performance, executive, exports = _fixtures()
    executive["all_facilities"] = executive["all_facilities"].iloc[:-1].copy()
    with pytest.raises(ValueError, match="does not cover the canonical priority register"):
        build_lineage_reconciliation_report(priority, actions, performance, executive, exports)


def test_lineage_rejects_action_status_total_drift():
    priority, actions, performance, executive, exports = _fixtures()
    performance["kpis"]["resolved"] = 99
    with pytest.raises(ValueError, match="KPI 'resolved'"):
        build_lineage_reconciliation_report(priority, actions, performance, executive, exports)


def test_lineage_rejects_exported_district_summary_drift():
    priority, actions, performance, executive, exports = _fixtures()
    exports["executive_district_briefing.csv"] = executive["district"].copy()
    exports["executive_district_briefing.csv"].loc[0, "tracked_actions"] = 99
    with pytest.raises(ValueError, match="differs from dashboard source"):
        build_lineage_reconciliation_report(priority, actions, performance, executive, exports)


def test_lineage_rejects_queue_with_unknown_facility():
    priority, actions, performance, executive, exports = _fixtures()
    executive["management_queue"] = executive["management_queue"].copy()
    executive["management_queue"].loc[0, "Facility_ID"] = "F-999"
    exports["executive_management_queue_top_n.csv"] = executive["management_queue"]
    with pytest.raises(ValueError, match="outside the canonical register"):
        build_lineage_reconciliation_report(priority, actions, performance, executive, exports)
