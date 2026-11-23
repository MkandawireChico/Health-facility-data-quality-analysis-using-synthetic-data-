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
