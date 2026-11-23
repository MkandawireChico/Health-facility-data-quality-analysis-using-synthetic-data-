# Commodity Availability and Replenishment Methodology

## Purpose

This layer demonstrates an end-to-end synthetic commodity stock-card workflow: monthly opening stock, receipts, demand, fulfilled consumption, unmet demand, closing stock, stockout-day estimates and replenishment planning under a configurable abstract budget.

## Synthetic commodity catalogue

Eight illustrative commodities are included across outpatient, HIV, TB, maternal health, child health, nutrition and family-planning programme labels. Names are examples only; this is not an approved Malawi essential medicines or health commodities list.

## Stock ledger simulation

For each synthetic facility, commodity and month:
- Monthly demand is sampled from a Poisson distribution using an illustrative demand rate per 10,000 catchment population and a facility-type multiplier.
- Opening stock carries forward from the prior month's closing balance.
- Synthetic receipts are generated at the beginning of the month.
- Fulfilled consumption is the lesser of available stock and demand.
- Unmet demand is the residual demand after available stock is exhausted.
- Closing stock equals opening stock plus receipts less fulfilled consumption.
- Estimated stockout days are proportional to the unmet share of monthly demand, capped by calendar month length.

The model does not simulate exact daily dispensing, expiry, batch/lot tracking, cold-chain status, delivery dates within a month, wastage, substitutions or transfers between facilities.

## Replenishment method

For the latest month, average demand is calculated over up to three recent months. Target stock is average daily demand multiplied by lead time plus buffer days. The default lead-time assumption is 30 days and the buffer is 15 days. Requested replenishment is the positive difference between target stock and closing stock.

The constrained worklist uses a deterministic priority-per-credit order. Priority combines an illustrative commodity essentiality weight, days-of-cover risk relative to lead time and recent stockout days. Each line is funded up to its requested units while respecting the total budget-credit ceiling. Ties are broken by Facility_ID and Commodity_ID.

## Interpretation safeguards

- All facilities, demand, stock balances, receipts, stockout events and unit costs are synthetic.
- Commodity names are illustrative, not an official national catalogue.
- Demand rates and facility-type multipliers are modelling assumptions, not clinical consumption standards.
- Budget credits are abstract units, not MWK or actual procurement prices.
- Receipts are assumed available at the start of each month; delivery timing and lead-time variability are not simulated.
- Stockout-day estimates are monthly approximations, not observed daily stock-card evidence.
- The worklist is a deterministic scenario, not a procurement order or operational recommendation.
- Real use requires verified stock cards, approved commodity master data, procurement prices, expiry and batch controls, lead-time history, consumption validation, stock transfers and accountable supply-chain review.

## Outputs

- `commodity_catalog.csv`
- `facility_commodity_stock_ledger.csv`
- `commodity_replenishment_plan.csv`
- `commodity_replenishment_summary.csv`
- `supply_chain_planning_report.json`

Run independently with `python src/supply_chain_planning.py --periods 24 --budget-credits 50000`, or as part of `python src/build_platform.py`.
