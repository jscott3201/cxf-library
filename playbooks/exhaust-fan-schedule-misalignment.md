# Playbook: Exhaust Fan Schedule Misalignment

| | |
|---|---|
| **Applies to** | SYS-FC-053 (exhaust running unoccupied), SYS-FC-057 (exhaust/AHU misalignment), CLU-08 |
| **Fix complexity** | Remote fix (90%) · On-site (10%) |
| **Typical time** | 15–30 min remote |
| **Typical cost** | $0 remote |
| **Energy impact** | EEM-07: 0.5–3% site energy. ~35% prevalence per PNNL 151-building study. The waste is twofold: direct fan energy plus the conditioning penalty from exhausting conditioned air and drawing in unconditioned outdoor air. An exhaust fan running during unoccupied hours in winter pulls heated air out of the building while drawing freezing air in through cracks, dramatically increasing heating energy. |

Adapted from HVAC FDD Reference v1.0, Remediation Playbooks (pp. 173–175).

## Step 1 — Verify the fault

1. For exhaust running unoccupied (SYS-FC-053):
   - Pull a 7-day trend of exhaust fan status overlaid with the building
     occupancy schedule.
   - Confirm the exhaust fan is running during unoccupied periods for more
     than 15 minutes.
   - Check whether the run is a legitimate demand override (e.g., lab
     exhaust, parking garage, kitchen hood).
2. For exhaust/AHU misalignment (SYS-FC-057):
   - Compare exhaust fan status to supply fan status over 7 days.
   - Condition 1: exhaust ON but supply OFF — this creates negative building
     pressure, pulling in unconditioned air through the envelope.
   - Condition 2: supply ON but exhaust OFF during occupied hours — this
     creates positive pressure and can cause IAQ issues.
3. Quantify the waste: exhaust fan energy = fan_rated_kW × (speed/100)³. Add
   the conditioning penalty: for each CFM of exhausted air, the building must
   condition the same volume of makeup air.

## Step 2 — Remote fix

1. Synchronize the exhaust fan schedule with the AHU schedule:
   - Both should reference the same master occupancy schedule.
   - If the exhaust fan is on a separate controller or timer, reprogram it to
     match.
2. Release any manual overrides on the exhaust fan command.
3. For exhaust fans controlled by standalone timers or switches (not
   integrated into the BAS):
   - Reprogram the timer to match the building schedule.
   - Better: connect the exhaust fan to the BAS via an interlock relay so it
     follows the supply fan status automatically.
4. Verify that holiday schedules are synchronized between the AHU and exhaust
   systems.
5. For demand-controlled exhaust (e.g., garage CO sensors, kitchen hoods):
   verify the demand sensor is working correctly and not falsely triggering
   the fan.

## Step 3 — On-site service (rare)

1. If the exhaust fan runs despite receiving the correct off command:
   - Check the contactor or relay for welding (stuck closed).
   - Check for a hand-off-auto switch left in hand (manual on) position.
   - Check for a hardwired interlock with another system (e.g., fire alarm
     override) keeping the fan running.
2. If the exhaust fan VFD has a fault keeping the fan running at a fixed
   speed, clear the VFD fault and restore normal BAS control.

## Step 4 — Confirm resolution

1. Monitor exhaust fan status vs. supply fan status for 3 consecutive
   occupied/unoccupied cycles.
2. Exhaust fans should start within 5 minutes of the supply fan and stop
   within 5 minutes of it shutting down.
3. During unoccupied hours, exhaust fans should remain off unless a
   legitimate demand override is active.
4. The fault should clear within 24–48 hours.
