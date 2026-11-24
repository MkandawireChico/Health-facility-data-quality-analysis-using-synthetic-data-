# Release readiness and integrity checks

The `src/release_readiness.py` module produces a transparent pass/warning/fail
report for the supplied integrated facility priority register, optional action
register and optional local platform build directory.

## Checks performed

- Required priority-register schema and non-empty facility population.
- Nonblank, unique facility identifiers.
- Numeric 0–100 score ranges and reconciliation of the integrated score to the
  arithmetic mean of its four component scores.
- Unique positive ranks.
- Corrective-action identifiers, supported statuses, reporting months,
  YYYY-MM-DD due dates and facility-ID linkage.
- If a local build directory is supplied, the module reads
  `platform_build_summary.json`, validates every manifest path remains inside
  the output directory, and recomputes artifact size and SHA-256 hashes.

A missing action register or missing local build summary is a warning, not a
pass. Integrity failures block the report. Readiness values describe only the
checks actually performed: BLOCKED, CONDITIONAL or DATA_CHECKS_PASS.

## Streamlit use

The expanded dashboard renders the check table and offers a CSV download.
The build summary and artifact manifest are checked only when the local
`data/warehouse` output exists. The report does not execute the build, tests,
notebook or Power BI, and does not inspect the hosted app.

## Limitations

All facility, operational, staffing and action data are synthetic. A passing
report does not establish clinical validity, official facility performance,
deployment, shared multi-user persistence, Power BI refresh or successful
full-suite CI. The full release gate remains in
`docs/release_validation_checklist.md`.
