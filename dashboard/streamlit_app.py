from __future__ import annotations

from pathlib import Path
import os
import sys

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from action_store import ActionRegisterStore, build_action_record_id
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
        "All records", "Requires follow-up", "Missing values", "Late reports", "Insufficient source data",
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
    "Expanded platform",
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
    st.write("Assign accountability, document root causes, track due dates and retain a field-level change history.")

    database_path = os.getenv(
        "HEALTH_DATA_ACTION_DB",
        str(ROOT / "data" / "warehouse" / "corrective_actions.sqlite"),
    )
    try:
        action_store = ActionRegisterStore(database_path)
        persisted_actions = action_store.get_actions()
    except Exception as exc:
        action_store = None
        persisted_actions = st.session_state.get("action_register", {})
        st.warning(
            f"SQLite persistence is unavailable: {exc}. Changes will remain in this browser session only."
        )

    flagged_rows = filtered[filtered["Requires_Follow_Up"]].copy()
    if not flagged_rows.empty:
        record_ids = [
            build_action_record_id(
                source_name, row["Facility"], row["Month"],
                row["Programme"], row["Indicator"],
            )
            for _, row in flagged_rows.iterrows()
        ]
        flagged_rows["Record_ID"] = record_ids

        action_rows = []
        for _, row in flagged_rows.iterrows():
            rid = row["Record_ID"]
            saved = persisted_actions.get(rid, {})
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
                "Root cause": saved.get("Root cause", ""),
                "Corrective action / notes": saved.get("Corrective action / notes", ""),
                "Due date": saved.get("Due date", ""),
            })
        action_df = pd.DataFrame(action_rows)
        edited = st.data_editor(
            action_df,
            use_container_width=True,
            hide_index=True,
            disabled=[
                "Record_ID", "Facility", "Month", "Programme", "Indicator",
                "Primary issue", "Issue count",
            ],
            column_config={
                "Status": st.column_config.SelectboxColumn(
                    "Status",
                    options=["Open", "In progress", "Resolved", "Escalated"],
                    required=True,
                ),
                "Assigned owner": st.column_config.TextColumn("Assigned owner"),
                "Root cause": st.column_config.TextColumn("Root cause", width="medium"),
                "Corrective action / notes": st.column_config.TextColumn(
                    "Corrective action / notes", width="large"
                ),
                "Due date": st.column_config.TextColumn("Due date (YYYY-MM-DD)"),
            },
            key="action_editor",
        )
        if action_store is not None:
            try:
                save_result = action_store.upsert_actions(edited.to_dict(orient="records"))
                st.caption(
                    f"SQLite save: {save_result['inserted']:,} new · "
                    f"{save_result['updated']:,} updated · {save_result['unchanged']:,} unchanged"
                )
                persisted_actions = action_store.get_actions()
            except Exception as exc:
                st.warning(f"Could not save action changes: {exc}")
        else:
            st.session_state["action_register"] = {
                row["Record_ID"]: {
                    "Status": row["Status"],
                    "Assigned owner": row["Assigned owner"],
                    "Root cause": row["Root cause"],
                    "Corrective action / notes": row["Corrective action / notes"],
                    "Due date": row["Due date"],
                }
                for _, row in edited.iterrows()
            }
            persisted_actions = st.session_state["action_register"]
    else:
        st.info("There are no new follow-up records in the current filter selection. Previously saved actions remain available below.")

    if persisted_actions:
        all_action_rows = [
            {"Record_ID": record_id, **fields}
            for record_id, fields in persisted_actions.items()
        ]
        all_actions_df = pd.DataFrame(all_action_rows)
        today = pd.Timestamp.now().normalize()
        due_dates = pd.to_datetime(all_actions_df["Due date"], errors="coerce")
        unresolved = ~all_actions_df["Status"].eq("Resolved")
        overdue = unresolved & due_dates.notna() & due_dates.lt(today)

        st.markdown("**Action portfolio**")
        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric("Total actions", f"{len(all_actions_df):,}")
        k2.metric("Open", int(all_actions_df["Status"].eq("Open").sum()))
        k3.metric("In progress", int(all_actions_df["Status"].eq("In progress").sum()))
        k4.metric("Resolved", int(all_actions_df["Status"].eq("Resolved").sum()))
        k5.metric("Overdue", int(overdue.sum()))

        st.dataframe(
            all_actions_df.sort_values(
                ["Status", "Due date"], na_position="last"
            ),
            use_container_width=True,
            hide_index=True,
        )
        st.download_button(
            "Download complete corrective action register",
            data=all_actions_df.to_csv(index=False).encode("utf-8"),
            file_name="health_facility_corrective_action_register.csv",
            mime="text/csv",
            key="download_complete_action_register",
        )

        if action_store is not None:
            st.caption(
                f"Local SQLite database: {database_path}. Actions and field-level history persist "
                "on a persistent local filesystem. Streamlit Community Cloud storage is ephemeral "
                "and is not a shared multi-user database; export regular backups."
            )
            with st.expander("Action audit history"):
                selected_history_id = st.selectbox(
                    "Record to inspect",
                    list(persisted_actions.keys()),
                    key="action_history_record",
                )
                history = action_store.history(selected_history_id)
                if history.empty:
                    st.caption("No field changes have been recorded yet.")
                else:
                    st.dataframe(history, use_container_width=True, hide_index=True)
        else:
            st.caption("Action assignments are session-scoped because SQLite is unavailable.")
    else:
        st.info("The action register is currently empty. Flagged records will appear here when they require follow-up.")

with tabs[5]:
    st.subheader("Data intake and quality assurance")
    st.write("These checks describe structural and value issues found in the selected source file.")
    template_columns = REQUIRED_COLUMNS + ["Submission_Date", "Deadline_Date"]
    template = pd.DataFrame(columns=template_columns)
    st.download_button(
        "Download CSV upload template",
        data=template.to_csv(index=False).encode("utf-8"),
        file_name="health_facility_reporting_template.csv",
        mime="text/csv",
    )
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


with tabs[6]:
    st.subheader("Expanded health data intelligence platform")
    st.write(
        "Analyse the staged multi-year synthetic reporting fact using peer-group "
        "anomaly detection, longitudinal monitoring and (when available) controlled-label evaluation."
    )
    st.info(
        "The expanded cohort is synthetic: 120 illustrative facilities, 60 monthly periods, "
        "8 programme areas and 40 indicators (288,000 expected records). District labels are "
        "Malawi-oriented; no real facility or Ministry of Health performance is represented."
    )
    st.markdown("**Upload a staged reporting CSV** generated by the repository pipeline.")
    platform_file = st.file_uploader(
        "Staged facility reporting data", type=["csv"], key="platform_staged_upload",
        help="Expected to contain Facility_ID, Facility, District, Month, Programme, Indicator, Reported_Value, Target_Value and ETL Quality_* flags."
    )
    platform_required = [
        "Facility_ID", "Facility", "District", "Month", "Programme", "Indicator",
        "Reported_Value", "Target_Value", "Quality_Missing_Reported_Value",
        "Quality_Source_Discrepancy", "Quality_Late_Submission",
    ]
    truth_required = [
        "Ground_Truth_Missing", "Ground_Truth_Source_Discrepancy",
        "Ground_Truth_Outlier", "Ground_Truth_Late",
    ]
    if platform_file is None:
        st.markdown("**Generate and stage the expanded cohort locally**")
        st.code(
            "python src/scale_data_generator.py\n"
            "python src/etl_pipeline.py\n"
            "python src/quality_analytics.py\n"
            "python src/statistical_monitoring.py",
            language="bash",
        )
        st.caption(
            "The 288,000-row generated CSV is intentionally not committed to GitHub. "
            "Generate it locally, then upload data/warehouse/staged/facility_reporting_staged.csv here."
        )
    else:
        st.caption(f"Selected file: {platform_file.name} · {platform_file.size / (1024 * 1024):.1f} MB")
        if st.button("Analyse expanded reporting platform", type="primary", key="run_platform_analysis"):
            try:
                platform_data = pd.read_csv(platform_file)
                missing_platform = sorted(set(platform_required) - set(platform_data.columns))
                if missing_platform:
                    st.error("This is not a staged platform extract. Missing columns: " + ", ".join(missing_platform))
                else:
                    from quality_analytics import add_operational_predictions, build_operational_profiles, build_district_profiles, evaluate_detectors
                    from statistical_monitoring import detect_peer_anomalies, build_monthly_control_chart

                    with st.spinner("Running peer anomaly detection and longitudinal monitoring..."):
                        predicted = add_operational_predictions(platform_data)
                        monthly, facility_profile, programme_profile = build_operational_profiles(platform_data)
                        district_profile, district_monthly = build_district_profiles(platform_data)
                        peer = detect_peer_anomalies(platform_data)
                        control = build_monthly_control_chart(platform_data)
                        metrics = None
                        if set(truth_required).issubset(platform_data.columns):
                            metrics = evaluate_detectors(platform_data)
                        issue_rate = float(predicted["Operational_Any_Detected_Issue"].mean()) if len(predicted) else float("nan")
                        result = {
                            "records": len(platform_data),
                            "facilities": int(platform_data["Facility_ID"].nunique()),
                            "districts": int(platform_data["District"].nunique()),
                            "months": int(pd.to_datetime(platform_data["Month"], errors="coerce").nunique()),
                            "programmes": int(platform_data["Programme"].nunique()),
                            "indicators": int(platform_data["Indicator"].nunique()),
                            "issue_rate": issue_rate,
                            "peer_anomaly_count": int(peer["Statistical_Anomaly"].sum()),
                            "peer_anomalies": peer.loc[peer["Statistical_Anomaly"], [
                                "Facility_ID", "Facility", "District", "Month", "Programme",
                                "Indicator", "Reported_Value", "Statistical_Anomaly_Score",
                                "Statistical_Method", "Peer_Group_Size",
                            ]].copy(),
                            "monthly": monthly,
                            "facility": facility_profile,
                            "programme": programme_profile,
                            "district": district_profile,
                            "district_monthly": district_monthly,
                            "control": control,
                            "metrics": metrics,
                            "synthetic_truth_available": metrics is not None,
                        }
                        st.session_state["expanded_platform_result"] = result
                    st.success("Expanded platform analysis completed for this session.")
            except Exception as exc:
                st.error(f"Platform analysis could not be completed: {exc}")

    result = st.session_state.get("expanded_platform_result")
    if result:
        st.divider()
        st.caption("Analysis result is held in this browser session. Upload and rerun to analyse a different extract.")
        p1, p2, p3, p4, p5 = st.columns(5)
        p1.metric("Staged records", f"{result['records']:,}")
        p2.metric("Facilities", f"{result['facilities']:,}")
        p3.metric("Reporting months", f"{result['months']:,}")
        p4.metric("Detected issue rate", pct(result["issue_rate"]))
        p5.metric("Peer anomalies", f"{result['peer_anomaly_count']:,}")

        left, right = st.columns(2)
        monthly = result["monthly"].copy()
        if not monthly.empty:
            monthly["Month"] = pd.to_datetime(monthly["Month"])
            left.plotly_chart(
                px.line(monthly, x="Month", y="detected_issue_rate_pct", markers=True,
                        title="Monthly detected issue rate", labels={"detected_issue_rate_pct": "Issue rate (%)"}),
                use_container_width=True,
            )
        facility_profile = result["facility"].head(15).sort_values("detected_issue_rate_pct")
        right.plotly_chart(
            px.bar(facility_profile, x="detected_issue_rate_pct", y="Facility",
                   orientation="h", title="Highest facility follow-up rates",
                   labels={"detected_issue_rate_pct": "Detected issue rate (%)"}),
            use_container_width=True,
        )
        st.markdown("**District performance and data-quality intelligence**")
        st.caption(
            "District labels are geographic context for this synthetic portfolio. "
            "These generated metrics do not represent actual district or Ministry of Health performance."
        )
        district_profile = result["district"].copy()
        district_monthly = result["district_monthly"].copy()
        if not district_profile.empty:
            district_left, district_right = st.columns(2)
            district_left.plotly_chart(
                px.bar(
                    district_profile.sort_values("detected_issue_rate_pct"),
                    x="detected_issue_rate_pct",
                    y="District",
                    orientation="h",
                    title="Detected issue rate by district",
                    labels={"detected_issue_rate_pct": "Detected issue rate (%)"},
                ),
                use_container_width=True,
            )
            district_right.plotly_chart(
                px.bar(
                    district_profile.sort_values("records"),
                    x="records",
                    y="District",
                    orientation="h",
                    title="Reporting volume by district",
                    labels={"records": "Facility-month-indicator records"},
                ),
                use_container_width=True,
            )
            st.dataframe(district_profile, use_container_width=True, hide_index=True)
            st.download_button(
                "Download district quality benchmark",
                data=district_profile.to_csv(index=False).encode("utf-8"),
                file_name="district_quality_benchmark.csv",
                mime="text/csv",
                key="download_district_quality_benchmark",
            )
        if not district_monthly.empty:
            st.plotly_chart(
                px.line(
                    district_monthly,
                    x="Month",
                    y="detected_issue_rate_pct",
                    color="District",
                    markers=True,
                    title="Monthly quality issue trends by district",
                    labels={"detected_issue_rate_pct": "Detected issue rate (%)"},
                ),
                use_container_width=True,
            )
            st.download_button(
                "Download district monthly trends",
                data=district_monthly.to_csv(index=False).encode("utf-8"),
                file_name="district_monthly_quality_trends.csv",
                mime="text/csv",
                key="download_district_monthly_trends",
            )

        st.markdown("**Programme and indicator quality profile**")
        st.dataframe(result["programme"], use_container_width=True, hide_index=True)
        st.markdown("**Statistical peer anomalies**")
        if result["peer_anomalies"].empty:
            st.success("No peer-group anomalies were detected with the configured minimum sample and thresholds.")
        else:
            st.dataframe(result["peer_anomalies"].head(500), use_container_width=True, hide_index=True)
            st.download_button(
                "Download all peer anomaly records",
                data=result["peer_anomalies"].to_csv(index=False).encode("utf-8"),
                file_name="statistical_peer_anomalies.csv", mime="text/csv",
            )
        st.markdown("**Monthly issue-rate monitoring**")
        st.dataframe(result["control"], use_container_width=True, hide_index=True)
        st.download_button(
            "Download monthly monitoring output",
            data=result["control"].to_csv(index=False).encode("utf-8"),
            file_name="monthly_issue_control_chart.csv", mime="text/csv",
        )
        if result["synthetic_truth_available"]:
            st.markdown("**Detector evaluation against synthetic ground truth**")
            st.dataframe(result["metrics"].style.format({
                "precision": "{:.1%}", "recall": "{:.1%}", "f1": "{:.1%}",
                "specificity": "{:.1%}", "false_positive_rate": "{:.1%}", "accuracy": "{:.1%}",
            }), use_container_width=True, hide_index=True)
            st.caption("These metrics evaluate recovery of controlled synthetic defects only. They are not estimates of real-world detector performance.")
        else:
            st.info("No Ground_Truth_* evaluation labels were found. Operational monitoring is available, but detector precision/recall are intentionally not calculated.")
        st.caption("MAD/IQR signals are prompts for verification, not proof of errors. Monthly three-sigma limits use the full observed period retrospectively and are not prospective alert thresholds.")
        if st.button("Clear expanded platform results", key="clear_platform_results"):
            st.session_state.pop("expanded_platform_result", None)
            st.rerun()
