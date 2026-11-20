from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from reporting import (
    REQUIRED_COLUMNS, assess_dataset, build_issue_register, facility_summary,
    validate_dataset,
)

DATA_PATHS = [
    ROOT / "data" / "raw" / "synthetic_health_facility_data.csv",
    ROOT / "data" / "processed" / "health_facility_data_processed.csv",
]
st.set_page_config(
    page_title="Health Facility Data Quality Workspace",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.block-container {padding-top:1.35rem;padding-bottom:2.5rem;max-width:1550px}
[data-testid="stMetric"] {background:#f3f7fb;border:1px solid #dce5ef;padding:13px 15px;border-radius:11px}
.hero {background:linear-gradient(110deg,#eaf3fb,#f4faf7);border:1px solid #d7e5ec;border-radius:15px;padding:21px 24px;margin-bottom:15px}
.hero h1 {color:#163d58;font-size:1.9rem;margin:0 0 5px}
.hero p {color:#456276;margin:0}
.small-note {font-size:.88rem;color:#526779}
</style>
""", unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def load_demo_data() -> pd.DataFrame:
    for path in DATA_PATHS:
        if path.exists():
            return pd.read_csv(path)
    raise FileNotFoundError("No bundled dataset was found under data/raw or data/processed.")


def pct(value: float) -> str:
    return f"{value:.1%}" if pd.notna(value) else "N/A"


st.markdown(
    '<div class="hero"><h1>Health Facility Data Quality Workspace</h1>'
    '<p>Reporting assurance · Source reconciliation · Facility risk · Corrective follow-up</p></div>',
    unsafe_allow_html=True,
)
st.caption(
    "Portfolio implementation using synthetic data. Upload a CSV to assess another dataset "
    "with the documented schema; do not upload identifiable patient information."
)

with st.sidebar:
    st.title("Workspace controls")
    st.caption("Rumphi District • Synthetic demonstration")
    uploaded = st.file_uploader("Assess a reporting CSV", type=["csv"], help="Your file is processed for this app session. It is not saved to the repository.")
    use_upload = uploaded is not None
    st.divider()
    st.caption("The bundled demonstration dataset is used when no file is uploaded.")

try:
    if use_upload:
        source_df = pd.read_csv(uploaded)
        source_name = uploaded.name
    else:
        source_df = load_demo_data()
        source_name = "Bundled synthetic dataset"
except Exception as exc:
    st.error(f"Could not read the selected CSV: {exc}")
    st.stop()

validation = validate_dataset(source_df)
if not validation["valid"]:
    st.error("The selected file cannot be assessed yet.")
    if validation["missing_columns"]:
        st.write("Missing required columns:", ", ".join(validation["missing_columns"]))
    st.info("Required columns: " + ", ".join(REQUIRED_COLUMNS))
    st.stop()

if validation["warnings"]:
    with st.expander(f"Data intake checks · {len(validation['warnings'])} warning(s)", expanded=bool(use_upload)):
        for warning in validation["warnings"]:
            st.warning(warning)
        st.write({
            "Rows": validation["row_count"],
            "Duplicate key rows": validation["duplicate_rows"],
            "Invalid reporting periods": validation["invalid_months"],
            "Invalid numeric values": validation["invalid_numeric_values"],
            "Negative values": validation["negative_values"],
            "Blank dimensions": validation["blank_dimensions"],
        })

assessed = assess_dataset(source_df)
register = build_issue_register(assessed)
facility_metrics = facility_summary(assessed)

with st.sidebar:
    facilities = sorted(assessed["Facility"].dropna().astype(str).unique())
    programmes = sorted(assessed["Programme"].dropna().astype(str).unique())
    selected_facilities = st.multiselect("Facilities", facilities, default=facilities)
    selected_programmes = st.multiselect("Programme areas", programmes, default=programmes)
    valid_months = assessed["Month"].dropna()
    if not valid_months.empty:
        date_range = st.date_input(
            "Reporting period",
            value=(valid_months.min().date(), valid_months.max().date()),
        )
    else:
        date_range = ()
    issue_types = [
        "All records", "Requires follow-up", "Missing values", "Late reports",
        "Source discrepancies", "Potential outliers", "Low completeness",
    ]
    issue_filter = st.selectbox("Record status", issue_types)

filtered = register[
    register["Facility"].astype(str).isin(selected_facilities)
    & register["Programme"].astype(str).isin(selected_programmes)
].copy()
if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
    filtered = filtered[filtered["Month"].between(pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1]))]
elif isinstance(date_range, (tuple, list)) and len(date_range) == 1:
    filtered = filtered[filtered["Month"].dt.date == date_range[0]]

issue_map = {
    "Requires follow-up": "Requires_Follow_Up",
    "Missing values": "Issue_Missing_Value",
    "Late reports": "Issue_Late_Report",
    "Insufficient source data": "Issue_Insufficient_Sources",
    "Source discrepancies": "Issue_Source_Discrepancy",
    "Potential outliers": "Issue_Potential_Outlier",
    "Low completeness": "Issue_Low_Completeness",
}
if issue_filter in issue_map:
    filtered = filtered[filtered[issue_map[issue_filter]]]

if filtered.empty:
    st.warning("No records match the current filters. Adjust the selections in the sidebar.")
    st.stop()

n = len(filtered)
completeness = filtered["Calculated_Completeness"].mean()
timeliness_known = filtered["Calculated_Timeliness"].isin(["On Time", "Late"])
on_time = filtered.loc[timeliness_known, "Calculated_Timeliness"].eq("On Time").mean() if timeliness_known.any() else float("nan")
consistency_known = filtered["Consistency_Flag"].isin(["Consistent", "Review Required"])
consistency = filtered.loc[consistency_known, "Consistency_Flag"].eq("Consistent").mean() if consistency_known.any() else float("nan")
flagged = filtered["Requires_Follow_Up"].mean()

st.caption(f"Source: **{source_name}** · {n:,} records in current view · {len(register):,} assessed records")
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Reporting records", f"{n:,}")
m2.metric("Field completeness", pct(completeness))
m3.metric("On-time rate", pct(on_time))
m4.metric("Source consistency", pct(consistency))
m5.metric("Requiring follow-up", pct(flagged))

tabs = st.tabs([
    "Executive overview", "Facility risk", "Programme & trends",
    "Source reconciliation", "Corrective action register", "Data quality checks",
])

with tabs[0]:
    st.subheader("Portfolio quality position")
    c1, c2 = st.columns(2)
    issue_summary = pd.DataFrame({
        "Issue": ["Missing values", "Late reports", "Insufficient source data", "Source discrepancies", "Potential outliers", "Low completeness"],
        "Records": [
            int(filtered["Issue_Missing_Value"].sum()),
            int(filtered["Issue_Late_Report"].sum()),
            int(filtered["Issue_Insufficient_Sources"].sum()),
            int(filtered["Issue_Source_Discrepancy"].sum()),
            int(filtered["Issue_Potential_Outlier"].sum()),
            int(filtered["Issue_Low_Completeness"].sum()),
        ],
    })
    c1.plotly_chart(px.bar(issue_summary, x="Issue", y="Records", title="Issue volume in current view"), use_container_width=True)
    completeness_by_facility = filtered.groupby("Facility", as_index=False)["Calculated_Completeness"].mean()
    c2.plotly_chart(
        px.bar(completeness_by_facility.sort_values("Calculated_Completeness"),
               x="Calculated_Completeness", y="Facility", orientation="h",
               title="Field completeness by facility",
               labels={"Calculated_Completeness": "Completeness"}),
        use_container_width=True,
    )
    if filtered["Month"].notna().any():
        monthly = filtered.assign(Period=filtered["Month"].dt.to_period("M").astype(str)).groupby("Period").agg(
            Records=("Facility", "size"),
            Missing_Rate=("Issue_Missing_Value", "mean"),
            Late_Rate=("Issue_Late_Report", "mean"),
            Source_Review_Rate=("Issue_Source_Discrepancy", "mean"),
        ).reset_index()
        st.plotly_chart(
            px.line(monthly, x="Period", y=["Missing_Rate", "Late_Rate", "Source_Review_Rate"],
                    markers=True, title="Monthly quality issue rates",
                    labels={"value": "Rate", "Period": "Reporting month", "variable": "Issue"}),
            use_container_width=True,
        )
    st.info("Issue categories overlap: one reporting record can have more than one quality flag. The follow-up percentage counts distinct records.")

with tabs[1]:
    st.subheader("Facility-level risk prioritisation")
    fac = facility_metrics[facility_metrics["Facility"].astype(str).isin(selected_facilities)].copy()
    if fac.empty:
        st.info("No facility summary is available for the selected filters.")
    else:
        st.plotly_chart(
            px.bar(fac.sort_values("Risk_Score"), x="Risk_Score", y="Facility", orientation="h",
                   title="Facility risk index (0–100)", labels={"Risk_Score": "Risk index"}),
            use_container_width=True,
        )
        display = fac[[
            "Facility", "Total_Records", "Average_Completeness", "On_Time_Rate",
            "Consistency_Rate", "Late_Rate", "Source_Discrepancy_Rate",
            "Missing_Rate", "Outlier_Rate", "Risk_Score",
        ]].rename(columns={
            "Total_Records": "Records", "Average_Completeness": "Completeness",
            "On_Time_Rate": "On-time rate", "Consistency_Rate": "Consistency",
            "Late_Rate": "Late rate", "Source_Discrepancy_Rate": "Source review rate",
            "Missing_Rate": "Missing rate", "Outlier_Rate": "Outlier rate",
            "Risk_Score": "Risk index",
        })
        st.dataframe(display.style.format({
            "Completeness": "{:.1%}", "On-time rate": "{:.1%}",
            "Consistency": "{:.1%}", "Late rate": "{:.1%}",
            "Source review rate": "{:.1%}", "Missing rate": "{:.1%}",
            "Outlier rate": "{:.1%}", "Risk index": "{:.1f}",
        }), use_container_width=True, hide_index=True)
        st.caption("The risk index is a transparent, equally weighted prioritisation aid based on five rates. It is not a validated facility-performance, clinical, or funding score. Facility ranking uses all assessed rows, not only the current date/programme filters.")

with tabs[2]:
    st.subheader("Programme and indicator monitoring")
    programme_summary = filtered.groupby(["Programme", "Indicator"], as_index=False).agg(
        Records=("Facility", "size"),
        Reported=("Reported_Value", "sum"),
        Target=("Target_Value", "sum"),
        Completeness=("Calculated_Completeness", "mean"),
        Late_Rate=("Issue_Late_Report", "mean"),
        Follow_Up_Rate=("Requires_Follow_Up", "mean"),
    )
    programme_summary["Target attainment"] = programme_summary["Reported"].div(programme_summary["Target"].where(programme_summary["Target"].ne(0)))
    st.dataframe(programme_summary.style.format({
        "Completeness": "{:.1%}", "Late_Rate": "{:.1%}",
        "Follow_Up_Rate": "{:.1%}", "Target attainment": "{:.1%}",
    }), use_container_width=True, hide_index=True)
    if filtered["Month"].notna().any():
        trend = filtered.groupby(["Month", "Programme"], as_index=False).agg(
            Reported=("Reported_Value", "sum"), Target=("Target_Value", "sum")
        )
        st.plotly_chart(
            px.line(trend, x="Month", y="Reported", color="Programme", markers=True,
                    title="Reported volume by programme over time"),
            use_container_width=True,
        )
    st.caption("Target attainment is an aggregate reported-value-to-target ratio. It is only interpretable where the indicator's target definition supports summation and comparison.")

with tabs[3]:
    st.subheader("Three-source reconciliation")
    source_columns = ["Paper_Value", "EMR_Value", "DHIS2_Value"]
    source_long = filtered.melt(
        id_vars=["Facility", "Programme", "Indicator", "Month"],
        value_vars=source_columns, var_name="Reporting source", value_name="Reported value",
    )
    st.plotly_chart(
        px.box(source_long, x="Reporting source", y="Reported value", color="Reporting source",
               title="Distribution of source values"),
        use_container_width=True,
    )
    discrepancy = filtered.groupby("Facility", as_index=False).agg(
        Mean_Absolute_Difference=("Source_Discrepancy_Abs", "mean"),
        Review_Rate=("Issue_Source_Discrepancy", "mean"),
    ).sort_values("Review_Rate", ascending=False)
    st.dataframe(discrepancy.style.format({"Mean_Absolute_Difference": "{:.1f}", "Review_Rate": "{:.1%}"}),
                 use_container_width=True, hide_index=True)
    st.info(
        "Production rule: for positive source minima, a review is raised only when relative "
        "discrepancy exceeds 20% AND absolute discrepancy exceeds 5 units. If the minimum "
        "source value is zero, the absolute 5-unit tolerance applies. The 10% relative-only "
        "baseline is diagnostic, not the production flag. A flag means verify the source documents; "
        "it does not prove which system is correct."
    )

with tabs[4]:
    st.subheader("Corrective action register")
    st.write("Assign an owner, record the next action, and track the status of each flagged record.")
    flagged_rows = filtered[filtered["Requires_Follow_Up"]].copy()
    if flagged_rows.empty:
        st.success("No flagged records in the current selection.")
    else:
        key_cols = ["Facility", "Month", "Programme", "Indicator"]
        flagged_rows["Record_ID"] = flagged_rows[key_cols].astype(str).agg("|".join, axis=1)
        flagged_rows["Record_ID"] += "|" + flagged_rows.index.astype(str)
        if "action_register" not in st.session_state:
            st.session_state.action_register = {}
        action_rows = []
        for _, row in flagged_rows.iterrows():
            rid = row["Record_ID"]
            saved = st.session_state.action_register.get(rid, {})
            action_rows.append({
                "Record_ID": rid,
                "Facility": row["Facility"],
                "Month": row["Month"].date().isoformat() if pd.notna(row["Month"]) else "",
                "Programme": row["Programme"],
                "Indicator": row["Indicator"],
                "Primary issue": row["Primary_Issue"],
                "Issue count": int(row["Issue_Count"]),
                "Status": saved.get("Status", "Open"),
                "Assigned owner": saved.get("Assigned owner", ""),
                "Corrective action / notes": saved.get("Corrective action / notes", ""),
            })
        action_df = pd.DataFrame(action_rows)
        edited = st.data_editor(
            action_df,
            use_container_width=True,
            hide_index=True,
            disabled=["Record_ID", "Facility", "Month", "Programme", "Indicator", "Primary issue", "Issue count"],
            column_config={
                "Status": st.column_config.SelectboxColumn("Status", options=["Open", "In progress", "Resolved", "Escalated"], required=True),
                "Assigned owner": st.column_config.TextColumn("Assigned owner"),
                "Corrective action / notes": st.column_config.TextColumn("Corrective action / notes", width="large"),
            },
            key="action_editor",
        )
        st.session_state.action_register = {
            row["Record_ID"]: {
                "Status": row["Status"],
                "Assigned owner": row["Assigned owner"],
                "Corrective action / notes": row["Corrective action / notes"],
            }
            for _, row in edited.iterrows()
        }
        a, b, c = st.columns(3)
        a.metric("Open", int((edited["Status"] == "Open").sum()))
        b.metric("In progress", int((edited["Status"] == "In progress").sum()))
        c.metric("Resolved", int((edited["Status"] == "Resolved").sum()))
        st.download_button(
            "Download corrective action register",
            data=edited.to_csv(index=False).encode("utf-8"),
            file_name="health_facility_corrective_action_register.csv",
            mime="text/csv",
        )
        st.caption("Action assignments are held in this browser session only. Download the register to preserve and share the work; persistent multi-user storage is not configured.")

with tabs[5]:
    st.subheader("Data intake and quality assurance")
    st.write("These checks describe structural and value issues found in the selected source file.")
    q1, q2, q3, q4 = st.columns(4)
    q1.metric("Rows loaded", f"{validation['row_count']:,}")
    q2.metric("Duplicate key rows", f"{validation['duplicate_rows']:,}")
    q3.metric("Invalid dates", f"{validation['invalid_months']:,}")
    q4.metric("Columns required", f"{len(REQUIRED_COLUMNS)}")
    numeric_issues = pd.DataFrame([
        {"Field": field, "Non-numeric values": count, "Negative values": validation["negative_values"][field]}
        for field, count in validation["invalid_numeric_values"].items()
    ])
    st.dataframe(numeric_issues, use_container_width=True, hide_index=True)
    st.download_button(
        "Download assessed records (CSV)",
        data=filtered.to_csv(index=False).encode("utf-8"),
        file_name="health_facility_assessed_records.csv",
        mime="text/csv",
    )
    st.download_button(
        "Download full issue register (CSV)",
        data=register.to_csv(index=False).encode("utf-8"),
        file_name="health_facility_issue_register.csv",
        mime="text/csv",
    )
    with st.expander("Required CSV schema"):
        st.code(", ".join(REQUIRED_COLUMNS))
        st.write("Month should be a parseable date. Numeric measures should contain numbers. Blank source values are allowed and will affect completeness/reconciliation.")

st.divider()
st.caption(
    "Synthetic portfolio demonstration only. Do not use for clinical decisions, official facility "
    "performance assessment, patient-level data processing, or operational reporting without "
    "local validation, governance approval, secure storage, and an agreed data-quality framework."
)
