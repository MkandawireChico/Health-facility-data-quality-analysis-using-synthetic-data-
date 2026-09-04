# Power BI Dashboard — Implementation Documentation

**Status: not yet built.** This is a structured implementation plan, written from the actual fields and findings in `data/processed/cleaned_health_facility_data.csv` (produced by `notebooks/health_data_quality_analysis.ipynb`), for building the dashboard in Power BI Desktop.

All data behind this dashboard is synthetic (see the project [README](../README.md)). Any screenshots added after building should carry the same synthetic-data notice.

---

## 1. Data source

Import `data/processed/cleaned_health_facility_data.csv`. It already has `Month` as a real date, all data-quality flags computed (`Consistency_Flag`, `Outlier_Flag`, `Primary_Issue`, `Reported_Value_Missing`), and the source-comparison fields (`Source_Max`, `Source_Min`, `Source_Discrepancy`, `Source_Discrepancy_Pct`).

## 2. Data model

A single flat table is sufficient for this dataset's size and structure — one row per Facility x Month x Programme x Indicator. Add a **Calendar** date table related to `Month`, marked as a Date Table, so month-over-month and trend visuals use proper time intelligence rather than the raw text/date column directly.

```
Calendar (date dimension) ---1:*--- cleaned_health_facility_data (fact/flat table)
```

## 3. Measures (DAX)

Only measures the dataset actually supports:

```dax
Overall Completeness = AVERAGE(health_data[Completeness_Score])

Timely Reporting % = 
    DIVIDE(
        CALCULATE(COUNTROWS(health_data), health_data[Timeliness] = "On Time"),
        COUNTROWS(health_data)
    )

Source Consistency % = 
    DIVIDE(
        CALCULATE(COUNTROWS(health_data), health_data[Consistency_Flag] = "Consistent"),
        COUNTROWS(health_data)
    )

Records Requiring Review = 
    CALCULATE(COUNTROWS(health_data), health_data[Primary_Issue] <> "No Major Issue")

Records Requiring Review % = DIVIDE([Records Requiring Review], COUNTROWS(health_data))

Missing Reports = CALCULATE(COUNTROWS(health_data), health_data[Reported_Value_Missing] = TRUE)

Late Reports = CALCULATE(COUNTROWS(health_data), health_data[Timeliness] = "Late")

Facilities Above Median Risk = 
    -- computed on the Facility Risk table (Section 5) rather than the flat fact table
    CALCULATE(
        DISTINCTCOUNT(facility_risk[Facility]),
        facility_risk[Risk_Score] > MEDIAN(facility_risk[Risk_Score])
    )
```

**Why `DIVIDE()` instead of `/`:** returns `BLANK()` rather than erroring when a filter/slicer selection produces a zero-row context (e.g. a facility/month combination with no records) — this happens often once slicers are added.

## 4. Facility risk table (calculated in Power Query or DAX)

The per-facility `Risk_Score` calculated in Section 10 of the notebook (`Average_Completeness`, `Late_Reports`, `Source_Discrepancies`, `Missing_Records`, `Outliers`, `Risk_Score`) should be built as either:
- a **Power Query summarized table**, replicating the notebook's `groupby().agg()`, or
- a **DAX summarize table** using `SUMMARIZE`/`ADDCOLUMNS` over the fact table.

Either way, this table drives Page 2 (Facility Performance) and the risk ranking visual.

## 5. Pages

### Page 1 — Data Quality Overview

KPI cards: `[Overall Completeness]`, `[Timely Reporting %]`, `[Source Consistency %]`, `[Records Requiring Review]`, Facilities Above Median Risk.

Visuals:
- Data-quality issue trend by month (line chart, `Primary_Issue` count over `Month`)
- Completeness by facility (bar)
- Records by `Primary_Issue` type (bar/donut)
- Completeness by programme (bar)

Slicers: Month, Facility, Programme, Indicator, Data_Source.

### Page 2 — Facility Performance

Selecting a facility (via slicer or a facility-list visual) filters:
- Completeness score, timeliness rate, discrepancy count, missing-record count, outlier count (cards)
- Monthly completeness/timeliness trend for the selected facility (line)
- A detail table: Programme, Indicator, Month, Primary_Issue, Reported_Value, Target_Value — this is the actual follow-up worklist an M&E Officer would use.

### Page 3 — Source Consistency

The strongest page, since source reconciliation is the core data-quality question here:
- Average `Source_Discrepancy_Pct` by facility (bar)
- Number of `Review Required` records by facility and by programme (bar)
- Monthly discrepancy trend (line)
- Scatter: `Source_Min` vs `Source_Max` per record, colored by `Consistency_Flag`, to visually show how far apart the three systems land

### Page 4 — Programme Monitoring

- Reported value vs. target, over time, filterable by Programme and Indicator (line/combo chart)
- Small multiples or a matrix for HIV / TB / Maternal Health / Child Health / Outpatient side by side

## 6. An honest caveat worth building into Page 3 directly

The notebook found that only **63.5%** of records are flagged `Consistent` at the 10%-discrepancy threshold — far more than the ~5% of records where a discrepancy was deliberately injected. That's because normal independent sampling noise between the three sources (each generated with its own random spread) frequently exceeds 10% on its own, especially for lower-volume indicators (e.g. "New TB Cases" with a target of 10–60 has a much bigger *relative* swing from a few units of noise than "OPD Visits" with a target of 500–1500).

**This is worth a callout box directly on Page 3, not just a footnote**, because a threshold that flags the majority of records is not a usable prioritization signal — an M&E Officer using this dashboard needs to know the 10% threshold is too strict at low volumes before trusting the discrepancy counts. A more realistic implementation would use an **indicator-relative or volume-scaled threshold** (e.g. a higher percentage threshold for low-target indicators, or an absolute-count threshold below a certain volume) rather than one flat 10% cut across every indicator regardless of scale.

## 7. Build order

1. Import data, build the Calendar table, build the Facility Risk summary table
2. Write the core measures (Section 3)
3. Build Page 1's KPI cards, checking each against the Python notebook's printed summary numbers
4. Build Pages 2–4 one visual at a time, sense-checking against the notebook
5. Add the Page 3 threshold-sensitivity callout (Section 6) — don't skip this; it's the difference between a dashboard that looks complete and one that's actually trustworthy
6. Add slicers last
7. Screenshot into `visuals/` and link from the main README
