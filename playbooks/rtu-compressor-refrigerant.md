# Playbook: RTU Compressor & Refrigerant Faults

| | |
|---|---|
| **Applies to** | RTU-0001, RTU-0002, RTU-0007 |
| **Fix complexity** | On-site service required |
| **Typical time** | 1–4 h on-site |
| **Typical cost** | $100–$500 (cleaning/filter) / $500–$2,000 (capacitor/charge) / $2,000–$8,000 (compressor) |
| **Energy impact** | EEM-23 (advanced RTU controls): 3–11% electricity savings. Catrini & Piacentino (2023) measured up to 47% fan power increase and 13.3% capacity reduction from evaporator fouling alone. RTUs are the most common HVAC system in commercial buildings — these faults often go unnoticed because the equipment is on the roof. |

Adapted from HVAC FDD Reference v1.0, Remediation Playbooks (pp. 168–169).

## Step 1 — Verify the fault

1. **Compressor short-cycling (RTU-0001):** pull the compressor run status
   trend and count starts per hour — more than 6 starts/hr indicates
   short-cycling. Check minimum on-time per cycle: less than 5 minutes is
   abnormal. (Albayati et al. 2023 achieved 95.7% accuracy on RTU fault
   classification with semi-supervised learning; the trend check remains the
   ground truth.)
2. **Evaporator fouling (RTU-0002):** calculate the temperature split
   RAT − SAT during steady-state cooling and compare to the baseline split
   for the current compressor stage. A 25% or greater reduction indicates
   fouling. Typical baselines: 8 °C (14 °F) at stage 1, 12 °C (22 °F) at
   stage 2.
3. **Condenser fouling (RTU-0007):** measure condenser leaving air
   temperature minus OAT and compare to baseline for the current stage and
   OAT. A 30% or greater increase indicates fouling.

## Step 2 — On-site service

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

## Step 3 — Confirm resolution

1. **Short-cycling:** monitor starts per hour over 48 hours. Target: fewer
   than 6 starts/hr with minimum 5-minute on-time.
2. **Evaporator fouling:** recalculate the temperature split — it should
   return to within 15% of baseline. (Note: this resolution target is
   tighter than RTU-0002's 25% alarm threshold — the fault clears well
   before the coil is fully recovered, so confirm against the 15% target,
   not against the alarm clearing.)
3. **Condenser fouling:** recalculate the condenser split — it should return
   to within 20% of baseline.
4. Schedule preventive maintenance: quarterly filter changes, annual coil
   cleaning. For multi-RTU sites, service all units in the same visit.
