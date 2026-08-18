# Playbook: Hot Water Plant Faults

| | |
|---|---|
| **Applies to** | HW-FC-050 (short-cycling), HW-FC-051 (efficiency), HW-FC-052 (OAT lockout) |
| **Fix complexity** | Remote fix (lockout) · Remote + on-site (cycling) · On-site (efficiency) |
| **Typical time** | 15 min (lockout) / 2–4 h (cycling) / 4–8 h (efficiency) |
| **Typical cost** | $0 lockout / $0–$500 cycling / $500–$3,000 efficiency |
| **Energy impact** | PNNL-27338 detects HW system issues including constant supply temperature (no reset), constant DP (no reset), high DP setpoint, high supply temp setpoint, and low loop delta-T. HW supply temp reset and DP reset together save 1–3% of site energy. Running boilers without OAT lockout wastes 100% of the fuel consumed during warm weather. |

Adapted from HVAC FDD Reference v1.0, Remediation Playbooks (pp. 164–165).

## Step 1 — Boiler OAT lockout not active (HW-FC-052)

1. Program an outdoor air temperature lockout in the BAS:
   - Disable the boiler plant when outdoor air rises above the heating design
     threshold.
   - Typical lockout: boiler off when outdoor air > 60 °F (15 °C).
   - Use hysteresis to prevent rapid toggling (e.g. re-enable at outdoor air
     < 55 °F / 13 °C).
2. Ensure the chilled water plant enables to pick up any cooling load after
   the boiler shuts down.
3. PNNL-27338 also detects constant HW supply temperature (no reset). Program
   an OAT-based reset: higher HW temp in cold weather, lower in mild weather.
   Typical range: 180 °F at 0 °F OAT, resetting down to 140 °F at 55 °F OAT.

## Step 2 — Boiler short-cycling (HW-FC-050)

1. Increase the minimum run-time between starts (default recommendation: 15
   minutes).
2. Check the staging differential — if it is too narrow, the boiler turns on
   and off rapidly.
3. For modulating boilers: check the minimum firing rate setting.
4. If the boiler is oversized for the current load:
   - Stage fewer boilers to keep each one loaded above its minimum firing
     rate.
   - For single-boiler plants, consider adding thermal storage or a buffer
     tank to absorb cycling.
5. Check boiler minimum flow requirements — low water flow can trip the
   safety and shut the boiler down prematurely.

## Step 3 — Boiler efficiency degradation (HW-FC-051)

1. Measure combustion efficiency with a flue gas analyzer. Target: O₂ level
   of 1.5% for natural gas, with flue temperature within the manufacturer's
   rating. Excess O₂ above 3% indicates too much combustion air — wasted
   energy up the stack.
2. Clean the fire-side heat transfer surfaces — soot buildup insulates the
   tubes and reduces efficiency.
3. Clean the water-side surfaces — mineral scale buildup has the same
   insulating effect.
4. Check the air-to-fuel ratio — excess combustion air carries heat up the
   stack without doing useful work.
5. Inspect the burner assembly, nozzles, and ignition system.
6. Check condensate return water quality (for steam systems).
7. PNNL-27338 also detects high HW differential pressure setpoints. If DP is
   set too high, pumps waste energy. Reset DP based on the most-open valve
   position.

## Step 4 — Confirm resolution

1. **OAT lockout:** the boiler should stop running during warm weather. The
   fault clears immediately.
2. **Short-cycling:** monitor starts per hour — should drop below 4. Allow 48
   hours for confirmation.
3. **Efficiency:** monitor combustion efficiency over 2 weeks. Target: return
   to within 5% of rated efficiency.
