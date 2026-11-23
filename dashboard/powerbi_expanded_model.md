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
| DimCommodity | One row per illustrative commodity | Commodity_ID, Commodity, Programme, Unit |
| DimEquipmentType | One row per illustrative equipment type | Equipment_Type, Category, Criticality |
| FactEquipmentAssetRegister (asset dimension role) | One row per synthetic asset | Asset_ID, Facility_ID, Equipment_Type, Install_Date, Asset_Status |

### Facts

| Fact | Grain | Purpose |
|---|---|---|
| FactReporting | Facility × month × programme × indicator | Reported value, target, submission dates, ETL quality flags |
| FactSourceObservation | Record × source | Normalized paper, EMR and DHIS2 source values for reconciliation |
| FactDetectorEvaluation | Defect × evaluation run | Synthetic-only precision, recall, F1 and confusion counts |
| FactFacilityIndicatorAttainment | Facility × programme × indicator | Pooled reported-to-target attainment by comparable indicator |
| FactDistrictIndicatorAttainment | District × programme × indicator | District comparison at comparable indicator grain |
| FactMonthlyIndicatorAttainment | Month × programme × indicator | Monthly target-attainment trend by indicator |
| FactProgrammeIndicatorAttainment | Programme × indicator | Overall comparable indicator attainment profile |
| FactMonthlyQualityTrend | Month | Operational issue volumes and rates |
| FactPeerAnomaly | Anomalous reporting record | Statistical review queue and peer score |
| FactFacilityCommodityStock | Facility × commodity × month | Synthetic opening stock, receipts, demand, unmet demand and stockout estimates |
| FactCommodityReplenishmentPlan | Facility × commodity snapshot | Requested, funded and unfunded replenishment units under an abstract budget |
| FactEquipmentAssetMonthly | Asset × month | Breakdowns, planned/unplanned downtime, uptime, PM completion, condition and risk |
| FactFacilityEquipmentMonthly | Facility × month | Aggregated equipment uptime, breakdowns, PM and maintenance costs |
| FactEquipmentMaintenanceWorkOrders | Work order event | Preventive and corrective maintenance events and statuses |
| FactEquipmentLatestAssetRisk | Asset × latest month | Latest asset risk and operating snapshot |

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
- DimIndicator[Indicator_Key] 1 → * FactProgrammeIndicatorAttainment[Indicator_Key]
- DimEquipmentType[Equipment_Type] 1 → * FactEquipmentAssetRegister[Equipment_Type], FactEquipmentAssetMonthly[Equipment_Type], FactEquipmentMaintenanceWorkOrders[Equipment_Type] and FactEquipmentLatestAssetRisk[Equipment_Type]
- DimFacility[Facility_ID] 1 → * FactEquipmentAssetRegister[Facility_ID], FactEquipmentAssetMonthly[Facility_ID], FactFacilityEquipmentMonthly[Facility_ID], FactEquipmentMaintenanceWorkOrders[Facility_ID] and FactEquipmentLatestAssetRisk[Facility_ID]
- FactEquipmentAssetRegister[Asset_ID] 1 → * FactEquipmentAssetMonthly[Asset_ID], FactEquipmentMaintenanceWorkOrders[Asset_ID] and FactEquipmentLatestAssetRisk[Asset_ID] (the register is the unique asset dimension in this model)
- DimDate[MonthStart] 1 → * FactEquipmentAssetMonthly[Month], FactFacilityEquipmentMonthly[Month], FactEquipmentMaintenanceWorkOrders[Month] and FactEquipmentLatestAssetRisk[Month]

- DimFacility[Facility_ID] 1 → * FactFacilityCommodityStock[Facility_ID] and FactCommodityReplenishmentPlan[Facility_ID]
- DimCommodity[Commodity_ID] 1 → * FactFacilityCommodityStock[Commodity_ID] and FactCommodityReplenishmentPlan[Commodity_ID]
- DimDate[MonthStart] 1 → * FactFacilityCommodityStock[Month]

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
7. **Target attainment** — facility, district and monthly reported-to-target attainment by programme-indicator pair; show valid-record denominators and under-target review bands.
8. **Resource allocation scenarios** — compare synthetic capacity gaps and three constrained allocation heuristics; keep assumptions and limitations visible.
9. **Commodity availability and replenishment** — monitor synthetic stockouts, unmet demand, days of cover and budget-constrained replenishment. 
10. **Cold-chain and expiry intelligence** — review synthetic temperature excursions, monitoring coverage, FEFO batch balances, near-expiry stock, expired quantities and facility-commodity risk bands. 
11. **Equipment maintenance and uptime** — monitor synthetic asset registers, preventive maintenance compliance, breakdowns, downtime, service availability, operational uptime and open work orders.
12. **Facility infrastructure and utilities reliability** — review synthetic power, water and connectivity interruptions, resilience scores and illustrative upgrade scenarios.
13. **Workforce capacity and staffing intelligence** — review synthetic establishment, vacancies, monthly attendance proxies, workload pressure and recruitment scenarios.

## Build instructions

1. Run `python src/build_platform.py` from the repository root.
2. In Power BI Desktop, create a text parameter named `pWarehouseRoot` pointing to the generated `data/warehouse` folder (no trailing slash).
3. Create/load the queries in `dashboard/powerquery/`: `FactReporting`, `DimFacility`, `DimIndicator`, `DimDate`, `DimSource`, `FactSourceObservation`, `FactMonthlyQualityTrend`, `FactMonthlyIssueControlChart`, `FactDistrictProfile`, `FactDistrictMonthlyTrend`, `FactPeerAnomaly`, `FactDetectorEvaluation`, `FactFacilityIndicatorAttainment`, `FactDistrictIndicatorAttainment`, `FactMonthlyIndicatorAttainment`, `FactProgrammeIndicatorAttainment`, `FactFacilityResourceCapacity`, `FactResourceAllocationScenario`, `DimCommodity`, `FactFacilityCommodityStock`, `FactCommodityReplenishmentPlan`, `DimColdChainCommodity`, `FactColdChainTemperature`, `FactCommodityBatchLedger`, `FactColdChainExpiryRisk`, `DimEquipmentType`, `FactEquipmentAssetRegister`, `FactEquipmentAssetMonthly`, `FactFacilityEquipmentMonthly`, `FactEquipmentMaintenanceWorkOrders`, `FactEquipmentLatestAssetRisk`, `FactFacilityInfrastructureProfiles`, `FactMonthlyInfrastructureReliability`, `FactLatestInfrastructureResilience`, `FactEquipmentInfrastructureAssociation`, `FactInfrastructureUpgradeScenarios`, `FactFacilityWorkforceEstablishment`, `FactMonthlyWorkforceCapacity`, `FactLatestWorkforceCapacity` and `FactWorkforceRecruitmentScenario`.
4. The FactReporting query removes all `Ground_Truth_*` fields before loading; keep detector evaluation as a separate synthetic-only governance table.
5. Create `DimDistrict` using `dashboard/dax/dimension_tables.dax`, then create the relationships listed above. Mark DimDate as the date table and sort MonthName by MonthNumber.
6. Add measures from `dashboard/dax/health_data_quality_measures.dax`.
7. Add the DAX resource, commodity, cold-chain and equipment measures and build the thirteen report pages using the layout plan.
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
| FactFacilityIndicatorAttainment | Facility-level attainment by programme-indicator pair |
| FactDistrictIndicatorAttainment | District-level attainment by programme-indicator pair |
| FactMonthlyIndicatorAttainment | Monthly attainment by programme-indicator pair |
| FactProgrammeIndicatorAttainment | Overall programme-indicator attainment |
| FactFacilityResourceCapacity | Facility baseline capacity requirement, synthetic availability and gap |
| FactResourceAllocationScenario | Facility allocation and residual capacity by scenario |
| FactFacilityResourceCapacity | Synthetic baseline requirement, availability and gap by facility |
| FactResourceAllocationScenario | Facility-level allocations and residual gaps by scenario |
| DimCommodity | Illustrative commodity catalogue keyed by Commodity_ID |
| FactFacilityCommodityStock | Facility × commodity × month simulated stock ledger |
| FactCommodityReplenishmentPlan | Latest-snapshot budget-constrained replenishment worklist |
| DimEquipmentType | Illustrative equipment type catalogue |
| FactEquipmentAssetRegister | One row per asset; serves as the asset dimension |
| FactEquipmentAssetMonthly | Asset-month maintenance and uptime performance |
| FactFacilityEquipmentMonthly | Facility-month equipment aggregate |
| FactEquipmentMaintenanceWorkOrders | Preventive/corrective work-order events |
| FactEquipmentLatestAssetRisk | Latest-month asset risk snapshot |

Create `DimDistrict` from the DAX dimension-table script. Connect it to DimFacility, FactDistrictProfile and FactDistrictMonthlyTrend using single-direction one-to-many relationships. The district aggregate facts are separate from the facility reporting fact; do not create fact-to-fact joins.


## Resource capacity and allocation scenario facts

Two additional Power Query facts are provided: `FactFacilityResourceCapacity` (baseline illustrative requirement, synthetic availability and gap) and `FactResourceAllocationScenario` (facility-level allocations and residual gaps for each of three strategies). Relate both to DimFacility on Facility_ID with single-direction one-to-many relationships. Use Scenario as a slicer for comparisons; do not relate the two facts directly. Resource units are abstract synthetic planning units, not staffing headcounts or currency. Refer to `docs/resource_planning_methodology.md` for assumptions and safeguards.

## Commodity availability and replenishment facts

Three Power Query templates extend the semantic model:
- `DimCommodity` — illustrative commodity catalogue keyed by Commodity_ID.
- `FactFacilityCommodityStock` — facility-commodity-month stock ledger with opening stock, receipts, demand, fulfilled consumption, unmet demand, closing stock and estimated stockout days.
- `FactCommodityReplenishmentPlan` — latest-snapshot replenishment requests, budget-constrained allocations and unfunded quantities.

Create single-direction one-to-many relationships from DimFacility, DimCommodity and DimDate to the applicable facts. FactFacilityCommodityStock joins all three dimensions. FactCommodityReplenishmentPlan joins DimFacility and DimCommodity; its Snapshot_Month can join DimDate if the model uses a dedicated role-playing date relationship. Do not join facts directly.

All inventory records and unit costs are synthetic. Budget credits are not MWK, the commodity list is illustrative, and stockout-day estimates are monthly approximations. See `docs/supply_chain_methodology.md`.


## Cold-chain and expiry facts

Four Power Query templates extend the model:
- `DimColdChainCommodity` — synthetic catalogue of illustrative temperature-sensitive commodities.
- `FactColdChainTemperature` — facility-month sensor coverage, temperature summaries and excursion estimates.
- `FactCommodityBatchLedger` — batch-month stock movements, expiry dates, FEFO consumption and remaining lot balances.
- `FactColdChainExpiryRisk` — facility-commodity-month demand, unmet demand, expiry exposure and risk-band summary.

Connect DimFacility and DimDate to all applicable facts using Facility_ID and Month. Connect DimColdChainCommodity to FactCommodityBatchLedger and FactColdChainExpiryRisk using Commodity_ID. FactColdChainTemperature is facility-month grain and has no commodity key. Do not create fact-to-fact relationships. Keep the batch ledger at Batch_ID × Month grain; do not aggregate repeated facility-commodity demand across batch rows.

The default 2–8°C band, shelf lives and expiry windows are illustrative assumptions, not official Malawi standards or product-specific storage instructions. Temperature excursions require product-specific review and do not establish product compromise. See `docs/cold_chain_methodology.md`.


## Equipment maintenance and uptime facts

Six Power Query templates extend the semantic model:
- `DimEquipmentType` — illustrative equipment catalogue with category, criticality and assumed maintenance/lifecycle fields.
- `FactEquipmentAssetRegister` — synthetic asset-level inventory and installation dates.
- `FactEquipmentAssetMonthly` — asset-month breakdown, downtime, uptime, PM, condition and risk metrics.
- `FactFacilityEquipmentMonthly` — facility-month aggregate performance.
- `FactEquipmentMaintenanceWorkOrders` — preventive and corrective work-order event records.
- `FactEquipmentLatestAssetRisk` — latest-month asset risk snapshot.

Connect DimEquipmentType and DimFacility to the relevant facts. Connect DimDate to all month-grain facts. Keep the asset register, asset-month performance, facility-month summary and work-order events at their respective grains; do not relate facts directly or aggregate the same downtime/cost measures from multiple fact tables at once. If a dedicated DimAsset is added, it can filter asset-month and work-order facts by Asset_ID.

Service availability excludes unplanned breakdown downtime. Operational uptime also subtracts planned maintenance downtime. The asset mix, expected lives, maintenance intervals, failure probabilities, condition scores and cost credits are synthetic assumptions, not official engineering standards or verified clinical service availability. See `docs/equipment_maintenance_methodology.md`.


## Facility infrastructure and utilities reliability

| Fact | Grain | Purpose |
|---|---|---|
| FactFacilityInfrastructureProfiles | Facility | Synthetic power, water and connectivity configuration attributes |
| FactMonthlyInfrastructureReliability | Facility × month | Interruption counts/hours, unserved hours, domain availability and resilience score |
| FactLatestInfrastructureResilience | Facility × latest month | Latest review snapshot and risk band |
| FactEquipmentInfrastructureAssociation | Power interruption band | Aggregate descriptive comparison with equipment uptime |
| FactInfrastructureUpgradeScenarios | Facility × upgrade package | Illustrative avoided-hour scenarios and abstract budget selection |

Relationships:
- DimFacility[Facility_ID] 1 → * FactFacilityInfrastructureProfiles[Facility_ID]
- DimFacility[Facility_ID] 1 → * FactMonthlyInfrastructureReliability[Facility_ID]
- DimDate[MonthStart] 1 → * FactMonthlyInfrastructureReliability[Month]
- DimFacility[Facility_ID] 1 → * FactLatestInfrastructureResilience[Facility_ID]
- DimDate[MonthStart] 1 → * FactLatestInfrastructureResilience[Month]
- DimFacility[Facility_ID] 1 → * FactInfrastructureUpgradeScenarios[Facility_ID]
- FactEquipmentInfrastructureAssociation is an aggregate band table; it has no facility or date key and should not be joined to facility-level facts.

Do not create fact-to-fact relationships. The infrastructure/equipment comparison is descriptive and not causal. All configurations, interruptions, resilience scores and upgrade costs are synthetic. Abstract credits are not MWK; see `docs/infrastructure_reliability_methodology.md`.


## Workforce capacity and staffing scenario facts

| Fact | Grain | Purpose |
|---|---|---|
| FactFacilityWorkforceEstablishment | Facility × role | Synthetic establishment, filled posts and vacancy baseline |
| FactMonthlyWorkforceCapacity | Facility × month | Filled/on-duty positions, absence, overtime and workload/capacity proxies |
| FactLatestWorkforceCapacity | Facility × latest month | Latest staffing coverage and review band |
| FactWorkforceRecruitmentScenario | Role | Vacancy totals and abstract-budget recruitment scenario |

Relationships:
- DimFacility[Facility_ID] 1 → * FactFacilityWorkforceEstablishment[Facility_ID]
- DimFacility[Facility_ID] 1 → * FactMonthlyWorkforceCapacity[Facility_ID]
- DimDate[MonthStart] 1 → * FactMonthlyWorkforceCapacity[Month]
- DimFacility[Facility_ID] 1 → * FactLatestWorkforceCapacity[Facility_ID]
- DimDate[MonthStart] 1 → * FactLatestWorkforceCapacity[Month]
- FactWorkforceRecruitmentScenario is role-aggregate and has no facility or date key; do not connect it to facility facts.

Use single-direction dimension-to-fact relationships and no fact-to-fact joins. All staffing values and role assumptions are synthetic. Catchment population is a workload proxy, not patient volume. Role mixes are not official staffing norms. Recruitment credits are not MWK. See `docs/workforce_planning_methodology.md`.
