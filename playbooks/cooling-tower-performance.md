# Playbook: Cooling Tower Performance, Control, and Freeze Protection

| | |
|---|---|
| **Applies to** | TOWER-0001 (approach high), TOWER-0002 (range collapse), TOWER-0003 (fan short-cycling), TOWER-0004 (fan proof), TOWER-0005 (overcooling with fan energy), TOWER-0006 (basin freeze protection), CHW-0005 (condenser approach high) |
| **Fix complexity** | Remote controls review or qualified on-site tower/electrical service |
| **Typical time** | 15–30 min remote triage; 1–4 h on-site after safe access is established |
| **Typical cost** | Site-specific; freeze/electrical protective findings are not safely reducible to a generic service-cost range |
| **Energy impact** | Degradation raises chiller lift; overcooling and unexpected fan operation can waste fan electricity. Freeze-protection findings are asset-protection alarms, not savings opportunities. |

**Library-authored playbook.** Mechanisms and safety constraints are grounded in
DOE FEMP/PNNL tower O&M guidance, BEE chiller guidance, NREL tower-control
discussion, and SPX/EVAPCO manufacturer material. Numeric rule thresholds remain
commissioning or site/OEM values as stated on each card.

> **Freeze/electrical safety:** follow the site and OEM freeze plan before field
> inspection. Do not bypass low-water cutoff, thermostat, over-temperature,
> vibration, fire, or other interlocks. Do not force a contactor or manually
> energize an unverified immersion heater. Confirm water level and electrical
> isolation using qualified personnel and the site's lockout/tagout procedure.

## Step 1 — Verify identity, applicability, and mode

1. Confirm point topology first: tower leaving water is the cold stream going to
   the chiller condenser; tower entering water is the warm chiller return.
2. Confirm every fan command, proof, speed, and outlet temperature belongs to
   the same tower object/cell. Do not pair a fleet OR or common header with one
   arbitrarily selected fan.
3. Confirm normal automatic ownership. Exclude maintenance, hand/local, tests,
   free cooling/waterside economizer, storage charging, emergency heat
   rejection, drain-down, deicing, or another approved low-water mode.
4. For TOWER-0006, establish that this is a wet tower with water intentionally
   present, the monitored heater/equivalent is part of the active freeze plan,
   basin level and low-water cutoff are healthy, and the configured basin limit
   and response time come from that site's OEM plan. Otherwise report NO_EVAL.
5. Check freshness, time alignment, scaling, and sensor calibration. A command
   echo is not run proof; a heater contactor proves less than measured current,
   and current proves less than delivered basin heat.

## Step 2 — Select the diagnostic branch

### A. No fan proof or unexpected fan operation — TOWER-0004

1. Read `yFailToStart` versus `yUnexpectedRun`; the repairs differ.
2. Failure to start: check VFD/starter faults, disconnect/overload, vibration or
   OEM interlock, motor/belt/gearbox, final cell-stage command, and proof source.
3. Unexpected run: check local/manual mode, service override, second controller,
   stuck output/contactor, VFD internal command, and normal coast-down timing.
4. Compare with TOWER-0003. Cycling plus intermittent proof often points to a
   drive/overload/control issue before it points to tower thermal performance.

### B. Overcooling while fan is loaded — TOWER-0005

1. Confirm the active setpoint is the final target for the same cold outlet.
2. Read `yOvercooled` and `yFanLoaded` separately. Cold water with the fan off is
   normal free convection and must not be dispatched as waste.
3. Check stale/local setpoints, VFD minimum speed, cell-stage deadbands, fan
   hand/override, sensor bias, and isolation/bypass valve sequence.
4. Review setpoint, mode, fan-state, or cell-count changes before the alarm; add
   a site holdoff longer than the normal response if required.
5. Do not assume colder condenser water always wastes whole-plant energy. Tune
   tower fan versus chiller lift from measured plant performance.

### C. Basin freeze protection — TOWER-0006

1. Treat `yHeaterFailToRun` as electrical/command-proof evidence and
   `yLowBasinTemp` as thermal evidence. A proven heater cannot mask cold water.
2. From a safe state, verify basin water level, low-water cutoff, local
   thermostat/controller state, disconnect/breaker/fuses, contactor, current or
   power proof, and representative submerged temperature.
3. Confirm the sensor is away from the heater plume and not in a dry or stagnant
   pocket. Confirm local OAT represents the tower exposure.
4. Remember that a basin heater protects the basin/discharge area only; it does
   not by itself protect exposed piping, pumps, or heat exchangers.
5. Command false with status true is outside the current graph but can indicate
   an uncontrolled or dry heater hazard. Follow the OEM/site safety workflow
   immediately; do not treat it as a harmless energy-only condition.

### D. Performance degradation — TOWER-0001, TOWER-0002, CHW-0005

1. For approach high, confirm full fan capacity and compare matched-load,
   matched-wet-bulb history against the commissioned design approach.
2. For range collapse, check condenser-water flow and actual heat rejection
   first; excess flow or an unloaded loop mimics tower failure.
3. For chiller condenser approach high with normal tower approach, investigate
   condenser tubes, flow, refrigerant-side non-condensables, and saturation-
   temperature derivation before cleaning tower fill.
4. If tower approach is high at capacity, inspect fill, spray/nozzle
   distribution, louvers, drift eliminators, air recirculation, fan delivery,
   and water-treatment records.

### E. Fan short-cycling — TOWER-0003

1. Confirm independent motor starts and a complete warmed-up trailing hour.
2. Review leaving-water deadband, cell-stage sequence, and minimum on/off times.
3. If sequence corrections do not resolve it, inspect VFD/starter, overload,
   belt/gearbox, vibration switches, and proof chatter.

## Step 3 — Correct remotely where authorized

1. Remove only approved stale overrides and restore normal automatic ownership.
2. Correct wrong point/setpoint mapping before changing physical controls.
3. Tune fan minimum, cell staging, deadband, and minimum on/off timers against
   measured response and manufacturer limits.
4. Never remotely defeat a protective interlock or raise/lower a freeze limit
   merely to clear an alarm.

## Step 4 — Confirm resolution

1. Fan command and independent proof should agree after their configured
   direction-specific delays; cycling should remain below its warmed-up limit.
2. During normal mechanical heat rejection, leaving water should recover inside
   its active setpoint allowance without unnecessary loaded-fan persistence.
3. For degradation, compare approach/range and chiller kW/ton at matched load,
   flow, and weather over the next suitable operating period.
4. For freeze protection, follow the OEM/site commissioning procedure and verify
   water level, all safeties, independent electrical proof, and representative
   basin temperature. Do not close the finding solely because the graph cleared.
