# Malawi Health Facility Data Intelligence & Performance Monitoring Platform

**Synthetic data engineering · Reporting quality assurance · Facility intelligence · Statistical monitoring · Corrective action management**

[![Project quality checks](https://github.com/MkandawireChico/Health-facility-data-quality-analysis-using-synthetic-data-/actions/workflows/quality-checks.yml/badge.svg)](https://github.com/MkandawireChico/Health-facility-data-quality-analysis-using-synthetic-data-/actions/workflows/quality-checks.yml)
[![Expanded platform build](https://github.com/MkandawireChico/Health-facility-data-quality-analysis-using-synthetic-data-/actions/workflows/platform-build.yml/badge.svg)](https://github.com/MkandawireChico/Health-facility-data-quality-analysis-using-synthetic-data-/actions/workflows/platform-build.yml)

> **Synthetic-data and responsible-use notice:** This repository contains no patient-level data and no actual Ministry of Health, DHIS2 or facility reporting extracts. Facility names, identifiers, catchment populations, targets and reported values are generated. Malawi district names are used as geographic labels only. The platform is a portfolio prototype, not a production health information system. Do not interpret its synthetic facility or district rankings as real service-delivery performance.

## Project overview

This project demonstrates how a health reporting data platform can move from raw facility submissions to governed, quality-assured analytical outputs and practical follow-up workflows.

It began as a compact 960-record data quality assessment and reporting dashboard. It has since been expanded into a reproducible, multi-year synthetic data platform with a relational-style facility dimension, a reporting fact table, structural quarantine, deterministic quality rules, detector evaluation, longitudinal analytics, robust peer anomaly detection, a Streamlit decision workspace, a SQLite-backed corrective action register and a Power BI implementation pack.

The expanded default cohort contains:

| Dimension | Scale |
|---|---:|
| Synthetic facilities | 120 |
| Malawi-oriented district labels | 6 |
| Monthly reporting periods | 60 |
| Programme areas | 8 |
| Indicators per programme | 5 |
| Total indicators | 40 |
| Facility-month-indicator fact records | **288,000** |

The 288,000-row build is generated on demand and is intentionally not committed to Git.

## What the platform does

### 1. Synthetic source generation

- Reproducible generation with a configurable random seed.
- Separate facility dimension and monthly reporting fact.
- Configurable facility count, start month and reporting horizon.
- Controlled missing values, source discrepancies, outliers and late reports.
- Ground-truth labels retained for evaluation, not operational scoring.

### 2. Data engineering and staging

- Required-schema enforcement and data type normalisation.
- Facility dimension enrichment using `Facility_ID`.
- Structural quarantine for broken identifiers, unknown facilities, invalid periods, blank programme/indicator dimensions and duplicate reporting grain.
- Analytical quality flags retained in the staged fact for review.
- Staging reconciliation and a machine-readable quality report.

### 3. Data quality and analytical monitoring

- Missing-value and numeric validity checks.
- Multi-source consistency and source spread.
- Reporting timeliness using submission and deadline dates.
- Operational detector evaluation using confusion counts, precision, recall, F1, specificity and false-positive rate.
- Monthly quality trends and volume-normalised facility and programme profiles.
- Robust MAD/IQR peer anomaly detection.
- Retrospective monthly issue-rate monitoring.

Ground-truth labels are only used to evaluate how well the synthetic detectors recover deliberately injected defects. They are not used to generate operational predictions, facility rankings, monthly issue rates or peer anomaly scores. These evaluation metrics are not real-world model validation.

### 4. Streamlit decision workspace

The browser-based workspace includes:

- Executive quality overview and filterable indicators.
- Facility risk prioritisation.
- Programme, indicator and reporting-period analysis.
- Paper, EMR and DHIS2 source reconciliation.
- Corrective action register with owner, root cause, due date and status.
- SQLite persistence and field-level action history.
- CSV upload, validation, templates and downloads.
- Expanded platform analysis for the staged multi-year cohort.

**Live app:** https://health-facility-data-quality-analysis.streamlit.app/

The expanded cohort is generated locally or through CI and can be uploaded to the Expanded Platform tab. It is not bundled into the deployed app.

### 5. Power BI implementation pack

The repository includes:
- Expanded star-schema and relationship specification.
- DAX measures for reporting volume, completeness, timeliness, source review and follow-up.
- Power Query M templates for the reporting fact, facility dimension and source observation fact.
- Dimension-table DAX and six-page report design guidance.

The existing `dashboard/health_facility_data_quality_dashboard.pbix` is the original compact demonstration. The expanded semantic model is supplied as an implementation pack; the binary PBIX has **not** been rebuilt to the 288,000-record model in this repository.

## Architecture

```text
Synthetic source generator
        |
        +--> Facility dimension
        |
        +--> Monthly reporting fact
                    |
                    v
          Staging and validation
             /           \
            v             v
       Staged fact     Structural quarantine
            |
            +-------------------------------+
            |                               |
            v                               v
  Operational quality rules        Synthetic detector evaluation
            |                         (ground truth only here)
            v
  Monthly / facility / programme profiles
            |
            v
  MAD / IQR peer anomalies + monthly monitoring
            |
       +----+-----------------------+
       |                            |
       v                            v
 Streamlit workspace          Power BI model pack
       |
       v
 SQLite corrective actions + field-level audit history
```

### Repository map

| Path | Purpose |
|---|---|
| `src/scale_data_generator.py` | Configurable 288k synthetic data generator |
| `src/etl_pipeline.py` | Staging, structural quarantine and quality profiling |
| `src/quality_analytics.py` | Detector evaluation and operational profiles |
| `src/statistical_monitoring.py` | MAD/IQR peer anomalies and monthly monitoring |
| `src/build_platform.py` | One-command end-to-end pipeline orchestrator |
| `src/action_store.py` | SQLite corrective action persistence and audit history |
| `src/reporting.py` | Streamlit assessment and issue-register logic |
| `dashboard/streamlit_app.py` | Streamlit decision workspace |
| `dashboard/powerbi_expanded_model.md` | Expanded Power BI semantic model and build guide |
| `dashboard/dax/` | DAX measures and dimension-table definitions |
| `dashboard/powerquery/` | Power Query M templates |
| `notebooks/health_data_quality_analysis.ipynb` | End-to-end analytical notebook |
| `docs/data_dictionary.md` | Field definitions and data structures |
| `docs/data_platform_blueprint.md` | Architecture, pipeline and governance blueprint |
| `docs/operational_workflow.md` | Operational quality-review workflow |
| `tests/` | Unit, integration and Streamlit smoke tests |

## Run locally

### 1. Set up the environment

Python 3.11 is used in CI.

```bash
git clone https://github.com/MkandawireChico/Health-facility-data-quality-analysis-using-synthetic-data-.git
cd Health-facility-data-quality-analysis-using-synthetic-data-
python -m venv .venv
```

Activate the environment:

```bash
# Windows PowerShell
.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate
```

Install dependencies:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Build the full synthetic platform

From the repository root:

```bash
python src/build_platform.py
```

This runs generation, staging, detector evaluation, operational profiling and statistical monitoring in sequence. It validates the expected fact count and reconciles staged plus quarantined rows.

Default outputs are written under the Git-ignored `data/warehouse/` directory:

```text
data/warehouse/
├── raw/
│   ├── facility_reporting_fact.csv
│   ├── facility_dimension.csv
│   └── generation_manifest.json
├── staged/
│   ├── facility_reporting_staged.csv
│   ├── facility_reporting_quarantine.csv
│   └── staging_quality_report.json
├── analytics/
│   ├── detector_evaluation_metrics.csv
│   ├── monthly_quality_trends.csv
│   ├── facility_quality_benchmark.csv
│   ├── programme_indicator_quality_profile.csv
│   ├── statistical_peer_anomalies.csv
│   ├── monthly_issue_control_chart.csv
│   └── expanded_platform_summary.json
└── platform_build_summary.json
```

Generate a smaller cohort for development:

```bash
python src/build_platform.py --facilities 12 --periods 12 --seed 42
```

Optional arguments:
- `--facilities`: number of synthetic facilities (default 120)
- `--periods`: number of monthly periods (default 60)
- `--start-month`: first reporting month (default 2021-01-01)
- `--seed`: random seed (default 42)
- `--output-dir`: output directory (default data/warehouse)

### 3. Launch the Streamlit workspace

```bash
streamlit run dashboard/streamlit_app.py
```

The main workspace uses the bundled compact demonstration dataset by default. To explore the expanded platform, upload the generated `data/warehouse/staged/facility_reporting_staged.csv` in the Expanded Platform tab.

### 4. Run the notebook

Open `notebooks/health_data_quality_analysis.ipynb` in Jupyter from the repository root. The notebook uses the same generator and analytical modules as the command-line workflow. Its default configuration processes the 288,000-record synthetic cohort.

### 5. Run tests

```bash
pytest -q
```

GitHub Actions runs:
- Python compilation, notebook syntax validation, unit and Streamlit smoke tests.
- A full default 288,000-record source-to-analytics build on relevant pull requests and main-branch changes. Generated validation outputs are uploaded as a short-lived workflow artifact, not committed to the repository.

## Corrective action persistence and deployment considerations

The corrective action register uses SQLite with field-level change history. Set `HEALTH_DATA_ACTION_DB` to choose the database path. On a persistent local host, saved action assignments remain available after the app restarts.

Streamlit Community Cloud's local filesystem is ephemeral and is not a shared multi-user database. The current live deployment therefore must not be treated as durable enterprise action management. A production deployment would require a managed database, authentication, role-based permissions, secure secrets, backups and an audit-retention policy.

## Quality rules and interpretation

- Source reconciliation uses a combined relative and absolute tolerance. For positive source minima, the production review rule requires relative spread above 20% **and** absolute spread above 5 units. If the minimum source value is zero, the absolute tolerance applies.
- Timeliness is based on submission and deadline dates when supplied; otherwise the legacy timeliness field or an unknown state is used.
- IQR peer/outlier methods require sufficient observations. MAD/IQR peer anomaly signals are verification prompts, not proof of an error.
- Monthly three-sigma limits use the full observed period retrospectively. They are descriptive signals, not prospective alert thresholds.
- Issue categories may overlap. Distinct follow-up records must not be calculated by adding individual issue counts.
- Synthetic detector precision, recall and F1 measure recovery of controlled injected defects only.

## Current limitations and production pathway

This is a substantial portfolio prototype, not a certified health information system. It does not include:
- Real Ministry of Health, DHIS2 or facility source integrations.
- Patient-level records or clinical decision support.
- Authentication, role-based access control or a shared multi-user database.
- Production audit governance, backup and disaster recovery.
- Domain-approved indicator definitions, target validation or operational alert SLAs.
- A rebuilt expanded-model PBIX file or production Power BI service deployment.
- Real-world validation of synthetic detector performance or statistical thresholds.

A production pathway would require stakeholder-approved data definitions, data-sharing agreements, security and privacy review, access controls, managed persistence, audit retention, source integration, monitoring ownership and validation with authorised real-world data.

## Portfolio context

The project demonstrates data generation, Python engineering, ETL design, data quality controls, analytical evaluation, statistical monitoring, interactive reporting, audit-aware workflow design, Power BI modelling and automated testing. It is designed to show the full path from source data to an actionable reporting-quality process while keeping the synthetic-data boundary explicit.
