# Power BI report build and interaction guide

## Status and intended use

This guide is the implementation specification for the expanded six-page Power BI report. It complements the semantic-model, Power Query and DAX files in this folder. The existing PBIX is still the original 960-record report; the expanded 288,000-record report must be assembled and saved in Power BI Desktop. No expanded PBIX or new screenshots are claimed by this guide.

The full cohort is synthetic. Display a visible banner on every page:

> SYNTHETIC PORTFOLIO DATA — facility names, district comparisons, populations and performance metrics are illustrative and are not Ministry of Health or actual facility results.

Import `dashboard/powerbi_theme.json` through View → Themes → Browse for themes before building pages. It supplies the accessible light palette, high-contrast text and consistent typography. Use descriptive titles and do not rely on colour alone to convey severity; pair status colours with labels and icons.

## Global canvas and navigation

- Canvas: 16:9 widescreen; suggested working page size 1280 × 720.
- Header: report title, page subtitle and synthetic-data banner.
- Left navigation rail: six clearly labelled page buttons using page-navigation bookmarks.
- Global slicers: reporting year/month, district, programme and indicator.
- Keep facility selection on pages where it is meaningful; avoid applying facility filters to district aggregate facts unless the filter path is explicitly designed.
- Add a visible Reset filters bookmark on every page.
- Use single-direction dimension-to-fact relationships. Do not create direct relationships between fact tables.

## Page 1 — Executive quality overview

**Decision question:** How much reporting has been received, where are the main quality risks, and are they changing?

Layout:
- Top row: total reporting records, facilities represented, reporting months, reported-value availability, on-time rate and distinct follow-up records.
- Middle left: monthly issue-rate line chart from FactMonthlyQualityTrend.
- Middle right: issue-type clustered columns for missing, source discrepancy, outlier and late records.
- Bottom: programme/indicator issue-rate matrix with conditional formatting and reporting volume beside the rate.

Interactions:
- Month, district, programme and indicator slicers filter operational visuals.
- Selecting a month cross-filters the issue-type breakdown and programme matrix.
- Drill through from a programme/indicator row to Programme and Indicator Monitoring.

Interpretation:
- Follow-up records are distinct records; issue categories overlap.
- On-time rate denominator includes only records with both submission and deadline dates.
- Reported-value availability is not a clinical completeness measure.

## Page 2 — District and facility intelligence

**Decision question:** Which synthetic reporting groups need verification, with what reporting volume?

Layout:
- Top row: districts represented, facilities represented, district-weighted issue rate.
- Left: horizontal bar chart of district issue rate, with record count in tooltip.
- Right: district reporting volume, so small denominators are visible.
- Centre/bottom: district-month trend line with district legend.
- Bottom table: facility, district, records, detected issue records, issue rate and follow-up rank.

Interactions:
- District selection filters the district-month trend and facility table.
- Facility table supports drill-through to a facility detail page (optional page if implemented).
- Tooltips should show record volume, facility count and individual issue counts.

Governance:
- District aggregate tables are pre-aggregated outputs. Use DimDistrict to filter them.
- Facility filters do not automatically filter district aggregate tables; avoid implying that they do.
- District labels are geographic context only. Every displayed rate is synthetic.

## Page 3 — Programme and indicator monitoring

**Decision question:** Which reporting indicators need data verification?

Layout:
- Programme comparison: reporting volume and distinct follow-up rate.
- Indicator matrix: programme, indicator, records, missing, source discrepancy, outlier, late and distinct issue rate.
- Monthly trend for the selected indicator.
- Optional small-multiple charts by programme where the visual remains legible.

Interactions:
- Programme selection filters the indicator matrix.
- Indicator selection filters monthly trends.
- Drill through to record-level worklist only if the report contains a controlled record identifier and the report is not distributed publicly.

## Page 4 — Source reconciliation

**Decision question:** Where do paper, EMR and DHIS2 values disagree?

Layout:
- KPI cards: source observations, records with at least two sources, discrepancy-review records, average source spread.
- Source distribution visual using FactSourceObservation.
- Record-level reconciliation table with Record_ID, facility, month, programme, indicator, Paper, EMR, DHIS2 and source spread.
- Matrix by district and programme showing review counts and rates.

Interactions:
- Source slicer filters source-value distribution.
- Selecting a record should highlight all three source observations.
- Use absolute spread and the existing hybrid discrepancy flag together; do not silently replace the operational rule with a visual-only threshold.

## Page 5 — Statistical monitoring

**Decision question:** Which values or reporting periods deserve closer review?

Layout:
- Peer anomaly count and number of peer groups with sufficient observations.
- Table of flagged records with facility, district, month, programme, indicator, reported value, peer-group size, method and score.
- Monthly issue-rate chart with centre line and retrospective upper/lower descriptive limits.
- Control status table with monthly record denominators and issue counts.

Interpretation:
- MAD/IQR flags are unusual peer observations, not proof of reporting error.
- Monthly limits are retrospective and calculated over the full observed period.
- Show monthly denominators beside rates; small denominators can make rates volatile.
- Do not label a review signal as a confirmed incident or clinical risk.

## Page 6 — Detector governance

**Decision question:** How did the deterministic rules perform against the defects deliberately injected into this synthetic dataset?

Layout:
- Persistent synthetic evaluation banner.
- Matrix by defect: support, predicted positives, TP, FP, FN, TN, precision, recall, F1 and false-positive rate.
- Precision/recall comparison by defect.
- Confusion-count chart or table.

Interactions:
- Keep this page separated from operational quality pages.
- Do not use FactDetectorEvaluation to filter operational issue rates or facility rankings.
- Explain that injected defects are controlled and may be easier to detect than real reporting problems.

## Optional page 7 — Facility detail

Only add this page if the report remains readable:
- facility profile and synthetic catchment attributes;
- monthly reporting volume and issue rates;
- indicator-level quality matrix;
- source reconciliation history;
- drill-through from the facility benchmark.

Avoid exposing patient-level data. The current dataset has no patient-level records.

## Accessibility and visual QA checklist

- Page titles and chart titles describe the metric and unit.
- Use high-contrast text and readable labels at normal desktop zoom.
- Use percentage formatting consistently; show counts as whole numbers.
- Sort month names by MonthNumber and use YearMonth for chronological axes.
- Do not use red/green alone; include text labels such as Review signal.
- Keep chart legends, axes and tooltip fields unambiguous.
- Verify that each slicer filters only the intended facts.
- Check district, facility, month, programme and indicator cross-filtering.
- Confirm no Ground_Truth_* fields appear in operational tables or report visuals.
- Confirm detector evaluation is visibly synthetic and isolated from operational metrics.
- Export each page to PDF and review clipping, labels and synthetic disclaimers.
- Save the final PBIX only after the model refresh and all page-level checks pass.

## Required model files

- Semantic model and relationships: powerbi_expanded_model.md
- Power Query M templates: powerquery/
- DAX measures: dax/health_data_quality_measures.dax
- Calculated dimensions: dax/dimension_tables.dax

The guide does not substitute for a completed Power BI Desktop refresh and visual review.
