# Playbook: Economizer Failure

| | |
|---|---|
| **Applies to** | AHU-FC-051, RTU-FC-053, CLU-03 |
| **Fix complexity** | Remote fix (40%) · Remote + on-site (40%) · On-site only (20%) |
| **Typical time** | 30 min remote / 1–3 h on-site |
| **Typical cost** | $0 remote / $100–$400 linkage repair / $500–$1,200 actuator |
| **Energy impact** | EEM-06: 0–7% site energy. EEM-23 (RTU advanced controls): 3–11% electricity. Cowan (2004): 54% of RTU economizers have at least one fault; disconnected linkages are the single most common failure mode. |

Adapted from HVAC FDD Reference v1.0, Remediation Playbooks (pp. 156–157).

## Step 1 — Verify the fault

1. Wait for favorable conditions (outdoor air cooler than return air and above
   the low-limit cutoff). Is the OA damper stuck at minimum? Is mechanical
   cooling active (cooling valve open or compressor running)? Both true =
   confirmed waste.
2. Compare the OAT sensor to a nearby weather station — a sensor reading high
   can lock out the economizer. PNNL-27338 AIRCx computes outdoor air fraction
   OAF = (MAT − RAT)/(OAT − RAT), reliable only when |OAT − RAT| > 5 °F.
3. Check both failure modes: (1) economizer not activating when favorable, and
   (2) economizer staying open when OAT is above the lockout — the second
   brings in excess hot outdoor air.

## Step 2 — Remote fix

1. Check the economizer enable/disable flag in the BAS; enable if off.
2. Check the high-limit setpoint. Fixed dry-bulb: ASHRAE 90.1 high-limit by
   climate — 75 °F zones 1A–3A, 70 °F zones 4A–5A, 65 °F zones 5B–8.
   Differential: free cooling should enable whenever OA is cooler than RA.
   Raise a too-low setpoint.
3. Remove seasonal lockouts blocking free cooling during mild weather.
4. If the OAT sensor has drifted, apply a calibration offset as a temporary
   fix.
5. RTUs with integrated economizers: verify DX staging allows the economizer
   to run with and without mechanical cooling — non-integrated operation loses
   significant free-cooling opportunity.

## Step 3 — On-site service

1. Manually command the OA damper to 100% and watch it physically move.
2. If it doesn't move: check actuator power/air supply; check the linkage —
   disconnected rod ends are the most common RTU economizer failure (rod-end
   pop-off, bent crank arm, stripped set screw, broken plastic clip). Replace
   linkage components ($50–$150).
3. If the actuator has failed, replace it ($300–$800).
4. RTUs: verify barometric relief / power exhaust works — inadequate relief
   creates positive pressure that prevents the damper opening fully.
5. Inspect damper blade seals — worn seals cause excess outdoor air when
   commanded closed (RTU-FC-054).

## Step 4 — Confirm resolution

1. Wait for the next favorable free-cooling period.
2. Verify the OA damper modulates between minimum and 100% as conditions
   change, and mechanical cooling drops during favorable periods.
3. The fault should clear within 24 hours.
4. Multi-RTU sites: survey all units — if one RTU has an economizer problem,
   30–50% of others on the same roof likely do too.
