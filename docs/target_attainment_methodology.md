# Target-attainment methodology

## Purpose

This layer adds a comparable-indicator performance view to the synthetic health-facility platform. It calculates reported-to-target attainment without combining unrelated indicators into a single facility score.

## Calculation

For each aggregation grain, records are grouped by the relevant facility, district, programme, indicator and/or month dimensions. Only valid records contribute:

- reporting month parses to a valid month;
- reported value is numeric and non-negative;
- target is numeric and strictly positive.

For a group:

`Attainment (%) = 100 × sum(valid reported values) / sum(valid targets)`

This pooled ratio preserves the target denominator and avoids taking an unweighted average of row-level percentages. Invalid or missing records are excluded from both totals. The output retains reporting-record count, valid-attainment-record count and valid-data percentage so users can see the evidence base.

## Outputs

- `facility_indicator_target_attainment.csv`: facility × programme × indicator.
- `district_indicator_target_attainment.csv`: district × programme × indicator.
- `programme_indicator_target_attainment.csv`: programme × indicator.
- `monthly_indicator_target_attainment.csv`: month × programme × indicator.
- `target_attainment_report.json`: method, valid-record rule, review bands and output inventory.

## Illustrative review bands

- Below 80%: below-target review.
- 80–99.9%: near target.
- At or above 100%: at/above target.
- No valid denominator: insufficient valid target data.

The 80% boundary is a portfolio demonstration convention, not a validated clinical, programme or Ministry of Health standard. Users should replace it only after agreeing indicator-specific definitions and thresholds with domain owners.

## Important limitations

- All facilities, targets, reported values and district performance are synthetic.
- Attainment is not population coverage, unique people served, or a clinical outcome.
- Catchment population is not used to infer coverage because indicators can count encounters, events, outputs or binary facility-readiness observations rather than unique people.
- Indicators are never pooled across unlike programme-indicator pairs.
- These outputs are decision-support examples, not official Malawi health-system performance measures.
