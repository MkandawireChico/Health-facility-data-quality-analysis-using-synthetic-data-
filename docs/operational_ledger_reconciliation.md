# Operational ledger reconciliation

The one-command platform build now runs cross-domain reconciliation checks
after the synthetic planning outputs are generated and before it writes the
final successful build summary and artifact manifest.

## Reconciliation controls

| Domain | Checks |
|---|---|
| Resource allocation | Requirement minus available units equals the baseline gap; each strategy covers the same facility set; allocations stay within facility gaps and the scenario pool; residual gaps and post-allocation coverage recalculate correctly |
| Commodity stock | Opening stock plus receipts equals fulfilled consumption plus closing stock; demand equals fulfilled plus unmet; stockout flags agree with stockout days; opening balances carry forward from prior closing balances |
| Cold-chain batches | Batch opening plus receipts equals consumption plus expiry plus closing stock; lot opening balances carry forward; facility–commodity–month expiry, near-expiry unit quantities, closing-stock and consumption totals reconcile to the risk summary (batch flags are never compared to unit counts) |
| Equipment maintenance | Total downtime reconciles to planned plus unplanned downtime; service availability and operational uptime recalculate from hours; maintenance cost and downtime reconcile to work orders |
| Infrastructure | Power and water interruption hours reconcile to backup/buffered and unserved hours; availability percentages recalculate from unserved hours; resilience score recalculates from availability and the facility backup-power assumption |
| Workforce | Filled, vacant, absent and on-duty positions reconcile; coverage, absence and workload-pressure measures recalculate from their source counts/proxies |

A facility–commodity–month with no cold-chain stock can legitimately have no
batch rows. The validator treats absent batch aggregates as zero only when the
risk summary also reports zero batch-backed quantities; non-zero quantities
without batch movements and orphan batch rows are rejected.

## Build behaviour

A failed reconciliation raises an error and prevents the build from being
reported as successful. The build summary includes row/facility/scenario
counts for each validated domain under
`operational_ledger_reconciliation`.

## Interpretation and limitations

All inputs and outputs remain synthetic. These checks establish internal
accounting consistency of the generated scenario—not real inventory accuracy,
staffing adequacy, engineering condition, clinical safety, procurement
feasibility or actual facility performance. Resource and procurement credits
are abstract units, not MWK. Successful execution of the complete test suite
and default 288,000-row build still requires functioning CI; adding these
checks does not itself prove that CI ran or passed.
