# Final repository audit — 23 November 2026

## Executive result

The expanded project is feature-complete in scope at the current development-branch level, but it is **not release-validated**. The seven pull requests are open, their dependency chain is currently consistent, and GitHub reports each as mergeable. Mergeability is only a branch-conflict signal; it is not evidence that tests, the full data build, notebook execution, Power BI refresh or browser QA passed.

Do not merge the stack while the required Actions checks are failing or unavailable.

## Repository and branch audit

Repository: `MkandawireChico/Health-facility-data-quality-analysis-using-synthetic-data-`

Default branch: `main`

The expanded platform branch contains source modules, focused tests, a 42-cell notebook, Streamlit application, Power Query templates, DAX measures, Power BI handover documentation, methodology documents and the release checklist.

The open pull-request dependency chain was checked on 23 November 2026:

| Order | PR | Head branch | Base branch | GitHub mergeable |
|---:|---:|---|---|---|
| 1 | #20 | `feat/district-intelligence-action-workflow` | `main` | Yes |
| 2 | #21 | `feat/resource-allocation-planning` | `feat/district-intelligence-action-workflow` | Yes |
| 3 | #22 | `feat/commodity-stockout-intelligence` | `feat/resource-allocation-planning` | Yes |
| 4 | #23 | `feat/cold-chain-batch-expiry-intelligence` | `feat/commodity-stockout-intelligence` | Yes |
| 5 | #24 | `feat/equipment-maintenance-uptime-intelligence` | `feat/cold-chain-batch-expiry-intelligence` | Yes |
| 6 | #25 | `feat/facility-infrastructure-utilities-intelligence` | `feat/equipment-maintenance-uptime-intelligence` | Yes |
| 7 | #26 | `feat/facility-workforce-capacity-intelligence` | `feat/facility-infrastructure-utilities-intelligence` | Yes |

The stack must be merged in this order, only after each parent is merged and the next child's base relationship is rechecked. Do not merge all seven simultaneously or bypass required checks.

## CI and validation audit

Workflow runs were retrieved for the reviewed PR heads:

| PR | Workflow result on reviewed head |
|---:|---|
| #20 | Expanded platform build: failure; project quality checks: failure |
| #21 | Expanded platform build: failure |
| #22 | Expanded platform build: failure |
| #23 | Expanded platform build: failure |
| #24 | Expanded platform build: failure |
| #25 | Expanded platform build: failure |
| #26 | Project quality checks: failure; expanded platform build: failure |

For the returned jobs, GitHub supplied no step summaries and no logs URL. Therefore the available evidence does **not** establish that Python tests or build assertions ran and failed. It also does not establish a successful run. This is consistent with the repository owner's reported Actions billing/runner-allocation blocker, but the job failure itself does not independently prove its root cause.

Required after runner allocation is restored:
- Run the quality workflow successfully on the final head of every PR.
- Run the expanded 120-facility, 60-period, 288,000-record build successfully.
- Inspect the build summary and verify every advertised artifact exists.
- Run the full test suite successfully.

## Source, notebook and integration review

- The source tree includes the central build orchestrator and modules for ETL, data quality, statistical monitoring, target attainment, resource allocation, commodity supply, cold-chain, equipment, infrastructure and workforce planning.
- Focused tests exist for these modules, the build orchestrator, Streamlit smoke testing and Power Query template inventory.
- The Power Query README enumerates the model queries and describes dimensional relationships, snapshot facts, fact grains and synthetic-data safeguards.
- The notebook is valid JSON with 42 cells and unique cell IDs. The resource-planning export now uses the notebook's resolved `OUTPUT_DIR`, avoiding a working-directory-dependent output location.
- Notebook JSON parsing is a structural check only. The notebook has not been executed end-to-end and the full notebook code has not been validated by a successful CI run.
- The Power Query inventory test is present, but it has not been executed successfully on the reviewed head.

## Dependencies and reproducibility

- `requirements.txt` declares the project's direct runtime, notebook and test dependencies using minimum-version ranges.
- The CI workflows target Python 3.11.
- No dependency lock file is present. A fresh install may resolve newer compatible package versions over time; exact environment reproduction is therefore not guaranteed. This is a reproducibility limitation, not a reason to guess or pin versions without a successful compatibility run.
- Generated expanded warehouse outputs under `data/warehouse/` are excluded from Git, as intended.
- The build workflow publishes generated warehouse artefacts when the job reaches its upload step; current failed jobs did not provide evidence that this step ran.

## Power BI and deployment audit

- The repository retains the original baseline PBIX and its four existing page images. These are baseline assets and should not be deleted as redundant.
- The expanded semantic-model pack contains Power Query M templates, DAX and a thirteen-page report build guide.
- The expanded PBIX has not been assembled or refreshed in Power BI Desktop. Query refresh, relationships, measures, report navigation and exported visuals remain manual release gates.
- The public Streamlit deployment must not be represented as containing unmerged feature-branch changes. A separate browser QA pass is still required after deployment.
- Screenshots of the expanded Streamlit or Power BI experience have not been captured as part of this audit.

## Data governance

The expanded cohort is synthetic: 120 illustrative facilities, six Malawi district labels, 60 monthly periods, eight programme areas, 40 indicators and 288,000 expected facility-month-indicator records. Facility identities, populations, observations, stock movements, assets, infrastructure events, workforce profiles and planning outputs are simulated. District labels are geographic references only; they do not represent actual district performance.

Abstract credits are not MWK. The scenario outputs are not clinical, procurement, staffing, product-disposition or engineering recommendations. No patient-level or employee-level personal data is generated.

## File-retention decision

No files were deleted during this audit. The baseline CSVs, PBIX, report-page images and original charts remain useful as the historical baseline and visual comparison set. Expanded warehouse extracts are generated locally and ignored by Git. Removing baseline assets before the expanded Power BI report is built and visually checked would reduce traceability without improving release readiness.

## Latest post-audit workflow check

After the audit and README link were committed, GitHub triggered fresh workflows on PR #26 head `e9888a5f4686bbd977667631b202ea908839c1da`:
- Project quality checks run #190 (`45192187822`): failed.
- Expanded platform build run #164 (`45192187836`): failed.

Both jobs returned no step summaries. The job-log download endpoint returned 404, so the underlying failure reason remains unavailable; no claim is made that test or build steps executed.

## Release decision

**Status: NOT READY TO MERGE OR RELEASE.**

The remaining blockers are external/manual validation rather than an identified branch conflict:
1. Restore GitHub Actions runner availability after the reported billing reset.
2. Obtain successful quality and full-build workflows on the final PR heads.
3. Execute the notebook from both the repository root and the `notebooks/` directory.
4. Complete Power BI Desktop refresh and save the expanded report as a separate PBIX.
5. Run Streamlit locally and visually verify the deployed application after deployment.
6. Capture final screenshots and update the README with only verified release claims.
7. Merge PRs #20–#26 in dependency order, rechecking each child base after its parent merges.

Until these gates are met, describe the project as an expanded development build with validation pending—not as a fully tested production platform.


## Integration review addendum — 23 November 2026

A focused integration review was performed after adding the executive briefing and
facility management drill-down.

- The executive briefing, facility drill-down, action-performance summaries,
  priority-action adapter and SQLite action store were exercised with their
  focused test modules in an isolated local Python environment: **49 tests
  passed**. Coverage includes district aggregation, facility filtering,
  priority-score reconciliation, action status counts, overdue deadlines,
  stable action IDs, persistence, field-level audit history, malformed dates,
  duplicate IDs/ranks and invalid reference dates. This is a focused subset,
  not the full repository suite.
- The review corrected two inaccurate assertions in the executive briefing
  tests: action resolution is rounded to two decimal places, and the selected
  facility in the fixture has one overdue unresolved action (the portfolio
  total is two).
- Date parsing for the management views and action-performance summaries now
  follows the documented YYYY-MM-DD action-date contract; invalid non-empty
  dates and invalid reference dates are rejected.
- GitHub Actions was triggered again for both the expanded platform build and
  project quality checks. Both runs failed before reporting any executed steps;
  the job-step endpoint returned empty step lists and downloadable logs were
  unavailable. This does not establish a code-test failure or prove the cause
  of the runner problem.
- The complete repository test suite, default 120-facility/60-period build,
  notebook execution, Streamlit browser workflow, hosted deployment and
  Power BI Desktop refresh remain unverified.

The project therefore remains **not release-validated**. Keep the seven-PR
dependency chain open and merge only after runner allocation is restored,
required checks execute successfully, and the manual release checklist is
completed. Do not infer deployment from branch commits.



## Release-readiness implementation addendum — 23 November 2026

A reusable release-readiness checker was added in `src/release_readiness.py`.
It checks priority-register schema, facility identifier uniqueness, score
ranges, integrated-score reconciliation, rank integrity, action record IDs,
status vocabulary, reporting months, due-date format and action-to-facility
linkage. When a local `platform_build_summary.json` is supplied, it verifies
that every manifest artifact exists inside the build directory and matches
its recorded byte size and SHA-256 digest. Missing optional action/build
inputs are warnings rather than false passes.

The Streamlit expanded-platform view now displays the pass/warning/fail table,
readiness state and downloadable CSV report. Documentation explains that
these checks do not replace CI, notebook, browser, deployment or Power BI
verification.

During this work, a pre-existing defect was found in
`src/platform_input_validation.py`: valid uploads referenced an uninitialised
month variable, and a return statement made the remaining facility metadata
and catchment-population checks unreachable. The validator was repaired to
handle missing required columns safely and validate every reporting month,
facility metadata field, catchment population, reported/target values and
quality flags. Nine additional tests cover those cases.

Nine new release-readiness tests cover valid/invalid priority registers,
action linkage, empty actions, absent build summaries, valid manifests,
manifest hash mismatches and path traversal. These tests have been added but
have **not yet been executed in GitHub Actions or a local checkout**.

The latest reviewed commit has two failed GitHub Actions runs. Both workflow
jobs report no step summaries and no downloadable logs. The available evidence
does not establish that Python installation or test commands ran; it also does
not establish that the code passed. Full validation remains pending.
