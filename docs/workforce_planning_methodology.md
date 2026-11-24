# Workforce capacity and staffing scenario methodology

## Scope and grain

The module generates:
- One facility-role establishment row for each of eight illustrative workforce categories.
- One facility-month capacity row containing filled positions, vacancies, absence, on-duty positions, overtime and workload/capacity proxies.
- A latest-month facility review snapshot.
- A role-level recruitment scenario under an abstract credit ceiling.

## Definitions

- **Illustrative establishment:** simulated position requirement by facility type and catchment-size multiplier.
- **Filled positions:** simulated number of filled posts in the facility-role establishment.
- **Available on duty:** filled positions less simulated absences for the month.
- **Workforce coverage:** filled positions divided by illustrative establishment.
- **Absence rate:** absent positions divided by filled positions.
- **Workforce pressure index:** a catchment-based workload proxy relative to weighted on-duty capacity, capped at 200.
- **Capacity proxy per 1,000 catchment:** weighted on-duty capacity divided by the synthetic catchment-based demand proxy.

The role categories are clinical officer, nurse, midwife, medical assistant, laboratory technician, pharmacy technician, health surveillance assistant and data clerk. Role weights are relative analytical multipliers only.

## Recruitment scenario

Vacancy totals are aggregated by role. The engine allocates the configurable abstract recruitment credit budget to roles in descending order of vacancy count, using a fixed illustrative cost per position. This is a transparent heuristic, not an optimisation model, approved establishment, salary budget, recruitment plan or procurement estimate. Credits are not MWK.

## Governance and limitations

All establishments, filled positions, absences, overtime, role weights and costs are synthetic. Catchment population is a demand proxy only; it is not observed patient volume, visits, workload, population coverage or service utilisation. Role mixes and risk bands are not official Malawi staffing norms, WHO recommendations or safe-staffing thresholds. Coverage and pressure metrics do not establish safe staffing, service quality, clinical outcomes or actual HR availability. No personal, employee or patient records are generated.

The module is for portfolio demonstration and should not be used for real staffing decisions, HR management, recruitment approvals, payroll, or clinical safety decisions without validated local data, standards and governance.
