# Playbook: VAV Minimum Flow / Reheat Waste

| | |
|---|---|
| **Applies to** | VAV-FC-050, VAV-FC-052, VAV-FC-055, CLU-05 |
| **Fix complexity** | Remote fix |
| **Typical time** | 15 min per box (can be done in batch on most BAS platforms) |
| **Typical cost** | $0 |
| **Energy impact** | EEM-15: 5–16% site energy, 7.7% national — the single highest-impact individual measure across all building types in the PNNL study. Medium and large offices see the greatest benefit. For a 50,000 ft² office at $2/ft² energy cost, correcting VAV minimums can save $5,000–$16,000/yr. |

Adapted from HVAC FDD Reference v1.0, Remediation Playbooks (pp. 160–161).

## Step 1 — Verify the fault

1. For each flagged VAV box, compare the programmed minimum airflow setpoint
   against the actual ventilation requirement for that zone (zone area and
   occupancy), and against actual airflow during low-demand periods. ASHRAE
   62.1 minimum for a typical office: floor area × 0.06 cfm/ft² + occupants ×
   5 cfm/person. Many boxes are set 2–5× higher than this requirement.
2. If the minimum airflow setpoint is significantly higher than the
   ventilation requirement, it is set too high.
3. Check whether the zone is in deadband (satisfied) or heating mode — is the
   reheat valve active?
4. Count how many boxes are flagged:
   - More than 50% of boxes flagged → likely an air-handler-level issue
     (supply air temperature set too low, forcing excess reheat). See the
     [missing-reset](missing-reset.md) playbook. PNNL-27338 AIRCx check: if
     more than 25% of zones have reheat valves open above 50%, the AHU SAT
     may be too low. *(Library note: PNNL-27338 §2.2.2–2.2.3's own
     form is a two-quantity test — zones-with-reheat-open fraction above 25%
     AND fleet-average valve command above 50%; the single-predicate gloss
     here is the reference's simplification. See AHU-FC-053's Deviations.)*
   - Only 1–3 boxes flagged → a zone-level configuration problem.

## Step 2 — Remote fix

1. Reduce the minimum airflow setpoint to match the actual ventilation
   requirement (calculate the zone's required outdoor air per ASHRAE 62.1).
   For dual-maximum VAV boxes, also review the heating maximum flow — it may
   be higher than necessary. G36 recommends a minimum of 20% of design
   airflow or the ventilation minimum, whichever is greater.
2. If the reheat valve is open while the zone is already satisfied
   (VAV-FC-052): command the valve to 0% and watch the zone temperature
   response. If the temperature continues to rise, the valve is physically
   stuck — see the [stuck-actuator](stuck-actuator.md) playbook.
3. Enable a summer reheat lockout if not already active: when outdoor air is
   above 21 °C (70 °F) and the zone is satisfied, disable the reheat valve
   entirely. SYS-FC-056 specifically detects zone reheat active during warm
   weather (~20% of buildings).
4. For buildings with many flagged boxes, consider a dual-maximum control
   strategy — separate heating-maximum and cooling-maximum airflow setpoints
   allow very low airflow during heating while keeping design airflow for
   cooling.

## Step 3 — On-site service

Only if the reheat valve is physically stuck: see the
[stuck-actuator](stuck-actuator.md) playbook for valve inspection and
replacement procedures.

## Step 4 — Confirm resolution

1. After reducing minimums, verify zone airflow during satisfied/deadband
   periods sits close to the ventilation requirement, and reheat energy has
   dropped (valve mostly closed when the zone is comfortable).
2. Faults should clear within 24 hours.
3. If more than 50% of boxes were affected, the air-handler-level fault (SAT
   setpoint too low) should also improve or resolve.
4. At 5–16% of site energy, this fix alone often pays for the entire FDD
   deployment within the first year.
