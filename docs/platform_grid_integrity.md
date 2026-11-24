# Exact platform grid and identity reconciliation

The one-command build validates the generated reporting fact against the full
configured cohort before ETL begins.

## Checks

- The fact row count equals facilities × configured months × configured
  programme-indicator pairs.
- Facility identifiers are nonblank, unique in the dimension, and the fact
  contains exactly the canonical facility population.
- The fact natural key
  (Facility_ID, Month, Programme, Indicator) is unique and contains no null or
  blank components.
- The observed programme-indicator pairs equal the configured generator
  catalogue exactly. Equal row counts or equal indicator counts alone are not
  accepted as proof of coverage.
- The observed reporting months equal the configured monthly sequence, not
  merely the same number of distinct months.
- Every facility-month contains the complete configured programme-indicator
  grid.
- Where canonical facility names and districts are present in the dimension,
  those values must match the generated fact for every row.

A failed check stops the build before staging and downstream analytics. The
build summary records the number of unique facility-month groups, configured
indicator pairs, natural keys and reporting months.

## Why exact-grid validation matters

A count-only check can pass if one indicator is accidentally omitted and
another is substituted, provided the row count remains unchanged. Exact set
reconciliation catches this type of silent schema/catalogue drift. Comparing
configured months also catches a shifted or substituted period sequence that
would otherwise pass a distinct-month count check.

## Scope and limitations

These checks validate the synthetic source fact and its facility dimension.
They do not establish that synthetic assumptions reflect real facilities,
that operational planning outputs are clinically or operationally appropriate,
or that the notebook, Power BI model, hosted dashboard or deployment has been
independently verified. The full 120-facility, 60-month build remains subject
to successful CI execution and release review.
