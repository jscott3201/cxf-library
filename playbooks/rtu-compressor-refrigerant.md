# Playbook: RTU Compressor & Refrigerant Faults

| | |
|---|---|
| **Applies to** | RTU-0001, RTU-0002, RTU-0007, RTU-0008, RTU-0009, RTU-0011 |
| **Fix complexity** | On-site service required |
| **Typical time** | 1–4 h on-site |
| **Typical cost** | $100–$500 (cleaning/filter) / $500–$2,000 (capacitor/charge) / $2,000–$8,000 (compressor) |
| **Energy impact** | EEM-23 (advanced RTU controls): 3–11% electricity savings. Catrini & Piacentino (2023) measured up to 47% fan power increase and 13.3% capacity reduction from evaporator fouling alone. RTUs are the most common HVAC system in commercial buildings — these faults often go unnoticed because the equipment is on the roof. |

Adapted from HVAC FDD Reference v1.0, Remediation Playbooks (pp. 168–169).

## Step 1 — Verify the fault

1. **Supply-fan prerequisite (RTU-0010):** before interpreting capacity,
   temperature split, or refrigerant signatures, compare the final supply-fan
   command with independent proof for that fan. A fail-to-start contests the
   airflow premise of RTU-0002 through RTU-0006. A commanded post-heat fan run
   must keep the final command true; purge, smoke control, and local hand modes
   omitted from the command are host NO_EVAL, not timer exceptions. Follow the
   [proof-of-operation](proof-of-operation.md) playbook for the mismatch itself.
2. **SAT tracking (RTU-0011):** confirm `sat_sp` is the final active
   mode-specific target, then verify stable supply-fan proof and mechanical
   heating/cooling status. Exclude startup, setpoint/mode steps, defrost,
   post-heat, demand response, normal DX off-cycles, and OEM limiting. Use
   `yTooWarm`/`yTooCold` only as direction evidence, not a root-cause verdict.
3. **Compressor short-cycling (RTU-0001):** pull the compressor run status
   trend and count starts per hour — more than 6 starts/hr indicates
   short-cycling. Check minimum on-time per cycle: less than 5 minutes is
   abnormal. (Albayati et al. 2023 achieved 95.7% accuracy on RTU fault
   classification with semi-supervised learning; the trend check remains the
   ground truth.)
4. **Evaporator fouling (RTU-0002):** calculate the temperature split
   RAT − SAT during steady-state cooling and compare to the baseline split
   for the current compressor stage. A 25% or greater reduction indicates
   fouling. Typical baselines: 8 °C (14 °F) at stage 1, 12 °C (22 °F) at
   stage 2.
5. **Condenser fouling (RTU-0007):** measure condenser leaving air
   temperature minus OAT and compare to baseline for the current stage and
   OAT. A 30% or greater increase indicates fouling.
6. **Refrigerant charge (RTU-0008/0009):** with the compressor settled at a
   steady stage, measure suction superheat and liquid subcooling at the
   service ports and compare to the unit's charging chart for the current
   conditions. High superheat with low subcooling indicates undercharge;
   subcooling well above the chart with normal-to-low superheat indicates
   overcharge. Rule out condenser airflow restriction (RTU-0007) first —
   it moves the same readings; low-ambient head-pressure control can mimic
   overcharge on a correctly charged unit.

## Step 2 — Remote triage

1. Confirm command, proof, temperature, and stage timestamps are fresh and
   aligned, and that each command/status pair has the same equipment scope.
2. Review local/remote state, smoke and freeze safeties, purge and post-heat
   states, compressor lockouts, and recent overrides or service activity.
3. Correct only verified BAS binding or sequence defects. Never bypass smoke,
   freeze, condensate, high/low-pressure, electrical, or OEM safeties, and do
   not repeatedly reset compressor or fan lockouts.
4. For RTU-0011, compare the tracking direction with economizer command,
   compressor/heating stage, fan proof, and OEM limit history before changing
   setpoints or tuning. A bad active-target binding is not a capacity fault.

## Step 3 — On-site service

Only qualified HVAC/refrigeration personnel may open panels, enter OEM service
mode, or work on a refrigerant circuit. Follow the manufacturer's procedure,
lockout/tagout requirements, and applicable refrigerant-recovery rules before
approaching belts, capacitors, contactors, fans, or compressors.

1. **Short-cycling — check in order of likelihood:**
   1. Thermostat differential: increase from 1 °F to 2–3 °F to prevent rapid
      cycling.
   2. Refrigerant charge: low charge causes low suction pressure, tripping
      the low-pressure safety. Check subcooling and superheat against
      manufacturer specs.
   3. Run capacitor: a weak capacitor makes the compressor struggle to
      start. Test with a capacitance meter — replace below 90% of rated
      value ($50–$150).
   4. Oversized equipment: if the unit is significantly oversized for the
      load, cycling is inherent — staging controls or a compressor VFD may
      help.
2. **Evaporator fouling:**
   1. Replace the air filter — the most common cause and the cheapest fix
      ($50–$200/bank).
   2. Inspect the evaporator coil; clean with coil cleaner and low-pressure
      water ($200–$500).
   3. Check the evaporator fan motor — degraded motors reduce airflow across
      the coil, mimicking fouling.
   4. Check for ice on the coil — icing indicates low refrigerant charge or
      a failed defrost cycle.
3. **Condenser fouling (RTU-0007):**
   1. Inspect the condenser coil from outside the unit — cottonwood seeds,
      leaves, and debris are the most common culprits.
   2. Clean the coil from the inside out with a garden hose or pressure
      washer ($0–$200).
   3. Check the condenser fan motor and blade condition.
   4. Check that adjacent RTUs are not discharging hot air into this unit's
      condenser intake — rearranging discharge hoods can fix this.

## Step 4 — Confirm resolution

1. **Short-cycling:** monitor starts per hour over 48 hours. Target: fewer
   than 6 starts/hr with minimum 5-minute on-time.
2. **Evaporator fouling:** recalculate the temperature split — it should
   return to within 15% of baseline. (Note: this resolution target is
   tighter than RTU-0002's 25% alarm threshold — the fault clears well
   before the coil is fully recovered, so confirm against the 15% target,
   not against the alarm clearing.)
3. **Condenser fouling:** recalculate the condenser split — it should return
   to within 20% of baseline.
4. **Supply fan:** through a normal controller-owned cycle, verify the final
   command and independent proof agree after commissioned pickup/dropout times.
   Do not force operation or bypass an interlock.
5. **SAT tracking:** after the causal repair, trend final active setpoint, SAT,
   fan proof, and conditioning proof across normal heating/cooling cycles. The
   error should remain inside the commissioned band once settled.
6. Schedule preventive maintenance: quarterly filter changes, annual coil
   cleaning. For multi-RTU sites, service all units in the same visit.
