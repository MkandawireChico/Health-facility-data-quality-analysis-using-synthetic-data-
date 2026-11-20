# Data dictionary and reporting contract

## Scope

This contract describes the CSV accepted by the Health Facility Data Quality Workspace. The bundled dataset is synthetic and exists only for demonstration and testing. The schema is a portfolio interface, not an official Malawi Ministry of Health or DHIS2 specification.

Do not upload patient names, patient identifiers, dates of birth, contact details, clinical notes, or row-level patient records. The intended grain is one aggregate facility–month–programme–indicator record.

## Required fields

| Field | Expected type | Meaning | Validation/use |
|---|---|---|---|
| `Facility` | Text | Reporting facility name/code | Required grouping dimension; blank values are flagged |
| `Programme` | Text | Programme area | Required grouping dimension |
| `Indicator` | Text | Indicator name/code | Required grouping dimension; used to group outlier checks |
| `Month` | Date | Reporting month/period | Must be parseable as a date |
| `Reported_Value` | Numeric | Value selected for the submitted report | Missing values are flagged; used in target and outlier analysis |
| `Target_Value` | Numeric | Corresponding target for the reporting record | Used for aggregate target-attainment context |
| `Data_Source` | Text | Source selected as the submitted value | Contributes to field completeness |
| `Paper_Value` | Numeric | Value transcribed from paper register | Used for three-way reconciliation |
| `EMR_Value` | Numeric | Value in electronic medical record source | Used for three-way reconciliation |
| `DHIS2_Value` | Numeric | Value in DHIS2 source | Used for three-way reconciliation |

## Optional fields

| Field | Expected type | Meaning | Behaviour |
|---|---|---|---|
| `Submission_Date` | Date | Date the aggregate report was submitted | Used for timeliness when paired with `Deadline_Date` |
| `Deadline_Date` | Date | Agreed submission deadline | Used for timeliness when paired with `Submission_Date` |
| `Timeliness` | Text | Existing timeliness category | Used only when actual submission/deadline date columns are not both supplied |

When both actual date columns are present, a submission on or before the deadline is **On Time**; a later submission is **Late**; either missing date yields **Unknown**. The optional date columns should be supplied together.

## Validation behaviour

- Required-column absence or an empty file prevents assessment.
- Unparseable reporting months, duplicate facility-month-programme-indicator keys, non-numeric values, negative values and blank dimensions are surfaced as intake warnings.
- Non-numeric values are coerced to missing for assessment; they are not guessed or imputed.
- Duplicate rows are not silently deleted.
- Negative values are not silently changed. They require source-level review and may be legitimate adjustments depending on the indicator.
- A source comparison requires at least two available source values. Fewer than two are labelled **Unknown Sources**, not consistent.

## Derived fields

| Field | Definition |
|---|---|
| `Calculated_Completeness` | Proportion of six value/source fields present: reported value, target, data source, paper, EMR and DHIS2 |
| `Calculated_Timeliness` | Actual date comparison when both date fields exist; otherwise the synthetic/existing `Timeliness` category; otherwise Unknown |
| `Source_Discrepancy_Abs` | Maximum minus minimum available source value |
| `Source_Discrepancy_Pct_Baseline` | Absolute discrepancy divided by minimum source value when minimum is positive; diagnostic only |
| `Consistency_Flag` | Production hybrid source review status; see operational workflow |
| `Outlier_Flag` | IQR-based statistical review flag grouped by programme and indicator |
| `Primary_Issue` | One highest-priority issue label for quick triage |
| `Issue_Count` | Count of all applicable issue flags for the record |
| `Requires_Follow_Up` | True when at least one issue flag is present |

## Interpretation

A flag is a prompt to verify source documents and reporting context, not proof of error or misconduct. Statistical outliers and cross-system discrepancies must be reviewed by an authorised data-quality focal person before any correction is made.
