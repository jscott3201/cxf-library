# Playbook: Heat Pump Faults

| | |
|---|---|
| **Applies to** | HP-0001 (COP degradation), HP-0002 (defrost anomaly), HP-0003 (reversing valve), HP-0004 (undercharge), HP-0005 (overcharge), HP-0006 (valve internal leakage) |
| **Fix complexity** | On-site service required |
| **Typical time** | 2–6 h on-site |
| **Typical cost** | $200–$1,500 (refrigerant/defrost) / $500–$3,000 (reversing valve) / $3,000–$8,000 (compressor) |
| **Energy impact** | HP-0001: 5–25% compressor energy waste from COP degradation. HP-0002: 3–10% heating energy from excessive defrost. HP-0003: 20–50% of mode energy when running in the wrong mode — this is a critical fault. Barandier (2023) found refrigerant undercharge is the most frequent heat pump fault. |

Adapted from HVAC FDD Reference v1.0, Remediation Playbooks (pp. 169–170).

## Step 1 — Verify the fault

1. **COP degradation (HP-0001):** calculate measured COP as thermal output
   divided by electrical input and compare it to the baseline regression model
   (COP vs. OAT). A 15% or greater drop below the baseline curve indicates
   degradation. Evaluate heating and cooling modes separately — degradation may
   appear in only one mode. Ensure the baseline R² > 0.6 before trusting the
   comparison.
2. **Defrost anomaly (HP-0002):** count defrost cycles per hour — more than
   4/hr is excessive. Check individual defrost duration — more than 15 minutes
   per cycle is abnormal. Check for defrost initiating when OAT is above 7 °C
   (45 °F); defrost should not be needed at mild temperatures.
3. **Reversing valve (HP-0003):** after a mode change command, wait 10
   minutes for the system to settle. In cooling mode, SAT should be well below
   RAT — if SAT > RAT, the valve has not switched. In heating mode, SAT should
   be well above RAT — if SAT < RAT, the valve has not switched. This is a
   Severity 2 (high) fault: the unit is actively working against its intended
   purpose.

## Step 2 — On-site service

1. **COP degradation:**
   1. Check refrigerant charge — undercharge is the most common fault per
      Barandier (2023). Measure subcooling and superheat.
   2. Check for refrigerant overcharge — also degrades COP, but less common.
   3. Inspect the condenser and evaporator coils for fouling (see the
      [rtu-compressor-refrigerant](rtu-compressor-refrigerant.md) playbook).
   4. Check compressor amp draw against nameplate — elevated amps suggest
      mechanical degradation.
   5. Check for non-condensable gases in the refrigerant circuit.
2. **Defrost anomaly:**
   1. Inspect the outdoor coil for heavy ice or frost buildup.
   2. Check the defrost temperature sensor — a failed sensor can trigger
      continuous defrost.
   3. Check the defrost control board for fault codes.
   4. If the unit uses time-temperature defrost, verify the timer settings
      match the manufacturer's recommendation.
3. **Reversing valve:**
   1. Check the reversing valve solenoid — listen for a click when the mode
      changes. No click indicates a failed solenoid ($100–$300 to replace).
   2. Check the wiring between the thermostat/controller and the reversing
      valve solenoid.
   3. If the solenoid energizes but the valve doesn't shift, the valve body is
      stuck. Low refrigerant charge can prevent the valve from shifting — check
      charge first.
   4. If the valve body has failed, replace the reversing valve ($500–$2,000
      plus refrigerant recovery).

## Step 3 — Confirm resolution

1. **COP:** monitor measured COP for 7 days — it should return to within 10%
   of the baseline curve.
2. **Defrost:** monitor defrost frequency and duration for 48 hours. Target:
   fewer than 4 cycles/hr, less than 10 minutes each.
3. **Reversing valve:** command multiple mode switches and verify SAT responds
   correctly each time.
