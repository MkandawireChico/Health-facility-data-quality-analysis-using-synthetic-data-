# Operational workflow and governance notes

## Intended use

The workspace demonstrates an aggregate reporting-quality workflow for an M&E or health-information team. It is designed to help users identify records for verification, not to make clinical decisions or certify official facility performance.

## 1. Intake

1. Start with the bundled synthetic data or upload a CSV that follows the [data dictionary](data_dictionary.md).
2. Review the intake panel before interpreting metrics.
3. Resolve missing columns before assessment. Investigate duplicate keys, invalid dates, non-numeric values, negative values and blank dimensions with the source owner.
4. Do not assume that a technically readable file is accurate or authorised for use.

## 2. Assessment rules

### Completeness

Completeness is calculated from actual presence of six value/source fields: reported value, target, data source, paper, EMR and DHIS2. It does not use the generator's simulated completeness score.

### Timeliness

When both `Submission_Date` and `Deadline_Date` are provided, the app compares those dates. If they are not both supplied, the app uses the existing `Timeliness` category where present. The bundled data uses synthetic timeliness labels.

### Source reconciliation

For records with at least two source values:

- When the minimum source value is zero, a difference greater than 5 units is flagged.
- When the minimum is positive, a record is flagged only when relative discrepancy exceeds 20% **and** absolute discrepancy exceeds 5 units.
- Fewer than two available source values produce **Unknown Sources** and are included in the follow-up register as insufficient source evidence.
- The 10% relative-only baseline is diagnostic and is not the production flag.

This rule is a configurable portfolio assumption. A real programme should agree thresholds by indicator, source, reporting frequency and operational context with its data-governance owners.

### Outlier detection

The app uses a 1.5 × IQR rule within programme/indicator groups. It requires at least five observations. An outlier is a statistical signal for review, not automatically an invalid value. Small samples, seasonality, service disruptions and indicator-specific distributions can affect interpretation.

### Facility risk index

The 0–100 index weights five dimensions equally: completeness shortfall, late reporting rate, source discrepancy rate, missing reported-value rate and outlier rate. Rates are used rather than raw counts so facilities with different reporting volumes can be compared more fairly.

The index is not externally validated and must not be used for sanctions, funding allocation, league tables or clinical judgements. Review the component rates and denominator before prioritising action.

## 3. Corrective action

For each flagged record, the register supports:

- status: Open, In progress, Resolved or Escalated
- assigned owner
- corrective-action notes

The current app stores these edits in the active Streamlit session only. Download the register to preserve the work. A production deployment would require authenticated users, role-based access, durable database storage, timestamps, audit history, backups and a defined retention policy.

## 4. Close the loop

1. Verify the discrepancy against approved source documents.
2. Contact the responsible reporting focal person through approved channels.
3. Record the agreed correction or explanation.
4. Update the reporting system of record using the organisation's authorised process.
5. Re-run assessment after the corrected aggregate extract is available.
6. Retain the before/after evidence and approval trail in the organisation's governed system.

## 5. Production-readiness gaps

This repository is a portfolio prototype, not a production health-information system. Before operational use it would need, at minimum:

- approval of the data contract and indicator-specific thresholds
- secure, access-controlled ingestion and storage
- authentication, authorisation and audit logging
- persistent action management and multi-user concurrency controls
- data retention, backup, incident response and privacy procedures
- validation against real, approved aggregate reporting extracts
- user acceptance testing with M&E and health-information staff
- monitoring, versioned releases and documented support ownership


## Corrective-action persistence

The Streamlit corrective-action register stores action details in a local
SQLite database using `src/action_store.py`. Each action can record an owner,
root cause, corrective action, due date and status. Changes are written to a
field-level history table with timestamps so users can inspect how an action
record evolved.

The default path is `data/warehouse/corrective_actions.sqlite`; set
`HEALTH_DATA_ACTION_DB` to use another path. The database is local to the
application host. Streamlit Community Cloud storage is ephemeral and is not a
shared multi-user database, so the CSV export remains an important backup.
Production use requires a managed database, authentication, role-based access,
backup/retention policy and audit governance.
