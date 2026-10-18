"""
Synthetic Health Facility Data Generator

Generates reproducible synthetic health facility reporting data with controlled
data-quality problem injections for testing data-quality assessment workflows.

All data is synthetic and does not represent actual facility or Ministry of Health data.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple
import json


class HealthDataGenerator:
    """Generates synthetic health facility data with traceable quality problem injections."""
    
    def __init__(self, random_seed: int = 42):
        """
        Initialize the generator with a fixed random seed for reproducibility.
        
        Args:
            random_seed: Fixed seed for reproducible data generation
        """
        self.random_seed = random_seed
        np.random.seed(random_seed)
        
        # Configuration
        self.facilities = [
            "Rumphi Central Health Centre",
            "Bolero Health Centre",
            "Mhuju Health Centre",
            "Chiweta Health Centre",
            "Katowo Health Centre",
            "Kachulu Health Centre",
            "Chitimba Health Centre",
            "Nyika Health Centre",
        ]
        
        self.programme_indicators = {
            "HIV": ["Patients on ART", "New ART Initiations"],
            "TB": ["New TB Cases", "TB Treatment Completions"],
            "Maternal Health": ["ANC Visits", "Facility Deliveries"],
            "Child Health": ["Immunisation Visits", "Under-5 Visits"],
            "Outpatient": ["OPD Visits", "New Outpatient Cases"],
        }
        
        self.months = pd.date_range(start="2025-01-01", end="2025-12-01", freq="MS")
        
        # Injection tracking
        self.injection_ledger = {
            "missing_values": [],
            "source_discrepancies": [],
            "outliers": [],
            "late_reports": []
        }
        
    def _get_target_range(self, indicator: str) -> Tuple[int, int]:
        """Return target range for a given indicator."""
        target_ranges = {
            "Patients on ART": (300, 900),
            "New ART Initiations": (20, 100),
            "New TB Cases": (10, 60),
            "TB Treatment Completions": (10, 50),
            "ANC Visits": (80, 300),
            "Facility Deliveries": (50, 200),
            "Immunisation Visits": (100, 500),
            "Under-5 Visits": (150, 600),
            "OPD Visits": (500, 1500),
            "New Outpatient Cases": (300, 1000),
        }
        return target_ranges.get(indicator, (100, 500))
    
    def generate_base_data(self) -> pd.DataFrame:
        """
        Generate the base dataset without quality problems.
        
        Returns:
            DataFrame with 960 rows (8 facilities × 12 months × 5 programmes × 2 indicators)
        """
        rows = []
        
        for facility in self.facilities:
            for month in self.months:
                for programme, indicators in self.programme_indicators.items():
                    for indicator in indicators:
                        target_min, target_max = self._get_target_range(indicator)
                        target = np.random.randint(target_min, target_max)
                        
                        # Generate base value with some natural variation
                        base_value = max(0, int(np.random.normal(target * 0.9, target * 0.15)))
                        
                        # Generate three source values with small random variation
                        paper = max(0, int(np.random.normal(base_value, max(2, target * 0.03))))
                        emr = max(0, int(np.random.normal(base_value, max(2, target * 0.04))))
                        dhis2 = max(0, int(np.random.normal(base_value, max(2, target * 0.04))))
                        
                        # Select data source
                        data_source = np.random.choice(
                            ["Paper Register", "EMR", "DHIS2"], p=[0.25, 0.35, 0.40]
                        )
                        source_values = {"Paper Register": paper, "EMR": emr, "DHIS2": dhis2}
                        reported_value = source_values[data_source]
                        
                        # Generate simulated completeness and timeliness
                        # (These will be replaced with calculated fields later)
                        completeness = np.random.uniform(0.80, 1.00)
                        if np.random.random() < 0.08:
                            completeness = np.random.uniform(0.40, 0.75)
                        
                        timely = np.random.choice(["On Time", "Late"], p=[0.88, 0.12])
                        
                        rows.append({
                            "Facility": facility,
                            "Month": month,
                            "Programme": programme,
                            "Indicator": indicator,
                            "Reported_Value": reported_value,
                            "Target_Value": target,
                            "Data_Source": data_source,
                            "Paper_Value": paper,
                            "EMR_Value": emr,
                            "DHIS2_Value": dhis2,
                            "Completeness_Score_Simulated": completeness,
                            "Timeliness_Simulated": timely,
                        })
        
        df = pd.DataFrame(rows)
        return df
    
    def inject_missing_values(self, df: pd.DataFrame, frac: float = 0.03, 
                             injection_seed: int = 10) -> pd.DataFrame:
        """
        Inject missing reported values.
        
        Args:
            df: Input dataframe
            frac: Fraction of rows to inject missing values into
            injection_seed: Random seed for injection selection
            
        Returns:
            Modified dataframe with injected missing values
        """
        np.random.seed(injection_seed)
        missing_indices = df.sample(frac=frac, random_state=injection_seed).index.tolist()
        
        df.loc[missing_indices, "Reported_Value"] = np.nan
        
        # Track injection
        for idx in missing_indices:
            self.injection_ledger["missing_values"].append({
                "index": int(idx),
                "facility": df.loc[idx, "Facility"],
                "month": str(df.loc[idx, "Month"]),
                "programme": df.loc[idx, "Programme"],
                "indicator": df.loc[idx, "Indicator"],
            })
        
        return df
    
    def inject_source_discrepancies(self, df: pd.DataFrame, frac: float = 0.05,
                                    injection_seed: int = 20) -> pd.DataFrame:
        """
        Inject source discrepancies by perturbing DHIS2 values.
        
        Args:
            df: Input dataframe
            frac: Fraction of rows to inject discrepancies into
            injection_seed: Random seed for injection selection
            
        Returns:
            Modified dataframe with injected source discrepancies
        """
        np.random.seed(injection_seed)
        discrepancy_indices = df.sample(frac=frac, random_state=injection_seed).index.tolist()
        
        perturbation_factors = np.random.uniform(0.60, 1.40, len(discrepancy_indices))
        
        for idx, factor in zip(discrepancy_indices, perturbation_factors):
            original_dhis2 = df.loc[idx, "DHIS2_Value"]
            df.loc[idx, "DHIS2_Value"] = int(round(original_dhis2 * factor))
            
            # Track injection
            self.injection_ledger["source_discrepancies"].append({
                "index": int(idx),
                "facility": df.loc[idx, "Facility"],
                "month": str(df.loc[idx, "Month"]),
                "programme": df.loc[idx, "Programme"],
                "indicator": df.loc[idx, "Indicator"],
                "original_dhis2": int(original_dhis2),
                "perturbed_dhis2": int(df.loc[idx, "DHIS2_Value"]),
                "perturbation_factor": round(float(factor), 4),
            })
        
        return df
    
    def inject_outliers(self, df: pd.DataFrame, frac: float = 0.02,
                       injection_seed: int = 30) -> pd.DataFrame:
        """
        Inject outliers by inflating reported values to 2-3x target.
        
        Args:
            df: Input dataframe
            frac: Fraction of rows to inject outliers into
            injection_seed: Random seed for injection selection
            
        Returns:
            Modified dataframe with injected outliers
        """
        np.random.seed(injection_seed)
        outlier_indices = df.sample(frac=frac, random_state=injection_seed).index.tolist()
        
        inflation_factors = np.random.uniform(2.0, 3.0, len(outlier_indices))
        
        for idx, factor in zip(outlier_indices, inflation_factors):
            target = df.loc[idx, "Target_Value"]
            original_value = df.loc[idx, "Reported_Value"]
            df.loc[idx, "Reported_Value"] = int(round(target * factor))
            
            # Track injection
            self.injection_ledger["outliers"].append({
                "index": int(idx),
                "facility": df.loc[idx, "Facility"],
                "month": str(df.loc[idx, "Month"]),
                "programme": df.loc[idx, "Programme"],
                "indicator": df.loc[idx, "Indicator"],
                "original_value": float(original_value) if pd.notna(original_value) else None,
                "injected_value": int(df.loc[idx, "Reported_Value"]),
                "target": int(target),
                "inflation_factor": round(float(factor), 4),
            })
        
        return df
    
    def inject_late_reports(self, df: pd.DataFrame, frac: float = 0.08,
                            injection_seed: int = 40) -> pd.DataFrame:
        """
        Inject late reports by forcing Timeliness to "Late".
        
        Args:
            df: Input dataframe
            frac: Fraction of rows to force to late
            injection_seed: Random seed for injection selection
            
        Returns:
            Modified dataframe with injected late reports
        """
        np.random.seed(injection_seed)
        late_indices = df.sample(frac=frac, random_state=injection_seed).index.tolist()
        
        for idx in late_indices:
            original_timeliness = df.loc[idx, "Timeliness_Simulated"]
            df.loc[idx, "Timeliness_Simulated"] = "Late"
            
            # Track injection
            self.injection_ledger["late_reports"].append({
                "index": int(idx),
                "facility": df.loc[idx, "Facility"],
                "month": str(df.loc[idx, "Month"]),
                "programme": df.loc[idx, "Programme"],
                "indicator": df.loc[idx, "Indicator"],
                "original_timeliness": original_timeliness,
            })
        
        return df
    
    def generate(self, injection_rates: Dict[str, float] = None) -> Tuple[pd.DataFrame, Dict]:
        """
        Generate the complete synthetic dataset with all injections.
        
        Args:
            injection_rates: Dictionary specifying injection rates for each problem type.
                            Defaults to: missing=0.03, discrepancy=0.05, outlier=0.02, late=0.08
        
        Returns:
            Tuple of (generated dataframe, injection_ledger)
        """
        if injection_rates is None:
            injection_rates = {
                "missing": 0.03,
                "discrepancy": 0.05,
                "outlier": 0.02,
                "late": 0.08,
            }
        
        # Generate base data
        df = self.generate_base_data()
        
        # Apply injections in sequence
        df = self.inject_missing_values(
            df, frac=injection_rates["missing"], injection_seed=10
        )
        df = self.inject_source_discrepancies(
            df, frac=injection_rates["discrepancy"], injection_seed=20
        )
        df = self.inject_outliers(
            df, frac=injection_rates["outlier"], injection_seed=30
        )
        df = self.inject_late_reports(
            df, frac=injection_rates["late"], injection_seed=40
        )
        
        # Rename simulated fields to match original schema
        df = df.rename(columns={
            "Completeness_Score_Simulated": "Completeness_Score",
            "Timeliness_Simulated": "Timeliness"
        })
        
        return df, self.injection_ledger
    
    def save_injection_ledger(self, output_path: Path):
        """Save the injection ledger to a JSON file."""
        with open(output_path, 'w') as f:
            json.dump(self.injection_ledger, f, indent=2)
    
    def get_injection_summary(self) -> Dict:
        """Return a summary of injections."""
        return {
            "missing_values": len(self.injection_ledger["missing_values"]),
            "source_discrepancies": len(self.injection_ledger["source_discrepancies"]),
            "outliers": len(self.injection_ledger["outliers"]),
            "late_reports": len(self.injection_ledger["late_reports"]),
        }


def main():
    """Generate and save synthetic data with injection ledger."""
    generator = HealthDataGenerator(random_seed=42)
    df, ledger = generator.generate()
    
    # Save raw data
    raw_dir = Path("data/raw")
    raw_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(raw_dir / "synthetic_health_facility_data.csv", index=False)
    
    # Save injection ledger
    generator.save_injection_ledger(raw_dir / "injection_ledger.json")
    
    print(f"Generated dataset: {df.shape[0]:,} rows x {df.shape[1]} columns")
    print(f"Injection summary: {generator.get_injection_summary()}")
    print(f"Saved to: {raw_dir / 'synthetic_health_facility_data.csv'}")
    print(f"Injection ledger: {raw_dir / 'injection_ledger.json'}")


if __name__ == "__main__":
    main()
