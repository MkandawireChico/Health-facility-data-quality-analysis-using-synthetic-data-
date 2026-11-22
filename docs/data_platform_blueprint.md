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
