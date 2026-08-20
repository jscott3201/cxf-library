# Playbook: VFD and Pump Faults

| | |
|---|---|
| **Applies to** | VFD-0001 through VFD-0005 (VFD-0002..0005 are library additions to the reference's line), PMP-0001, PMP-0002, AHU-0039, PMP-0003 |
| **Fix complexity** | On-site service required |
| **Typical time** | 2–4 h |
| **Typical cost** | $200–$2,000 |
| **Energy impact** | Pump energy follows the cube law: reducing pump speed by 20% reduces pump power by 49%. A pump deadheading (running against closed valves) wastes 100% of its energy as heat and risks mechanical damage. Differential pressure reset (EEM-10/11) saves 0.5–2% of site energy by allowing pumps to run slower. |

Adapted from HVAC FDD Reference v1.0, Remediation Playbooks (pp. 167–168).

The pump rules named above are verified in this library:
[PMP-0001](../faults/pmp/PMP-0001/card.md) and
[PMP-0002](../faults/pmp/PMP-0002/card.md) (family index:
[faults/pmp](../faults/pmp/README.md)).

## Decision tree

Follow control authority before component replacement:

1. Confirm remote/auto/bypass state.
2. Compare speed command and feedback.
3. Determine whether the loop is pinned at minimum or maximum and read the
   process-error direction.
4. Check current, torque, safety, demand, and application limits plus mechanical
   restrictions.
5. Review tuning, process-sensor quality, and setpoint-reset behavior.
6. Inspect current/kW trends only after control-state findings are resolved.

Do not manually energize, transfer, or bypass a drive outside the site's
approved operating and electrical-safety procedure.

## Step 1 — Confirm control authority (VFD-0005)

1. Verify the final drive enable is actually commanded, not merely an upstream
   system request.
2. Read the HOA/keypad selector and configured command source. "Auto" must mean
   the commissioned remote BAS source, not local PID auto or terminal control.
3. Confirm bypass from authoritative drive mode or contactor/power-path proof.
   Bypass available, ready, or commanded is not active bypass.
4. Check whether maintenance, emergency, fire/smoke, commissioning, or a
   functional test explains the state. If approved, suppress the diagnostic
   rather than defeating the safety sequence.
5. Restore authority only through approved procedures, then allow the loop and
   setpoint to settle before evaluating downstream faults.

## Step 2 — Compare speed command and feedback (VFD-0001)

1. Verify command and feedback are both normalized to percent of rated speed;
   do not compare percent with Hz.
2. Check command-source configuration and fieldbus communication.
3. Check the drive display for current, torque, thermal derating, and fault
   codes such as overcurrent, overvoltage, or ground fault.
4. Check the cooling fan and heatsink — overheating can cause quiet derating
   before the drive trips.
5. Compare drive-reported speed with a tachometer only after confirming what
   each point measures.

## Step 3 — Inspect loop saturation (VFD-0002, VFD-0003)

1. Confirm process value and setpoint are from the same loop, share units, and
   use a commissioned site-specific error threshold.
2. At minimum speed, use the error direction to distinguish overdelivery/a
   minimum set too high from underdelivery, obstruction, or bad sensing.
3. At maximum speed, verify the configured maximum and inspect current, torque,
   safety, demand, and application limits before calling the equipment
   undersized.
4. Inspect filters, coils, strainers, dampers, valves, belts, couplings,
   impellers, and the distribution path for restrictions or degradation.
5. Confirm the setpoint was settled long enough for the application's time
   constant; a real reset/load step is not a capacity fault.

## Step 4 — Inspect hunting (VFD-0004)

1. Trend speed, process value, and setpoint together at 60 seconds or faster;
   change-of-value logs can hide crossings.
2. If only speed hunts, inspect command, feedback, drive limits, and mechanical
   backlash. If only the process hunts, inspect its sensor and external load.
3. If both hunt, compare phase before retuning: process movement leading speed
   suggests a real disturbance or sensor problem; speed leading process suggests
   aggressive tuning or actuator/drive behavior.
4. Exclude startup, staging, setpoint reset, smoke/purge, and manual tuning tests.
5. Change one tuning parameter at a time and preserve protective/current/torque
   limits. Observe for at least two evaluation windows after each change.

## Step 5 — Electrical and drive service

1. Check VFD input and output power and calculate drive efficiency only after
   mode, scaling, and control-state findings are resolved.
2. Check harmonic distortion where symptoms or site requirements justify it.
3. Follow the manufacturer's diagnostics for the exact drive and motor.
4. If the VFD is failing, replacement is typically $500–$2,000 depending on
   motor horsepower; confirm the diagnosis before replacement.

## Step 6 — Pump on with no flow / deadheading (PMP-0001, PMP-0002)

1. **Remote fix:** check the differential pressure setpoint — it may be set too
   high, forcing the pump to work against closed valves.
2. **Remote fix:** implement a differential pressure reset sequence if one
   doesn't exist — the same trim-and-respond logic as air-handler duct static
   pressure reset (see the [missing-reset](missing-reset.md) playbook).
   EEM-10: 0.5–2% site energy savings.
3. **On-site:** check for closed isolation valves downstream of the pump.
4. **On-site:** check the strainer for blockage.
5. **On-site:** verify the pump impeller condition — damaged impellers produce
   no flow despite the motor running.
6. For variable-primary CHW systems, verify the minimum-flow bypass valve is
   functioning. Without it, the lead pump may deadhead when all AHU valves
   close.

## Step 7 — Confirm resolution

1. Verify the drive remains in the commissioned remote-auto state with bypass
   inactive whenever normal operation is expected.
2. Verify output tracks command within the commissioned tolerance.
3. Verify the process returns within its allowance band without sustained
   minimum/maximum saturation or material hunting.
4. For pumps, verify flow is present and differential pressure is in range.
5. Confirm suppressions release on the same drive instance and observe for at
   least two hunting windows before closing an instability finding.
