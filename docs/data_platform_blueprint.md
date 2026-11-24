# Expanded Health Data Intelligence Platform — Build Blueprint

## Project direction

This repository is expanding from a 960-row demonstration into a reproducible,
synthetic health-facility data intelligence platform. The target cohort is
**120 synthetic facilities × 60 months × 8 programmes × 5 indicators =
288,000 reporting records**.

All facility names, identifiers, catchment populations and reporting values are
synthetic. District names provide a Malawi-oriented geographic demonstration;
the data does not describe actual district or facility performance and contains
no patient-level information.

## Target analytical model

| Table | Grain | Purpose |
|---|---|---|
| Facility dimension | One row per synthetic facility | District, facility type, ownership, urban/rural classification and synthetic catchment population |
| Reporting fact | One row per facility × month × programme × indicator | Reported values, targets, source values, submission/deadline dates and controlled quality defects |
| Generation manifest | One record per generation run | Seed, dimensions, requested injection rates and actual injection counts |

Facility_ID is the stable relationship key. Record_ID uniquely identifies each
fact row. The intended natural key is Facility_ID + Month + Programme + Indicator.

## Controlled quality defects and evaluation

The generator injects four independently labelled problem classes:
- missing reported values;
- cross-source discrepancies;
- extreme reported-value outliers;
- late submissions.

Ground_Truth fields are evaluation labels, not operational inputs. Detection
logic should be evaluated against these labels using precision, recall, F1,
false-positive rate and confusion matrices. Ground-truth fields must be excluded
from model features and operational scoring.

## Reproducibility

Run from the repository root:

    python src/scale_data_generator.py

Optional controls:

    python src/scale_data_generator.py --seed 42 --facilities 120 --start-month 2021-01-01 --periods 60 --output-dir data/warehouse/raw

The command writes facility_reporting_fact.csv, facility_dimension.csv and
generation_manifest.json. The full fact file is generated at runtime and is
intentionally not committed as a large generated CSV; the code and manifest
schema are version controlled.

## Planned platform layers

1. Synthetic source layer: generator, facility dimension, reporting fact and manifest.
2. Staging and quality layer: schema contracts, duplicate detection, type normalization, validity checks and source reconciliation.
3. Analytics layer: longitudinal trends, statistical process control, anomaly evaluation, district/facility benchmarking and programme monitoring.
4. Operational layer: persistent corrective-action records, ownership, due dates, escalation and audit history.
5. Presentation layer: Streamlit decision workspace, Power BI semantic model and documented analytical notebook.

## Interpretation safeguards

- This is a portfolio engineering and analytics prototype, not a production health information system.
- No real Ministry of Health, DHIS2 or facility dataset is represented.
- Synthetic target values are scenario parameters, not official service-delivery targets.
- Risk scores and anomaly thresholds require domain validation before operational use.
- Ground-truth labels are retained to measure detection performance and must not leak into operational scoring.


## Implemented staging pipeline

The repository now includes a staging layer in `src/etl_pipeline.py`.
It reads the generated reporting fact and facility dimension, normalizes reporting
months and numeric/date fields, and enriches records from the authoritative
facility dimension using `Facility_ID`.

Structural integrity failures are quarantined rather than silently repaired:
missing or duplicated record identifiers, missing/unknown facility identifiers,
invalid reporting months, blank programme/indicator values and duplicate
facility-month-programme-indicator keys. All duplicate natural-key members are
quarantined so the surviving row is not chosen arbitrarily.

Analytical quality defects remain in the staged dataset with explicit flags:
missing reported values, invalid numeric text, negative values, invalid source
labels, incomplete source evidence, late submissions and material source spread.
This distinction prevents potentially useful but imperfect reporting records
from disappearing before analysis.

Run after generating the raw data:

    python src/scale_data_generator.py
    python src/etl_pipeline.py

Outputs are written to `data/warehouse/staged/`:
- `facility_reporting_staged.csv`
- `facility_reporting_quarantine.csv`
- `staging_quality_report.json`

The quality report summarizes input volume, staging yield, quarantine reasons
and issue counts. Ground-truth injection labels are not used by the staging
rules. The test suite exercises valid ingestion, structural quarantine,
duplicate handling, quality flags and persisted outputs.


## Implemented detector evaluation and operational analytics

The analytics layer is implemented in `src/quality_analytics.py`. Run it after staging:

    python src/quality_analytics.py

It evaluates four detectors (missing reported values, cross-source discrepancy,
reported-value outliers and late submissions) against the synthetic generator's
separate ground-truth labels. Each defect receives a confusion matrix and
precision, recall, F1, specificity, false-positive rate, accuracy, support and
predicted-positive count. The outlier detector uses a transparent
Reported_Value / Target_Value > 1.5 rule, aligned to the generator's injected
2–3x target outliers.

The same run produces operational profiles by month, facility and
programme/indicator. Facility rates are volume-normalised and ranked to support
follow-up prioritisation. Crucially, operational predictions and profiles are
constructed without reading ground-truth columns; those labels are used only
inside the evaluation step. Synthetic-label metrics measure recovery of known
injected defects in this controlled dataset, not validated real-world accuracy.

Outputs are written to `data/warehouse/analytics/`:
- `detector_evaluation_metrics.csv`
- `monthly_quality_trends.csv`
- `facility_quality_benchmark.csv`
- `programme_indicator_quality_profile.csv`
- `quality_analytics_report.json`

The module includes tests for confusion-matrix calculations, outlier detection,
ground-truth isolation, volume-normalised profiles and output persistence.


## Statistical monitoring and peer anomaly detection

The statistical layer is implemented in `src/statistical_monitoring.py` and runs
after staging:

    python src/statistical_monitoring.py

It compares reported values within district × programme × indicator peer groups.
The primary detector uses the median absolute deviation (MAD) robust z-score;
when MAD is zero, it falls back to an IQR fence and then a scale-aware median
tolerance for degenerate distributions. Groups below the minimum observation
count are not flagged. These are review prompts, not proof of reporting error.

A monthly issue-rate control view combines missing-value, source-discrepancy and
late-submission flags. Its three-sigma limits are calculated retrospectively
from the full observed period, so they are descriptive and must not be treated
as prospective alerting limits or a validated statistical process-control
system.

Outputs:
- `statistical_peer_anomalies.csv`
- `monthly_issue_control_chart.csv`
- `statistical_monitoring_report.json`

The generator also prevents a missing reported value from simultaneously
receiving an injected reported-value outlier label. Other defect categories
may overlap, so issue counts are not additive. All monitoring outputs exclude
ground-truth fields from their operational calculations.


## Streamlit expanded-platform workspace

The Streamlit app includes an **Expanded platform** workspace for staged
multi-year extracts. Upload the output of the ETL staging step
(`data/warehouse/staged/facility_reporting_staged.csv`) to run peer-group
anomaly detection, monthly issue-rate monitoring, facility/programme profiling
and optional detector evaluation when the synthetic ground-truth labels are
present. The app reports when evaluation labels are absent rather than
fabricating precision/recall metrics.

The uploaded analysis is session-scoped. The app does not persist the uploaded
data or analysis to a shared database. The 288,000-row generated dataset is
intentionally excluded from Git; generate it locally with the documented CLI
and upload the staged CSV when using this workspace. Streamlit browser QA and
performance testing on the deployed service remain separate validation tasks.


## Expanded analytical notebook

`notebooks/health_data_quality_analysis.ipynb` has been rebuilt around the
288,000-record platform. It runs the generator, validates the fact grain,
stages and quarantines records, evaluates operational detectors, creates
facility/programme/monthly profiles, applies statistical peer anomaly checks,
and exports reproducible warehouse artefacts. It includes an explicit
ground-truth isolation check by comparing operational predictions with and
without all `Ground_Truth_*` columns. Run from the repository root after
installing `requirements.txt`; a full run processes the complete synthetic
cohort and writes generated outputs under the ignored `data/warehouse/`
directory.


## One-command end-to-end build

Run the complete source-to-analytics pipeline with:

    python src/build_platform.py

The orchestrator writes raw fact/dimension tables and a generation manifest,
runs staging and structural quarantine, evaluates the operational detectors,
builds longitudinal profiles, and runs statistical peer anomaly/monthly
monitoring. It validates generated row counts and staging reconciliation and
writes `platform_build_summary.json`. The default configuration creates
288,000 records. Smaller builds can be configured with `--facilities`,
`--periods`, `--seed` and `--output-dir`.

The `Expanded platform build` GitHub Actions workflow runs the full default
cohort on relevant pull requests and main-branch changes, then publishes
generated warehouse artefacts for seven days. These outputs are validation
artefacts, not committed operational data.


## District-level quality intelligence

The operational analytics module also writes:
- `district_quality_profile.csv`: one row per district with reporting volume, distinct facility count, detected issue counts/rate and follow-up rank.
- `district_monthly_quality_trends.csv`: one row per district and month with record volume, facilities and detected issue rates.

These profiles are created only from operational ETL flags and derived detector outputs. Ground-truth columns are not used. District labels are synthetic-scenario geography and must not be interpreted as real district performance. The Streamlit Expanded Platform view includes district comparisons and longitudinal trends.

## Target-attainment and programme-performance layer

`src/target_attainment.py` calculates pooled reported-to-target attainment at facility-indicator, district-indicator, programme-indicator and month-indicator grain. It compares only matching programme-indicator pairs; unlike indicators are never combined into a single facility score. Missing/invalid months, missing or negative reported values, and missing/non-positive targets are excluded from numerator and denominator, while valid-data percentages remain available for interpretation.

Outputs include `facility_indicator_target_attainment.csv`, `district_indicator_target_attainment.csv`, `programme_indicator_target_attainment.csv`, `monthly_indicator_target_attainment.csv` and `target_attainment_report.json`. Illustrative bands are below 80%, 80–99.9%, and at/above 100%; they are not official service standards. These are not population coverage or unique people served. See `docs/target_attainment_methodology.md`.

## Corrective action register identity and lifecycle

Corrective-action record identifiers are generated from the selected source name and the facility-month-programme-indicator grain. They do not depend on dataframe row order or active filters. The dashboard exposes all saved actions, status totals, overdue actions, CSV export and field-level audit history. The default SQLite database persists on a durable local filesystem; Streamlit Community Cloud does not guarantee durable local storage or multi-instance consistency. A managed database and authentication are still required for production multi-user use.
