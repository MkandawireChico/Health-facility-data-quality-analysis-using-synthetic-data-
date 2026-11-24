# Integrated facility corrective-action workflow

## Purpose

The integrated facility priority register can be converted into a practical corrective-action queue. Each facility receives one action record for the latest simulated month represented by the workforce profile. The record carries the priority band, score, rank and review domains into an immutable issue description; users then assign an owner, document a root cause, write the corrective action and set a due date.

## Identity and repeatability

Action identifiers are generated from a stable source label, facility ID, reporting month and workflow type. They do not depend on table row order or current dashboard filters. Re-running the same synthetic period therefore reloads the same action record instead of creating duplicates. A new simulated month creates a new period-specific record.

The adapter validates facility identity, unique facilities, supported priority bands, unique positive ranks, score bounds and reporting month before creating rows. Existing owner, status, root-cause, notes and due-date values are carried forward when the queue is rebuilt.

## Workflow

The Streamlit form supports four statuses:
- **Open:** identified, not yet underway.
- **In progress:** an owner is implementing or coordinating the response.
- **Resolved:** the assigned response has been completed and recorded.
- **Escalated:** requires higher-level review or support.

Users can assign an owner, document the root cause, enter corrective-action notes and set a due date in YYYY-MM-DD format. Invalid due dates block the entire save. The action portfolio displays counts by status and identifies overdue unresolved actions. Each saved field change is written to the existing SQLite field-level audit history. The action register can be exported as CSV.

## Storage and governance limitations

The workflow reuses the existing local SQLite corrective-action database. This avoids a second, disconnected action store. The default location is data/warehouse/corrective_actions.sqlite; HEALTH_DATA_ACTION_DB can override it.

The SQLite database is suitable for a local demonstration or a single persistent deployment volume. Streamlit Community Cloud's ordinary filesystem is ephemeral, and a local SQLite file is not a shared multi-user database. Production use requires managed persistent storage, authentication, role-based access, concurrency controls, backups and an explicit retention policy. Export backups regularly.

## Interpretation

All facility priority inputs and simulated reporting periods are synthetic. The priority register is a transparent triage aid, not a verified facility assessment or a clinical, safety, staffing, procurement or resource-allocation recommendation. Assigning an action does not establish that a real-world problem exists or that the suggested response is approved.

## Performance monitoring

Saved integrated facility actions are summarised across the portfolio, by district and by reporting month. The dashboard reports total tracked actions, resolved actions, resolution rate, open/in-progress/escalated workload and overdue unresolved actions. District summaries include tracked workload, status counts, overdue count and resolution rate. Monthly trend charts show action throughput and the share of records marked Resolved.

Overdue is calculated by comparing a non-empty due date with the dashboard's current date; resolved actions are excluded. A blank or invalid due date is not counted as overdue. Reporting month is the synthetic month attached to the action record, not the date the action was edited.

These are workflow-process measures, not outcome verification. A record marked Resolved is counted as resolved even though the application does not independently validate that the underlying facility issue has been corrected. Historical summaries depend on the action records retained in the configured SQLite database.


## Facility management drill-down

The expanded platform includes a facility selector that joins the integrated priority register to saved corrective-action records using the canonical facility identifier embedded in each action label. The selected facility view displays its overall priority band and score, four component scores, review domains, action counts by status, resolution rate, overdue unresolved actions, and monthly action progress. It remains available when no action has yet been saved for the selected facility.

Where an action record exists, the view can display its owner, root cause, corrective-action notes, due date and overdue flag. The audit selector retrieves field-level changes from the same SQLite action store used by the corrective-action workflow. No second database or parallel action register is created.

The drill-down validates facility identifiers and action record identity before joining records. Facility IDs must be present and unique in the priority register; action labels must end in a bracketed canonical facility ID. Unknown selected IDs, malformed labels, duplicate action IDs and unsupported statuses are rejected rather than silently misattributed.

All displayed priority and action information remains synthetic. The view is a portfolio demonstration, not a live health facility management system. Persistence and multi-user limitations described above still apply.
