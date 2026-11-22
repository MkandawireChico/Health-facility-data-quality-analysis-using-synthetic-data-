"""Scalable synthetic health-facility reporting data platform."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd

DEFAULT_DISTRICTS = ("Blantyre", "Lilongwe", "Mzimba", "Zomba", "Mangochi", "Rumphi")
DEFAULT_PROGRAMMES = {
    "HIV": {"ART clients currently receiving treatment": (250,1200), "New ART initiations": (10,120), "Viral load samples collected": (80,650), "Viral load suppression results": (60,600), "HIV testing encounters": (100,900)},
    "Tuberculosis": {"Presumptive TB clients screened": (30,400), "New TB cases notified": (5,100), "TB treatment completions": (5,90), "TB contacts screened": (10,180), "TB clients tested for HIV": (5,100)},
    "Maternal Health": {"First ANC visits": (30,350), "Fourth ANC visits": (20,280), "Facility deliveries": (20,260), "Postnatal visits within 48 hours": (15,240), "Caesarean deliveries": (1,60)},
    "Child Health": {"Children receiving Penta 1": (20,300), "Children receiving Penta 3": (15,280), "Children receiving measles vaccine": (15,280), "Fully immunised children": (10,260), "Under-five outpatient visits": (80,900)},
    "Outpatient": {"Total outpatient visits": (250,2500), "New outpatient visits": (120,1500), "Under-five outpatient visits": (80,900), "Malaria suspected cases tested": (50,1200), "Malaria confirmed cases": (10,700)},
    "Nutrition": {"Children screened for acute malnutrition": (30,450), "New SAM admissions": (1,70), "New MAM admissions": (2,100), "SAM treatment exits cured": (1,65), "Vitamin A supplementation": (30,500)},
    "Family Planning": {"New family planning acceptors": (5,160), "Current family planning users": (40,650), "Contraceptive revisits": (20,500), "Postpartum family planning clients": (2,100), "Long-acting method insertions": (1,90)},
    "Water Sanitation and Hygiene": {"Facilities with functional water supply": (0,1), "Facilities with functional sanitation": (0,1), "Facilities with handwashing stations": (0,1), "Health promotion sessions": (2,80), "Community outreach sessions": (2,100)},
}

class ScaledHealthDataGenerator:
    """Generate synthetic facility, reporting-period and indicator tables."""
    def __init__(self, seed: int = 42, facility_count: int = 120,
                 start_month: str = "2021-01-01", periods: int = 60,
                 districts: tuple[str, ...] = DEFAULT_DISTRICTS,
                 programmes: dict[str, dict[str, tuple[int,int]]] | None = None):
        if facility_count < 1 or periods < 1 or not districts:
            raise ValueError("facility_count, periods and districts must be non-empty and positive")
        self.seed, self.facility_count = int(seed), int(facility_count)
        self.months = pd.date_range(start=start_month, periods=periods, freq="MS")
        self.districts = tuple(districts)
        self.programmes = programmes or DEFAULT_PROGRAMMES
        if not self.programmes or any(not values for values in self.programmes.values()):
            raise ValueError("Each programme must contain at least one indicator")
        self.rng = np.random.default_rng(self.seed)

    @property
    def indicator_count(self) -> int:
        return sum(len(v) for v in self.programmes.values())

    @property
    def expected_record_count(self) -> int:
        return self.facility_count * len(self.months) * self.indicator_count

    def generate_facilities(self) -> pd.DataFrame:
        rng = np.random.default_rng(self.seed + 101)
        numbers = np.arange(1, self.facility_count + 1)
        return pd.DataFrame({
            "Facility_ID": [f"MWI-SYN-{n:04d}" for n in numbers],
            "Facility_Name": [f"Synthetic Facility {n:04d}" for n in numbers],
            "District": [self.districts[i % len(self.districts)] for i in range(self.facility_count)],
            "Facility_Type": rng.choice(["Health Centre","Community Hospital","District Hospital"], self.facility_count, p=[.78,.17,.05]),
            "Urban_Rural": rng.choice(["Urban","Peri-urban","Rural"], self.facility_count, p=[.18,.22,.60]),
            "Ownership": rng.choice(["Public","CHAM","Private"], self.facility_count, p=[.78,.17,.05]),
            "Catchment_Population": rng.integers(4000,85000,self.facility_count),
            "Is_Synthetic": True,
        })

    def generate(self, injection_rates: dict[str,float] | None = None
                 ) -> tuple[pd.DataFrame,pd.DataFrame,dict[str,Any]]:
        rates = {"missing":.025,"source_discrepancy":.04,"outlier":.015,"late":.08}
        if injection_rates:
            unknown=set(injection_rates)-set(rates)
            if unknown: raise ValueError(f"Unknown injection rate(s): {sorted(unknown)}")
            rates.update(injection_rates)
        for name,rate in rates.items():
            if not 0 <= rate <= 1: raise ValueError(f"{name} rate must be between 0 and 1")

        facilities=self.generate_facilities()
        fidx=np.repeat(np.arange(self.facility_count),len(self.months)*self.indicator_count)
        midx=np.tile(np.repeat(np.arange(len(self.months)),self.indicator_count),self.facility_count)
        indicator_rows=[(p,i,b) for p,items in self.programmes.items() for i,b in items.items()]
        iidx=np.tile(np.arange(len(indicator_rows)),self.facility_count*len(self.months))
        n=self.expected_record_count
        programmes=np.array([x[0] for x in indicator_rows],dtype=object)[iidx]
        indicators=np.array([x[1] for x in indicator_rows],dtype=object)[iidx]
        low=np.array([x[2][0] for x in indicator_rows],dtype=float)[iidx]
        high=np.array([x[2][1] for x in indicator_rows],dtype=float)[iidx]
        target=self.rng.integers(low.astype(int),high.astype(int)+1)
        facility_effect=self.rng.lognormal(0,.12,self.facility_count)[fidx]
        seasonal=1+.06*np.sin(2*np.pi*midx/12)
        base=np.maximum(0,np.rint(target*self.rng.normal(.88,.09,n)*facility_effect*seasonal)).astype(int)
        paper=np.maximum(0,np.rint(self.rng.normal(base,np.maximum(1,target*.025))).astype(int))
        emr=np.maximum(0,np.rint(self.rng.normal(base,np.maximum(1,target*.03))).astype(int))
        dhis2=np.maximum(0,np.rint(self.rng.normal(base,np.maximum(1,target*.035))).astype(int))
        source_names=np.array(["Paper Register","EMR","DHIS2"],dtype=object)
        source_choice=self.rng.choice(3,n,p=[.25,.35,.40])
        reported=np.column_stack([paper,emr,dhis2])[np.arange(n),source_choice].astype(float)
        masks={name:self.rng.random(n)<rate for name,rate in rates.items()}
        original_reported=reported.copy()
        original_dhis2=dhis2.copy()
        outlier_mask=masks["outlier"]
        reported[outlier_mask]=np.rint(target[outlier_mask]*self.rng.uniform(2,3,outlier_mask.sum()))
        discrepancy_mask=masks["source_discrepancy"]
        dhis2[discrepancy_mask]=np.rint(dhis2[discrepancy_mask]*self.rng.choice([.55,.65,1.35,1.5],discrepancy_mask.sum())).astype(int)
        reported[masks["missing"]]=np.nan
        report_months=self.months.to_numpy()[midx]
        deadlines=pd.to_datetime(report_months)+pd.offsets.MonthEnd(0)+pd.Timedelta(days=10)
        offsets=self.rng.integers(0,9,n)
        late_mask=masks["late"]
        offsets[late_mask]=self.rng.integers(1,16,late_mask.sum())
        submissions=deadlines+pd.to_timedelta(offsets,unit="D")
        fact=pd.DataFrame({
            "Record_ID":[f"R{x:07d}" for x in range(1,n+1)],
            "Facility_ID":facilities["Facility_ID"].to_numpy()[fidx],
            "Facility":facilities["Facility_Name"].to_numpy()[fidx],
            "District":facilities["District"].to_numpy()[fidx],
            "Month":pd.to_datetime(report_months),"Programme":programmes,"Indicator":indicators,
            "Reported_Value":reported,"Target_Value":target,"Data_Source":source_names[source_choice],
            "Paper_Value":paper,"EMR_Value":emr,"DHIS2_Value":dhis2,
            "Submission_Date":submissions,"Deadline_Date":deadlines,
            "Ground_Truth_Missing":masks["missing"],
            "Ground_Truth_Source_Discrepancy":masks["source_discrepancy"],
            "Ground_Truth_Outlier":masks["outlier"],"Ground_Truth_Late":masks["late"],
            "Ground_Truth_Original_Reported_Value":original_reported,
            "Ground_Truth_Original_DHIS2_Value":original_dhis2,
        })
        manifest={"synthetic":True,"seed":self.seed,"facility_count":self.facility_count,
            "district_count":len(self.districts),"programme_count":len(self.programmes),
            "indicator_count":self.indicator_count,"period_count":len(self.months),
            "expected_record_count":n,"actual_record_count":len(fact),
            "injection_rates_requested":rates,
            "injection_counts":{k:int(v.sum()) for k,v in masks.items()},
            "note":"Ground-truth labels evaluate detection methods; they are not operational inputs."}
        return fact,facilities,manifest

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed",type=int,default=42)
    parser.add_argument("--facilities",type=int,default=120)
    parser.add_argument("--start-month",default="2021-01-01")
    parser.add_argument("--periods",type=int,default=60)
    parser.add_argument("--output-dir",default="data/warehouse/raw")
    args=parser.parse_args()
    generator=ScaledHealthDataGenerator(args.seed,args.facilities,args.start_month,args.periods)
    fact,facilities,manifest=generator.generate()
    output=Path(args.output_dir); output.mkdir(parents=True,exist_ok=True)
    fact.to_csv(output/"facility_reporting_fact.csv",index=False)
    facilities.to_csv(output/"facility_dimension.csv",index=False)
    (output/"generation_manifest.json").write_text(json.dumps(manifest,indent=2))
    print(json.dumps(manifest,indent=2)); print(f"Saved outputs to {output.resolve()}")

if __name__=="__main__":
    main()
