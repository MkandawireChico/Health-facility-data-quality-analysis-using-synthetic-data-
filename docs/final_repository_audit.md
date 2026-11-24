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


## Exact source-grid integrity addendum — 24 November 2026

The source-to-ETL boundary now validates the exact configured reporting grid, not only aggregate row counts. src/build_platform.py compares the generated programme-indicator catalogue with the generator configuration, verifies the configured monthly sequence, checks the complete facility × month × programme-indicator natural-key set, reconciles the facility population, and checks generated facility names and districts against the canonical dimension.

This closes a count-only validation gap: a substituted indicator could previously preserve the expected row count and indicators-per-facility-month while still producing an incorrect catalogue. The revised check fails the build on that mismatch before staging.

Four regression tests were added for indicator substitution, incomplete indicator coverage, substituted reporting months and facility metadata drift. The existing successful-grid fixture was updated for the expanded diagnostic summary. The implementation is documented in docs/platform_grid_integrity.md and linked from the README.

The source and tests were committed to the existing feat/facility-workforce-capacity-intelligence branch and PR #26. These new tests have NOT been executed: the repository GitHub Actions runner allocation issue remains unresolved, and no local checkout is available in this session. Do not interpret the added tests or static code changes as a passing test result. The default 288,000-row build and downstream output reconciliation remain unverified until CI can execute successfully.


### Follow-up CI observation — 24 November 2026

After the exact-grid changes, Expanded platform build run 45345557288 (run #247) was created for the branch and then failed at the job level. The job endpoint returned status=completed, conclusion=failure, steps=null and no log URL. The run therefore provides no evidence that the build or Python tests executed. The separate project quality workflow was not reported for the latest source commit. Automated validation remains blocked/unverified.


## Operational ledger reconciliation addendum — 24 November 2026

A new src/operational_reconciliation.py module adds cross-domain internal-accounting checks and the one-command build now runs them before recording its final build summary. The checks cover: resource allocation gap, residual and coverage calculations plus scenario pool bounds; commodity stock balance, demand fulfilment, stockout flag/day agreement and month-to-month stock continuity; cold-chain batch balance and continuity plus batch-to-risk-summary reconciliation; equipment downtime and availability calculations plus maintenance work-order cost/downtime reconciliation; infrastructure power/water hour balances, availability percentages and the weighted resilience formula including the facility backup-power assumption; and workforce filled/vacant/absent/on-duty counts, coverage, absence and workload-pressure calculations.

Regression coverage was added in tests/test_operational_reconciliation.py for valid scenarios and intentionally broken resource, stock, cold-chain, equipment, infrastructure and workforce reconciliations, including a valid zero-stock month with no batch records. The small end-to-end platform test now checks that all six domain reconciliation summaries are present. Documentation is in docs/operational_ledger_reconciliation.md and the README.

A code-review adjustment was made for a valid cold-chain edge case: when no lot exists in a facility-commodity-month, the lot ledger can legitimately have no row. The reconciler accepts that only when all batch-backed quantities in the risk summary are zero; it rejects orphan lot rows and non-zero summary quantities without batch movements.

These source and test changes are committed on feat/facility-workforce-capacity-intelligence and remain part of PR #26. The latest source/test commits have no reported workflow run, and the earlier runner failure returned no executed steps or logs. The new tests and full build have NOT been run successfully. The checks are authored controls, not evidence of passing CI or real-world operational validity.


### Cold-chain reconciliation precision follow-up — 24 November 2026

A final code review tightened near-expiry reconciliation: the batch ledger's Near_Expiry_90_Days field is a Boolean lot flag, while the risk summary reports the number of units. The reconciler now sums Closing_Stock_Units only for lots whose 90-day flag is true, rather than summing Boolean flags. A multi-lot regression test verifies this distinction. The cold-chain reconciler also explicitly permits risk-summary-only rows when the facility/commodity/month has zero batch-backed quantities, while rejecting non-zero summary quantities without lot movements and orphan lot records.


### Latest CI result for operational reconciliation — 24 November 2026

The latest branch head 0f655c407ad7dd8b226291721bcc3d9d20b5f2b4 triggered Project quality checks run #290 (45346668300) and Expanded platform build run #264 (45346668416). Both completed with failure at job level. Their job records contain steps=null and logs_url=null. Therefore, the available Actions response does not establish that the test or build commands executed, and it does not establish a code-level test failure or a passing result. Full test and build validation remains outstanding.


## Integrated priority and executive queue audit — 24 November 2026

A focused review of the cross-domain priority register and executive management
briefing found that the briefing checked component-score arithmetic but did not
independently enforce the documented priority-band thresholds or the
priority-register's deterministic rank sequence. This could allow a stale or
manually edited register to display a score that did not match its band, or
ranks that did not follow descending score and ascending facility ID.

The executive briefing now rejects:
- priority bands inconsistent with the documented thresholds (High review
  >=50, Focused review >=25 and <50, Routine review <25);
- fractional, missing, non-positive or non-contiguous ranks; and
- rank sequences that do not follow descending integrated score with ascending
  Facility_ID as the deterministic tie-break.

Regression tests cover inconsistent bands, fractional ranks, incorrect rank
order and tied scores. The management queue itself intentionally retains its
separate operational sort (priority score, then overdue actions, then rank);
the canonical priority rank remains the score/Facility_ID ordering.

The source and tests are committed to the existing workforce-capacity branch
and PR #26. GitHub Actions execution is still unverified at the time of this
addendum; do not treat added tests as passing. The review does not change the
mixed time scopes of the four priority inputs or the synthetic-only
interpretation.


The same audit also found that resource baseline gap units were reconciled to
requirement and available units, but the coverage percentage used in the
priority score was only range-checked. The build now independently recalculates
coverage as available units divided by positive illustrative requirement units,
multiplied by 100 and rounded to two decimals. A regression case rejects a
coverage value that does not match the underlying unit counts. This retains
legitimate capacity values above 100% as synthetic surplus.


## Cross-dashboard corrective-action reconciliation audit — 24 November 2026

A cross-check of the executive briefing against the separate district/month
action-performance module identified a district attribution risk. The action
register stores a human-readable facility label containing both a district
and a canonical Facility_ID. The executive briefing previously used the ID to
join actions to the priority register but did not verify that the district
embedded in the label matched the canonical district. A stale or edited label
could therefore attribute an action to one district in the action-performance
dashboard and another in the executive briefing.

The executive briefing now extracts the district from the action label and
requires an exact match to the canonical priority-register district for that
Facility_ID. Regression tests reject mismatched districts and compare
district-level tracked, resolved, overdue, open, in-progress and escalated
counts between the executive briefing and action-performance module.

This closes a known district attribution inconsistency at the executive
integration boundary. It does not validate action ownership, evidence of
completion, or real-world facility identity; all data remain synthetic.
The new tests have been committed but automated execution is still
unverified.


## Dashboard consistency audit — Prompt 30, 24 November 2026

The integrated action-performance dashboard previously grouped action labels
by their embedded district without checking that the Facility_ID belonged to
that district in the current integrated priority register. The executive
briefing now performs that check, and the action-performance module now accepts
the same priority register and independently enforces the same canonical
facility-to-district mapping. Unknown facility IDs and mismatched district
labels are rejected before district summaries are returned.

The Streamlit expanded-platform view now passes the current priority register
to action-performance validation. It also creates one management reference
date per render and passes that date to the portfolio overdue calculation,
action-performance module, executive briefing and facility drill-down. This
prevents adjacent dashboard panels from calculating overdue status against
different dates if the view crosses midnight.

Regression tests were added for action records whose district label conflicts
with the canonical facility mapping and for unknown facility IDs. The date is
initialized even when the action register is empty so the executive briefing
and facility drill-down retain a valid shared reference date.

The source, dashboard and test changes are committed to the existing workforce
capacity feature branch and PR #26. No successful automated run has been
verified for these latest commits. The Streamlit app, notebook and Power BI
expanded model still require separate execution/browser/Desktop validation.


## Management export completeness audit — Prompt 31, 24 November 2026

The original expanded-analysis ZIP is generated before the saved corrective-action
portfolio, executive briefing, release-readiness checks and facility drill-down
are calculated. It therefore represents analytical outputs, not a complete
management review. Its dashboard label and filename now explicitly identify it
as the analytical outputs pack.

A separate management review ZIP is now assembled after those sections run.
It includes the integrated facility priority register and saved integrated
action register, plus district/monthly action performance, full executive
facility briefing, executive district and domain summaries, the top-N management
queue, release-readiness checks, selected-facility action history and priority
components when available, and all available field-level action audit history.
Its JSON summary records the snapshot date, selected facility, action count,
included tables and which optional management sections were successfully
prepared. The export is a point-in-time review bundle, not a database backup.

ZIP creation is factored into `src/management_export.py`, which validates
table types and archive filenames, and has dedicated tests for archive contents,
summary integrity, and invalid/path-traversal inputs. These tests have been
committed but have not yet been confirmed by a successful CI run. No merge or
deployment has been performed.


## End-to-end data-lineage audit — Prompt 32, 24 November 2026

A cross-artifact reconciliation layer was added in `src/lineage_audit.py`.
The upstream build path was also traced: `src/build_platform.py` already
checks the generated facility-month-indicator natural-key grid, generated
versus staged/analytics row counts, monthly quality/monitoring/attainment
populations, disjoint facility/district/programme-indicator quality profile
totals, resource/workforce facility populations and six operational ledgers
(resource, commodity stock, cold-chain, equipment, infrastructure and
workforce). The analytical ZIP is assembled from the same result DataFrames
used by the Streamlit analytical sections. These are code-level controls;
their full build execution remains unverified.

The Streamlit management ZIP is now withheld unless the following checks pass:

- The executive all-facility output contains exactly the canonical priority
  register facility IDs and retains the same district, integrated score, rank
  and priority band for every facility.
- The validated action-performance register contains the same unique
  `Record_ID` population and status totals as the saved integrated action
  register.
- Action-performance status totals, overdue KPI, district/status aggregates,
  and monthly action totals reconcile to the saved action portfolio.
- Executive tracked/overdue KPIs and district status totals reconcile to the
  action-performance view. Districts with no saved actions are retained in the
  executive portfolio and treated as zero when compared with the
  action-performance view, which only emits districts that have actions.
- The management ZIP's priority, action, action-performance, executive and
  top-N queue CSVs must match the exact DataFrames supplied to the corresponding
  dashboard views. The full executive facility output is kept distinct from
  the separate top-12 management queue.

A passing `lineage_reconciliation_checks.csv` is included in the ZIP summary
and tables. If a required view is unavailable or any comparison fails, the
complete management ZIP is withheld rather than presented as reconciled.
Nine regression tests were added in `tests/test_lineage_audit.py` for the
valid cross-artifact path, missing saved actions, executive facility
population drift, action KPI drift, district export drift, invalid queue
facilities, an empty action portfolio, monthly status-total drift and
executive facility status-total drift. The existing
executive-versus-action-performance district test was adjusted to align
zero-action districts explicitly.

These changes are committed to the existing
`feat/facility-workforce-capacity-intelligence` branch and PR #26. The tests
have been added but have **not been executed successfully** in this session.
The latest previously observed Actions failures had no step summaries or
downloadable logs; this audit does not claim a passing test suite, a successful
288,000-row build, browser QA, Power BI refresh or deployment. PR #26 remains
open and unmerged.


### Prompt 32 CI observation — 24 November 2026

The latest Prompt 32 head `993a9c2804bddfbca94b28f60d559c6bf9652ed8`
triggered Expanded platform build run #293 (`45349421992`) and Project
quality checks run #319 (`45349422082`). Both report job-level failure.
The job-step endpoint returned an empty list for each job, and the log
download was unavailable. It is unknown whether any Python test or build
command executed; this is neither a passing result nor evidence of a
code-level test failure. The nine new lineage tests remain unverified.



## CI failure investigation — Prompt 33, 24 November 2026

The quality workflow definition was inspected directly. Its intended steps are
checkout, Python 3.11 setup, dependency installation, Python module compilation,
notebook JSON/code-cell validation, and the full pytest suite. The expanded
platform workflow similarly checks out the repository, sets up Python 3.11,
installs requirements, and runs `python src/build_platform.py`.

For the Prompt 32 head recorded above, the latest workflow runs were retried
using GitHub's failed-jobs-only rerun operation. The rerun operation was
accepted for Expanded platform build run #293 (run ID 45349421992) and Project
quality checks run #319 (run ID 45349422082). On immediate inspection, the
expanded build job was again completed with failure and had no recorded steps;
the quality job was still queued and also exposed no steps at that instant.
The step endpoint returned an empty list for both jobs. The log archive
remained unavailable.

This evidence still does not identify a Python exception, failed test, failed
dependency install, or build assertion. An empty step list is consistent with
a job failing before its first step, but does not by itself establish the
underlying cause. The rerun has therefore not been treated as a code-level
failure or a successful validation.

No speculative source-code workaround or runner-image change was made. The
next diagnostic requirement is access to the actual GitHub Actions run/job
details or logs, including any runner provisioning and workflow-level
annotations. Until those are available, CI remains blocked/unverified and the
stacked PR must not be merged. The Streamlit deployment, notebook execution,
and expanded Power BI refresh also remain independently unverified.


### Prompt 33 retry follow-up

A later poll of both rerun attempts showed that the quality-check job also
completed with failure. Its step list remained empty, as did the expanded
platform build step list. Neither retry produced downloadable job logs. Both
reruns therefore ended in the same diagnostic state: job-level failure with
no command-level evidence.


## Application and dashboard QA — Prompt 34, 24 November 2026

A source-level review of the Streamlit upload and corrective-action workflows
identified two persistence-boundary defects.

First, uploaded corrective-action record IDs were based on the source filename
and row dimensions, but not the uploaded file contents. Replacing a CSV with
different content under the same filename could therefore reuse prior action
assignments. Uploaded files now contribute a SHA-256 content fingerprint to
their action IDs. The bundled demonstration dataset retains its legacy ID
scheme, avoiding an unnecessary change to existing bundled-demo action keys.
Tests cover repeat uploads, changed file content and legacy-key compatibility.

Second, when SQLite was unavailable, the session fallback replaced the entire
session action dictionary with only the currently filtered editor rows. This
could discard actions outside the active filters. It also stored only editable
fields, so the fallback portfolio/export could omit facility, month, programme,
indicator and issue context. The fallback now merges by Record_ID, preserves
records outside the active filter, and stores the complete edited row. Tests
cover preservation and field completeness.

The application review also reconfirmed that action persistence on the hosted
Streamlit Community Cloud filesystem is not a shared durable multi-user
database; this limitation remains explicitly disclosed. The review was source
inspection only: no browser interaction, hosted-app smoke test, database
migration test against a live deployment, or full pytest run was completed.
The changes are committed to the existing workforce branch and PR #26. CI
results must be checked separately and are not inferred from these source
changes.


### Prompt 34 CI observation

The commit containing the Prompt 34 regression tests triggered Project quality
checks run #331 (45351107904) and Expanded platform build run #304
(45351107816). Both are reported as job-level failures. The job records expose
no steps and no logs; direct log retrieval returned BlobNotFound. It is
therefore unknown whether Python compilation, pytest, dependency installation
or the full platform build began. The new action-ID and session-fallback tests
remain unverified and must not be described as passing.


## Dashboard filter, source-scope and portfolio QA — Prompt 35, 24 November 2026

A deeper review of the corrective-action portfolio found a source-isolation
defect introduced by storing content-version-scoped action IDs but loading
every SQLite action into the current dashboard. A portfolio displayed while
assessing one upload could therefore include records from an unrelated upload
or the bundled synthetic dataset. The same issue could affect the session-only
fallback.

The dashboard now calculates the full set of follow-up record IDs for the
current source version before applying interactive facility, programme and
date filters. It loads and displays only saved actions belonging to that
source version. This preserves the intended distinction: sidebar filters
control the editor's current rows, while the portfolio covers all saved
actions for the current source version. Other source versions remain in the
local database and are not silently deleted.

The SQLite retrieval method now chunks large ID filters into batches of 500,
avoiding dependence on unusually high SQLite bind-variable limits. Added a
regression test with more than 1,000 records to verify chunked retrieval and
exclusion of an ID outside the requested source scope.

The remaining UI review confirms that the no-match filter state currently
shows an explanatory warning and stops rendering the remaining tabs. This is
safe from incorrect calculations but is less useful than an in-dashboard
empty state with a clear filter-reset path; it remains a usability improvement
for a subsequent prompt. Large Plotly views and full-row CSV downloads have
not been benchmarked in a live browser at the 288,000-row scale.

This prompt was source-level QA and regression-test authoring only. The tests
have not been executed in a local environment. GitHub Actions job records for
recent commits have repeatedly failed at job level with no step records or
downloadable logs, so no test or build success is claimed. No merge or
deployment was performed.


### Prompt 35 empty-filter state refinement

The previous no-match branch called `st.stop()`, hiding every dashboard tab
when the selected facility/programme/date/status filters returned zero rows.
It now shows a clear warning but allows the remaining tabs to render. This
keeps the saved action portfolio and expanded platform views accessible even
when the current analytical slice is empty. The charts and metrics in the
current slice are expected to show empty/N/A values rather than fabricate
observations. This interaction has not yet been browser-tested.


### Prompt 35 CI status

The source commit for the large-ID lookup regression test triggered Expanded
platform build run #309 (45351381317) and Project quality checks run #336
(45351381395). Both were reported as job-level failures with no step records
or downloadable logs. The later no-match UX commit triggered runs #311
(45351462253) and #338 (45351462241), also reported as completed failures.
No command-level failure can be identified from these records. The 1,105-row
lookup test, application tests and full platform build remain unverified.



## Management export integrity and spreadsheet-safety audit — Prompt 36, 24 November 2026

A focused review of the complete management ZIP builder identified several
archive-boundary risks. The reserved `management_summary.csv` name was checked
case-sensitively, allowing an uppercase variant to bypass the reservation, and
case-insensitive duplicate filenames could extract ambiguously on common
desktop filesystems. The archive builder now validates every table name and
DataFrame before writing any ZIP entry, reserves the summary names without
case sensitivity, and rejects case-insensitive duplicates.

Management CSVs can contain free-text notes and other user-entered strings.
Those strings are now checked for spreadsheet formula prefixes (=, +, - and @),
including prefixes preceded by whitespace/control characters, and are escaped
with a leading apostrophe. Numeric DataFrame columns remain numeric and are not
modified, including legitimate negative values. This is an export safeguard;
it does not modify the in-memory dashboard data.

The summary is serialized as strict JSON with non-finite numeric values
rejected. ZIP entries use fixed timestamps and stable summary-key ordering so
identical inputs produce byte-for-byte identical archives. Regression tests
were added for reserved-name collisions, case-insensitive duplicates,
formula-like text, numeric preservation, non-finite summary values and
deterministic archive bytes, alongside the existing contents and path
validation tests.

These are source changes and authored tests only. The repository's Actions
runner/log problem still prevents confirmation that the tests execute
successfully; no test pass, full platform build, browser download, merge or
deployment is claimed. PR #26 remains the active unmerged change set.
