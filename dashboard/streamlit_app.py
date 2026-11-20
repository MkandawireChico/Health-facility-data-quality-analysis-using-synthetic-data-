from __future__ import annotations

from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
DATA_PATHS = [
    ROOT / "data" / "processed" / "health_facility_data_processed.csv",
    ROOT / "data" / "raw" / "synthetic_health_facility_data.csv",
]
st.set_page_config(page_title="Health Data Quality Command Centre", page_icon="🏥", layout="wide")

st.markdown("""
<style>
    .block-container {padding-top: 1.6rem; padding-bottom: 2.5rem; max-width: 1500px;}
    [data-testid="stMetric"] {background:#f4f7fb;border:1px solid #dce5ef;padding:14px 16px;border-radius:12px;}
    .hero {background:linear-gradient(110deg,#eaf3fb,#f5faf8);border:1px solid #d9e7ed;border-radius:16px;padding:22px 24px;margin-bottom:18px;}
    .hero h1 {color:#153b56;margin:0 0 6px 0;font-size:2rem;}
    .hero p {color:#456276;margin:0;}
    div[data-testid="stDataFrame"] {border:1px solid #e1e8ef;border-radius:10px;}
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data() -> tuple[pd.DataFrame, str]:
    for path in DATA_PATHS:
        if path.exists():
            df = pd.read_csv(path)
            return df, str(path.relative_to(ROOT))
    raise FileNotFoundError("No dataset found. Add the processed or raw CSV under data/.")

try:
    df, source_label = load_data()
except Exception as exc:
    st.error(f"Unable to load project data: {exc}")
    st.stop()

required = {"Facility", "Programme", "Indicator", "Reported_Value", "Target_Value"}
missing = required.difference(df.columns)
if missing:
    st.error(f"The selected dataset is missing required columns: {', '.join(sorted(missing))}")
    st.stop()

df["Month"] = pd.to_datetime(df.get("Month"), errors="coerce")
if "Calculated_Completeness" not in df:
    completeness_fields = [
        "Reported_Value", "Target_Value", "Paper_Value",
        "EMR_Value", "DHIS2_Value", "Data_Source"
    ]
    if all(column in df.columns for column in completeness_fields):
        # Calculate completeness from actual field presence; do not substitute
        # the generator's simulated Completeness_Score.
        df["Calculated_Completeness"] = (
            df[completeness_fields].replace("", pd.NA).notna().mean(axis=1)
        )
if "Calculated_Timeliness" not in df and "Timeliness" in df:
    df["Calculated_Timeliness"] = df["Timeliness"]
if "Consistency_Flag" not in df:
    df["Consistency_Flag"] = "Not available"
if "Outlier_Flag" not in df:
    df["Outlier_Flag"] = False
if "Reported_Value_Missing" not in df:
    df["Reported_Value_Missing"] = df["Reported_Value"].isna()

st.sidebar.title("Health Data Quality")
st.sidebar.caption("Rumphi District • Synthetic portfolio dataset")
st.sidebar.divider()
facilities = sorted(df["Facility"].dropna().unique())
programmes = sorted(df["Programme"].dropna().unique())
months = sorted(df["Month"].dropna().unique())
selected_facilities = st.sidebar.multiselect("Facilities", facilities, default=facilities)
selected_programmes = st.sidebar.multiselect("Programme areas", programmes, default=programmes)
if months:
    month_range = st.sidebar.date_input("Reporting period", value=(pd.Timestamp(min(months)).date(), pd.Timestamp(max(months)).date()))
else:
    month_range = ()
issue_options = ["All records", "Records requiring review", "Missing values", "Late reports", "Outliers"]
issue_filter = st.sidebar.selectbox("Quality issue", issue_options)
filtered = df[df["Facility"].isin(selected_facilities) & df["Programme"].isin(selected_programmes)].copy()
if isinstance(month_range, (tuple, list)) and len(month_range) == 2:
    start, end = pd.Timestamp(month_range[0]), pd.Timestamp(month_range[1])
    filtered = filtered[filtered["Month"].between(start, end)]
elif isinstance(month_range, (tuple, list)) and len(month_range) == 1:
    filtered = filtered[filtered["Month"].dt.date == month_range[0]]
if issue_filter == "Records requiring review":
    filtered = filtered[(filtered["Consistency_Flag"].astype(str).isin(["Review Required", "Inconsistent"])) | filtered["Reported_Value_Missing"].astype(bool) | filtered["Outlier_Flag"].astype(bool) | filtered.get("Calculated_Timeliness", pd.Series(index=filtered.index, dtype=str)).eq("Late")]
elif issue_filter == "Missing values":
    filtered = filtered[filtered["Reported_Value_Missing"].astype(bool)]
elif issue_filter == "Late reports":
    filtered = filtered[filtered.get("Calculated_Timeliness", pd.Series(index=filtered.index, dtype=str)).eq("Late")]
elif issue_filter == "Outliers":
    filtered = filtered[filtered["Outlier_Flag"].astype(bool)]

st.markdown('<div class="hero"><h1>Health Facility Data Quality Command Centre</h1><p>Monitor reporting completeness, source consistency, timeliness and facility-level follow-up priorities.</p></div>', unsafe_allow_html=True)
st.caption(f"Dataset: {source_label} · {len(filtered):,} records in current view · All data is synthetic and illustrative.")
if filtered.empty:
    st.warning("No records match the selected filters. Adjust the sidebar filters.")
    st.stop()

def rate(series: pd.Series) -> float:
    values = pd.to_numeric(series, errors="coerce").dropna()
    return float(values.mean()) if len(values) else float("nan")

total = len(filtered)
late_rate = filtered.get("Calculated_Timeliness", pd.Series("Unknown", index=filtered.index)).eq("Late").mean()
consistent_rate = filtered["Consistency_Flag"].eq("Consistent").mean()
completeness = rate(filtered["Calculated_Completeness"]) if "Calculated_Completeness" in filtered else float("nan")
issue_mask = (filtered["Reported_Value_Missing"].astype(bool) | filtered["Outlier_Flag"].astype(bool) | filtered["Consistency_Flag"].isin(["Review Required", "Inconsistent"]) | filtered.get("Calculated_Timeliness", pd.Series(index=filtered.index, dtype=str)).eq("Late"))
a,b,c,d,e = st.columns(5)
a.metric("Reporting records", f"{total:,}")
b.metric("Average completeness", f"{completeness:.1%}" if pd.notna(completeness) else "N/A")
c.metric("On-time reporting", f"{1-late_rate:.1%}")
d.metric("Source consistency", f"{consistent_rate:.1%}")
e.metric("Records flagged", f"{issue_mask.mean():.1%}")

tab1, tab2, tab3, tab4 = st.tabs(["Executive overview", "Facility performance", "Source reconciliation", "Record worklist"])
with tab1:
    left, right = st.columns(2)
    facility_comp = filtered.groupby("Facility", as_index=False)["Calculated_Completeness"].mean() if "Calculated_Completeness" in filtered else pd.DataFrame()
    if not facility_comp.empty:
        left.plotly_chart(px.bar(facility_comp.sort_values("Calculated_Completeness"), x="Calculated_Completeness", y="Facility", orientation="h", title="Completeness by facility", labels={"Calculated_Completeness":"Completeness"}), use_container_width=True)
    else:
        left.info("Completeness metric is not present in this dataset.")
    issue_counts = pd.DataFrame({"Issue":["Missing values","Late reports","Source review","Outliers"],"Records":[
        int(filtered["Reported_Value"].isna().sum()),
        int(filtered.get("Calculated_Timeliness", pd.Series(index=filtered.index,dtype=str)).eq("Late").sum()),
        int(filtered["Consistency_Flag"].isin(["Review Required","Inconsistent"]).sum()),
        int(filtered["Outlier_Flag"].astype(bool).sum())
    ]})
    right.plotly_chart(px.bar(issue_counts, x="Issue", y="Records", title="Quality flags in current view"), use_container_width=True)
    if "Month" in filtered and filtered["Month"].notna().any():
        trend = filtered.assign(Month=filtered["Month"].dt.to_period("M").astype(str)).groupby("Month",as_index=False).agg(records=("Facility","size"), missing_rate=("Reported_Value_Missing","mean"))
        st.plotly_chart(px.line(trend,x="Month",y="missing_rate",markers=True,title="Monthly missing-value rate",labels={"missing_rate":"Missing rate"}),use_container_width=True)
with tab2:
    fac = filtered.groupby("Facility",as_index=False).agg(
        Records=("Facility","size"),
        Completeness=("Calculated_Completeness","mean") if "Calculated_Completeness" in filtered else ("Reported_Value","count"),
        Missing=("Reported_Value_Missing","sum"),
        Late=("Calculated_Timeliness",lambda x:(x=="Late").sum()) if "Calculated_Timeliness" in filtered else ("Reported_Value","count"),
        Source_reviews=("Consistency_Flag",lambda x:x.isin(["Review Required","Inconsistent"]).sum()),
        Outliers=("Outlier_Flag","sum")
    )
    fac["Issue rate"] = (fac["Missing"]+fac["Late"]+fac["Source_reviews"]+fac["Outliers"])/(4*fac["Records"])
    st.dataframe(fac.sort_values("Issue rate",ascending=False).style.format({"Completeness":"{:.1%}","Issue rate":"{:.1%}"}),use_container_width=True,hide_index=True)
    st.caption("Issue rate is a simple average of four issue proportions; a record with multiple flags can contribute to more than one category. It is a prioritisation aid, not a validated clinical or facility performance score.")
with tab3:
    if {"Paper_Value","EMR_Value","DHIS2_Value"}.issubset(filtered.columns):
        source_long=filtered.melt(id_vars=["Facility","Programme"],value_vars=["Paper_Value","EMR_Value","DHIS2_Value"],var_name="Source",value_name="Reported value")
        st.plotly_chart(px.box(source_long,x="Source",y="Reported value",color="Source",title="Distribution of values across reporting sources"),use_container_width=True)
    if "Source_Discrepancy_Pct" in filtered:
        discrepancy=filtered.groupby("Facility",as_index=False)["Source_Discrepancy_Pct"].mean().sort_values("Source_Discrepancy_Pct",ascending=False)
        st.plotly_chart(px.bar(discrepancy,x="Source_Discrepancy_Pct",y="Facility",orientation="h",title="Average source discrepancy by facility",labels={"Source_Discrepancy_Pct":"Mean relative discrepancy"}),use_container_width=True)
    st.info("Consistency flags depend on the documented rule and thresholds. Review low-volume indicators and source context before treating a discrepancy as an error.")
with tab4:
    columns=[c for c in ["Facility","Month","Programme","Indicator","Reported_Value","Target_Value","Data_Source","Consistency_Flag","Calculated_Timeliness","Outlier_Flag","Primary_Issue"] if c in filtered.columns]
    worklist=filtered.loc[issue_mask,columns].sort_values(["Facility","Month"],na_position="last")
    st.write(f"{len(worklist):,} records currently flagged for follow-up.")
    st.dataframe(worklist,use_container_width=True,hide_index=True)
    st.download_button("Download filtered worklist (CSV)",data=worklist.to_csv(index=False).encode("utf-8"),file_name="health_data_quality_worklist.csv",mime="text/csv")
    st.download_button("Download filtered dataset (CSV)",data=filtered.to_csv(index=False).encode("utf-8"),file_name="health_data_quality_filtered.csv",mime="text/csv")

st.divider()
st.caption("Portfolio demonstration only. Synthetic data; not for clinical decisions, facility performance assessment or operational reporting.")
