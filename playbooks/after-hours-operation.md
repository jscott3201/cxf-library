# Playbook: After-Hours Operation

| | |
|---|---|
| **Applies to** | AHU-0018, AHU-0026, AHU-0027, SYS-0003, SYS-0004, CLU-04, CLU-08 |
| **Fix complexity** | Remote fix (95%) · On-site (5%) |
| **Typical time** | 15–30 min remote |
| **Typical cost** | $0 |
| **Energy impact** | EEM-04: 3–9% site energy. EEM-16 (deadbands/setbacks): 3–16% site energy, top measure nationally at 7.7%. PNNL-27338 AIRCx flags fans running during more than 30% of unoccupied hours, or duct static pressure above 0.2 in. w.g. during unoccupied periods. |

Adapted from HVAC FDD Reference v1.0, Remediation Playbooks (pp. 157–159).

## Step 1 — Verify the fault

1. Pull a 7-day trend of supply fan run status overlaid with the occupancy
   schedule; confirm the equipment runs during unoccupied periods.
2. Check for legitimate after-hours reasons: morning warmup / night cooldown
   (normal but should be time-limited to 1–2 hours) and tenant override
   requests (should be time-limited, never indefinite).
3. PNNL-27338 checks: unoccupied fan runtime > 30% of total unoccupied hours,
   or duct static pressure > 0.2 in. w.g. during unoccupied hours.
4. Check the BAS time zone setting — daylight saving mismatches are a common
   culprit.
5. Quantify the waste: unoccupied runtime hours × fan kW × (1 + thermal
   conditioning penalty). The thermal penalty is typically 1.5–3× the fan
   energy because the AHU is also conditioning outdoor air unnecessarily.

## Step 2 — Remote fix

1. Correct the occupancy schedule if it's wrong — the most common fix.
2. Remove stuck overrides: check the BACnet priority array on the fan command
   and release any manual override (a top retro-commissioning finding,
   PNNL-27338).
3. If morning warmup / evening cooldown runs too long: limit pre-conditioning
   to 1–2 hours maximum, ideally with an optimal start algorithm (PNNL
   EEM-27/28 starts the AHU just in time to reach setpoint by occupancy).
4. Set after-hours override time limits: each override event auto-expires
   after at most 2 hours; ensure an override can never run indefinitely.
5. Verify holiday schedules are current — missed holidays are a common source
   of after-hours waste.
6. Building-wide issues: fix the master schedule and verify all air handlers,
   exhaust fans, and lighting reference the same schedule.
7. Enable night setback temperatures: widen the unoccupied deadband to ~13 °C
   heating / ~29 °C cooling (55/85 °F, or site-appropriate values) — EEM-16
   alone saves 3–16% of site energy depending on building type.

## Step 3 — On-site service (rare)

1. If the fan runs despite a correct off command: check for a welded/stuck
   contactor or relay, a hardwired VFD run-signal bypass, or a hand-off-auto
   switch left in Hand.
2. If an occupancy sensor falsely detects occupancy: check location and
   sensitivity — PIR sensors trigger from HVAC air currents, rodents, or
   direct sunlight on the lens.

## Step 4 — Confirm resolution

1. Monitor fan status during 3 consecutive unoccupied periods.
2. All after-hours faults should clear within 24–48 hours.
3. Verify lighting (SYS-0003) and exhaust fans (SYS-0004) also shut down
   on the corrected schedule — these often share the same root cause.
