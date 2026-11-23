# Facility infrastructure and utilities reliability methodology

## Scope and grain

This module generates a synthetic facility infrastructure profile and a facility-month reliability fact. It models three domains:

- Electricity: interruption events, total interruption hours, backup hours and unserved interruption hours.
- Water: shortage events, shortage hours, buffered hours and unserved shortage hours.
- Connectivity: interruption events and downtime hours.

Each facility has one illustrative infrastructure configuration. Monthly metrics use one row per Facility_ID × Month. A latest-month snapshot supports a facility review list. Where the equipment monthly summary is available, it is joined at Facility_ID × Month for a descriptive comparison with mean operational uptime.

## Synthetic assumptions

Power configurations, water sources, connectivity modalities, backup capacity, water storage, event frequency, event duration, availability weights, risk bands, upgrade costs and avoided-hour factors are generated assumptions. They are not actual utility-provider data, engineering standards, official Malawi facility inventories, or quotations. The synthetic profile is deterministic for a fixed seed.

Power availability deducts outage hours not notionally covered by the modelled backup response. Water availability deducts shortage hours not notionally buffered by the modelled storage capacity. Connectivity availability deducts simulated connectivity downtime. The resilience score is a weighted composite: 40% power availability, 30% water availability, 20% connectivity availability and 10% illustrative backup-power capacity score.

These calculations do not represent water potability, power quality, generator fuel sufficiency, network bandwidth, or actual operational readiness. Availability is not clinical service availability and does not establish patient impact.

## Equipment relationship

The equipment comparison groups paired facility-month observations by unserved power-interruption band and reports mean equipment operational uptime. The module records a Pearson correlation when both variables vary. This is descriptive association within generated data, not causal evidence. It does not estimate how many breakdowns were caused by outages or demonstrate a clinical service interruption.

## Upgrade scenario

Four illustrative packages are evaluated for each facility: backup power, water storage, connectivity resilience and an integrated package. The engine selects the highest avoided-hours-per-100-credits package for each facility only when the simulated package has positive avoided interruption hours. Facilities with no modeled interruption exposure receive no package selection and consume no budget. Eligible facility-level choices are then ranked under a configurable abstract credit ceiling. This is a transparent scenario heuristic, not a validated optimisation, engineering design, procurement specification or recommendation. Credits are not MWK.

## Outputs

- `facility_infrastructure_profiles.csv`
- `facility_monthly_infrastructure_reliability.csv`
- `facility_latest_infrastructure_resilience.csv`
- `equipment_infrastructure_association.csv`
- `infrastructure_upgrade_scenarios.csv`
- `infrastructure_planning_report.json`

## Governance and limitations

All data is synthetic. No actual electricity, water, connectivity, generator, sensor, maintenance-log or utility-provider records are represented. District labels are contextual labels only. No patient-level data is generated. The outputs are for portfolio demonstration and should not be used for real facility ranking, clinical decisions, engineering work, procurement or budget allocation.
