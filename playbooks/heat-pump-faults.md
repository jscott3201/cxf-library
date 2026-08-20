# Playbook: Heat Pump Faults

| | |
|---|---|
| **Applies to** | HP-0001 (COP degradation), HP-0002 (defrost anomaly), HP-0003 (reversing valve), HP-0004 (undercharge), HP-0005 (overcharge), HP-0006 (valve internal leakage), HP-0007 (compressor proof), HP-0008 (auxiliary heat above lockout) |
| **Fix complexity** | On-site service required |
| **Typical time** | 2–6 h on-site |
| **Typical cost** | $200–$1,500 (refrigerant/defrost) / $500–$3,000 (reversing valve) / $3,000–$8,000 (compressor) |
| **Energy impact** | HP-0001: 5–25% compressor energy waste from COP degradation. HP-0002: 3–10% heating energy from excessive defrost. HP-0003: 20–50% of mode energy when running in the wrong mode — this is a critical fault. Barandier (2023) found refrigerant undercharge is the most frequent heat pump fault. |

Adapted from HVAC FDD Reference v1.0, Remediation Playbooks (pp. 169–170).

## Step 1 — Verify the fault

1. **Compressor proof (HP-0007):** first compare the final command with
   independent run proof for the same compressor or explicitly documented
   compressor group. Review OEM lockouts, defrost state, anti-cycle logic, and
   safety status. If any of those states can withhold operation, they must be
   reflected in the final command or make the rule NO_EVAL; do not use an
   upstream thermostat demand or fleet request as the command.
2. **Auxiliary heat above lockout (HP-0008):** prove the point represents an
   explicitly classified auxiliary source actively producing space heat, not
   availability, demand, crankcase/base-pan heat, or defrost heat. Verify
   heating and defrost/emergency state, the installed lockout/balance point or
   dual-fuel switchover, compressor proof, and whether concurrent operation is
   actually prohibited by the OEM/site strategy.
3. **COP degradation (HP-0001):** calculate measured COP as thermal output
   divided by electrical input and compare it to the baseline regression model
   (COP vs. OAT). A 15% or greater drop below the baseline curve indicates
   degradation. Evaluate heating and cooling modes separately — degradation may
   appear in only one mode. Ensure the baseline R² > 0.6 before trusting the
   comparison.
4. **Defrost anomaly (HP-0002):** count defrost cycles per hour — more than
   4/hr is excessive. Check individual defrost duration — more than 15 minutes
   per cycle is abnormal. Check for defrost initiating when OAT is above 7 °C
   (45 °F); defrost should not be needed at mild temperatures.
5. **Reversing valve (HP-0003):** after a mode change command, wait 10
   minutes for the system to settle. In cooling mode, SAT should be well below
   RAT — if SAT > RAT, the valve has not switched. In heating mode, SAT should
   be well above RAT — if SAT < RAT, the valve has not switched. This is a
   Severity 2 (high) fault: the unit is actively working against its intended
   purpose.

## Step 2 — Remote triage

1. Confirm command and proof timestamps are fresh, aligned, and scoped to the
   same physical compressor. An aggregate OR can hide a failed lag compressor.
2. Review controller and VFD/OEM fault histories, local/remote state, defrost,
   pressure and temperature safeties, anti-cycle timing, and recent service.
3. Correct only verified BAS binding or sequence defects. Never bypass smoke,
   freeze, condensate, high/low-pressure, electrical, or OEM safeties, and do
   not repeatedly reset a compressor lockout.
4. For HP-0008, inspect thermostat/OEM staging, site OAT lockout, recovery and
   demand-response modes, and OAT sensor quality. Never disable backup heat
   until load, equipment safety, and the installed sequence have been verified.

## Step 3 — On-site service

Only qualified HVAC/refrigeration personnel may open electrical panels, enter
OEM service mode, or work on a refrigerant circuit. Follow the manufacturer's
procedure, lockout/tagout requirements, and applicable refrigerant-recovery
rules before approaching capacitors, contactors, motors, or compressors.

1. **Compressor proof:**
   1. Verify the final output at the controller and the independent proof at the
      same compressor without forcing or bypassing an interlock.
   2. Inspect approved terminals, contactors, overloads, current/speed proof,
      and wiring under the manufacturer's de-energized test procedure.
   3. Diagnose any active OEM safety or lockout before attempting a single
      manufacturer-authorized reset.
2. **COP degradation:**
   1. Check refrigerant charge — undercharge is the most common fault per
      Barandier (2023). Measure subcooling and superheat.
   2. Check for refrigerant overcharge — also degrades COP, but less common.
   3. Inspect the condenser and evaporator coils for fouling (see the
      [rtu-compressor-refrigerant](rtu-compressor-refrigerant.md) playbook).
   4. Check compressor amp draw against nameplate — elevated amps suggest
      mechanical degradation.
   5. Check for non-condensable gases in the refrigerant circuit.
3. **Defrost anomaly:**
   1. Inspect the outdoor coil for heavy ice or frost buildup.
   2. Check the defrost temperature sensor — a failed sensor can trigger
      continuous defrost.
   3. Check the defrost control board for fault codes.
   4. If the unit uses time-temperature defrost, verify the timer settings
      match the manufacturer's recommendation.
4. **Reversing valve:**
   1. Check the reversing valve solenoid — listen for a click when the mode
      changes. No click indicates a failed solenoid ($100–$300 to replace).
   2. Check the wiring between the thermostat/controller and the reversing
      valve solenoid.
   3. If the solenoid energizes but the valve doesn't shift, the valve body is
      stuck. Low refrigerant charge can prevent the valve from shifting — check
      charge first.
   4. If the valve body has failed, replace the reversing valve ($500–$2,000
      plus refrigerant recovery).
5. **Auxiliary heat:** with the unit under normal OEM control, verify the
   auxiliary contactor/fuel valve and independent production proof, OAT input,
   and configured lockout/switchover. Qualified personnel should correct only
   the confirmed sensor, staging, or configuration defect; do not bypass
   high/low-pressure, electrical, temperature, or defrost safeties.

## Step 4 — Confirm resolution

1. **Compressor proof:** through a normal OEM-controlled cycle, verify command
   and independent proof agree after the commissioned pickup/dropout allowances.
   Do not force a compressor start or bypass anti-cycle and safety logic.
2. **COP:** monitor measured COP for 7 days — it should return to within 10%
   of the baseline curve.
3. **Defrost:** monitor defrost frequency and duration for 48 hours. Target:
   fewer than 4 cycles/hr, less than 10 minutes each.
4. **Reversing valve:** use manufacturer-approved operation to verify multiple
   mode changes and confirm SAT responds correctly each time.
5. **Auxiliary heat:** monitor normal heating through representative OAT/load
   conditions. Confirm required backup heat remains available below the
   commissioned strategy and prohibited concurrent operation stays clear above it.
