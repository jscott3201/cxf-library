# Playbook: Zone Heating in Warm Weather

| | |
|---|---|
| **Applies to** | SYS-FC-056, CLU-05 |
| **Fix complexity** | Remote fix (85%) · On-site (15%) |
| **Typical time** | 15–30 min remote |
| **Typical cost** | $0 remote / $200–$600 on-site (stuck valve) |
| **Energy impact** | Found in ~20% of buildings per PNNL 151-building study. 100% of reheat energy consumed during warm weather is pure waste — the building is paying to heat air that was just mechanically cooled. In perimeter zones with solar gain, this is especially wasteful. A single reheat coil running at 50% during summer can waste $500–$2,000/yr. |

Adapted from HVAC FDD Reference v1.0, Remediation Playbooks (pp. 172–173).

## Step 1 — Verify the fault

1. Confirm the reheat valve command is above 10% when outdoor air temperature
   is above 21°C (70°F).
2. Check whether this is a single zone or building-wide:
   - A single zone: likely a stuck valve or a zone-level control issue.
   - Multiple zones: likely a missing seasonal lockout or the AHU SAT is set
     too low (driving reheat across many zones).
3. Check the zone temperature: if the zone is already at or above setpoint
   and the reheat valve is open, the valve is operating wastefully.
4. In perimeter zones, check for solar gain overcooling the space — the
   reheat may be fighting solar-driven overcooling. If so, the root cause is
   lack of solar-responsive control rather than a hardware fault.

## Step 2 — Remote fix

1. Program an outdoor air temperature lockout for zone reheat:
   - When OAT > 21°C (70°F) and the zone is satisfied, disable the reheat
     valve.
   - Use hysteresis: re-enable at OAT < 18°C (65°F).
2. Check the zone's minimum airflow setpoint — if it's too high, excess cool
   air is being delivered and then reheated. Reducing the minimum (see the
   VAV Minimum Flow / Reheat Waste playbook) eliminates the root cause.
3. For building-wide issues, check the AHU SAT setpoint:
   - If SAT is locked at 55°F (13°C) year-round, raise it during mild weather
     via SAT reset (see the Missing Reset playbook).
   - A 2°F increase in SAT during part-load conditions can eliminate reheat
     in 30–50% of zones.
4. For perimeter zones with solar gain: consider a demand-based reheat enable
   that allows reheat only when zone temperature drops below the heating
   setpoint minus 1°F.

## Step 3 — On-site service (if the reheat valve is stuck open)

1. Command the reheat valve to 0% and physically verify it closes.
2. If the valve does not close, see the Stuck Actuator playbook for repair
   procedures.
3. For perimeter heating systems not controlled by the BAS (e.g., standalone
   baseboard heaters with local thermostats): lower the thermostat setpoint
   for summer or add a manual seasonal shutoff.

## Step 4 — Confirm resolution

1. Monitor reheat valve commands during warm weather for 7 days.
2. Reheat valves should remain at 0% when OAT is above the lockout threshold
   and zones are satisfied.
3. The fault should clear within 24 hours.
