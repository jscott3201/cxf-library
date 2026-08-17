# Playbook: Missing Reset Strategy (SAT / DSP)

| | |
|---|---|
| **Applies to** | AHU-FC-057 (SAT reset), AHU-FC-058 (DSP reset), AHU-FC-053 (SAT SP too low), AHU-FC-065 (excess static pressure), CLU-02 |
| **Fix complexity** | Remote fix (90%) · Controller upgrade (10%) |
| **Typical time** | 1–4 h remote (sequence programming) |
| **Typical cost** | $0 remote / $2,000–$5,000 if controller upgrade needed |
| **Energy impact** | EEM-05 (SAT reset): 1–4.4% site energy, 2.5% national median. EEM-12 (DSP reset): 1–3% site energy via cubed fan law. Combined, absent in 74% of buildings (PNNL 151-building study). |

Adapted from HVAC FDD Reference v1.0, Remediation Playbooks (pp. 154–156).

## Step 1 — Verify the fault

1. Plot the SAT setpoint vs. outdoor air temperature over 7 days. A flat
   setpoint means no reset; one that varies without correlating to zone demand
   means misconfigured reset logic. PNNL-27338 AIRCx threshold: if
   MAX(sat_stpt) − MIN(sat_stpt) < 2 °F over the window, no reset is detected.
2. Plot the DSP setpoint vs. the highest zone damper position. Flat setpoint
   with dampers well below 100% means no reset (AIRCx: MAX − MIN < 0.25 in.
   w.g.). Good operation: most zone dampers 50–75% open; bad: all near 100% or
   all near 0%.
3. Check whether zone-level demand requests reach the AHU controller — if no
   requests arrive, the issue is at the zone level or the comms path.

## Step 2 — Remote fix

1. If the reset sequence exists but is disabled: re-enable it; verify all VAV
   boxes send requests to the correct air handler.
2. If no SAT reset exists, program trim-and-respond per G36 §5.16.2: start
   18 °C (65 °F); trim up +0.2 °F per interval when zones satisfied; respond
   down −0.5 °F per zone cooling request; range 13–18 °C (55–65 °F).
3. If no DSP reset exists, program trim-and-respond per G36 §5.16.1: start
   0.5 in. w.g.; trim −0.03 in. per interval when dampers not maxed; respond
   +0.06 in. per zone airflow request; max = design static, min 0.2 in. w.g.
4. If trim-and-respond is active but ineffective: check trim interval (~2 min
   SAT, ~1 min DSP); ensure respond magnitude exceeds trim magnitude; check
   request thresholds at the VAV boxes.
5. High-SAT heuristics (PNNL-27338): >60% of zone dampers above 90% open → SAT
   too high, lower it; >25% of zones with reheat valves above 50% → SAT too
   low.

## Step 3 — On-site service (rarely needed)

1. If the AHU controller doesn't support trim-and-respond logic, upgrade the
   controller ($2,000–$5,000 including labor) — uncommon outside legacy
   pneumatic or first-generation digital controls.
2. Verify zone controllers communicate with the AHU controller; check trunk
   cabling, repeaters, protocol converters (e.g. MSTP-to-IP routers).

## Step 4 — Confirm resolution

1. Monitor setpoints over 7 days after programming.
2. SAT setpoint should modulate up during low demand, down during high demand;
   DSP setpoint should decrease when zone dampers are mostly closed.
3. The fault should clear within one evaluation window (typically 7 days).
4. Expected savings: ~2.5% of site energy from SAT reset alone (PNNL national
   median); DSP reset adds 1–3% via the cubed fan law (a 20% fan-speed
   reduction yields ~49% fan-power reduction).
