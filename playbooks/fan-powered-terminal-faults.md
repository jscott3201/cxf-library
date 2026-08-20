# Playbook: Fan-Powered Terminal Faults

| | |
|---|---|
| **Applies to** | FPB-0001, FPB-0002, FPB-0003 |
| **Fix complexity** | Remote (45%) · On-site (55%) |
| **Typical time** | 10–30 min remote; 30 min–3 h on-site |
| **Typical cost** | $0 remote to site-specific fan, controller, damper, sensor, actuator, or valve repair |
| **Energy impact** | Terminal-fan waste, excess primary airflow, and hydronic reheat leakage; low airflow/fan failure may instead be delivery risk |

## Step 1 — Verify the fault

1. Identify series versus parallel topology from drawings and a walk-down. Do
   not infer subtype from a point name.
2. Confirm schedule, mode, final active airflow setpoint, AHU fan/static
   availability, overrides, freeze/condensate/smoke states, and maintenance.
3. For FPB-0001 compare the final same-fan command with independent proof. A
   series fan may run continuously occupied; a parallel fan may be off normally.
4. For FPB-0002 confirm the flow point is AHU-fed primary inlet flow, not total
   discharge or induced branch flow; verify units and K-factor.
5. For FPB-0003 confirm hydronic heat is available, airflow crosses the coil,
   and both temperatures are immediately around it. PFPU measurements must stay
   inside the fan/reheat branch before mixing.

## Step 2 — Remote triage

1. Release only documented BAS overrides and compare command, proof, airflow,
   setpoint, valve command, and coil temperatures on a common timestamp.
2. Check terminal controller mode, downloaded constants, airflow calibration,
   and the serving AHU's fan/static-reset state.
3. Trend one representative operating transition. Do not force a parallel fan
   on in a mode that intentionally leaves it off, and do not treat setpoint-ramp
   error as settled tracking.
4. If the valve reads shut but coil rise persists, inspect any available pipe
   temperatures and hot-water differential pressure before dispatch.

## Step 3 — On-site service

Only qualified HVAC/electrical/hydronic personnel following site lockout/tagout
and manufacturer procedures may open panels, approach rotating equipment, or
service valves. Never bypass smoke, freeze, condensate, electrical, or other
safeties to make a point agree.

1. Fan: inspect HOA/local ownership, relay/contactor, ECM/VFD faults, wheel,
   bearing, belt/coupling, and the independent proof device.
2. Primary airflow: inspect pickup tubing/ring, inlet obstruction, damper blade,
   linkage/actuator, controller K-factor, and available inlet static pressure.
3. Reheat: verify actuator stroke and linkage, valve close-off, seat debris,
   manual bypass/three-way piping, and unintended gravity circulation. Do not
   force a valve against freeze protection or a live safety sequence.
4. Reposition or replace mislocated sensors; a mixed PFPU discharge sensor is
   not a casual substitute for a branch-local coil outlet sensor.

## Step 4 — Confirm resolution

1. Under safe, representative automatic operation, confirm final fan command
   and proof agree through an allowed transition.
2. Confirm primary flow settles inside its commissioned band after the active
   target and serving AHU pressure settle.
3. With the hydronic valve legitimately shut and residual heat expired, confirm
   coil-local rise remains below threshold while branch airflow is proven.
4. Observe at least one normal occupied/heating transition for the actual
   subtype and verify the rule does not reassert.
