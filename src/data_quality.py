"""
Data Quality Assessment Module

Provides functions for calculating data quality metrics, validating data,
and detecting data-quality problems in health facility reporting data.
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional
import json
from pathlib import Path


class DataQualityAssessor:
    """Assesses data quality in health facility reporting data."""
    
    def __init__(self, df: pd.DataFrame):
        """
        Initialize the assessor with a dataset.
        
        Args:
            df: DataFrame containing health facility reporting data
        """
        self.df = df.copy()
        self.required_fields = [
            "Facility", "Month", "Programme", "Indicator",
            "Reported_Value", "Target_Value", "Data_Source",
            "Paper_Value", "EMR_Value", "DHIS2_Value"
        ]
    
    def validate_schema(self) -> Dict[str, any]:
        """
        Validate that the dataset has the expected schema.
        
        Returns:
            Dictionary with validation results
        """
        missing_columns = [col for col in self.required_fields if col not in self.df.columns]
        
        # Check for duplicate keys
        if all(col in self.df.columns for col in ["Facility", "Month", "Programme", "Indicator"]):
            key_cols = ["Facility", "Month", "Programme", "Indicator"]
            duplicates = self.df.duplicated(subset=key_cols).sum()
        else:
            duplicates = None
        
        # Check date range
        if "Month" in self.df.columns:
            self.df["Month"] = pd.to_datetime(self.df["Month"], errors="coerce")
            invalid_dates = self.df["Month"].isna().sum()
            date_range = (
                self.df["Month"].min(),
                self.df["Month"].max()
            ) if self.df["Month"].notna().any() else (None, None)
        else:
            invalid_dates = None
            date_range = (None, None)
        
        return {
            "has_required_columns": len(missing_columns) == 0,
            "missing_columns": missing_columns,
            "total_rows": len(self.df),
            "duplicate_keys": duplicates,
            "invalid_dates": invalid_dates,
            "date_range": date_range,
        }
    
    def calculate_field_completeness(self) -> pd.DataFrame:
        """
        Calculate completeness from actual field presence.
        
        For each record, completeness is calculated as the proportion of
        required fields that are present and valid (not null/empty).
        
        Returns:
            DataFrame with added Calculated_Completeness field
        """
        required_numeric = ["Reported_Value", "Target_Value", "Paper_Value", "EMR_Value", "DHIS2_Value"]
        required_categorical = ["Data_Source"]
        
        def row_completeness(row):
            present = 0
            total = len(required_numeric) + len(required_categorical)
            
            for field in required_numeric:
                if pd.notna(row[field]) and row[field] != "":
                    present += 1
            
            for field in required_categorical:
                if pd.notna(row[field]) and row[field] != "":
                    present += 1
            
            return present / total if total > 0 else 0
        
        self.df["Calculated_Completeness"] = self.df.apply(row_completeness, axis=1)
        
        return self.df
    
    def calculate_timeliness_from_dates(self, submission_date_col: str = None,
                                        deadline_col: str = None) -> pd.DataFrame:
        """
        Calculate timeliness from submission and deadline dates.
        
        If submission_date_col and deadline_col are not provided, this function
        will create simulated fields for demonstration purposes.
        
        Args:
            submission_date_col: Name of submission date column
            deadline_col: Name of deadline column
            
        Returns:
            DataFrame with added Calculated_Timeliness field
        """
        if submission_date_col and deadline_col:
            if submission_date_col in self.df.columns and deadline_col in self.df.columns:
                self.df[submission_date_col] = pd.to_datetime(self.df[submission_date_col], errors="coerce")
                self.df[deadline_col] = pd.to_datetime(self.df[deadline_col], errors="coerce")
                
                # On time if submission <= deadline (submission on deadline counts as on time)
                self.df["Calculated_Timeliness"] = np.where(
                    self.df[submission_date_col] <= self.df[deadline_col],
                    "On Time",
                    "Late"
                )
                
                # Handle missing dates
                self.df.loc[self.df[submission_date_col].isna(), "Calculated_Timeliness"] = "Unknown"
                self.df.loc[self.df[deadline_col].isna(), "Calculated_Timeliness"] = "Unknown"
            else:
                raise ValueError(f"Columns {submission_date_col} or {deadline_col} not found")
        else:
            # For synthetic data without actual submission/deadline dates,
            # we'll use the simulated Timeliness field as a placeholder
            if "Timeliness" in self.df.columns:
                self.df["Calculated_Timeliness"] = self.df["Timeliness"]
            else:
                self.df["Calculated_Timeliness"] = "Unknown"
        
        return self.df
    
    def assess_source_consistency(self, baseline_threshold: float = 0.10,
                                  improved_threshold: float = 0.20,
                                  absolute_tolerance: int = 5) -> pd.DataFrame:
        """
        Assess consistency between Paper, EMR, and DHIS2 sources.
        
        Implements both a baseline 10% rule and an improved rule that:
        - Uses absolute tolerance for low-volume indicators
        - Uses relative tolerance for higher-volume indicators
        - Handles zero minimum values explicitly
        
        Args:
            baseline_threshold: Baseline relative threshold (default 0.10 = 10%)
            improved_threshold: Improved relative threshold (default 0.20 = 20%)
            absolute_tolerance: Absolute tolerance for low-volume indicators
            
        Returns:
            DataFrame with consistency flags and discrepancy measures
        """
        source_columns = ["Paper_Value", "EMR_Value", "DHIS2_Value"]
        
        # Calculate source statistics
        self.df["Source_Max"] = self.df[source_columns].max(axis=1)
        self.df["Source_Min"] = self.df[source_columns].min(axis=1)
        self.df["Source_Discrepancy_Abs"] = self.df["Source_Max"] - self.df["Source_Min"]
        
        # Baseline rule: relative discrepancy
        self.df["Source_Discrepancy_Pct_Baseline"] = np.where(
            self.df["Source_Min"] > 0,
            self.df["Source_Discrepancy_Abs"] / self.df["Source_Min"],
            np.nan
        )
        
        source_count = self.df[source_columns].notna().sum(axis=1)
        insufficient_sources = source_count < 2

        self.df["Consistency_Flag_Baseline"] = np.where(
            insufficient_sources,
            "Unknown Sources",
            np.where(
                self.df["Source_Discrepancy_Pct_Baseline"] > baseline_threshold,
                "Review Required",
                "Consistent"
            )
        )
        
        # Improved rule: hybrid absolute + relative
        self.df["Consistency_Flag_Improved"] = np.where(
            # If all sources are missing, mark as unknown
            insufficient_sources,
            "Unknown Sources",
            np.where(
                # If minimum is zero, use absolute tolerance
                (self.df["Source_Min"] == 0),
                np.where(
                    self.df["Source_Discrepancy_Abs"] > absolute_tolerance,
                    "Review Required",
                    "Consistent"
                ),
                # For positive values, require both a material relative
                # difference and an absolute difference above tolerance.
                np.where(
                    (self.df["Source_Discrepancy_Pct_Baseline"] > improved_threshold)
                    & (self.df["Source_Discrepancy_Abs"] > absolute_tolerance),
                    "Review Required",
                    "Consistent"
                )
            )
        )
        
        # Use the volume-aware hybrid rule as the production flag.
        # Preserve the 10% baseline in its separate diagnostic column for comparison.
        self.df["Consistency_Flag"] = self.df["Consistency_Flag_Improved"]
        
        return self.df
    
    def detect_outliers_iqr(self, groupby_cols: list = ["Programme", "Indicator"],
                           iqr_multiplier: float = 1.5,
                           min_observations: int = 5) -> pd.DataFrame:
        """
        Detect outliers using IQR method within groups.
        
        Args:
            groupby_cols: Columns to group by for IQR calculation
            iqr_multiplier: Multiplier for IQR bounds (default 1.5)
            min_observations: Minimum observations required to apply IQR rule
            
        Returns:
            DataFrame with Outlier_Flag field
        """
        # Use an explicit group loop rather than groupby.apply. This keeps the
        # result a one-dimensional Series across pandas versions (including 3.x).
        outlier_flags = pd.Series(False, index=self.df.index, dtype=bool)
        for _, group in self.df.groupby(groupby_cols, group_keys=False, dropna=False, sort=False):
            if len(group) < min_observations:
                continue

            values = pd.to_numeric(group["Reported_Value"], errors="coerce")
            q1 = values.quantile(0.25)
            q3 = values.quantile(0.75)
            iqr = q3 - q1
            if pd.isna(iqr) or iqr == 0:
                continue

            lower = q1 - iqr_multiplier * iqr
            upper = q3 + iqr_multiplier * iqr
            group_flags = ((values < lower) | (values > upper)).fillna(False)
            outlier_flags.loc[group.index] = group_flags.astype(bool)

        self.df["Outlier_Flag"] = outlier_flags
        
        return self.df
    
    def assign_primary_issue(self) -> pd.DataFrame:
        """
        Assign a primary issue label to each record based on priority.
        
        Priority order: Missing Data > Insufficient Source Data > Source Discrepancy >
        Late Reporting > Potential Outlier > Low Completeness > No Major Issue
        
        Returns:
            DataFrame with Primary_Issue field
        """
        conditions = [
            self.df["Reported_Value"].isna(),
            self.df["Consistency_Flag"] == "Unknown Sources",
            self.df["Consistency_Flag"] == "Review Required",
            self.df.get("Calculated_Timeliness", self.df.get("Timeliness", pd.Series())) == "Late",
            self.df["Outlier_Flag"] == True,
            self.df.get("Calculated_Completeness", self.df.get("Completeness_Score", pd.Series())) < 0.80,
        ]
        
        choices = [
            "Missing Data",
            "Insufficient Source Data",
            "Source Discrepancy",
            "Late Reporting",
            "Potential Outlier",
            "Low Completeness"
        ]
        
        self.df["Primary_Issue"] = np.select(conditions, choices, default="No Major Issue")
        
        return self.df
    
    def calculate_facility_risk(self, weights: Dict[str, float] = None) -> pd.DataFrame:
        """
        Calculate comparable facility risk scores from issue rates.

        Default weights allocate 20 points to each of five dimensions, producing
        a 0-100 index. Scores are prioritisation aids, not clinical performance
        ratings. Custom weights may be supplied using the same five keys.
        """
        if weights is None:
            weights = {
                "completeness_shortfall": 20,
                "late": 20,
                "discrepancy": 20,
                "missing": 20,
                "outlier": 20,
            }

        completeness_col = (
            "Calculated_Completeness"
            if "Calculated_Completeness" in self.df.columns
            else "Completeness_Score"
        )
        timeliness_col = (
            "Calculated_Timeliness"
            if "Calculated_Timeliness" in self.df.columns
            else "Timeliness"
        )
        required = [completeness_col, timeliness_col, "Consistency_Flag",
                    "Reported_Value", "Outlier_Flag"]
        missing_columns = [column for column in required if column not in self.df.columns]
        if missing_columns:
            raise ValueError(
                "Cannot calculate facility risk; missing columns: "
                + ", ".join(missing_columns)
            )

        facility_quality = self.df.groupby("Facility").agg(
            Average_Completeness=(completeness_col, "mean"),
            Total_Records=("Facility", "size"),
            Late_Rate=(timeliness_col, lambda x: (x == "Late").mean()),
            Source_Discrepancy_Rate=(
                "Consistency_Flag",
                lambda x: (
                    x[x.isin(["Consistent", "Review Required", "Inconsistent"])]
                    .isin(["Review Required", "Inconsistent"]).mean()
                    if x.isin(["Consistent", "Review Required", "Inconsistent"]).any()
                    else 0.0
                ),
            ),
            Missing_Rate=("Reported_Value", lambda x: x.isna().mean()),
            Outlier_Rate=("Outlier_Flag", "mean"),
        )

        facility_quality["Risk_Score"] = (
            (1 - facility_quality["Average_Completeness"]) * weights["completeness_shortfall"]
            + facility_quality["Late_Rate"] * weights["late"]
            + facility_quality["Source_Discrepancy_Rate"] * weights["discrepancy"]
            + facility_quality["Missing_Rate"] * weights["missing"]
            + facility_quality["Outlier_Rate"] * weights["outlier"]
        )
        return facility_quality.sort_values("Risk_Score", ascending=False)

    def validate_against_injections(self, injection_ledger_path: Path) -> Dict[str, any]:
        """
        Validate detection rules against injected ground truth.
        
        Args:
            injection_ledger_path: Path to injection ledger JSON file
            
        Returns:
            Dictionary with validation results including precision/recall
        """
        with open(injection_ledger_path, 'r') as f:
            ledger = json.load(f)
        
        # Create sets of injected indices
        injected_missing = set(item["index"] for item in ledger["missing_values"])
        injected_discrepancy = set(item["index"] for item in ledger["source_discrepancies"])
        injected_outlier = set(item["index"] for item in ledger["outliers"])
        injected_late = set(item["index"] for item in ledger["late_reports"])
        
        # Get detected indices
        detected_missing = set(self.df[self.df["Reported_Value"].isna()].index)
        detected_discrepancy = set(self.df[self.df["Consistency_Flag"] == "Review Required"].index)
        detected_outlier = set(self.df[self.df["Outlier_Flag"] == True].index)
        detected_late = set(self.df[self.df["Timeliness"] == "Late"].index)
        
        # Calculate metrics for each issue type
        def calculate_metrics(injected, detected):
            true_positives = len(injected & detected)
            false_positives = len(detected - injected)
            false_negatives = len(injected - detected)
            true_negatives = len(self.df) - true_positives - false_positives - false_negatives
            
            precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else None
            recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else None
            
            return {
                "true_positives": true_positives,
                "false_positives": false_positives,
                "false_negatives": false_negatives,
                "true_negatives": true_negatives,
                "precision": precision,
                "recall": recall,
            }
        
        return {
            "missing_values": calculate_metrics(injected_missing, detected_missing),
            "source_discrepancies": calculate_metrics(injected_discrepancy, detected_discrepancy),
            "outliers": calculate_metrics(injected_outlier, detected_outlier),
            "late_reports": calculate_metrics(injected_late, detected_late),
        }
    
    def get_summary_metrics(self) -> Dict[str, any]:
        """Calculate summary data-quality metrics."""
        completeness_col = "Calculated_Completeness" if "Calculated_Completeness" in self.df.columns else "Completeness_Score"
        timeliness_col = "Calculated_Timeliness" if "Calculated_Timeliness" in self.df.columns else "Timeliness"
        
        overall_completeness = self.df[completeness_col].mean()
        timely_reporting = (self.df[timeliness_col] == "On Time").mean()
        consistency_rate = (self.df["Consistency_Flag"] == "Consistent").mean()
        total_issues = (self.df["Primary_Issue"] != "No Major Issue").sum()
        
        return {
            "overall_completeness": overall_completeness,
            "timely_reporting": timely_reporting,
            "consistency_rate": consistency_rate,
            "total_issues": total_issues,
            "total_records": len(self.df),
            "issues_percentage": total_issues / len(self.df),
        }
