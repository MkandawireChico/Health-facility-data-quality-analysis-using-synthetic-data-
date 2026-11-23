# Cold-Chain, Batch Traceability and Expiry Methodology

## Purpose

This module demonstrates an integrated synthetic cold-chain monitoring and batch-inventory workflow. It produces facility-month temperature summaries, lot-level stock snapshots, FEFO consumption allocations, near-expiry quantities, expiry wastage estimates and review-priority indicators.

## Synthetic commodity catalogue

Four generic illustrative temperature-sensitive commodity labels are generated. They are not an approved Malawi essential medicines or vaccines list, and they do not imply actual facility stock or programme availability.

## Temperature monitoring

A synthetic sensor is assigned to each facility. Daily minimum and maximum temperatures are generated and aggregated to facility-month:
- number of calendar days and observed days;
- observation coverage percentage;
- mean, minimum and maximum observed temperature;
- excursion days and estimated excursion hours;
- monitoring status (sufficient, incomplete or missing).

The default 2–8°C band is a generic modelling assumption used only to demonstrate an alert workflow. It is not a universal storage instruction, a national policy claim or a substitute for the specific product label and approved storage guidance. Users can override the bounds through the Python API/CLI for scenario analysis.

The simulation includes occasional controlled excursions and missing daily observations. It does not model calibrated continuous logger data, refrigerator mapping, power interruption telemetry, freeze indicators, vaccine vial monitors, excursion adjudication or product stability decisions.

## Batch and lot ledger

Each facility and commodity receives a synthetic lot identifier, supplier identifier, manufacture date, receipt date, expiry date, receipt quantity and abstract unit cost. Batch-level snapshots retain:
- opening stock and receipts;
- fulfilled consumption allocated to the lot;
- expired quantity and closing stock;
- days to expiry at month end;
- near-expiry stock bands at 30, 60 and 90 days;
- linked facility-month temperature excursion indicators.

The monthly stock equation is:

`Opening + Receipts - Fulfilled Consumption - Expired = Closing`

Demand is generated at facility-commodity-month grain. Consumption is allocated to available lots in expiry-date order (FEFO: First Expiry, First Out). Remaining stock from a lot whose expiry date falls within the month is treated as expired at month end. A lot whose expiry date is before the reporting month is expired at the start of the month.

The model does not represent exact daily dispensing, batch recalls, quarantined stock, returns, wastage causes other than expiry, inter-facility transfers, supplier delivery performance or verified stock-card reconciliations.

## Risk score and review bands

The illustrative score combines:
- 50% of the observed monthly temperature excursion-day rate; and
- 50% of the closing stock share with expiry within 90 days.

A missing temperature denominator produces a Data Gap band. High/Medium/Low are prioritisation labels for this synthetic scenario, not clinical safety classifications. A temperature excursion is not proof that product potency has been compromised; only an authorised, product-specific review can determine disposition.

## Outputs

- `cold_chain_catalog.csv`
- `facility_cold_chain_temperature_monitoring.csv`
- `facility_commodity_batch_ledger.csv`
- `cold_chain_expiry_risk_summary.csv`
- `cold_chain_planning_report.json`

Run with `python src/cold_chain_planning.py --periods 24 --seed 42`, or include it in `python src/build_platform.py`.

## Governance safeguards

All facilities, suppliers, sensors, lots, dates, temperatures, demand, receipts, consumption, expiry events and costs are synthetic. Temperature bounds and shelf lives are assumptions, not official Malawi standards. The outputs are portfolio demonstration artefacts and must never be represented as live inventory, validated cold-chain evidence or operational product-disposition instructions.
