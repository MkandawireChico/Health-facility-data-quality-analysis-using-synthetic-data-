# Equipment Asset, Maintenance and Uptime Methodology

## Purpose

The equipment module demonstrates how a synthetic health-facility equipment register can be linked to monthly asset performance, preventive maintenance schedules, corrective work orders, downtime and review-priority scores.

## Asset catalogue and inventory

The simulation assigns four common equipment categories to each facility and adds further diagnostic/clinical-support assets to facilities labelled as hospitals. The catalogue contains seven illustrative equipment types:
- Vaccine refrigerator
- Standby generator
- Solar power system
- Autoclave
- Oxygen concentrator
- Ultrasound scanner
- Laboratory microscope

The inventory includes synthetic asset IDs, installation dates, expected service lives, criticality labels and abstract replacement-cost credits. The equipment mix is a modelling convenience, not an assessment of what any real facility owns or requires.

## Monthly asset performance

Each asset receives one monthly performance record:
- calendar hours;
- breakdown event count and unplanned downtime;
- scheduled preventive maintenance and planned maintenance downtime;
- service availability and operational uptime;
- preventive-maintenance due/completed/overdue status;
- condition score, maintenance credits and risk score.

Definitions:
- **Service availability** = 100 × (calendar hours − unplanned breakdown downtime) / calendar hours.
- **Operational uptime** = 100 × (calendar hours − unplanned breakdown downtime − planned maintenance downtime) / calendar hours.

The first metric excludes planned maintenance time; the second subtracts it. Neither is a verified clinical service availability measure.

## Preventive and corrective work orders

Preventive work orders are created when the illustrative maintenance interval is reached. Completion is simulated probabilistically. Corrective work orders are created for simulated breakdown events. The work-order cost credits reconcile to monthly maintenance cost credits at asset-month grain.

Work-order statuses and due dates are generated examples. They do not indicate real technician assignments, service-level agreements, vendor commitments or actual maintenance backlog.

## Risk score

The 0–100 equipment review score combines:
- 40% unplanned downtime intensity;
- 35% overdue preventive maintenance signal;
- 25% asset age relative to its assumed service life.

The score is modestly adjusted by the illustrative criticality label. Low/Medium/High are prioritisation bands for this demonstration, not engineering safety classifications. A high score is a prompt to inspect source records and asset condition, not proof that equipment is unsafe or unavailable.

## Outputs

- `equipment_catalog.csv`
- `facility_equipment_asset_register.csv`
- `equipment_asset_monthly_performance.csv`
- `facility_equipment_monthly_summary.csv`
- `equipment_maintenance_work_orders.csv`
- `equipment_latest_asset_risk_status.csv`
- `equipment_maintenance_report.json`

Run with `python src/equipment_maintenance.py --periods 60 --seed 42`, or include it in `python src/build_platform.py`.

## Governance and limitations

All asset records, acquisition dates, failure events, work orders, downtime, condition scores and costs are synthetic. Failure probabilities, asset lives, maintenance intervals, criticality weights and abstract credits are assumptions, not official Malawi Ministry of Health standards, engineering specifications, manufacturer instructions or procurement quotations. No physical inspections, sensor telemetry, service logs, spare-parts records, qualified technician assessments or verified inventory are represented. This module is a portfolio prototype, not an operational asset-management system.
