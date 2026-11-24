# Executive facility management briefing

## Purpose

The executive management briefing turns the integrated facility priority register and saved corrective-action records into a concise, cross-facility review pack. It is designed to support a portfolio demonstration: compare synthetic facility priority bands, identify which domains most frequently carry non-zero scores, compare district-labelled groups, and surface a ranked list for management review.

## Inputs and reconciliation

The briefing consumes the current integrated facility priority register and the existing integrated corrective-action portfolio. It does not create or maintain a second action database.

- Facility identifiers must be populated and unique in the priority register.
- Priority bands must be one of High review, Focused review or Routine review.
- Integrated and component scores must be numeric and within 0–100.
- The integrated score must reconcile to the rounded arithmetic mean of its four component scores.
- Each action's canonical facility ID is extracted from its facility label and must exist in the priority register.
- Action record IDs must be populated and unique; statuses must be Open, In progress, Resolved or Escalated.
- Overdue means an unresolved action with a valid due date earlier than the briefing reference date. Missing due dates are not treated as overdue.

## Executive outputs

The briefing reports:
- Facility count, priority-band counts, mean integrated score, saved action count, overdue action count and action resolution rate.
- District-labelled comparisons of facility priority bands, mean priority score and action workload/status.
- Domain concentration: count of facilities with a non-zero score in data quality, resource capacity, operational resilience and supply/cold chain.
- A ranked management queue with facility priority, action status counts, overdue actions and rule-based follow-up text.
- A CSV export of the full facility management queue.

The default queue is sorted by descending integrated priority score, then overdue action count, then the existing deterministic priority rank. The dashboard displays a shorter top section while the download contains all facilities.

## Follow-up text

The follow-up text is generated from explicit rules, not a predictive model. High-review facilities are flagged for a facility review; focused-review facilities for a targeted domain review; routine facilities for monitoring. The text also notes overdue unresolved actions, remaining open/in-progress actions, or the absence of a saved action assignment. These are prompts to inspect the synthetic register, not automatic operational instructions.

## Interpretation and limitations

All facility, district, resource, service, supply, workforce and corrective-action information is synthetic. District labels are geographic grouping context and do not represent actual district performance. Priority inputs retain the mixed time scopes described in the [integrated priority methodology](integrated_facility_priority_methodology.md): quality spans the current synthetic build, operational and supply/cold-chain indicators are latest-month snapshots, and resource capacity is a baseline scenario.

A non-zero domain score means that the synthetic screening component has a value above zero; it does not establish a real-world incident or service failure. The integrated score uses equal weights and is not calibrated against outcomes. Action resolution is based on the saved status field and is not independently verified. The briefing must not be presented as a Ministry of Health performance report, clinical risk score, staffing instruction, procurement order or live operational dashboard.

The action store remains the existing local SQLite demonstration store. Its persistence and multi-user limitations continue to apply. A hosted Streamlit deployment must not be assumed to include these unmerged branch changes.
