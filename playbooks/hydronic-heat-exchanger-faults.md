# Playbook: Hydronic Heat-Exchanger Faults

| | |
|---|---|
| **Applies to** | HX-0001 through HX-0003 |
| **Fix complexity** | Remote validation (30%) · qualified on-site hydronic service (70%) |
| **Typical time** | 20–60 min remote; 1–6 h on-site, longer for cleaning/isolation work |
| **Typical cost** | Site-specific sensor/actuator repair through exchanger cleaning or replacement |
| **Energy impact** | Lost transfer raises upstream heating/cooling energy; unintended transfer wastes plant and pumping energy and may defeat isolation |

## Step 1 — Prove the topology and evidence

1. Identify one physical exchanger and trace both inlet/outlet pairs from
   drawings and a walk-down. Keep primary and secondary identities fixed.
2. Confirm every temperature and flow has that same equipment scope, timestamp
   basis, and unit. Reject common-header or fleet totals.
3. Record each side's fluid, glycol concentration where applicable, density and
   heat-capacity source, and validity range.
4. Verify derived effectiveness/heat transfer inputs, energy-balance tolerance,
   expected-model version/readiness/domain, and training/commissioning period.
   Never fit a clean expectation on the episode being judged.
5. Confirm automatic mode, stable setpoints/flows/valves, maintenance state,
   safety/protective sequences, and the commissioned re-warm interval after a
   direction, pump, valve, or setpoint change.

## Step 2 — Separate the signatures

1. For HX-0002, verify `exchange_cmd` is the final state that means both
   branches should flow. Availability or an upstream plant request is not
   enough. Compare the missing side with its pump command/proof, isolation
   valves, strainer DP, air/pressure state, and meter quality.
2. For HX-0001, compare actual and expected effectiveness only inside the
   frozen model's domain. Check the two independently calculated side heat
   rates before blaming the exchanger.
3. For HX-0003, confirm the named valve is intended to isolate the whole path
   and its final command is closed. Allow commissioned transport/thermal soak,
   then inspect actual position if available, residual branch flow, bypasses,
   check valves, and gravity circulation.

## Step 3 — Remote triage

1. Release only documented BAS overrides. Do not defeat freeze protection,
   minimum-flow, pressure, or other protective sequences.
2. Trend all four temperatures, both flows, final command/valve command, signed
   heat transfer, actual/expected effectiveness, and readiness/domain flags at
   a common fixed cadence.
3. Compare sensor offsets during a legitimate no-transfer equalization period
   only when the system can be placed there safely.
4. Inspect model inputs and fluid-property configuration. A bad density,
   glycol concentration, point sign, or connection swap can manufacture both
   low effectiveness and false energy imbalance.

## Step 4 — Qualified on-site service

Only qualified hydronic/HVAC personnel following site lockout/tagout,
pressure/temperature isolation, drain/fill, chemical-handling, and manufacturer
procedures may open equipment, stroke valves locally, clean plates/tubes, or
service pumps. Never isolate a required safety path or open a hot/pressurized
system to test a diagnostic.

1. Inspect the missing-flow side for pump/coupling failure, closed isolation,
   actuator/linkage failure, clogged strainer, air lock, fouling, failed check
   valve, low system pressure, or a bad meter.
2. Inspect low effectiveness for plate/tube fouling, scaling, blocked channels,
   gasket/internal bypass leakage, incorrect piping, degraded glycol, and
   sensor placement/calibration.
3. Inspect unintended transfer for a passing valve seat, undersized actuator or
   insufficient close-off rating, linkage failure, manual bypass, parallel
   open path, failed check valve, or thermosiphon flow.
4. Use chemical or mechanical cleaning only under the exchanger and water-
   treatment manufacturer's procedures; preserve corrosion and freeze control.

## Step 5 — Confirm resolution

1. Revalidate all point scaling, side identity, timestamps, and energy balance.
2. Observe settled automatic operation in the applicable heating and/or cooling
   direction and confirm both branch flows when exchange is finally commanded.
3. Re-establish or deliberately preserve the clean baseline under a documented
   change-control policy after cleaning/replacement; do not let an online model
   silently learn a fault.
4. With the isolation valve legitimately closed and soak expired, confirm
   transfer remains within the commissioned no-load uncertainty envelope.
5. Observe for at least one full persistence interval after settling and verify
   the finding does not reassert.
