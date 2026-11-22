# Expanded Power BI semantic model and report design

## Scope and status

This is the **Power BI implementation pack** for the expanded synthetic platform. It defines the target star schema, Power Query transformations, DAX measures and report-page design. The existing `health_facility_data_quality_dashboard.pbix` remains the original 960-row demonstration; this documentation does not claim that the binary PBIX has already been rebuilt. Apply the model in Power BI Desktop using the generated warehouse files.

All records, facility identifiers, facility names, catchment populations and metrics are synthetic. District labels are Malawi-oriented context only. No patient-level or real Ministry of Health / DHIS2 data is used.

## Source artefacts

Generate the full warehouse:

```bash
python src/build_platform.py
```

Use these outputs from `data/warehouse/`:
- `raw/facility_dimension.csv`
- `staged/facility_reporting_staged.csv`
- `analytics/detector_evaluation_metrics.csv`
- `analytics/monthly_quality_trends.csv`
- `analytics/facility_quality_benchmark.csv`\n- `analytics/district_quality_benchmark.csv`
- `analytics/programme_indicator_quality_profile.csv`
- `analytics/statistical_peer_anomalies.csv`
- `analytics/monthly_issue_control_chart.csv`

Generated files are Git-ignored. Set Power Query parameters to the local paths on the machine where Power BI Desktop is running.

## Star schema

### Dimensions

| Dimension | Grain | Key fields |
|---|---|---|
| DimFacility | One row per synthetic facility | Facility_ID, Facility_Name, District, Facility_Type, Urban_Rural, Ownership, Catchment_Population |
| DimDate | One row per calendar month | MonthStart, Year, Quarter, MonthNumber, MonthName |
| DimIndicator | One row per programme-indicator pair | Indicator_Key, Programme, Indicator |
| DimSource | One row per reporting source | Source |

### Facts

| Fact | Grain | Purpose |
|---|---|---|
| FactReporting | Facility × month × programme × indicator | Reported value, target, submission dates, ETL quality flags |
| FactSourceObservation | Record × source | Normalized paper, EMR and DHIS2 source values for reconciliation |
| FactDetectorEvaluation | Defect × evaluation run | Synthetic-only precision, recall, F1 and confusion counts |
| FactMonthlyQualityTrend | Month | Operational issue volumes and rates |
| FactPeerAnomaly | Anomalous reporting record | Statistical review queue and peer score |\n| FactDistrictQualityBenchmark | One row per synthetic district | Volume-normalised detected issue rate and follow-up rank |

### Relationships

- DimDistrict[District] 1 → * DimFacility[District]
- DimDistrict[District] 1 → * FactDistrictQualityBenchmark[District]\n- DimFacility[Facility_ID] 1 → * FactReporting[Facility_ID]
- DimDate[MonthStart] 1 → * FactReporting[Month]
- DimIndicator[Indicator_Key] 1 → * FactReporting[Indicator_Key]
- DimFacility[Facility_ID] 1 → * FactSourceObservation[Facility_ID]
- DimDate[MonthStart] 1 → * FactSourceObservation[Month]
- DimIndicator[Indicator_Key] 1 → * FactSourceObservation[Indicator_Key]
- DimSource[Source] 1 → * FactSourceObservation[Source]
- DimDate[MonthStart] 1 → * FactMonthlyQualityTrend[Month]

Use single-direction filtering from dimensions to facts. Avoid fact-to-fact relationships and ambiguous bidirectional filters. Detector evaluation is a separate governance fact and must not feed operational issue rates or facility rankings.

## Ground-truth governance

Do **not** import `Ground_Truth_*` fields into FactReporting. They are controlled labels for evaluating synthetic defect detection only. Import the aggregate detector metrics as FactDetectorEvaluation and label the page and visuals clearly as synthetic test results. They are not real-world performance estimates.

## Report page plan

1. **Executive quality overview** — record volume, reporting-value availability, on-time rate, source review rate, distinct records requiring follow-up, monthly trend.
2. **District and facility intelligence** — facility rates, volume context, follow-up ranking and district comparisons. Avoid presenting synthetic rankings as actual district performance.
3. **Programme and indicator monitoring** — programme/indicator volume, reporting completeness and issue rates.
4. **District quality benchmarking** — volume-normalised issue rates and facility counts across the synthetic district groups.
5. **Source reconciliation** — source value distributions, absolute spread and source review queue.
6. **Statistical monitoring** — MAD/IQR peer anomalies and retrospective monthly issue-rate limits. Signals are review prompts, not proof of error.
7. **Detector governance** — precision, recall, F1 and confusion counts on synthetic injected defects; display a persistent synthetic-evaluation disclaimer.

## Build instructions

1. Run `python src/build_platform.py` from the repository root.
2. In Power BI Desktop, create text parameters for the staged fact, facility dimension and analytics folder paths.
3. Use the Power Query templates in `dashboard/powerquery/`.
4. Create the relationships listed above and mark DimDate as the date table.
5. Add the measures in `dashboard/dax/health_data_quality_measures.dax`.
6. Build the seven report pages using the layout plan.
7. Validate filter behaviour at facility, district, month, programme and indicator levels.
8. Keep the synthetic-data disclaimer visible on every report page and in exported PDFs.

## Limitations

- The model is a portfolio semantic-model specification, not a production health data warehouse.
- Catchment population and all reported metrics are synthetic.
- The current monthly control limits are retrospective descriptive limits.
- Corrective-action ownership and audit history are not persisted in a shared database.
- Production use would require validated definitions, access controls, audit trails, secure hosting, agreed refresh SLAs and domain review.
