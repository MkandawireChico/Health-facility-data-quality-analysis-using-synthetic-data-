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
- `analytics/facility_quality_benchmark.csv`
- `analytics/programme_indicator_quality_profile.csv`
- `analytics/statistical_peer_anomalies.csv`
- `analytics/monthly_issue_control_chart.csv`
- `analytics/facility_indicator_target_attainment.csv`
- `analytics/district_indicator_target_attainment.csv`
- `analytics/programme_indicator_target_attainment.csv`
- `analytics/monthly_indicator_target_attainment.csv`

Generated files are Git-ignored. Set Power Query parameters to the local paths on the machine where Power BI Desktop is running.

## Star schema

### Dimensions

| Dimension | Grain | Key fields |
|---|---|---|
| DimFacility | One row per synthetic facility | Facility_ID, Facility_Name, District, Facility_Type, Urban_Rural, Ownership, Catchment_Population |
| DimDate | One row per calendar month | MonthStart, Year, Quarter, MonthNumber, MonthName |
| DimIndicator | One row per programme-indicator pair | Indicator_Key, Programme, Indicator |
| DimDistrict | One row per district label | District |
| DimSource | One row per reporting source | Source |

### Facts

| Fact | Grain | Purpose |
|---|---|---|
| FactReporting | Facility × month × programme × indicator | Reported value, target, submission dates, ETL quality flags |
| FactSourceObservation | Record × source | Normalized paper, EMR and DHIS2 source values for reconciliation |
| FactDetectorEvaluation | Defect × evaluation run | Synthetic-only precision, recall, F1 and confusion counts |
| FactFacilityIndicatorAttainment | Facility × programme × indicator | Pooled reported-to-target attainment by comparable indicator |
| FactDistrictIndicatorAttainment | District × programme × indicator | District comparison at comparable indicator grain |
| FactMonthlyIndicatorAttainment | Month × programme × indicator | Monthly target-attainment trend by indicator |
| FactMonthlyQualityTrend | Month | Operational issue volumes and rates |
| FactPeerAnomaly | Anomalous reporting record | Statistical review queue and peer score |
| FactFacilityIndicatorAttainment | Facility × programme × indicator | Pooled reported-to-target attainment by comparable indicator |
| FactDistrictIndicatorAttainment | District × programme × indicator | District comparison at comparable indicator grain |
| FactMonthlyIndicatorAttainment | Month × programme × indicator | Monthly target-attainment trend by indicator |

### Relationships

- DimDistrict[District] 1 → * DimFacility[District]
- DimDistrict[District] 1 → * FactDistrictProfile[District]
- DimDistrict[District] 1 → * FactDistrictMonthlyTrend[District]
- DimFacility[Facility_ID] 1 → * FactReporting[Facility_ID]
- DimDate[MonthStart] 1 → * FactReporting[Month]
- DimIndicator[Indicator_Key] 1 → * FactReporting[Indicator_Key]
- DimFacility[Facility_ID] 1 → * FactSourceObservation[Facility_ID]
- DimDate[MonthStart] 1 → * FactSourceObservation[Month]
- DimIndicator[Indicator_Key] 1 → * FactSourceObservation[Indicator_Key]
- DimSource[Source] 1 → * FactSourceObservation[Source]
- DimDate[MonthStart] 1 → * FactMonthlyQualityTrend[Month]
- DimDate[MonthStart] 1 → * FactMonthlyIssueControlChart[Month]
- DimDate[MonthStart] 1 → * FactDistrictMonthlyTrend[Month]
- DimFacility[Facility_ID] 1 → * FactPeerAnomaly[Facility_ID]
- DimDate[MonthStart] 1 → * FactPeerAnomaly[Month]
- DimIndicator[Indicator_Key] 1 → * FactPeerAnomaly[Indicator_Key]
- DimFacility[Facility_ID] 1 → * FactFacilityIndicatorAttainment[Facility_ID]
- DimIndicator[Indicator_Key] 1 → * FactFacilityIndicatorAttainment[Indicator_Key]
- DimDistrict[District] 1 → * FactDistrictIndicatorAttainment[District]
- DimIndicator[Indicator_Key] 1 → * FactDistrictIndicatorAttainment[Indicator_Key]
- DimDate[MonthStart] 1 → * FactMonthlyIndicatorAttainment[Month]
- DimIndicator[Indicator_Key] 1 → * FactMonthlyIndicatorAttainment[Indicator_Key]
- DimFacility[Facility_ID] 1 → * FactFacilityIndicatorAttainment[Facility_ID]
- DimIndicator[Indicator_Key] 1 → * FactFacilityIndicatorAttainment[Indicator_Key]
- DimDistrict[District] 1 → * FactDistrictIndicatorAttainment[District]
- DimIndicator[Indicator_Key] 1 → * FactDistrictIndicatorAttainment[Indicator_Key]
- DimDate[MonthStart] 1 → * FactMonthlyIndicatorAttainment[Month]
- DimIndicator[Indicator_Key] 1 → * FactMonthlyIndicatorAttainment[Indicator_Key]

Use single-direction filtering from dimensions to facts. Avoid fact-to-fact relationships and ambiguous bidirectional filters. Detector evaluation is a separate governance fact and must not feed operational issue rates or facility rankings.

## Ground-truth governance

Do **not** import `Ground_Truth_*` fields into FactReporting. They are controlled labels for evaluating synthetic defect detection only. Import the aggregate detector metrics as FactDetectorEvaluation and label the page and visuals clearly as synthetic test results. They are not real-world performance estimates.

## Report page plan

1. **Executive quality overview** — record volume, reporting-value availability, on-time rate, source review rate, distinct records requiring follow-up, monthly trend.
2. **District and facility intelligence** — district-month issue-rate trends, facility rates, volume context, follow-up ranking and district comparisons. Avoid presenting synthetic rankings as actual district performance.
3. **Programme and indicator monitoring** — programme/indicator volume, reporting completeness and issue rates.
4. **Source reconciliation** — source value distributions, absolute spread and source review queue.
5. **Statistical monitoring** — MAD/IQR peer anomalies and retrospective monthly issue-rate limits. Signals are review prompts, not proof of error.
6. **Detector governance** — precision, recall, F1 and confusion counts on synthetic injected defects; display a persistent synthetic-evaluation disclaimer.

## Build instructions

1. Run `python src/build_platform.py` from the repository root.
2. In Power BI Desktop, create a text parameter named `pWarehouseRoot` pointing to the generated `data/warehouse` folder (no trailing slash).
3. Create/load the queries in `dashboard/powerquery/`: `FactReporting`, `DimFacility`, `DimIndicator`, `DimDate`, `DimSource`, `FactSourceObservation`, `FactMonthlyQualityTrend`, `FactMonthlyIssueControlChart`, `FactDistrictProfile`, `FactDistrictMonthlyTrend`, `FactPeerAnomaly` and `FactDetectorEvaluation`.
4. The FactReporting query removes all `Ground_Truth_*` fields before loading; keep detector evaluation as a separate synthetic-only governance table.
5. Create `DimDistrict` using `dashboard/dax/dimension_tables.dax`, then create the relationships listed above. Mark DimDate as the date table and sort MonthName by MonthNumber.
6. Add measures from `dashboard/dax/health_data_quality_measures.dax`.
7. Build the six report pages using the layout plan.
8. Validate filter behaviour at facility, district, month, programme and indicator levels.
9. Keep the synthetic-data disclaimer visible on every report page and in exported PDFs.

## Limitations

- The model is a portfolio semantic-model specification, not a production health data warehouse.
- Catchment population and all reported metrics are synthetic.
- The current monthly control limits are retrospective descriptive limits.
- Corrective-action ownership and audit history are not persisted in a shared database.
- Production use would require validated definitions, access controls, audit trails, secure hosting, agreed refresh SLAs and domain review.


### District profile outputs

The analytical pipeline also exports `district_quality_profile.csv` and
`district_monthly_quality_trends.csv`. These are operational profiles based
on derived quality flags, not synthetic ground-truth labels. Use DimDistrict to filter DimFacility, FactDistrictProfile and FactDistrictMonthlyTrend; DimFacility then filters FactReporting.
The district labels and all underlying performance values remain synthetic.


## Power Query implementation inventory

The query files are executable Power Query M templates, not screenshots or mockups. Set the single `pWarehouseRoot` text parameter to the local `data/warehouse` directory. Query names and their source artefacts:

| Query | Warehouse source / role |
|---|---|
| FactReporting | Staged operational fact; excludes ground-truth columns |
| DimFacility | Raw synthetic facility dimension |
| DimIndicator | Distinct programme-indicator combinations |
| DimDate | Continuous monthly calendar |
| DimSource | Controlled Paper / EMR / DHIS2 source dimension |
| FactSourceObservation | Unpivots the three source-value columns to one row per source observation |
| FactMonthlyQualityTrend | Monthly operational profile |
| FactMonthlyIssueControlChart | Retrospective monthly issue-rate limits |
| FactDistrictProfile | District-level synthetic operational profile |
| FactDistrictMonthlyTrend | District-month volumes and issue rates |
| FactPeerAnomaly | Statistical anomalies only; filtered to flagged records |
| FactDetectorEvaluation | Aggregate detector evaluation against synthetic labels |

Create `DimDistrict` from the DAX dimension-table script. Connect it to DimFacility, FactDistrictProfile and FactDistrictMonthlyTrend using single-direction one-to-many relationships. The district aggregate facts are separate from the facility reporting fact; do not create fact-to-fact joins.
