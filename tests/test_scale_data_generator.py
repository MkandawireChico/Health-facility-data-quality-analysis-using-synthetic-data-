"""Tests for the expanded synthetic data platform generator."""
import sys
from pathlib import Path
import pandas as pd
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from scale_data_generator import ScaledHealthDataGenerator

def small_generator(seed=7):
    return ScaledHealthDataGenerator(seed=seed,facility_count=6,start_month="2024-01-01",periods=3,
        districts=("North","Central","South"),
        programmes={"HIV":{"ART clients":(100,200),"New initiations":(5,30)},
                    "TB":{"New cases":(1,20),"Treatment completions":(1,20)}})

def test_expected_scale_and_unique_fact_grain():
    gen=small_generator()
    fact,facilities,manifest=gen.generate({"missing":0,"source_discrepancy":0,"outlier":0,"late":0})
    assert gen.expected_record_count==72 and len(fact)==72 and len(facilities)==6
    assert not fact.duplicated(["Facility_ID","Month","Programme","Indicator"]).any()
    assert manifest["actual_record_count"]==72

def test_generator_is_reproducible():
    a,af,am=small_generator().generate()
    b,bf,bm=small_generator().generate()
    pd.testing.assert_frame_equal(a,b); pd.testing.assert_frame_equal(af,bf)
    assert am["injection_counts"]==bm["injection_counts"]

def test_ground_truth_labels_and_injected_values():
    fact,_,manifest=small_generator(12).generate({"missing":.1,"source_discrepancy":.15,"outlier":.05,"late":.2})
    for label,key in [("Ground_Truth_Missing","missing"),("Ground_Truth_Source_Discrepancy","source_discrepancy"),
                      ("Ground_Truth_Outlier","outlier"),("Ground_Truth_Late","late")]:
        assert int(fact[label].sum())==manifest["injection_counts"][key]
    assert fact.loc[fact.Ground_Truth_Missing,"Reported_Value"].isna().all()
    late=fact.Ground_Truth_Late
    assert fact.loc[late,"Submission_Date"].gt(fact.loc[late,"Deadline_Date"]).all()

def test_facility_dimension_has_unique_keys_and_metadata():
    _,facilities,_=small_generator().generate()
    assert facilities.Facility_ID.is_unique and facilities.Facility_Name.is_unique
    assert facilities.District.nunique()==3 and facilities.Is_Synthetic.all()
    assert facilities.Catchment_Population.gt(0).all()

@pytest.mark.parametrize("kwargs",[{"facility_count":0},{"periods":0},{"districts":()}])
def test_invalid_configuration_rejected(kwargs):
    with pytest.raises(ValueError): ScaledHealthDataGenerator(**kwargs)

def test_invalid_injection_rate_rejected():
    with pytest.raises(ValueError): small_generator().generate({"missing":1.2})


def test_missing_report_is_not_also_labelled_as_reported_value_outlier():
    fact, _, _ = ScaledHealthDataGenerator(seed=19, facility_count=30, periods=12).generate(
        {"missing": 0.25, "outlier": 0.25}
    )
    assert not (fact["Ground_Truth_Missing"] & fact["Ground_Truth_Outlier"]).any()
    assert fact.loc[fact["Ground_Truth_Outlier"], "Reported_Value"].notna().all()
