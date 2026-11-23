from __future__ import annotations

from pathlib import Path
import io
import json
import os
import sys
import zipfile

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from action_store import ActionRegisterStore, build_action_record_id
from target_attainment import build_target_attainment_profiles
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
        due_text = edited["Due date"].fillna("").astype(str).str.strip()
        parsed_due = pd.to_datetime(due_text.where(due_text.ne(""), pd.NA), format="%Y-%m-%d", errors="coerce")
        invalid_due = due_text.ne("") & parsed_due.isna()
        if invalid_due.any():
            st.error(
                "Corrective action due dates must use YYYY-MM-DD. "
                f"Invalid entries: {int(invalid_due.sum())}. No changes were saved."
            )
        elif action_store is not None:
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
        resource_pool_input = st.number_input("Illustrative resource pool (abstract units)", min_value=0, max_value=10000, value=120, step=10, help="Scenario input only; units are not staff headcounts or a monetary budget.")
        supply_budget_input = st.number_input("Commodity replenishment budget (abstract credits)", min_value=0, max_value=10000000, value=50000, step=1000, help="Synthetic budget credits only; not MWK or an approved procurement allocation.")
        if st.button("Analyse expanded reporting platform", type="primary", key="run_platform_analysis"):
            try:
                platform_data = pd.read_csv(platform_file)
                missing_platform = sorted(set(platform_required) - set(platform_data.columns))
                if missing_platform:
                    st.error("This is not a staged platform extract. Missing columns: " + ", ".join(missing_platform))
                else:
                    from quality_analytics import add_operational_predictions, build_operational_profiles, build_district_profiles, evaluate_detectors
                    from statistical_monitoring import detect_peer_anomalies, build_monthly_control_chart
                    from resource_planning import build_resource_planning_profiles
                    from supply_chain_planning import build_supply_chain_profiles
                    from cold_chain_planning import build_cold_chain_profiles
                    from equipment_maintenance import build_equipment_maintenance_profiles

                    with st.spinner("Running quality, statistical, resource and commodity supply-chain analytics..."):
                        predicted = add_operational_predictions(platform_data)
                        monthly, facility_profile, programme_profile = build_operational_profiles(platform_data)
                        district_profile, district_monthly = build_district_profiles(platform_data)
                        attainment = build_target_attainment_profiles(platform_data)
                        peer = detect_peer_anomalies(platform_data)
                        control = build_monthly_control_chart(platform_data)
                        resource_columns = ["Facility_ID", "Facility", "District", "Facility_Type", "Urban_Rural", "Catchment_Population"]
                        resource_facilities = platform_data[resource_columns].drop_duplicates("Facility_ID").rename(columns={"Facility": "Facility_Name"})
                        resource = build_resource_planning_profiles(resource_facilities, resource_pool=int(resource_pool_input))
                        supply = build_supply_chain_profiles(
                            resource_facilities, periods=24, start_month="2025-01-01", seed=42,
                            budget_credits=int(supply_budget_input),
                        )
                        cold_chain = build_cold_chain_profiles(
                            resource_facilities, periods=24, start_month="2025-01-01", seed=42,
                        )
                        equipment = build_equipment_maintenance_profiles(
                            resource_facilities, periods=24, start_month="2025-01-01", seed=42,
                        )
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
                            "attainment": attainment,
                            "control": control,
                            "resource": resource,
                            "supply": supply,
                            "cold_chain": cold_chain,
                            "equipment": equipment,
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

        # Package the derived outputs into one portable management/review bundle.
        export_buffer = io.BytesIO()
        facility_attainment_summary = result["attainment"]["facility_indicator"]
        valid_attainment_summary = facility_attainment_summary.dropna(subset=["attainment_pct"])
        export_summary = {
            "synthetic_data": True,
            "staged_records": int(result["records"]),
            "facilities": int(result["facilities"]),
            "districts": int(result["districts"]),
            "reporting_months": int(result["months"]),
            "programme_areas": int(result["programmes"]),
            "indicators": int(result["indicators"]),
            "detected_issue_rate_pct": (
                round(float(result["issue_rate"]) * 100, 2)
                if pd.notna(result["issue_rate"]) else None
            ),
            "peer_anomaly_records": int(result["peer_anomaly_count"]),
            "commodity_stockout_facility_item_pairs": int(result["supply"]["replenishment_plan"]["Recent_Stockout_Days"].gt(0).sum()),
            "commodity_replenishment_requested_units": int(result["supply"]["replenishment_plan"]["Requested_Replenishment_Units"].sum()),
            "commodity_replenishment_allocated_units": int(result["supply"]["replenishment_plan"]["Allocated_Replenishment_Units"].sum()),
            "commodity_replenishment_budget_credits": int(result["supply"]["scenario_summary"]["budget_credits"].iloc[0]),
            "commodity_supply_chain_assumptions": result["supply"]["assumptions"]["limitations"],
            "commodity_supply_chain_interpretation": "All stock, demand, receipts, stockouts and costs are synthetic. Budget credits are not MWK; the commodity list is illustrative and the replenishment worklist is not an order.",
            "cold_chain_high_risk_pairs_latest": int(result["cold_chain"]["expiry_risk_summary"].loc[result["cold_chain"]["expiry_risk_summary"]["Month"].eq(result["cold_chain"]["expiry_risk_summary"]["Month"].max()), "Risk_Band"].eq("High").sum()),
            "cold_chain_temperature_excursion_facility_months": int(result["cold_chain"]["temperature_monitoring"]["Temperature_Excursion_Flag"].sum()),
            "cold_chain_near_expiry_90_day_units_latest": int(result["cold_chain"]["expiry_risk_summary"].loc[result["cold_chain"]["expiry_risk_summary"]["Month"].eq(result["cold_chain"]["expiry_risk_summary"]["Month"].max()), "Near_Expiry_90_Day_Units"].sum()),
            "cold_chain_expired_units": int(result["cold_chain"]["expiry_risk_summary"]["Expired_Units"].sum()),
            "cold_chain_assumptions": result["cold_chain"]["assumptions"]["limitations"],
            "equipment_asset_count": int(len(result["equipment"]["asset_register"])),
            "equipment_high_risk_assets_latest": int(result["equipment"]["latest_asset_status"]["Risk_Band"].eq("High").sum()),
            "equipment_mean_operational_uptime_pct_latest": round(float(result["equipment"]["latest_asset_status"]["Operational_Uptime_Pct"].mean()), 2),
            "equipment_open_work_orders_latest": int(result["equipment"]["maintenance_work_orders"].loc[result["equipment"]["maintenance_work_orders"]["Month"].eq(result["equipment"]["maintenance_work_orders"]["Month"].max()), "Status"].ne("Closed").sum()) if not result["equipment"]["maintenance_work_orders"].empty else 0,
            "equipment_assumptions": result["equipment"]["assumptions"]["limitations"],
            "facility_indicator_combinations_with_valid_targets": int(len(valid_attainment_summary)),
            "facility_indicator_combinations_below_80_pct": int(valid_attainment_summary["attainment_pct"].lt(80).sum()),
            "facility_indicator_combinations_at_or_above_100_pct": int(valid_attainment_summary["attainment_pct"].ge(100).sum()),
            "synthetic_ground_truth_evaluation_available": bool(result["synthetic_truth_available"]),
            "ground_truth_scope": (
                "Detector metrics evaluate controlled synthetic defects only."
                if result["synthetic_truth_available"] else
                "No ground-truth evaluation was performed."
            ),
            "interpretation": (
                "District and facility metrics are synthetic portfolio demonstrations, "
                "not actual Malawi Ministry of Health performance. Statistical signals "
                "are review prompts, not proof of reporting error or clinical risk."
            ),
        }
        export_tables = {
            "monthly_quality_trends.csv": result["monthly"],
            "facility_quality_benchmark.csv": result["facility"],
            "programme_indicator_quality_profile.csv": result["programme"],
            "district_quality_profile.csv": result["district"],
            "district_monthly_quality_trends.csv": result["district_monthly"],
            "statistical_peer_anomalies.csv": result["peer_anomalies"],
            "monthly_issue_control_chart.csv": result["control"],
            "facility_indicator_target_attainment.csv": result["attainment"]["facility_indicator"],
            "district_indicator_target_attainment.csv": result["attainment"]["district_indicator"],
            "programme_indicator_target_attainment.csv": result["attainment"]["programme_indicator"],
            "monthly_indicator_target_attainment.csv": result["attainment"]["monthly_indicator"],
            "facility_resource_capacity.csv": result["resource"]["facility_capacity"],
            "resource_allocation_scenarios.csv": result["resource"]["scenario_allocations"],
            "resource_allocation_scenario_summary.csv": result["resource"]["scenario_summary"],
            "commodity_catalog.csv": result["supply"]["commodity_catalog"],
            "facility_commodity_stock_ledger.csv": result["supply"]["inventory_ledger"],
            "commodity_replenishment_plan.csv": result["supply"]["replenishment_plan"],
            "commodity_replenishment_summary.csv": result["supply"]["scenario_summary"],
            "cold_chain_catalog.csv": result["cold_chain"]["cold_chain_catalog"],
            "facility_cold_chain_temperature_monitoring.csv": result["cold_chain"]["temperature_monitoring"],
            "facility_commodity_batch_ledger.csv": result["cold_chain"]["batch_ledger"],
            "cold_chain_expiry_risk_summary.csv": result["cold_chain"]["expiry_risk_summary"],
            "equipment_catalog.csv": result["equipment"]["equipment_catalog"],
            "facility_equipment_asset_register.csv": result["equipment"]["asset_register"],
            "equipment_asset_monthly_performance.csv": result["equipment"]["asset_monthly_performance"],
            "facility_equipment_monthly_summary.csv": result["equipment"]["facility_monthly_summary"],
            "equipment_maintenance_work_orders.csv": result["equipment"]["maintenance_work_orders"],
            "equipment_latest_asset_risk_status.csv": result["equipment"]["latest_asset_status"],
        }
        if result["metrics"] is not None:
            export_tables["synthetic_detector_evaluation_metrics.csv"] = result["metrics"]
        with zipfile.ZipFile(export_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("management_summary.json", json.dumps(export_summary, indent=2))
            for filename, frame in export_tables.items():
                archive.writestr(filename, frame.to_csv(index=False))
        st.download_button(
            "Download complete expanded analysis pack (ZIP)",
            data=export_buffer.getvalue(),
            file_name="malawi_health_facility_data_intelligence_analysis.zip",
            mime="application/zip",
            key="download_expanded_analysis_pack",
        )
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

        st.markdown("**Target attainment and service-performance intelligence**")
        st.caption(
            "Attainment compares pooled reported values with pooled targets for the same programme and indicator. "
            "It is not population coverage, unique people served, or an official performance measure. "
            "The 80% review band is an illustrative portfolio threshold."
        )
        attainment = result["attainment"]
        facility_attainment = attainment["facility_indicator"]
        district_attainment = attainment["district_indicator"]
        monthly_attainment = attainment["monthly_indicator"]
        valid_facility_attainment = facility_attainment.dropna(subset=["attainment_pct"])
        if not valid_facility_attainment.empty:
            a1, a2, a3 = st.columns(3)
            a1.metric("Facility-indicator combinations", f"{len(valid_facility_attainment):,}")
            a2.metric("Below 80% of target", int(valid_facility_attainment["attainment_pct"].lt(80).sum()))
            a3.metric("At or above target", int(valid_facility_attainment["attainment_pct"].ge(100).sum()))
            under_target = valid_facility_attainment.sort_values("attainment_pct").head(20)
            st.plotly_chart(
                px.bar(
                    under_target.sort_values("attainment_pct"),
                    x="attainment_pct", y="Facility", color="Indicator", orientation="h",
                    title="Lowest facility-level indicator attainment",
                    labels={"attainment_pct": "Reported-to-target attainment (%)"},
                    hover_data=["District", "Programme", "Indicator", "valid_attainment_records"],
                ),
                use_container_width=True,
            )
            st.dataframe(under_target, use_container_width=True, hide_index=True)
            st.download_button(
                "Download facility-indicator target attainment",
                data=facility_attainment.to_csv(index=False).encode("utf-8"),
                file_name="facility_indicator_target_attainment.csv", mime="text/csv",
            )
        if not district_attainment.empty:
            st.markdown("**District attainment by comparable indicator**")
            st.dataframe(district_attainment, use_container_width=True, hide_index=True)
            st.download_button(
                "Download district-indicator attainment",
                data=district_attainment.to_csv(index=False).encode("utf-8"),
                file_name="district_indicator_target_attainment.csv", mime="text/csv",
            )
        if not monthly_attainment.empty:
            st.plotly_chart(
                px.line(
                    monthly_attainment, x="Month", y="attainment_pct", color="Indicator",
                    facet_col="Programme", facet_col_wrap=2, markers=True,
                    title="Monthly target attainment by programme and indicator",
                    labels={"attainment_pct": "Reported-to-target attainment (%)"},
                ),
                use_container_width=True,
            )
            st.download_button(
                "Download monthly indicator attainment",
                data=monthly_attainment.to_csv(index=False).encode("utf-8"),
                file_name="monthly_indicator_target_attainment.csv", mime="text/csv",
            )

        st.markdown("**Resource capacity and allocation scenario laboratory**")
        st.caption(
            "All resource requirements and available units are synthetic planning abstractions. "
            "They are not official staffing norms, budgets, clinical standards, or operational recommendations. "
            "Catchment population is a configurable planning proxy, not observed patient volume or service coverage."
        )
        resource_summary = result["resource"]["scenario_summary"]
        resource_facility = result["resource"]["facility_capacity"]
        resource_allocations = result["resource"]["scenario_allocations"]
        r1, r2, r3 = st.columns(3)
        r1.metric("Facilities with a baseline gap", int(resource_facility["Baseline_Gap_Units"].gt(0).sum()))
        r2.metric("Total illustrative gap units", int(resource_facility["Baseline_Gap_Units"].sum()))
        r3.metric("Scenario resource pool", int(resource_summary["resource_pool"].iloc[0]) if not resource_summary.empty else 0)
        st.plotly_chart(
            px.bar(
                resource_summary, x="Scenario", y="residual_gap_units", color="Scenario",
                title="Residual capacity gap after each allocation strategy",
                labels={"residual_gap_units": "Unfilled illustrative units"},
            ),
            use_container_width=True,
        )
        st.dataframe(resource_summary, use_container_width=True, hide_index=True)
        scenario_choice = st.selectbox(
            "Inspect facility allocations",
            ["gap_priority", "equity", "equal"],
            format_func=lambda value: {"gap_priority": "Largest capacity gap first", "equity": "Rural-weighted equity", "equal": "Equal-share rounds"}[value],
            key="resource_scenario_choice",
        )
        selected_allocations = resource_allocations[resource_allocations["Scenario"].eq(scenario_choice)].sort_values(
            ["Residual_Gap_Units", "Facility_ID"], ascending=[False, True]
        )
        st.dataframe(selected_allocations, use_container_width=True, hide_index=True)
        st.download_button(
            "Download selected allocation scenario",
            data=selected_allocations.to_csv(index=False).encode("utf-8"),
            file_name=f"resource_allocation_{scenario_choice}.csv",
            mime="text/csv",
            key="download_resource_scenario",
        )

        st.markdown("**Commodity availability, stockout and replenishment intelligence**")
        st.caption(
            "This is a synthetic stock-card simulation. Commodity demand, receipts, unit costs and stockouts are generated examples—not actual facility inventory, procurement prices, national consumption standards or an approved essential commodities list. Budget credits are abstract and are not MWK."
        )
        supply = result["supply"]
        stock_ledger = supply["inventory_ledger"]
        replenishment = supply["replenishment_plan"]
        supply_summary = supply["scenario_summary"].iloc[0]
        s1, s2, s3, s4 = st.columns(4)
        s1.metric("Facility–commodity pairs", f"{len(replenishment):,}")
        s2.metric("Pairs with recent stockouts", f"{int(replenishment['Recent_Stockout_Days'].gt(0).sum()):,}")
        s3.metric("Requested replenishment units", f"{int(replenishment['Requested_Replenishment_Units'].sum()):,}")
        s4.metric("Unfunded replenishment units", f"{int(replenishment['Unfunded_Replenishment_Units'].sum()):,}")
        monthly_stockouts = (
            stock_ledger.groupby("Month", as_index=False)
            .agg(
                Facility_Commodity_Pairs=("Commodity_ID", "size"),
                Stockout_Pairs=("Stockout_Flag", "sum"),
                Unmet_Demand_Units=("Unmet_Demand_Units", "sum"),
            )
        )
        monthly_stockouts["Stockout_Pair_Rate_Pct"] = (
            100 * monthly_stockouts["Stockout_Pairs"] / monthly_stockouts["Facility_Commodity_Pairs"]
        )
        st.plotly_chart(
            px.line(
                monthly_stockouts, x="Month", y="Stockout_Pair_Rate_Pct", markers=True,
                title="Monthly share of facility–commodity pairs with a simulated stockout",
                labels={"Stockout_Pair_Rate_Pct": "Pairs with stockout (%)"},
            ),
            use_container_width=True,
        )
        commodity_risk = (
            replenishment.groupby("Commodity", as_index=False)
            .agg(
                Facilities=("Facility_ID", "nunique"),
                Recent_Stockout_Pairs=("Recent_Stockout_Days", lambda values: int(values.gt(0).sum())),
                Requested_Units=("Requested_Replenishment_Units", "sum"),
                Unfunded_Units=("Unfunded_Replenishment_Units", "sum"),
            )
            .sort_values("Recent_Stockout_Pairs", ascending=False)
        )
        st.dataframe(commodity_risk, use_container_width=True, hide_index=True)
        st.markdown("**Budget-constrained replenishment worklist**")
        st.caption(
            f"Snapshot month: {pd.to_datetime(supply_summary['snapshot_month']).strftime('%B %Y')} · "
            f"Budget: {int(supply_summary['budget_credits']):,} abstract credits · "
            f"Allocated: {int(supply_summary['allocated_cost_credits']):,} credits · "
            f"Unspent: {int(supply_summary['unspent_budget_credits']):,} credits"
        )
        supply_columns = [
            "Facility_Name", "District", "Commodity", "Programme", "Closing_Stock_Units",
            "Estimated_Days_of_Cover", "Recent_Stockout_Days", "Requested_Replenishment_Units",
            "Allocated_Replenishment_Units", "Unfunded_Replenishment_Units",
            "Allocated_Cost_Credits", "Post_Allocation_Days_of_Cover",
        ]
        supply_worklist = replenishment.sort_values(
            ["Recent_Stockout_Days", "Estimated_Days_of_Cover", "Priority_Score"],
            ascending=[False, True, False], na_position="first",
        )
        st.dataframe(supply_worklist[supply_columns], use_container_width=True, hide_index=True)
        st.download_button(
            "Download commodity replenishment worklist",
            data=supply_worklist.to_csv(index=False).encode("utf-8"),
            file_name="commodity_replenishment_worklist.csv",
            mime="text/csv",
            key="download_commodity_replenishment",
        )
        with st.expander("View simulated stock ledger"):
            st.dataframe(stock_ledger.tail(500), use_container_width=True, hide_index=True)
            st.download_button(
                "Download full simulated stock ledger",
                data=stock_ledger.to_csv(index=False).encode("utf-8"),
                file_name="facility_commodity_stock_ledger.csv",
                mime="text/csv",
                key="download_commodity_stock_ledger",
            )

        st.markdown("**Cold-chain, batch traceability and expiry intelligence**")
        st.caption(
            "Synthetic monitoring scenario only. The 2–8°C band, shelf lives and alert windows are illustrative assumptions, not product-specific storage instructions or official Malawi standards. Monthly summaries do not replace calibrated continuous temperature logs, batch quarantine procedures or professional product-stability decisions."
        )
        cold = result["cold_chain"]
        cold_risk = cold["expiry_risk_summary"]
        cold_temp = cold["temperature_monitoring"]
        cold_batches = cold["batch_ledger"]
        latest_cold_month = cold_risk["Month"].max()
        latest_cold = cold_risk.loc[cold_risk["Month"].eq(latest_cold_month)].copy()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("High-risk facility–commodity pairs", f"{int(latest_cold['Risk_Band'].eq('High').sum()):,}")
        c2.metric("Facility-month temperature excursions", f"{int(cold_temp['Temperature_Excursion_Flag'].sum()):,}")
        c3.metric("Units expiring within 90 days", f"{int(latest_cold['Near_Expiry_90_Day_Units'].sum()):,}")
        c4.metric("Expired units in simulation", f"{int(cold_risk['Expired_Units'].sum()):,}")
        monthly_cold = cold_risk.groupby("Month", as_index=False).agg(
            High_Risk_Pairs=("Risk_Band", lambda values: int(values.eq("High").sum())),
            Near_Expiry_90_Day_Units=("Near_Expiry_90_Day_Units", "sum"),
            Expired_Units=("Expired_Units", "sum"),
            Unmet_Demand_Units=("Unmet_Demand_Units", "sum"),
        )
        cold_left, cold_right = st.columns(2)
        cold_left.plotly_chart(
            px.line(
                monthly_cold, x="Month", y="High_Risk_Pairs", markers=True,
                title="Monthly high-risk facility–commodity pairs",
            ),
            use_container_width=True,
        )
        cold_right.plotly_chart(
            px.line(
                monthly_cold, x="Month", y=["Near_Expiry_90_Day_Units", "Expired_Units"],
                markers=True, title="Near-expiry and expired stock (units)",
            ),
            use_container_width=True,
        )
        monthly_temperature = cold_temp.groupby("Month", as_index=False).agg(
            Excursion_Facility_Months=("Temperature_Excursion_Flag", "sum"),
            Average_Data_Coverage_Pct=("Temperature_Data_Coverage_Pct", "mean"),
        )
        st.plotly_chart(
            px.line(
                monthly_temperature, x="Month", y="Excursion_Facility_Months",
                markers=True, title="Facility-month temperature excursion signals",
            ),
            use_container_width=True,
        )
        st.markdown("**Latest batch and facility review worklist**")
        risk_order = {"High": 0, "Medium": 1, "Low": 2, "Data Gap": 3}
        latest_cold["Risk_Order"] = latest_cold["Risk_Band"].map(risk_order).fillna(4)
        cold_worklist = latest_cold.sort_values(
            ["Risk_Order", "Cold_Chain_Risk_Score", "Near_Expiry_90_Day_Units"],
            ascending=[True, False, False], na_position="last",
        ).drop(columns=["Risk_Order"])
        cold_columns = [
            "Facility_Name", "District", "Commodity", "Risk_Band", "Cold_Chain_Risk_Score",
            "Temperature_Excursion_Days", "Temperature_Data_Coverage_Pct",
            "Near_Expiry_30_Day_Units", "Near_Expiry_60_Day_Units",
            "Near_Expiry_90_Day_Units", "Expired_Units", "Unmet_Demand_Units",
        ]
        st.dataframe(cold_worklist[cold_columns], use_container_width=True, hide_index=True)
        st.download_button(
            "Download cold-chain and expiry risk worklist",
            data=cold_worklist.to_csv(index=False).encode("utf-8"),
            file_name="cold_chain_expiry_risk_worklist.csv",
            mime="text/csv",
            key="download_cold_chain_risk_worklist",
        )
        with st.expander("Inspect batch-level traceability ledger"):
            st.dataframe(cold_batches.tail(500), use_container_width=True, hide_index=True)
            st.download_button(
                "Download complete batch ledger",
                data=cold_batches.to_csv(index=False).encode("utf-8"),
                file_name="facility_commodity_batch_ledger.csv",
                mime="text/csv",
                key="download_cold_chain_batch_ledger",
            )
            st.download_button(
                "Download facility temperature monitoring",
                data=cold_temp.to_csv(index=False).encode("utf-8"),
                file_name="facility_cold_chain_temperature_monitoring.csv",
                mime="text/csv",
                key="download_cold_chain_temperature",
            )

        st.markdown("**Equipment asset, maintenance and uptime intelligence**")
        st.caption(
            "All asset inventories, service events, downtime, maintenance costs and condition scores are synthetic. Failure probabilities, asset lives, maintenance intervals and criticality labels are illustrative planning assumptions—not engineering standards, verified facility inventories or clinical service availability evidence. Abstract credits are not MWK."
        )
        equipment = result["equipment"]
        asset_register = equipment["asset_register"]
        asset_monthly = equipment["asset_monthly_performance"]
        facility_equipment = equipment["facility_monthly_summary"]
        maintenance_orders = equipment["maintenance_work_orders"]
        latest_assets = equipment["latest_asset_status"].copy()
        latest_equipment_month = asset_monthly["Month"].max()
        latest_orders = maintenance_orders.loc[maintenance_orders["Month"].eq(latest_equipment_month)].copy()
        open_orders = latest_orders.loc[~latest_orders["Status"].eq("Closed")].copy()
        e1, e2, e3, e4 = st.columns(4)
        e1.metric("Synthetic equipment assets", f"{len(asset_register):,}")
        e2.metric("Mean operational uptime", f"{latest_assets['Operational_Uptime_Pct'].mean():.1f}%")
        e3.metric("High-risk assets", f"{int(latest_assets['Risk_Band'].eq('High').sum()):,}")
        e4.metric("Open work orders", f"{len(open_orders):,}")
        monthly_equipment = asset_monthly.groupby("Month", as_index=False).agg(
            Mean_Operational_Uptime_Pct=("Operational_Uptime_Pct", "mean"),
            Mean_Service_Availability_Pct=("Service_Availability_Pct", "mean"),
            Breakdown_Events=("Breakdown_Count", "sum"),
            Unplanned_Downtime_Hours=("Unplanned_Downtime_Hours", "sum"),
        )
        equipment_left, equipment_right = st.columns(2)
        equipment_left.plotly_chart(
            px.line(
                monthly_equipment, x="Month", y=["Mean_Operational_Uptime_Pct", "Mean_Service_Availability_Pct"],
                markers=True, title="Monthly simulated uptime and service availability",
            ),
            use_container_width=True,
        )
        equipment_right.plotly_chart(
            px.bar(
                latest_assets.sort_values("Equipment_Risk_Score").tail(15),
                x="Equipment_Risk_Score", y="Asset_ID", color="Risk_Band", orientation="h",
                title="Highest-priority equipment assets",
                hover_data=["Facility_Name", "District", "Equipment_Type", "Unplanned_Downtime_Hours", "Preventive_Maintenance_Overdue"],
            ),
            use_container_width=True,
        )
        monthly_pm = facility_equipment.groupby("Month", as_index=False).agg(
            PM_Due=("PM_Due", "sum"), PM_Completed=("PM_Completed", "sum"),
            PM_Overdue=("PM_Overdue", "sum"),
        )
        monthly_pm["PM_Completion_Pct"] = (
            100 * monthly_pm["PM_Completed"] / monthly_pm["PM_Due"].replace(0, float("nan"))
        )
        st.plotly_chart(
            px.line(
                monthly_pm, x="Month", y="PM_Completion_Pct", markers=True,
                title="Preventive maintenance completion rate",
            ),
            use_container_width=True,
        )
        st.markdown("**Maintenance work-order queue**")
        if open_orders.empty:
            st.success("No synthetic maintenance work orders remain open in the latest simulated month.")
        else:
            st.dataframe(
                open_orders.sort_values(["Priority", "Due_Date"], ascending=[True, True]),
                use_container_width=True, hide_index=True,
            )
        st.download_button(
            "Download maintenance work-order register",
            data=maintenance_orders.to_csv(index=False).encode("utf-8"),
            file_name="equipment_maintenance_work_orders.csv",
            mime="text/csv",
            key="download_equipment_work_orders",
        )
        st.markdown("**Facility equipment performance**")
        st.dataframe(
            facility_equipment.loc[facility_equipment["Month"].eq(latest_equipment_month)],
            use_container_width=True, hide_index=True,
        )
        st.download_button(
            "Download latest equipment risk register",
            data=latest_assets.to_csv(index=False).encode("utf-8"),
            file_name="equipment_latest_asset_risk_status.csv",
            mime="text/csv",
            key="download_equipment_risk_register",
        )
        with st.expander("Inspect asset register and monthly equipment history"):
            st.dataframe(asset_register, use_container_width=True, hide_index=True)
            st.dataframe(asset_monthly.tail(500), use_container_width=True, hide_index=True)
            st.download_button(
                "Download full equipment asset register",
                data=asset_register.to_csv(index=False).encode("utf-8"),
                file_name="facility_equipment_asset_register.csv",
                mime="text/csv",
                key="download_equipment_asset_register",
            )
            st.download_button(
                "Download full asset-month performance history",
                data=asset_monthly.to_csv(index=False).encode("utf-8"),
                file_name="equipment_asset_monthly_performance.csv",
                mime="text/csv",
                key="download_equipment_monthly_performance",
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
        control_chart = result["control"].copy()
        if not control_chart.empty:
            control_chart["Month"] = pd.to_datetime(control_chart["Month"], errors="coerce")
            st.plotly_chart(
                px.line(
                    control_chart,
                    x="Month",
                    y=["Issue_Rate", "Centre_Line", "Lower_Control_Limit", "Upper_Control_Limit"],
                    markers=True,
                    title="Monthly issue rate with retrospective p-chart limits",
                    labels={"value": "Proportion of records", "variable": "Series"},
                ),
                use_container_width=True,
            )
        st.caption(
            "The centre line is the pooled issue proportion. Limits use month-specific "
            "denominators, so lower-volume months have wider bands. These are retrospective "
            "descriptive limits, not prospective alert thresholds."
        )
        st.dataframe(control_chart, use_container_width=True, hide_index=True)
        st.download_button(
            "Download monthly monitoring output",
            data=control_chart.to_csv(index=False).encode("utf-8"),
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
