# Playbook: Stuck or Failed Actuator

| | |
|---|---|
| **Applies to** | AHU-0020, AHU-0014, AHU-0015, VAV-0004 |
| **Fix complexity** | On-site service required |
| **Typical time** | 1–4 h on-site |
| **Typical cost** | $200–$1,200 (actuator + labor) |
| **Energy impact** | Stuck actuators are a root cause behind multiple high-energy faults: simultaneous heating and cooling (10–30% AHU thermal), economizer failure (0–7% site), leaking coil valves (0.5–5% site in cold climates, EEM-03). Fixing one stuck actuator often resolves 2–5 related fault alarms. |

Adapted from HVAC FDD Reference v1.0, Remediation Playbooks (pp. 159–160).

## Step 1 — Verify the fault

1. Plot the command signal vs. position feedback over 24 hours; confirm a
   persistent gap of more than 10% for more than 30 minutes.
2. From the BAS, manually command the actuator through its full range (0% →
   100% → back). If feedback tracks the command, it was likely a temporary
   glitch — monitor for recurrence. If feedback stays flat regardless of
   command, the actuator or linkage has failed.
3. Check for downstream faults this actuator causes: a stuck heating valve →
   simultaneous H&C (AHU-0016); a stuck OA damper → economizer failure
   (AHU-0017).

## Step 2 — Remote check (limited options)

1. Release any manual overrides on the command point.
2. Check whether BAS auto-tuning or demand-limiting features are restricting
   the command range.
3. Pneumatic actuators: check the pneumatic transducer output against the
   command signal.
4. Check the controller's alarm/fault log — some DDC controllers log
   communication errors or actuator timeout events that pinpoint the failure.

## Step 3 — On-site service

1. At the actuator, check in order: (1) is the linkage still connected —
   disconnected linkages are the most common cause; (2) is the actuator
   receiving its control signal (voltage / air pressure at the actuator);
   (3) manually stroke the valve or damper — does it move freely?
2. Disconnected linkage: reconnect and tighten ($0–$50).
3. No signal at the actuator: trace wiring back to the controller; check
   fuses and breakers.
4. Signal present but no motion: replace the actuator — small valve actuators
   $200–$600, large damper actuators $300–$800, multi-section damper banks
   $500–$1,200.
5. Valve body seized from corrosion or debris: replace the valve
   ($500–$2,000).
6. Normally-open heating coil valves: verify the actuator has a spring
   return — without it, any power or signal loss opens the valve and creates
   simultaneous heating and cooling.

## Step 4 — Confirm resolution

1. After repair, command the actuator through its full range from the BAS;
   verify position feedback tracks within 5%.
2. The fault should clear immediately.
3. If this actuator was causing simultaneous H&C or economizer failure, check
   all downstream fault codes within 24 hours — they should resolve too.
