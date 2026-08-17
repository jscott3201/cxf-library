# Playbook: VFD and Pump Faults

| | |
|---|---|
| **Applies to** | VFD-FC-050, PMP-FC-050, PMP-FC-051 |
| **Fix complexity** | On-site service required |
| **Typical time** | 2–4 h |
| **Typical cost** | $200–$2,000 |
| **Energy impact** | Pump energy follows the cube law: reducing pump speed by 20% reduces pump power by 49%. A pump deadheading (running against closed valves) wastes 100% of its energy as heat and risks mechanical damage. Differential pressure reset (EEM-10/11) saves 0.5–2% of site energy by allowing pumps to run slower. |

Adapted from HVAC FDD Reference v1.0, Remediation Playbooks (pp. 167–168).

PMP-FC-050 and PMP-FC-051 are a future family here — this library has no
`PMP-FC-*` rules yet, so the pump IDs above are the reference's own.

## Step 1 — VFD command/feedback deviation (VFD-FC-050)

1. Check VFD input and output power — calculate drive efficiency.
2. Check harmonic distortion levels.
3. Check the cooling fan and heatsink — overheating causes the VFD to derate,
   reducing output.
4. Check for VFD fault codes on the drive display — common codes include
   overcurrent, overvoltage, and ground fault.
5. If the VFD is failing, replace it: $500–$2,000 depending on motor
   horsepower.

## Step 2 — Pump on with no flow / deadheading (PMP-FC-050, PMP-FC-051)

1. **Remote fix:** check the differential pressure setpoint — it may be set
   too high, forcing the pump to work against closed valves.
2. **Remote fix:** implement a differential pressure reset sequence if one
   doesn't exist — the same trim-and-respond logic as air handler duct static
   pressure reset (see the [missing-reset](missing-reset.md) playbook).
   EEM-10: 0.5–2% site energy savings.
3. **On-site:** check for closed isolation valves downstream of the pump.
4. **On-site:** check the strainer for blockage.
5. **On-site:** verify the pump impeller condition — damaged impellers produce
   no flow despite the motor running.
6. For variable-primary CHW systems: verify the minimum flow bypass valve is
   functioning. Without it, the lead pump may deadhead when all AHU valves
   close.

## Step 3 — Confirm resolution

1. After service, verify that the VFD output tracks the command signal within
   5%.
2. For pumps, verify flow is present and differential pressure is within the
   normal range.
3. Faults should clear immediately after the root cause is resolved.
