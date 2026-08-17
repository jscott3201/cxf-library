---
schema: cxf-library/fault-card/v1
id: RTU-FC-052
name: Discharge and mixed air temperature inconsistency (AFDD0)
equipment: rtu
status: verified
phase: 2
method: rule
severity: 3
category: COMFORT_ENERGY
confidence: LOW
estimation_method: QUALITATIVE_ONLY
source:
  - "HVAC FDD Reference v1.0 §11, RTU-FC-052"
  - "PNNL-23790 (AFDD0)"
  - "Schein et al. 2006"
g36: null
clusters: []
suppresses: [RTU-FC-051, RTU-FC-053]
suppressed_by: []
related: [RTU-FC-051, RTU-FC-053, AHU-FC-062]
playbooks: [sensor-drift]
operating_states: "all active modes — idle, mechanical cooling, and heating each get their own test"
preconditions: "Supply fan running and both sensors present; with the fan off there is no air to measure and the verdict is NO_EVAL, not healthy. The host must also hold evaluation off for min_stage_runtime (10 min) after any compressor or heater stage change, while the coil or heat exchanger is still coming up to temperature and the two sensors legitimately disagree with the new state."
points:
  - sat
  - mat
  - comp_status
  - htg_status
outputs:
  - name: yFault
    description: True while the supply/mixed air temperature relationship has contradicted the compressor and heater state for at least alarm_delay
params:
  consistency_threshold:
    default: 3.0
    unit: "°C"
    description: Maximum |sat − mat| tolerated with no compressor and no heat running; covers combined sensor accuracy plus fan heat
    cxf: idleDev.t
  cooling_direction_threshold:
    default: 1.0
    unit: "°C"
    description: How far supply air may rise above mixed air with a compressor running before the cooling direction counts as contradicted
    cxf: coolDir.t
  heating_direction_threshold:
    default: 1.0
    unit: "°C"
    description: How far supply air may fall below mixed air with heat energized before the heating direction counts as contradicted
    cxf: htgDir.t
  alarm_delay:
    default: 1800.0
    unit: s
    description: Continuous inconsistency required before the alarm asserts (30 min)
    cxf: persist.delayTime
energy_impact:
  affected_subsystem: RTU temperature sensing — prerequisite gate, no load of its own
  savings_range: sensor-dependent; gates the other RTU diagnostics
  climate_sensitivity: neutral
  runtime_estimation: "none in-rule; the reference points at Energy Impact Reference §4.4. A wrong sat or mat costs whatever the diagnostics and control loops downstream do with the bad number"
emissions:
  scope: "1|2"
  method: QUALITATIVE_EMISSIONS
verified:
  engine_rev: e2ff2f8
  content_id: "cxf:fnv1a128:bbf281b458fc8b62a9a6634ae288429e"
  date: 2026-08-17
---

## Description

Air leaving a rooftop unit has to be explained by what the unit is doing.
With no compressor and no heat, supply air should arrive at the mixed-air
condition give or take fan heat and sensor error. With a compressor running it
must be colder than the mixture. With gas or electric heat energized it must be
warmer. Half an hour of the temperatures saying otherwise means either a sensor
is lying or the equipment is not doing what its status point claims.

This is PNNL's AFDD0 (PNNL-23790), the prerequisite the rest of the RTU chapter
is built on: the diagnostics it gates read the same two sensors it is checking,
so their verdicts are worth nothing while it is active. It is the RTU analog of
AHU-FC-062, and the two divide the sensor-integrity work differently.
AHU-FC-062 checks containment — mixed air between outdoor and return air — a
relation that holds in every operating state and needs no equipment status at
all. This rule checks direction, and direction depends on what is running, so
it takes compressor and heater status as inputs and carries a different test
per state. The RTU chapter uses both: RTU-FC-054 and RTU-FC-055 are gated
behind AHU-FC-062 instantiated on the RTU's own `mat`/`oat`/`rat`, while this
rule needs only the two temperatures and the status a packaged unit already
reports. Prevalence is roughly 15% of units.

## Detection Logic

```
dev_sm = sat − mat
idle   = NOT comp_status AND NOT htg_status

yFault = ( idle        AND |dev_sm|      > consistency_threshold       )
      OR ( comp_status AND  dev_sm       > cooling_direction_threshold )
      OR ( htg_status  AND  (mat − sat)  > heating_direction_threshold ),
         sustained for alarm_delay
```

Block graph (`rule.cxf.jsonld`):

![RTU-FC-052 block graph](diagram.svg)

Three branches, each a `Logical.And` of an equipment state against a
temperature test, ORed together and held by `persist`. `devSM` computes
`sat − mat` and fans out twice: through `absDev` to the idle branch, which cares
only about the magnitude of the disagreement, and straight into `coolDir`,
which cares about its sign. `devMS` computes the opposite difference for the
heating branch. All three comparisons are strict `>` against positive
thresholds, so a deviation sitting exactly on any of them reads healthy: 3.0 °C
while idle is not a fault, 3.1 °C is.

The state gating is what makes the branches safe to OR. A 12 °C spread between
supply and mixed air is a gross violation when nothing is running and the
expected result when the compressor is on; `idle` (both `Not`s ANDed) holds the
idle branch off in every active mode, so the same numbers cannot be read by two
branches with opposite expectations. `persist` requires 30 continuous minutes
and resets on any tick where no branch is violated, which is what rides out the
pull-down after a stage start. A violation that hands off from one branch to
another inside a single tick does not reset it — the timer sees an unbroken
contradiction, which is the right reading of the physics but also why the
host's `min_stage_runtime` precondition earns its keep: the minutes right after
a stage change are when a lagging sensor is most likely to carry a stale
disagreement across the handoff.

## Possible Diagnoses

1. `sat` or `mat` sensor out of calibration
2. Supply air temperature sensor in the wrong location — reading a stratified
   slice of the discharge, or radiant heat from the heat exchanger rather than
   the air stream
3. Compressor running with no refrigerant flow: lost charge, failed compressor,
   or a stuck reversing valve on a heat pump
4. Heater energized with no heat output: failed ignition, tripped high-limit,
   closed gas valve, or an open electric heat element
5. Sensor wiring: swapped `sat` and `mat` leads, a shorted or open sensor, or a
   status point wired to the wrong stage

## Energy Impact

COMFORT_ENERGY, LOW confidence, QUALITATIVE_ONLY. Nothing here is directly
computable: a mis-read temperature burns no fuel by itself, and a compressor
running without refrigerant burns plenty but this rule cannot say how much
without capacity data it does not have. PNNL EEM-01 (sensor recalibration)
covers the sensor half at 0–5% of site energy across a whole sensor population.
The honest accounting matches AHU-FC-062's: the value of this rule is the
accuracy it restores to RTU-FC-051 and RTU-FC-053, both of which read the same
two sensors, plus the mechanical failures it catches on the way — a compressor
drawing full power and moving no heat is the most expensive thing on this list
and the least likely to be noticed from the zone until the space gets warm.

## Emissions Impact

QUALITATIVE_EMISSIONS, LOW confidence. Scope is recorded as `1|2` because it
depends on which half of the unit is wrong: a heating branch violation on a
gas-fired RTU points at scope 1 combustion, a cooling branch violation at scope
2 electricity, and an idle violation at whichever subsystem the bad reading
later misdirects. Avoided-emissions basis: N/A.

## Deviations

- **Two `Subtract` blocks rather than one difference and a negation.** The
  reference states the heating test as `mat − sat` against its threshold, which
  is `−dev_sm` compared to a positive number. CDL has no unary negate, so the
  alternatives were a `MultiplyByParameter` with `k = −1` or a second
  subtraction. This library keeps negative parameter values out of rule
  documents (precedent: AHU-FC-055's `designConst`), and a second `Subtract` is
  also the plainer read of the card's own wording. Algebraically identical.
- **Three independent thresholds, two of which default to the same number.**
  `cooling_direction_threshold` and `heating_direction_threshold` are both
  1.0 °C, and one shared parameter on both paths would have been smaller. They
  stay separate because the reference lists them separately and because the two
  are not the same physical quantity — the cooling side is bounded by
  evaporator approach, the heating side by heat exchanger effectiveness, and a
  host tuning one has no reason to move the other.
- **`min_stage_runtime` is a host precondition, not a block.** The reference
  requires 10 minutes of stage runtime before evaluating. That is an
  operating-state gate on a transition the rule cannot see (the block graph has
  status, not stage-change history), and this library keeps state gating
  host-side — the treatment the G36-derived AHU rules give ModeDelay
  (AHU-FC-012, -014, -015). It is declared in
  `preconditions`. The 30-minute persistence does not substitute for it: a
  unit that stages up and stays up trips the timer from the moment of the
  change, so `alarm_delay` only covers the transient if the transient is
  shorter than 30 minutes, which for a cold coil in a hot plenum it usually is
  but not always.
- **Fan-running is a precondition too.** With the fan off both sensors read
  stagnant air in different parts of a cabinet and the comparison means
  nothing. Host-gated, per the design stance.
- **Suppression is declared, not encoded.** The reference's note — "when
  active, suppresses RTU-FC-051 and RTU-FC-053" — lives in `suppresses` and is
  enforced by the host. The engine is status-blind and each rule is an
  independent composite, so the block graph cannot express it. Same treatment
  as AHU-FC-062, whose CLU-09 role this rule plays for the RTU chapter without
  being a cluster member: the reference defines no RTU sensor-integrity cluster
  and `clusters` is therefore empty rather than reusing an AHU cluster ID.
- **Simultaneous heating and cooling is reported, not refereed.** With both
  statuses true the idle branch is held off and both directional branches
  evaluate, so whichever direction the temperatures contradict raises the
  alarm. A unit heating and cooling at once is already broken, and this rule
  makes no attempt to decide which half is at fault — the vectors pin the
  behavior (`simultaneous_heating_and_cooling`), and the diagnosis belongs to
  whoever opens the panel.
- `persist.delayOnInit = true` (CDL default is `false`), the library's standing
  choice: an inconsistency already present when the controller starts waits out
  the full 30 minutes rather than alarming on the first tick.

## Notes

The suppression contract is the point of this card. While `yFault` is true,
RTU-FC-051 (evaporator coil fouling) and RTU-FC-053 (economizer not modulating)
are computing on numbers known to be wrong, and the host must report them as
NO_EVAL rather than healthy — a silenced rule is not a passing rule. RTU-FC-051
consumes `sat` directly in its temperature split, and its whole verdict is a
ratio against an 8 °C baseline: a 3 °C bias on that one sensor moves the ratio
by 37 percentage points, which is the entire distance from a clean coil to an
alarm.

The rule deliberately cannot tell a sensor fault from a mechanical one, and the
diagnosis order that follows from that is worth stating: check the sensors
first, because it is the cheap end. Two thermometers and ten minutes will tell
you whether `sat` and `mat` agree with reality, and the
[sensor-drift](../../../playbooks/sensor-drift.md) playbook covers the fix
($30–$80 for a replacement temperature sensor). Only once both sensors read
true does the alarm point at diagnoses 3 and 4, and then it means a compressor
or a heater is running and producing nothing — a service call, not a
calibration.
