# Playbook: Low Chilled Water Delta-T

| | |
|---|---|
| **Applies to** | CHW-FC-053, related to CHW-FC-050 |
| **Fix complexity** | Remote + on-site |
| **Typical time** | 2–8 h (investigation across multiple air handler coils) |
| **Typical cost** | $0–$2,000 (depends on root cause) |
| **Energy impact** | Low delta-T is one of the most common and costly chilled water plant problems. It forces additional pumps and chillers to run to meet load, increasing pump energy by 30–100% and reducing plant COP. PNNL-27338 detects low delta-T for both CHW and HW systems when the supply-return differential falls below threshold at moderate loads. |

Adapted from HVAC FDD Reference v1.0, Remediation Playbooks (pp. 163–164).

## Step 1 — Verify the fault

1. Calculate the plant delta-T: chilled water return temperature minus supply
   temperature.
2. Compare to the design delta-T (typically 10–14 °F / 5.5–7.8 °C).
3. If delta-T is less than 50% of design when the plant is above 30% load,
   low delta-T is confirmed — one of the most common and costly chilled water
   plant problems.
4. Check whether the low delta-T is plant-wide or concentrated at specific
   AHUs. Trending return water temperature at each AHU isolates the worst
   offenders.

## Step 2 — Remote fix

1. Check for three-way valve bypass: where three-way valves exist on air
   handler coils, water can bypass the coil without picking up heat.
   Converting to two-way valves is a capital project but high-value.
2. Check air handler chilled water valve control — valves should modulate
   smoothly between 0% and 100%. If valves are stuck partially open on
   multiple air handlers, that explains the low delta-T.
3. Check chiller staging: too many chillers running at light load dilutes the
   plant delta-T. Adjust staging thresholds so fewer chillers handle the load
   at higher efficiency.
4. Check CHW differential pressure reset (EEM-10): if DP is set too high,
   valves throttle excessively and water bypasses through the coils too
   quickly to transfer full heat. Resetting DP based on the most-open valve
   position saves 0.5–2% site energy.

## Step 3 — On-site service

1. Inspect air handler coils for fouling — dirty coils reduce heat transfer,
   which directly lowers the temperature differential. Clean coils at
   $200–$500 per coil.
2. Check chilled water valve sizing — oversized valves tend to hunt and never
   fully load the coils. The worst offenders may need valve replacement.
3. Check for air trapped in the chilled water piping — air locks reduce water
   flow through coils. Bleed air at high points in the piping system.

## Step 4 — Confirm resolution

1. Monitor plant delta-T over 2 weeks.
2. Target: delta-T at or above 75% of design when the plant is above 50%
   load.
3. The fault should clear and pump energy should decrease as fewer pumps are
   needed to move the same cooling capacity.
