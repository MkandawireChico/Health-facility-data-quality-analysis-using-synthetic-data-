"""Release-readiness checks for the expanded synthetic facility platform."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd


def _check(name: str, status: str, detail: str, severity: str = "warning") -> dict[str, str]:
    return {"check": name, "status": status, "severity": severity, "detail": detail}


def build_release_readiness_report(
    priority_register: pd.DataFrame,
    action_register: pd.DataFrame | None = None,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Return transparent pass/warning/fail checks; never infer unperformed QA."""
    checks: list[dict[str, str]] = []
    priority = priority_register.copy()
    required = {
        "Facility_ID", "Facility_Name", "District", "Priority_Band",
        "Integrated_Priority_Rank", "Integrated_Priority_Score",
        "Data_Quality_Priority_Score", "Resource_Gap_Priority_Score",
        "Operational_Priority_Score", "Supply_Cold_Chain_Priority_Score",
    }
    missing = sorted(required - set(priority.columns))
    if missing:
        checks.append(_check("Priority register schema", "FAIL", f"Missing columns: {missing}", "fail"))
    elif priority.empty:
        checks.append(_check("Priority register schema", "FAIL", "Priority register is empty.", "fail"))
    else:
        checks.append(_check("Priority register schema", "PASS", f"{len(priority)} facility rows and all required columns present.", "pass"))
        ids = priority["Facility_ID"].astype("string").str.strip()
        if ids.isna().any() or ids.eq("").any() or ids.duplicated().any():
            checks.append(_check("Facility identifier integrity", "FAIL", "Facility IDs are blank or duplicated.", "fail"))
        else:
            checks.append(_check("Facility identifier integrity", "PASS", f"{ids.nunique()} unique facility IDs.", "pass"))
        score_columns = [
            "Integrated_Priority_Score", "Data_Quality_Priority_Score",
            "Resource_Gap_Priority_Score", "Operational_Priority_Score",
            "Supply_Cold_Chain_Priority_Score",
        ]
        score_ok = True
        for column in score_columns:
            values = pd.to_numeric(priority[column], errors="coerce")
            if values.isna().any() or not values.between(0, 100).all():
                score_ok = False
                break
        if not score_ok:
            checks.append(_check("Priority score ranges", "FAIL", "One or more scores are non-numeric or outside 0–100.", "fail"))
        else:
            components = priority[score_columns[1:]].apply(pd.to_numeric, errors="coerce")
            overall = pd.to_numeric(priority["Integrated_Priority_Score"], errors="coerce")
            if ((components.mean(axis=1) - overall).abs() > 0.01).any():
                checks.append(_check("Priority score reconciliation", "FAIL", "Integrated scores do not equal the mean of four component scores.", "fail"))
            else:
                checks.append(_check("Priority score reconciliation", "PASS", "Integrated scores reconcile to the four component scores.", "pass"))
        rank = pd.to_numeric(priority["Integrated_Priority_Rank"], errors="coerce")
        if rank.isna().any() or rank.duplicated().any() or (rank < 1).any():
            checks.append(_check("Priority rank integrity", "FAIL", "Ranks must be unique positive numeric values.", "fail"))
        else:
            checks.append(_check("Priority rank integrity", "PASS", "Ranks are unique positive numeric values.", "pass"))

    actions = action_register if action_register is not None else pd.DataFrame()
    if action_register is None:
        checks.append(_check("Corrective-action register", "WARNING", "No action register was supplied; action-level checks were not run."))
    elif actions.empty:
        checks.append(_check("Corrective-action register", "PASS", "Action register is empty; no action rows to validate.", "pass"))
    else:
        action_required = {"Record_ID", "Facility", "Month", "Status", "Due date"}
        absent = sorted(action_required - set(actions.columns))
        if absent:
            checks.append(_check("Corrective-action register", "FAIL", f"Missing columns: {absent}", "fail"))
        else:
            record_ids = actions["Record_ID"].astype("string").str.strip()
            if record_ids.isna().any() or record_ids.eq("").any() or record_ids.duplicated().any():
                checks.append(_check("Action record identifiers", "FAIL", "Record IDs are blank or duplicated.", "fail"))
            else:
                checks.append(_check("Action record identifiers", "PASS", f"{len(actions)} unique action records.", "pass"))
            allowed = {"Open", "In progress", "Resolved", "Escalated"}
            if not actions["Status"].isin(allowed).all():
                checks.append(_check("Action status values", "FAIL", "Unsupported or blank action statuses found.", "fail"))
            else:
                checks.append(_check("Action status values", "PASS", "All action statuses use the supported workflow vocabulary.", "pass"))
            months = pd.to_datetime(actions["Month"], errors="coerce")
            if months.isna().any():
                checks.append(_check("Action reporting months", "FAIL", "One or more action reporting months are invalid.", "fail"))
            else:
                checks.append(_check("Action reporting months", "PASS", "All action reporting months parse successfully.", "pass"))
            due_text = actions["Due date"].fillna("").astype(str).str.strip()
            due = pd.to_datetime(due_text.where(due_text.ne(""), pd.NA), format="%Y-%m-%d", errors="coerce")
            if (due_text.ne("") & due.isna()).any():
                checks.append(_check("Action due dates", "FAIL", "Non-empty due dates must use YYYY-MM-DD.", "fail"))
            else:
                checks.append(_check("Action due dates", "PASS", "All populated due dates use YYYY-MM-DD; blanks remain allowed.", "pass"))
            if "Facility_ID" in priority.columns and "Facility" in actions.columns:
                import re
                extracted = actions["Facility"].astype(str).str.extract(r"\[([^\[\]]+)\]\s*$", expand=False)
                known = set(priority["Facility_ID"].astype(str).str.strip())
                if extracted.isna().any() or not set(extracted.dropna().str.strip()).issubset(known):
                    checks.append(_check("Action-to-facility links", "FAIL", "Action labels are malformed or reference unknown facilities.", "fail"))
                else:
                    checks.append(_check("Action-to-facility links", "PASS", "Every action maps to a known facility ID.", "pass"))

    if output_dir is None:
        checks.append(_check("Build artifact manifest", "WARNING", "No build output directory supplied; artifact checks were not run."))
    else:
        root = Path(output_dir)
        summary_path = root / "platform_build_summary.json"
        if not summary_path.is_file():
            checks.append(_check("Build artifact manifest", "WARNING", f"Build summary not found at {summary_path}; no build artifact claims verified."))
        else:
            try:
                summary = json.loads(summary_path.read_text(encoding="utf-8"))
                manifest = summary.get("artifact_manifest", {})
                if not isinstance(manifest, dict) or not manifest:
                    checks.append(_check("Build artifact manifest", "FAIL", "Build summary has no non-empty artifact_manifest.", "fail"))
                else:
                    missing_artifacts = []
                    corrupt_artifacts = []
                    for name, item in manifest.items():
                        path = (root / item.get("path", "")).resolve()
                        if root.resolve() not in path.parents or not path.is_file() or path.stat().st_size <= 0:
                            missing_artifacts.append(name)
                            continue
                        digest = hashlib.sha256(path.read_bytes()).hexdigest()
                        if digest != item.get("sha256") or path.stat().st_size != item.get("size_bytes"):
                            corrupt_artifacts.append(name)
                    if missing_artifacts or corrupt_artifacts:
                        checks.append(_check("Build artifact manifest", "FAIL", f"Missing/empty: {missing_artifacts}; hash/size mismatches: {corrupt_artifacts}.", "fail"))
                    else:
                        checks.append(_check("Build artifact manifest", "PASS", f"All {len(manifest)} listed artifacts exist and match recorded size and SHA-256.", "pass"))
            except (OSError, ValueError, TypeError, AttributeError) as exc:
                checks.append(_check("Build artifact manifest", "FAIL", f"Build summary could not be validated: {exc}", "fail"))

    failed = sum(item["status"] == "FAIL" for item in checks)
    warnings = sum(item["status"] == "WARNING" for item in checks)
    passed = sum(item["status"] == "PASS" for item in checks)
    if failed:
        readiness = "BLOCKED"
    elif warnings:
        readiness = "CONDITIONAL"
    else:
        readiness = "DATA_CHECKS_PASS"
    return {
        "readiness": readiness,
        "passed": passed,
        "warnings": warnings,
        "failed": failed,
        "checks": pd.DataFrame(checks, columns=["check", "status", "severity", "detail"]),
        "scope": (
            "Checks cover supplied synthetic registers and any supplied local build manifest only. "
            "They do not establish clinical validity, official facility performance, deployment, "
            "Power BI refresh, notebook execution, multi-user persistence or full-suite CI success."
        ),
    }
