"""Synthetic facility workforce capacity and staffing scenario analytics.

All role establishments, staffing levels, attendance, workload proxies and costs
are simulated planning assumptions, not actual HR records or staffing standards.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd

ROLES = {
    "Clinical Officer": {"weight": 1.35, "cost": 1200},
    "Nurse": {"weight": 1.00, "cost": 850},
    "Midwife": {"weight": 1.05, "cost": 900},
    "Medical Assistant": {"weight": 0.90, "cost": 700},
    "Laboratory Technician": {"weight": 1.10, "cost": 950},
    "Pharmacy Technician": {"weight": 0.95, "cost": 800},
    "Health Surveillance Assistant": {"weight": 0.75, "cost": 550},
    "Data Clerk": {"weight": 0.70, "cost": 600},
}
REQUIRED = ["Facility_ID","Facility_Name","District","Facility_Type","Urban_Rural","Catchment_Population"]


def _facilities(data: pd.DataFrame) -> pd.DataFrame:
    missing = sorted(set(REQUIRED)-set(data.columns))
    if missing:
        raise ValueError(f"Facility dimension missing required columns: {missing}")
    out=data[REQUIRED].copy()
    if out.empty:
        raise ValueError("At least one facility is required")
    out["Facility_ID"]=out["Facility_ID"].astype("string").str.strip()
    if out["Facility_ID"].isna().any() or out["Facility_ID"].eq("").any() or out["Facility_ID"].duplicated().any():
        raise ValueError("Facility_ID must be populated and unique")
    out["Catchment_Population"]=pd.to_numeric(out["Catchment_Population"],errors="coerce").fillna(0).clip(lower=0)
    for col in ["Facility_Name","District","Facility_Type","Urban_Rural"]:
        out[col]=out[col].fillna("Unknown").astype(str).str.strip()
    return out


def build_workforce_profiles(facilities: pd.DataFrame, periods: int=60,
                             start_month: str="2021-01-01", seed: int=42,
                             recruitment_budget_credits: int=50000) -> dict[str,pd.DataFrame]:
    if not isinstance(periods,int) or periods<1:
        raise ValueError("periods must be a positive integer")
    if recruitment_budget_credits<0:
        raise ValueError("recruitment budget must be non-negative")
    fac=_facilities(facilities)
    rng=np.random.default_rng(seed)
    months=pd.date_range(pd.Timestamp(start_month).to_period("M").to_timestamp(),periods=periods,freq="MS")
    establishments=[]
    monthly=[]
    for f in fac.to_dict("records"):
        typ=str(f["Facility_Type"]).lower()
        hospital="hospital" in typ
        base={"Clinical Officer":2 if hospital else 1,"Nurse":8 if hospital else 4,
              "Midwife":4 if hospital else 2,"Medical Assistant":3 if hospital else 2,
              "Laboratory Technician":3 if hospital else 1,"Pharmacy Technician":2 if hospital else 1,
              "Health Surveillance Assistant":5 if hospital else 3,"Data Clerk":2 if hospital else 1}
        scale=max(0.65,min(2.2,float(f["Catchment_Population"])/18000))
        for role,definition in ROLES.items():
            required=max(1,int(round(base[role]*scale)))
            fill_rate=float(rng.uniform(.62,.98))
            filled=min(required,int(round(required*fill_rate)))
            establishments.append({**{k:f[k] for k in ["Facility_ID","Facility_Name","District","Facility_Type","Urban_Rural"]},
                "Role":role,"Illustrative_Establishment":required,"Baseline_Filled_Positions":filled,
                "Baseline_Vacancies":required-filled,"Workforce_Weight":definition["weight"],
                "Synthetic_Recruitment_Cost_Credits_Per_Position":definition["cost"],"Synthetic_Data":True})
        for month in months:
            total_required=0; total_filled=0; weighted_available=0.0
            role_month=[]
            for role,definition in ROLES.items():
                establishment=next(x for x in establishments if x["Facility_ID"]==f["Facility_ID"] and x["Role"]==role)
                required=establishment["Illustrative_Establishment"]
                baseline=establishment["Baseline_Filled_Positions"]
                drift=int(rng.choice([-1,0,0,0,1],p=[.08,.62,.12,.10,.08]))
                filled=max(0,min(required,baseline+drift))
                absent=int(rng.binomial(filled,float(rng.uniform(.025,.12))))
                available=filled-absent
                overtime=float(max(0,rng.normal(8+max(0,required-available)*2,5)))
                total_required+=required;total_filled+=filled
                weighted_available+=available*definition["weight"]
                role_month.append({"Role":role,"Required":required,"Filled":filled,"Absent":absent,
                                   "Available":available,"Overtime_Hours":round(overtime,1)})
            # Demand is a synthetic catchment-based workload proxy, not patient counts.
            demand_proxy=float(f["Catchment_Population"])/1000 * (1.0 if not hospital else 1.25)
            capacity_index=weighted_available/max(demand_proxy,1.0)
            coverage=100*total_filled/max(total_required,1)
            absence_rate=100*sum(x["Absent"] for x in role_month)/max(total_filled,1)
            vacancy=total_required-total_filled
            pressure=100*min(2.0,demand_proxy/max(weighted_available,1.0))
            monthly.append({"Facility_ID":f["Facility_ID"],"Facility_Name":f["Facility_Name"],"District":f["District"],
                "Month":month,"Illustrative_Establishment":total_required,"Filled_Positions":total_filled,
                "Vacant_Positions":vacancy,"Absent_Positions":sum(x["Absent"] for x in role_month),
                "Available_On_Duty_Positions":sum(x["Available"] for x in role_month),
                "Workforce_Coverage_Pct":round(coverage,2),"Absence_Rate_Pct":round(absence_rate,2),
                "Estimated_Overtime_Hours":round(sum(x["Overtime_Hours"] for x in role_month),1),
                "Synthetic_Workload_Demand_Proxy":round(demand_proxy,2),
                "Weighted_Available_Capacity":round(weighted_available,2),
                "Workforce_Pressure_Index":round(pressure,2),
                "Capacity_Proxy_Per_1000_Catchment":round(capacity_index,2),"Synthetic_Data":True})
    establishment_df=pd.DataFrame(establishments)
    monthly_df=pd.DataFrame(monthly)
    latest_month=monthly_df["Month"].max()
    latest=monthly_df.loc[monthly_df["Month"].eq(latest_month)].merge(
        fac[["Facility_ID","Catchment_Population","Urban_Rural","Facility_Type"]],on="Facility_ID",how="left",validate="one_to_one")
    latest["Workforce_Risk_Band"]=pd.cut(latest["Workforce_Coverage_Pct"],[-.01,65,80,100.01],labels=["High","Moderate","Lower"]).astype(str)
    role_gap=establishment_df.groupby("Role",as_index=False).agg(
        Required_Positions=("Illustrative_Establishment","sum"),Filled_Positions=("Baseline_Filled_Positions","sum"),
        Vacancies=("Baseline_Vacancies","sum"),Cost_Per_Position=("Synthetic_Recruitment_Cost_Credits_Per_Position","first"))
    role_gap["Recruitment_Cost_Credits"]=role_gap["Vacancies"]*role_gap["Cost_Per_Position"]
    role_gap=role_gap.sort_values(["Vacancies","Role"],ascending=[False,True]).reset_index(drop=True)
    remaining=int(recruitment_budget_credits)
    role_gap["Funded_Positions"]=0
    for idx,row in role_gap.iterrows():
        affordable=min(int(row["Vacancies"]),remaining//int(row["Cost_Per_Position"]))
        role_gap.loc[idx,"Funded_Positions"]=affordable
        remaining-=affordable*int(row["Cost_Per_Position"])
    role_gap["Unfunded_Positions"]=role_gap["Vacancies"]-role_gap["Funded_Positions"]
    role_gap["Budget_Credits_Available"]=int(recruitment_budget_credits)
    role_gap["Budget_Credits_Unallocated"]=remaining
    return {"establishment":establishment_df,"monthly_workforce":monthly_df,
            "latest_facility_workforce":latest.sort_values(["Workforce_Coverage_Pct","Facility_ID"]),
            "role_recruitment_scenario":role_gap}


def run_workforce_planning(facility_path: Path, output_dir: Path, periods: int=60,
                           start_month: str="2021-01-01", seed: int=42,
                           recruitment_budget_credits: int=50000) -> dict[str,Any]:
    facilities=pd.read_csv(facility_path)
    result=build_workforce_profiles(facilities,periods,start_month,seed,recruitment_budget_credits)
    output_dir=Path(output_dir);output_dir.mkdir(parents=True,exist_ok=True)
    files={"establishment":"facility_workforce_establishment.csv",
           "monthly_workforce":"facility_monthly_workforce_capacity.csv",
           "latest_facility_workforce":"facility_latest_workforce_capacity.csv",
           "role_recruitment_scenario":"workforce_recruitment_scenario.csv"}
    for key,name in files.items():result[key].to_csv(output_dir/name,index=False)
    latest=result["latest_facility_workforce"]
    report={"synthetic_data":True,"facilities":int(facilities["Facility_ID"].nunique()),
        "facility_month_records":len(result["monthly_workforce"]),
        "latest_mean_coverage_pct":round(float(latest["Workforce_Coverage_Pct"].mean()),2),
        "latest_high_review_priority_facilities":int(latest["Workforce_Risk_Band"].eq("High").sum()),
        "total_baseline_vacancies":int(result["establishment"]["Baseline_Vacancies"].sum()),
        "funded_recruitment_positions":int(result["role_recruitment_scenario"]["Funded_Positions"].sum()),
        "recruitment_budget_credits_unallocated":int(result["role_recruitment_scenario"]["Budget_Credits_Unallocated"].iloc[0]),
        "outputs":list(files.values()),
        "limitations":["All establishment, filled positions, absences and overtime are synthetic.",
        "Workload is a catchment-based proxy, not patient volume or service utilisation.",
        "Role mixes and vacancy bands are illustrative, not official Malawi staffing norms.",
        "Recruitment credits are abstract and are not MWK; no salaries or HR records are represented.",
        "Coverage and pressure scores are planning review aids, not evidence of safe staffing or clinical quality."]}
    (output_dir/"workforce_planning_report.json").write_text(json.dumps(report,indent=2))
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--facilities",type=Path,default=Path("data/warehouse/raw/facility_dimension.csv"))
    parser.add_argument("--output-dir",type=Path,default=Path("data/warehouse/analytics"))
    parser.add_argument("--periods",type=int,default=60)
    parser.add_argument("--start-month",default="2021-01-01")
    parser.add_argument("--seed",type=int,default=42)
    parser.add_argument("--recruitment-budget-credits",type=int,default=50000)
    args=parser.parse_args()
    print(json.dumps(run_workforce_planning(args.facilities,args.output_dir,args.periods,args.start_month,args.seed,args.recruitment_budget_credits),indent=2))


if __name__=="__main__":
    main()
