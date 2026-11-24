# Integrated facility priority register methodology

## Purpose

The integrated facility priority register creates one synthetic, auditable review queue from four existing analytical domains:

1. Data quality: the facility-level detected-issue rate across all reporting periods in the current synthetic build.
2. Resource capacity: the baseline gap between illustrative requirement units and synthetic available units.
3. Operational resilience: the latest-month review flag across equipment uptime, infrastructure reliability and workforce coverage.
4. Supply and cold-chain continuity: the latest-month review flag across commodity stockouts, high cold-chain risk, temperature excursions, near-expiry stock and explicit temperature-monitoring data gaps.

The register is intended to help users inspect several modelled domains together. It is not a clinical risk model, a safe-staffing assessment, an official facility score, a procurement recommendation or a verified operational performance ranking.

## Facility identity and reconciliation

All four inputs must contain exactly the canonical facility population from the facility dimension. Facility IDs must be unique and populated, and facility names and district labels must agree across the source profiles. Duplicate or missing facility rows, invalid numeric measures and inconsistent population counts stop the build rather than silently producing a partial ranking.

The quality benchmark is a whole-period profile. Operational resilience and supply/cold-chain values are latest-simulated-month snapshots. Resource capacity is a static baseline scenario. The register labels this mixed time scope explicitly; the scores should not be interpreted as four synchronized time-series measurements.

## Score construction

Each component is represented on a 0–100 review-priority scale:

- **Data quality:** detected issue records divided by all facility reporting records, multiplied by 100.
- **Resource gap:** 100 minus baseline capacity coverage percentage, floored at zero and capped at 100. Capacity above the illustrative requirement is treated as surplus, not as a negative gap.
- **Operational resilience:** 100 when the latest-month operational review flag is raised, otherwise 0.
- **Supply/cold chain:** 100 when the latest-month supply review flag is raised, otherwise 0. A cold-chain data-gap state is included as a reason for review.

The integrated score is the unweighted arithmetic mean of the four component scores. Equal weights are a transparent demonstration choice, not an empirically calibrated weighting scheme.

Priority bands are illustrative:
- **High review:** score at least 50.
- **Focused review:** score at least 25 and below 50.
- **Routine review:** score below 25.

Facilities are sorted by descending score, then ascending facility ID for deterministic tie-breaking.

## Interpretation and limitations

All underlying facility, reporting, resource, workforce, commodity, cold-chain, equipment and infrastructure data are synthetic. Thresholds and assumptions are modelling choices. The review flags identify scenarios worth inspecting; they do not establish actual shortages, unsafe conditions, service interruption, data falsification or clinical harm.

A facility may rank highly because several synthetic review flags overlap. Users should inspect each component and the source assumptions before drawing conclusions. The dashboard and exported CSV retain the component scores, review domains, benchmark scope and interpretation note so the ranking is auditable.
