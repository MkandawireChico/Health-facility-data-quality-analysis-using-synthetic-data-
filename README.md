# Health Facility Data Quality Assessment & Reporting Dashboard
## Rumphi District, Malawi (Synthetic Portfolio Dataset)

## Project Overview

This project demonstrates a practical data quality assessment and reporting workflow for health facilities, using a realistic **synthetic** dataset representing monthly reporting across multiple programme areas and three parallel data sources (Paper Register, EMR, DHIS2).

The analysis identifies incomplete records, inconsistencies between reporting systems, delayed reporting, unusual values, and other data-quality problems that would affect programme monitoring and decision-making in a real health information system.

Built as a portfolio demonstration for Data Technician, Data Analyst, Monitoring & Evaluation (M&E), and health informatics roles.

**All data in this project is synthetic, generated programmatically with a fixed random seed (see `notebooks/health_data_quality_analysis.ipynb`, Section 1). It does not represent actual patient, facility, or Ministry of Health data. Facility names are illustrative, chosen to be plausible for the district, not drawn from any real facility list.**

## Problem Statement

Health programmes depend on accurate, complete, and timely information for monitoring performance and supporting operational decisions. Where information is recorded across paper registers, electronic medical records, and platforms like DHIS2, differences between sources create real data-quality problems: missing values, duplicate or inconsistent records, delayed reporting, out-of-range values, and disagreement between systems. These problems make routine reporting less reliable and increase the time required for verification and correction.

This project demonstrates how a Data Technician or M&E Assistant could identify these issues systematically using Python, and present the results through a Power BI dashboard designed around an M&E Officer's actual follow-up workflow.

## Objectives

1. Assess data completeness across facilities and programme areas
2. Identify inconsistencies between paper, EMR, and DHIS2 records
3. Identify unusual or potentially erroneous reported values
4. Analyse reporting timeliness
5. Identify facilities with recurring data-quality problems
6. Analyse trends in reported indicators over time
7. Produce a prioritized, risk-ranked view to support M&E follow-up decisions
8. Demonstrate a complete, reproducible workflow from raw data to actionable output

## Synthetic Dataset

Generated in the notebook (not sourced from anywhere): 8 fictional facilities x 12 months (2025) x 5 programme areas x 2 indicators each x information from 3 reporting sources = **960 monthly facility-indicator records**.

Programme areas: **HIV, TB, Maternal Health, Child Health, Outpatient** (two indicators each — e.g. HIV has "Patients on ART" and "New ART Initiations").

Four categories of realistic data-quality problems are deliberately injected with their own fixed random seeds, so the exact affected rows are reproducible:
- **Missing reported values** — 3% of records
- **Source discrepancies** (DHIS2 perturbed 40–60% from the other sources) — 5% of records
- **Outliers** (reported value inflated to 2–3x target) — 2% of records
- **Forced late reports** — an additional 8% of records, on top of the ~12% baseline lateness rate

No real patient-level information is included anywhere in this project.

## Tools Used

Python (Pandas, NumPy, Matplotlib, Seaborn) · Jupyter Notebook · Power BI (implementation guide)

Python was used for data generation, cleaning, validation, data-quality assessment, and visualisation. Power BI is the target tool for the final interactive dashboard (see [`dashboard/`](dashboard/)).

## Project Workflow

```
Raw Synthetic Data → Data Inspection → Data Cleaning → Data Validation
    → Data Quality Assessment → Exploratory Analysis → Key Findings → Power BI Dashboard
```

## Data Quality Dimensions

- **Completeness** — are required fields/records available? (`Completeness_Score`)
- **Consistency** — do the three reporting sources agree? (`Consistency_Flag`)
- **Timeliness** — was reporting completed on time? (`Timeliness`)
- **Validity** — do reported values fall within a reasonable range? (`Outlier_Flag`, per-indicator IQR rule)

## Key Findings

*(These describe what this specific synthetic dataset shows once generated and analysed — they demonstrate the type of insight the workflow produces, not real Rumphi District conditions. All figures are computed directly in `notebooks/health_data_quality_analysis.ipynb`.)*

1. **Overall completeness is 87.0%**, timely reporting is **80.8%**, and **537 of 960 records (56%)** carry at least one data-quality flag — a useful reminder that "mostly fine" summary statistics can still sit on top of a majority-flagged dataset once every dimension is checked, not just one.

2. **Source Discrepancy is the single largest issue category** (339 records, 35% of all records) — well above the 5% of records where a discrepancy was deliberately injected. Investigating why revealed an important methodological finding, not just a data problem: **the 10% discrepancy threshold is too strict relative to ordinary sampling noise for low-volume indicators.** An indicator like "New TB Cases" (target 10–60) swings much more in *relative* terms from a few units of natural noise than "OPD Visits" (target 500–1500) does — so the same flat 10% threshold catches far more low-volume indicators by chance. This is documented as a specific caveat in [`dashboard/powerbi_dashboard_documentation.md`](dashboard/powerbi_dashboard_documentation.md) (Section 6), because shipping a dashboard with a threshold this sensitive would flood an M&E Officer's worklist with false positives.

3. **Kachulu and Rumphi Central Health Centres have the lowest reporting timeliness** (74.2% and 77.5% on-time respectively), while Katowo Health Centre is most timely (85.0%).

4. **Katowo and Bolero Health Centres have the lowest average completeness** (84.7% and 85.3%), while Rumphi Central is highest (88.6%) — notably the facility with the *worst* timeliness has the *best* completeness, showing these two dimensions don't necessarily move together and both need tracking independently.

5. **Chiweta Health Centre has the most source-discrepancy records** (53), followed by Bolero (50) and Kachulu (49) — Katowo has the fewest (33).

6. **Kachulu Health Centre ranks highest on the combined risk score** (165.5), driven by a combination of below-average completeness, high discrepancy count, and high lateness — making it the top candidate for follow-up under this scoring approach. Katowo ranks lowest-risk (119.8) despite having the most source discrepancies, because its strong completeness and timeliness outweigh that in the combined score — illustrating why a single combined metric needs to be checked against its components before acting on it.

Full facility-by-facility, programme-by-programme, and monthly breakdowns are in the notebook itself.

## Recommended Dashboard

Not yet built — see [`dashboard/powerbi_dashboard_documentation.md`](dashboard/powerbi_dashboard_documentation.md) for the full implementation plan: data model, DAX measures, a 4-page layout (Data Quality Overview, Facility Performance, Source Consistency, Programme Monitoring), and — importantly — a documented plan to surface the threshold-sensitivity finding above directly in the dashboard rather than only in this README.

## Decision-Making Use Case

A Monitoring & Evaluation Officer could use the dashboard to prioritise follow-up. For example: a facility shows low completeness for HIV reporting and repeated Paper/DHIS2 disagreement. The officer could identify the affected months, review source documents, contact the responsible facility staff, correct the reporting issue, and monitor that facility in subsequent cycles. This is what turns the dashboard from a reporting tool into a data-quality monitoring tool.

## Project Structure

```
health-facility-data-quality/
├── data/
│   ├── raw/
│   │   └── synthetic_health_facility_data.csv       # As generated, before cleaning
│   └── processed/
│       └── cleaned_health_facility_data.csv         # Cleaned + all quality flags added
├── notebooks/
│   └── health_data_quality_analysis.ipynb           # Full workflow, executed with real outputs
├── dashboard/
│   └── powerbi_dashboard_documentation.md           # Implementation guide (not yet built)
├── visuals/
│   └── charts/                                       # 7 chart exports from the notebook
├── requirements.txt
└── README.md
```

**What belongs where:** `data/` holds only the dataset and its two states (raw synthetic, cleaned); `notebooks/` is the analysis itself, meant to be read top-to-bottom; `dashboard/` is planning/documentation for the BI layer (the `.pbix` would go here once built); `visuals/charts/` holds static exports for embedding in documentation.

## How to Run

```bash
git clone <this-repo>
cd health-facility-data-quality
pip install -r requirements.txt

jupyter notebook notebooks/health_data_quality_analysis.ipynb
# Run all cells — this regenerates the synthetic dataset (fixed seed = identical output),
# performs the full data-quality assessment, and writes data/processed/ and visuals/charts/
```

## Ethical Considerations

This project uses entirely synthetic data. No real patient information, patient identifiers, or actual facility records are used at any point. Facility names and all numerical results exist solely to demonstrate the workflow. This project does not claim to represent actual Ministry of Health, DHIS2, or Rumphi District facility performance.

## Portfolio Relevance

Demonstrates skills relevant to: Data Technician · Data Analyst · Monitoring & Evaluation Assistant · Health Information Systems Assistant · M&E Data Officer · Research Data Assistant · Health Informatics roles — specifically the ability to move from raw, imperfect data to validated information and a prioritized, actionable output.

## Future Improvements

- Rebuild the Power BI dashboard from the guide in `dashboard/` and add screenshots here
- Replace the flat 10% consistency threshold with an indicator-relative or volume-scaled threshold, informed by Finding #2 above
- Add a simple statistical control-chart approach (e.g. rolling mean ± 2 SD) as an alternative to the per-indicator IQR outlier rule, and compare which flags more sensibly
- If real (properly anonymized/aggregated) reporting data ever becomes available for a similar workflow, validate whether the same data-quality patterns hold

## Author

Chico Mkandawire
MSc Data Science, Malawi University of Science and Technology (in progress)
BSc Management Information Systems, Malawi University of Business and Applied Sciences
