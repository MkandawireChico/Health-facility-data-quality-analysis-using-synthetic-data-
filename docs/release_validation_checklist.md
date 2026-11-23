# Release validation checklist

This checklist is the release gate for the expanded synthetic health-facility
intelligence platform. A mergeable pull request is not a validated release.

## 1. Automated checks

- [ ] GitHub Actions runner allocation is available and the repository billing
      limit has reset.
- [ ] Project quality checks complete successfully on the final head of each
      pull request in dependency order.
- [ ] Python compilation succeeds for `src/` and `dashboard/`.
- [ ] Notebook JSON parses and every code cell passes AST syntax validation.
- [ ] Full `pytest -q` suite passes.
- [ ] Full default platform build succeeds (120 facilities, 60 periods,
      288,000 synthetic fact records).
- [ ] Platform output manifest lists only existing generated artifacts.
- [ ] Generated validation artifact is inspected for expected files and
      summary metrics.

## 2. Merge sequence

Merge only after the relevant PR's required checks pass, and verify the next
child PR's base/head relationship after each merge:

1. PR #20 — district intelligence and corrective actions
2. PR #21 — resource allocation
3. PR #22 — commodity supply chain
4. PR #23 — cold-chain and batch expiry
5. PR #24 — equipment maintenance and uptime
6. PR #25 — infrastructure and utilities
7. PR #26 — workforce capacity

Do not merge a child before its parent. Do not bypass failed or missing checks.

## 3. Manual application verification

- [ ] Install dependencies from `requirements.txt` in a clean Python 3.11
      environment.
- [ ] Run `python src/build_platform.py` from the repository root.
- [ ] Run `streamlit run dashboard/streamlit_app.py`.
- [ ] Verify the deployed Streamlit app separately; feature-branch code is not
      assumed to be present in the current public deployment.
- [ ] Exercise filters, uploads, downloads, corrective-action persistence,
      and each planning section.
- [ ] Confirm SQLite persistence limitations on Streamlit Community Cloud are
      disclosed.
- [ ] Rebuild and refresh the expanded Power BI semantic model in Power BI
      Desktop; validate Power Query refresh, relationships, DAX measures,
      report navigation and exported visuals.

## 4. Data governance and release documentation

- [ ] State clearly that facilities, IDs, populations, observations,
      operational events, staffing and costs are synthetic.
- [ ] Do not describe abstract credits as Malawi Kwacha or as approved budgets.
- [ ] Do not describe synthetic readiness, uptime, staffing or target-attainment
      proxies as official standards or verified clinical service availability.
- [ ] Confirm no patient-level or employee-level personal data is included.
- [ ] Update README with the final validated build, deployment and report
      status. Distinguish tested, merged, deployed and manually verified work.

## 5. Release decision

The project is ready to leave feature development only when automated checks
pass and all material manual limitations are documented. If Actions billing
or runner allocation remains blocked, keep the PR stack open and report the
release as unvalidated rather than bypassing CI.
