# Power BI Dashboard — Implementation Documentation

**Status: built.** A Power BI report file exists at `dashboard/health_facility_data_quality_dashboard.pbix` with four pages: Data Quality Overview, Facility Performance, Source Consistency, and Programme Monitoring. Screenshots of each page are available in the dashboard folder.

This documentation describes the data model, measures, and design that were used to build the report, based on the fields and findings in `data/processed/health_facility_data_processed.csv` (produced by `notebooks/health_data_quality_analysis.ipynb`).

All data behind this dashboard is synthetic (see the project [README](../README.md)). Any screenshots added after building should carry the same synthetic-data notice.

---

## 1. Data source

Import `data/processed/health_facility_data_processed.csv`. This file contains all calculated data quality metrics including:
- `Calculated_Completeness` (0-1 scale, based on actual field presence)
- `Calculated_Timeliness` ("On Time" or "Late", based on reporting dates)
- `Consistency_Flag` ("Consistent" or "Inconsistent", using 20% relative + 5 absolute threshold)
- `Outlier_Flag` (boolean, using IQR method grouped by indicator)
- `Reported_Value_Missing` (boolean, ground truth from data generation)
- Source comparison fields: `Source_Max`, `Source_Min`, `Source_Discrepancy`, `Source_Discrepancy_Pct`
- `Month` (period field for time-based analysis)

## 2. Data model

A single flat table is sufficient for this dataset's size and structure — one row per Facility x Month x Programme x Indicator. Add a **Calendar** date table related to `Month`, marked as a Date Table, so month-over-month and trend visuals use proper time intelligence rather than the raw text/date column directly.

```
Calendar (date dimension) ---1:*--- health_facility_data_processed (fact/flat table)
```

## 3. Measures (DAX)

Only measures the dataset actually supports:

```dax
Overall Completeness = AVERAGE(health_facility_data_processed[Calculated_Completeness])

Timely Reporting % = 
    DIVIDE(
        CALCULATE(COUNTROWS(health_facility_data_processed), health_facility_data_processed[Calculated_Timeliness] = "On Time"),
        COUNTROWS(health_facility_data_processed)
    )

Source Consistency % = 
    DIVIDE(
        CALCULATE(COUNTROWS(health_facility_data_processed), health_facility_data_processed[Consistency_Flag] = "Consistent"),
        COUNTROWS(health_facility_data_processed)
    )

Missing Reports = CALCULATE(COUNTROWS(health_facility_data_processed), health_facility_data_processed[Reported_Value_Missing] = TRUE)

Late Reports = CALCULATE(COUNTROWS(health_facility_data_processed), health_facility_data_processed[Calculated_Timeliness] = "Late")

Outlier Count = CALCULATE(COUNTROWS(health_facility_data_processed), health_facility_data_processed[Outlier_Flag] = TRUE)
```

**Why `DIVIDE()` instead of `/`:** returns `BLANK()` rather than erroring when a filter/slicer selection produces a zero-row context (e.g. a facility/month combination with no records) — this happens often once slicers are added.

## 4. Facility risk table (calculated in Power Query or DAX)

The per-facility `Risk_Score` calculated in Section 10 of the notebook uses rate-based metrics (normalized by reporting volume) rather than raw counts. The summary includes:
- `Missing_Rate` (proportion of records with missing values)
- `Inconsistent_Rate` (proportion flagged as inconsistent)
- `Late_Rate` (proportion submitted late)
- `Outlier_Rate` (proportion flagged as outliers)
- `Avg_Completeness` (average calculated completeness)
- `Risk_Score` (0-100 scale, weighted sum of the five dimensions)

Build this as either:
- a **Power Query summarized table**, replicating the notebook's `groupby().agg()`, or
- a **DAX summarize table** using `SUMMARIZE`/`ADDCOLUMNS` over the fact table.

This table drives Page 2 (Facility Performance) and the risk ranking visual.

## 5. Pages

### Page 1 — Data Quality Overview

KPI cards: `[Overall Completeness]`, `[Timely Reporting %]`, `[Source Consistency %]`, `[Missing Reports]`, `[Late Reports]`, `[Outlier Count]`.

Visuals:
- Data-quality issue trend by month (line chart, showing rates of missing, late, inconsistent, and outlier records over `Month`)
- Completeness by facility (bar chart using `Calculated_Completeness`)
- Issue breakdown by type (bar/donut chart showing counts of missing, late, inconsistent, outlier records)
- Completeness by programme (bar chart using `Calculated_Completeness`)

Slicers: Month, Facility, Programme, Indicator, Data_Source.

### Page 2 — Facility Performance

Selecting a facility (via slicer or a facility-list visual) filters:
- Risk score, completeness rate, timeliness rate, inconsistency rate, outlier rate (cards from facility risk table)
- Monthly completeness/timeliness trend for the selected facility (line chart using rates)
- A detail table: Programme, Indicator, Month, Reported_Value, Target_Value, Calculated_Completeness, Calculated_Timeliness, Consistency_Flag, Outlier_Flag — this is the actual follow-up worklist an M&E Officer would use.

### Page 3 — Source Consistency

The strongest page, since source reconciliation is the core data-quality question here:
- Average `Source_Discrepancy_Pct` by facility (bar)
- Inconsistent records count by facility and by programme (bar)
- Monthly inconsistency rate trend (line chart using rates)
- Scatter: `Source_Min` vs `Source_Max` per record, colored by `Consistency_Flag`, to visually show how far apart the three systems land

### Page 4 — Programme Monitoring

- Reported value vs. target, over time, filterable by Programme and Indicator (line/combo chart)
- Small multiples or a matrix for HIV / TB / Maternal Health / Child Health / Outpatient side by side

## 6. An honest caveat worth building into Page 3 directly

The notebook initially found that using a simple 10% discrepancy threshold flagged a large majority of records as inconsistent due to natural random variation between the three independent sources. This was particularly problematic for low-volume indicators where small absolute differences resulted in large percentage swings.

**The improved implementation uses a more realistic threshold: 20% relative difference OR 5 absolute count difference.** This dual threshold approach:
- Reduces false positives for high-volume indicators (where 20% is meaningful)
- Reduces false positives for low-volume indicators (where 5 absolute units is a meaningful threshold)
- Better reflects operational M&E practice where thresholds are often volume-adjusted

**This is worth a callout box directly on Page 3**, because it explains why the current consistency rate is more usable than a simple 10% threshold would be. Users should understand that the threshold choice significantly affects what gets flagged for review.

## 7. Build order

1. Import data, build the Calendar table, build the Facility Risk summary table
2. Write the core measures (Section 3)
3. Build Page 1's KPI cards, checking each against the Python notebook's printed summary numbers
4. Build Pages 2–4 one visual at a time, sense-checking against the notebook
5. Add the Page 3 threshold-sensitivity callout (Section 6) — don't skip this; it's the difference between a dashboard that looks complete and one that's actually trustworthy
6. Add slicers last
7. Screenshot into `visuals/` and link from the main README
