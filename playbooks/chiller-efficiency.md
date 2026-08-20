# Playbook: Chilled-Water Plant Diagnosis

| | |
|---|---|
| **Applies to** | CHW-0001 through CHW-0009, CLU-06 |
| **Fix complexity** | Remote controls review · On-site service · Capital repair |
| **Typical time** | 2–8 h initial diagnosis; longer for baseline confirmation or tube/compressor work |
| **Typical cost** | Controls-only to $1,000–$3,000 tube cleaning / $5,000+ compressor service |
| **Energy impact** | EEM-11 (CHW temperature reset): 0.5–2% site energy. EEM-10 (CHW DP reset): 0.5–2%. EEM-26 (tower controls): 1–6% electricity. A 10% kW/ton degradation on a 500-ton plant can cost $5,000–$15,000/yr, but proof/cycling/tracking findings must be sized separately. |

Adapted from HVAC FDD Reference v1.0, Remediation Playbooks (pp. 161–163),
with library-authored command/proof, tracking, and cycling triage.

## Step 1 — Establish commanded versus running machines (CHW-0008)

1. List each chiller separately: final BAS stage command, independent run proof,
   local/remote mode, active lockout, and timestamp freshness. Plant enable or a
   fleet-OR status is not enough.
2. For `yFailToStart`, follow the sequence in order: lead/lag selection,
   isolation valves, chilled/condenser-water pumps and flow proof, oil system,
   starter/drive, and chiller safeties. Do not bypass anti-recycle protection.
3. For `yUnexpectedRun`, check local/manual mode, service overrides, a second
   controller, welded/stuck outputs, and whether the command was bound upstream
   of the machine's real control owner.
4. Verify the configured 300/120-second proof windows exceed this machine's
   normal start and stop sequences plus point-delivery latency.

## Step 2 — Confirm flow, permissives, and measurement boundaries

1. Confirm evaporator and condenser flow are established for each running
   machine and minimum-flow interlocks are satisfied.
2. Verify isolation and bypass valve positions, strainers, pump proof, and
   branch/header topology before diagnosing the refrigerant circuit.
3. Confirm `chiller_load`, temperatures, and power/tons belong to the intended
   machine. On parallel plants, do not read a mixed-header value onto each
   chiller without proving that boundary is the controlled target.
4. Rule out sensor, scaling, timestamp, flow-meter, and power-meter error.

## Step 3 — Inspect CHWST tracking direction (CHW-0007)

1. Compare the individual evaporator leaving-water temperature with the final
   active target delivered to that controller. A common header is acceptable
   only when the staged machines genuinely regulate that same point.
2. Exclude startup pull-down, reset ramps, staging transfer, ice-making, and
   current/lift/surge/freeze/demand limiting before interpreting the alarm.
3. `yTooWarm`: check capacity, flow, fouling, refrigerant, permissives, sensor
   bias, and whether the setpoint actually reached the local controller.
4. `yTooCold`: check aggressive staging, local-loop tuning, reset delivery,
   sensor bias, and a machine controlling a different target than the BAS.
5. A CHW-0008 fail-to-start direction makes tracking non-evaluable; an
   unexpected-running machine can still have meaningful tracking evidence.

## Step 4 — Review starts, timers, and staging (CHW-0009)

1. Trend per-machine proof at a cadence that resolves the shortest OFF/ON
   dwell. At the defaults, use a fixed 60-second evaluator and
   `count_scale=evaluation_window/tick`.
2. Compare each start with load, CHWST/setpoint, plant enable, lead/lag
   selection, minimum on/off timers, and lockout/safety history.
3. Look for low-load inability to turn down, narrow deadbands, insufficient
   loop volume/storage, unstable proof, or safety trip/auto-reset cycling.
4. Apply the manufacturer's starts-per-hour and minimum on/off limits. The
   library's three-start threshold is a commissioning placeholder.

## Step 5 — Then evaluate efficiency, reset, delta-T, and approach

1. Review CHW-0001 kW/ton against its per-machine fitted baseline and verify the
   fit period, tons conversion, load domain, and meter boundary.
2. Check CHWST reset (CHW-0002) and loop DP reset (CHW-0003). A setpoint locked
   too low increases lift; a poor DP sequence can waste pump energy.
3. Review low delta-T (CHW-0004) with coil valves, bypass/decoupler flow,
   staging, and return-water temperature. Do not attribute a plant/header
   signature to one chiller without branch evidence.
4. Compare condenser (CHW-0005) and evaporator (CHW-0006) approaches with their
   design/commissioned values, load floor, refrigerant P-T provenance, water
   temperatures, and flow.
5. Check tower fan staging, condenser-water reset, and pump operation. Higher
   condensing lift can explain both approach and kW/ton degradation.

## Step 6 — On-site service after controls and sensors are cleared

1. High condenser approach: inspect condenser flow and strainer, clean tubes,
   verify water treatment, and purge non-condensables as applicable.
2. High evaporator approach: inspect chilled-water flow/strainer and clean
   evaporator tubes.
3. Normal approaches with high kW/ton: leak-test and verify refrigerant charge,
   compressor/VFD current, power quality, oil system, and mechanical condition.
4. For persistent proof or cycling faults, inspect starter/drive histories,
   contacts, compressor protections, run-proof wiring, and local controller
   event logs before replacing equipment.

## Step 7 — Confirm resolution

1. Verify command and independent proof agree through normal start/stop cycles.
2. Observe at least one full CHWST tracking delay after startup and staging; the
   active machine should remain within its commissioned band.
3. Observe at least one complete cycling window with manufacturer-compliant
   start count and minimum on/off times.
4. Confirm flow, delta-T, setpoint reset, and both approach temperatures are in
   their commissioned domains.
5. Monitor kW/ton on a disjoint post-repair period; do not refit the baseline on
   the faulty interval merely to make CHW-0001 clear.
