"""Build stable corrective-action records from integrated facility priorities."""
from __future__ import annotations

import pandas as pd

from action_store import build_action_record_id


REQUIRED_PRIORITY_COLUMNS = {
    "Facility_ID", "Facility_Name", "District", "Priority_Band",
    "Integrated_Priority_Rank", "Integrated_Priority_Score", "Review_Domains",
}


def build_priority_action_rows(
    priority_register: pd.DataFrame,
    latest_month,
    persisted_actions: dict[str, dict] | None = None,
    source_name: str = "expanded-platform-integrated-priority",
) -> pd.DataFrame:
    """Create one stable action row per facility without overwriting saved work."""
    missing = sorted(REQUIRED_PRIORITY_COLUMNS - set(priority_register.columns))
    if missing:
        raise ValueError(f"Priority register is missing columns: {missing}")
    if priority_register.empty:
        return pd.DataFrame(columns=[
            "Record_ID", "Facility", "Month", "Programme", "Indicator",
            "Primary issue", "Issue count", "Status", "Assigned owner",
            "Root cause", "Corrective action / notes", "Due date",
        ])
    data = priority_register.copy()
    for column in ["Facility_ID", "Facility_Name", "District", "Priority_Band"]:
        if data[column].isna().any():
            raise ValueError(f"Priority register contains missing {column}")
        data[column] = data[column].astype(str).str.strip()
        if data[column].eq("").any():
            raise ValueError(f"Priority register contains blank {column}")
    if data["Facility_ID"].duplicated().any():
        raise ValueError("Priority register contains duplicate facility identifiers")
    if data["Review_Domains"].isna().any():
        raise ValueError("Priority register contains missing review domains")
    if not data["Priority_Band"].isin(
        ["High review", "Focused review", "Routine review"]
    ).all():
        raise ValueError("Priority register contains an unsupported priority band")
    scores = pd.to_numeric(data["Integrated_Priority_Score"], errors="coerce")
    if scores.isna().any() or not scores.between(0, 100).all():
        raise ValueError("Integrated priority scores must be finite values between 0 and 100")
    ranks = pd.to_numeric(data["Integrated_Priority_Rank"], errors="coerce")
    if (ranks.isna().any() or ranks.lt(1).any() or ranks.mod(1).ne(0).any()
            or ranks.duplicated().any()):
        raise ValueError("Integrated priority ranks must be unique positive integers")
    month = pd.to_datetime(latest_month, errors="coerce")
    if pd.isna(month) or month.tzinfo is not None:
        raise ValueError("Latest simulated month must be a valid timezone-naive date")
    month_value = month.to_period("M").to_timestamp().strftime("%Y-%m-%d")
    saved_actions = persisted_actions or {}
    rows = []
    for (_, row), score, rank in zip(data.iterrows(), scores, ranks):
        record_id = build_action_record_id(
            source_name, row["Facility_ID"], month_value,
            "Integrated facility review", "Cross-domain priority review",
        )
        domains = str(row["Review_Domains"]).strip()
        domain_count = 0 if domains in {"", "none", "nan"} else len(
            [item for item in domains.split(";") if item.strip()]
        )
        saved = saved_actions.get(record_id, {})
        rows.append({
            "Record_ID": record_id,
            "Facility": f'{row["Facility_Name"]} ({row["District"]}) [{row["Facility_ID"]}]',
            "Month": month_value,
            "Programme": "Integrated facility review",
            "Indicator": "Cross-domain priority review",
            "Primary issue": (
                f'{row["Priority_Band"]} · score {float(score):.2f}/100 · '
                f'rank {int(rank)} · domains: {domains or "none"}'
            ),
            "Issue count": int(domain_count),
            "Status": saved.get("Status", "Open"),
            "Assigned owner": saved.get("Assigned owner", ""),
            "Root cause": saved.get("Root cause", ""),
            "Corrective action / notes": saved.get("Corrective action / notes", ""),
            "Due date": saved.get("Due date", ""),
        })
    return pd.DataFrame(rows)
