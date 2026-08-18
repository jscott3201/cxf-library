# Playbook: Chiller Efficiency Degradation

| | |
|---|---|
| **Applies to** | CHW-0001, CLU-06 (also the reference's CHW-FC-008/009, not yet authored) |
| **Fix complexity** | On-site service (cleaning) · Capital (refrigerant/compressor) |
| **Typical time** | 4–8 h on-site (tube cleaning) |
| **Typical cost** | $1,000–$3,000 cleaning / $5,000+ compressor service |
| **Energy impact** | EEM-11 (CHW temp reset): 0.5–2% site energy. EEM-10 (CHW DP reset): 0.5–2%. EEM-26 (cooling tower controls): 1–6% electricity. A 10% degradation in chiller kW/ton on a 500-ton plant at $0.12/kWh costs $5,000–$15,000/yr in excess energy. |

Adapted from HVAC FDD Reference v1.0, Remediation Playbooks (pp. 161–163).

## Step 1 — Verify the fault

1. Review the chiller's kW/ton trend against the baseline model over 30 days.
2. Determine whether the deviation is gradual (suggesting fouling) or sudden
   (suggesting refrigerant loss or a mechanical issue).
3. Compare the condenser approach temperature and evaporator approach
   temperature to their design values:
   - Condenser approach = condenser leaving water temp − refrigerant
     condensing temp. Design: typically 1–2 °F.
   - Evaporator approach = refrigerant evaporating temp − chilled water
     leaving temp. Design: typically 1–2 °F.
   - An approach temperature more than 2× design indicates fouling on that
     side.
4. Rule out measurement error: verify that flow meters and power meters are
   reading correctly before assuming a chiller problem.

## Step 2 — Remote check (limited options)

1. Check the chilled water supply temperature reset setpoint — if it is
   locked too low, the chiller has to work harder than necessary. EEM-11:
   resetting CHW supply temperature up during part-load conditions saves
   0.5–2% of site energy.
2. Check the condenser water temperature reset — lowering condenser water
   temperature improves efficiency, but raising it by 2–3 °F decreases
   efficiency by 2–3%. EEM-13: optimizing condenser water temperature saves
   0.5–2% site energy in large offices.
3. Check the chiller staging sequence — make sure the lead/lag logic isn't
   running one chiller at high load when two chillers at part load would be
   more efficient.
4. Check cooling tower fan staging and speed control — insufficient condenser
   water flow or inadequate tower capacity raises head pressure and degrades
   chiller efficiency (EEM-26: 1–6% electricity savings).

## Step 3 — On-site service

1. **Condenser approach temperature high (condenser-side fouling):**
   1. Clean the condenser tubes (recommended annually).
   2. Check the condenser water flow rate — a blocked strainer reduces flow
      and degrades heat transfer.
   3. Purge non-condensable gases from the condenser.
   4. Cost: $1,000–$3,000 for tube cleaning.
2. **Evaporator approach temperature high (evaporator-side fouling):**
   1. Clean the evaporator tubes.
   2. Check the chilled water flow rate and pump performance.
3. **Both approach temperatures normal but kW/ton still high:**
   1. Check the refrigerant charge — this is the most common root cause.
   2. Leak-test all fittings, oil pump joints, and relief valves.
   3. Recharge as needed. Cost: $500–$2,000 depending on refrigerant type.
4. **Compressor issue suspected:**
   1. Check compressor motor amp draw against the nameplate rating.
   2. Run vibration analysis if equipment is available.
   3. Cost: $5,000+ for major compressor service.

## Step 4 — Confirm resolution

1. After service, monitor kW/ton for 2 weeks.
2. The chiller should return to within 10% of its baseline efficiency.
3. The fault should clear once the efficiency baseline is re-established.
