"""Tests for synthetic facility workforce capacity planning."""
import sys
from pathlib import Path
import pandas as pd
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from workforce_planning import build_workforce_profiles,run_workforce_planning


def sample_facilities():
    return pd.DataFrame({
        "Facility_ID":["F001","F002","F003"],
        "Facility_Name":["Alpha","Beta","Gamma"],
        "District":["Blantyre","Mzimba","Zomba"],
        "Facility_Type":["Health Centre","District Hospital","Community Hospital"],
        "Urban_Rural":["Rural","Urban","Peri-urban"],
        "Catchment_Population":[9000,55000,26000],
    })


def test_deterministic_facility_month_and_role_grains():
    a=build_workforce_profiles(sample_facilities(),periods=4,seed=7)
    b=build_workforce_profiles(sample_facilities(),periods=4,seed=7)
    pd.testing.assert_frame_equal(a["establishment"],b["establishment"])
    pd.testing.assert_frame_equal(a["monthly_workforce"],b["monthly_workforce"])
    assert len(a["establishment"])==3*8
    assert len(a["monthly_workforce"])==3*4
    assert not a["establishment"].duplicated(["Facility_ID","Role"]).any()
    assert not a["monthly_workforce"].duplicated(["Facility_ID","Month"]).any()


def test_workforce_counts_and_rates_are_consistent():
    result=build_workforce_profiles(sample_facilities(),periods=6,seed=9)
    monthly=result["monthly_workforce"]
    assert (monthly["Illustrative_Establishment"]>=monthly["Filled_Positions"]).all()
    assert (monthly["Filled_Positions"]>=monthly["Available_On_Duty_Positions"]).all()
    assert (monthly["Vacant_Positions"]==monthly["Illustrative_Establishment"]-monthly["Filled_Positions"]).all()
    assert monthly["Workforce_Coverage_Pct"].between(0,100).all()
    assert monthly["Absence_Rate_Pct"].between(0,100).all()
    assert monthly["Estimated_Overtime_Hours"].ge(0).all()
    assert monthly["Synthetic_Data"].all()


def test_recruitment_scenario_is_budget_constrained():
    result=build_workforce_profiles(sample_facilities(),periods=2,seed=5,recruitment_budget_credits=10000)
    role=result["role_recruitment_scenario"]
    assert (role["Funded_Positions"]<=role["Vacancies"]).all()
    assert (role["Unfunded_Positions"]==role["Vacancies"]-role["Funded_Positions"]).all()
    assert (role["Funded_Positions"]*role["Cost_Per_Position"]).sum()<=10000
    assert role["Funded_Positions"].sum()>0


def test_invalid_inputs_and_export_artifacts(tmp_path):
    with pytest.raises(ValueError,match="missing required columns"):
        build_workforce_profiles(sample_facilities().drop(columns=["District"]))
    with pytest.raises(ValueError,match="At least one facility"):
        build_workforce_profiles(sample_facilities().iloc[:0])
    with pytest.raises(ValueError,match="periods"):
        build_workforce_profiles(sample_facilities(),periods=0)
    with pytest.raises(ValueError,match="periods"):
        build_workforce_profiles(sample_facilities(),periods=True)
    with pytest.raises(ValueError,match="non-negative integer"):
        build_workforce_profiles(sample_facilities(),recruitment_budget_credits=-1)
    with pytest.raises(ValueError,match="non-negative integer"):
        build_workforce_profiles(sample_facilities(),recruitment_budget_credits=1000.5)
    path=tmp_path/"facilities.csv"
    sample_facilities().to_csv(path,index=False)
    report=run_workforce_planning(path,tmp_path/"analytics",periods=3,seed=3)
    assert report["synthetic_data"] is True
    assert report["facility_month_records"]==9
    for filename in report["outputs"]:
        assert (tmp_path/"analytics"/filename).exists()
    assert (tmp_path/"analytics"/"workforce_planning_report.json").exists()
