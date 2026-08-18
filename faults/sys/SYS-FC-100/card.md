---
schema: cxf-library/fault-card/v1
id: SYS-FC-100
name: Sensor flatline while equipment active
equipment: sys
status: verified
phase: 3
method: rule
severity: 3
category: PROTECTIVE
confidence: LOW
estimation_method: QUALITATIVE_ONLY
source:
  - "Accepted design: _research/fc100-sensor-health-design.md — §1 (the flatline shape and its activity gate), §2 (why a physical-plausibility rule does not break the fault-given-valid-data stance), §2.3 (the adjudicates contract), §4.3 (Discrete.Sampler mechanics and the MovingAverage rejection), §4.4 (the flatline vector strategy this card's scenarios follow)"
  - "Yang, H., Cho, S., Tae, C.-S., Zaheeruddin, M. (2008). Sequential rule based algorithms for temperature sensor fault detection in air handling units. Energy Conversion and Management 49(8), 2291-2306. doi:10.1016/j.enconman.2008.01.029 — rule-based temperature-sensor FDD validated on real AHUs; the source of the isolation argument this card's adjudicates verdict rests on"
  - "Liao, H., Cai, W., Cheng, F., Dubey, S., Rajesh, P. B. (2021). An Online Data-Driven Fault Diagnosis Method for Air Handling Units by Rule and Convolutional Neural Networks. Sensors 21(13), 4358. doi:10.3390/s21134358 — published evidence that a cheap deterministic sensor layer under a heavier diagnostic layer works in the field"
  - "Dey, D., Dong, B. (2016). A probabilistic approach to diagnose faults of air handling units in buildings. Energy and Buildings 130, 177-187. doi:10.1016/j.enbuild.2016.08.017 — the motivation stated negatively: a satisfied equipment rule cannot separate a real fault from a sensor fault after the fact"
  - "Library-authored: the HVAC FDD Reference v1.0 specifies no flatline rule in any chapter. Name, severity 3 and method: rule are faults/sys/README.md's; everything else is argued on this card"
  - "Sibling precedent: AHU-FC-057 (the Discrete.Sampler baseline plus flatness dwell this graph reuses), AHU-FC-062 and RTU-FC-052 (physical-plausibility rules the library already ships), VAV-FC-050 (the per-binding placeholder parameter convention)"
g36: null
clusters: [CLU-09]
suppresses: []
suppressed_by: []
adjudicates:
  points: [sensor_value]
  verdict: invalid_while_active
related: [SYS-FC-054, SYS-FC-101, AHU-FC-062, RTU-FC-052]
playbooks: [sensor-drift]
operating_states: "all — the rule evaluates only while equip_active is true, and its own yWindowOk reports whether a complete window of running time has accumulated"
preconditions: "Host delivery quality must be resolved before this rule runs, and this is the load-bearing precondition rather than boilerplate: a value the host is re-serving from cache because the subscription died presents to the graph as a perfectly frozen sensor, and the rule will report flatline and be right about the number it was given and wrong about the transmitter. Freshness, PointStatus and gap handling stay where the reference's ch.4 puts them — host-side, ahead of this rule (design doc §2.2). sensor_value must be bound to a live measurement: a setpoint, a configured constant, a schedule output or a host-derived aggregate that only refreshes hourly will all read as flatline and none of them is a sensor. equip_active must be bound to the run status of the equipment whose process actually drives the bound sensor — sf_status for an AHU supply-air temperature, comp_status for a suction line, pump_status for a loop reading. A VAV box has no run status of its own; bind the parent AHU's fan status or zone_airflow > 0 and record which. Both flatline_band and flatline_window are per-binding site configuration in the bound point's units and MUST be set for this instance before the rule is trusted; the shipped defaults are a worked example for a supply-air temperature, not a site value. Where yWindowOk is false the verdict is NO_EVAL, not a healthy sensor."
points:
  - sensor_value
  - equip_active
outputs:
  - name: yFault
    description: True while the bound sensor has stayed within flatline_band of its window baseline continuously for flatline_window of running time, and has then held that condition for a further alarm_delay. While true, the host treats sensor_value as invalid for every rule bound to this equipment instance that consumes it (see adjudicates)
  - name: yWindowOk
    description: Evaluability signal — true once equip_active has been continuously true for a full flatline_window, which is the shortest run the rule can form any verdict from. False means NO_EVAL, never a healthy sensor
params:
  flatline_band:
    default: 0.25
    unit: "varies (the bound point's units)"
    description: "How far the reading may travel from its window baseline and still count as not moving. PER-BINDING SITE CONFIGURATION, in the units of whatever real point sensor_value is bound to — the VAV-FC-050 ventilation_requirement convention. The shipped 0.25 is the worked example for sensor_value := sat on an AHU (0.25 °C: above the 0.1 °C quantum most BAS report a duct temperature at, well below the 1-3 °C a controlled supply-air temperature travels in two hours). It is meaningless on any other quantity — see Deviations for the duct-static counter-example and for which direction each mis-tuning fails in."
    cxf: stillBand.t
  flatline_window:
    default: 7200.0
    unit: s
    description: "How long the reading must stay inside the band, measured in running time, before the rule believes the sensor rather than the process. ADOPTED at 2 h and argued in Deviations; tune within roughly 1-4 h per binding. One card parameter binds three block parameters — the sampler that produces the baseline and both dwell timers — and hosts must set all three together."
    cxf: [sensRef.samplePeriod, stillHeld.delayTime, windowOk.delayTime]
  alarm_delay:
    default: 900.0
    unit: s
    description: "Further continuous persistence after the window completes, before the alarm asserts (15 min). The retuning knob for alarm hygiene, kept separate from flatline_window because that parameter also sets the baseline's re-arm period and cannot be moved for reporting reasons alone."
    cxf: persist.delayTime
energy_impact:
  affected_subsystem: Sensor integrity gate — the equipment the bound point serves
  savings_range: "sensor-dependent; the value delivered is preserved diagnostic coverage and avoided false findings, not energy"
  climate_sensitivity: neutral
  runtime_estimation: "none — a frozen transmitter wastes nothing by itself. The cost is the fan-out: while this fault is active every rule bound to sensor_value on this equipment instance is reading a fiction, and the equipment faults hiding behind it accrue their own waste unobserved. Attribute the energy to the rules this one adjudicates, as AHU-FC-062 does"
emissions:
  scope: "1|2"
  method: QUALITATIVE_EMISSIONS
verified:
  engine_rev: e2ff2f8
  content_id: "cxf:fnv1a128:e9b6eca9434e06c98d3fbdf289ffa6c6"
  date: 2026-08-17
---

## Description

A transmitter that has stopped reporting change is the quietest failure in a
building. Nothing alarms, no zone complains, the trend line is beautifully
smooth, and every rule downstream of that point keeps producing verdicts from a
number that stopped being a measurement weeks ago. A frozen sensor element, a
controller holding a last-known-good value, a point re-served from cache after a
subscription died — all three present identically: zero variance under a load
that should be producing some.

This rule is the library's first *meta-rule*. Its `yFault` is a claim about a
point rather than about a machine, and its `adjudicates` frontmatter names that
point so the host can take it out of service for every other rule bound to the
same equipment instance. That is the whole reason to write it: Dey & Dong (2016)
layer a Bayesian network over APAR precisely because a satisfied equipment rule
cannot separate coil fouling from a temperature-sensor bias after the fact, and
the cheaper answer is to detect the sensor case directly and remove it from the
candidate set before the equipment rules are read at all.

Writing it does not break the library's stance, for the reason the design doc
§2 works through and this card states in brief: *delivery* quality — did a
sample arrive, when, and what did the field bus say about it — stays host-side
and is untouched by this rule, which in fact depends on the host having settled
it first. What lands in the graph is *physical plausibility*: the sample arrived
on time, with clean status, and it is wrong. The library already ships two rules
of exactly that kind, AHU-FC-062 and RTU-FC-052, and nobody argued they broke
anything. This is the third, generalized across equipment.

It is library-authored. The HVAC FDD Reference specifies no flatline rule in any
chapter; the shape, both thresholds and the evaluability output are argued here
and grounded in the accepted design plus Yang et al. (2008) and Liao et al.
(2021), which put a deterministic sensor-rule layer under a heavier diagnostic
one and reported it working on real air handlers.

The rule binds **role points**, not canonical ones. `sensor_value` and
`equip_active` are whatever the host's instance configuration says they are for
this deployment — that is the documented exception in SCHEMA.md's points
contract, and the same binding record is what resolves the `adjudicates` target
and drives the NO_EVAL fan-out.

## Detection Logic

```
baseline   = Sampler(sensor_value, flatline_window)   (re-arms once per window)
still      = |sensor_value − baseline| < flatline_band

yWindowOk  = equip_active held continuously for flatline_window
                                            (false ⇒ host reports NO_EVAL)
yFault     = (still AND equip_active) held continuously for flatline_window,
             then sustained a further alarm_delay
```

Block graph (`rule.cxf.jsonld`):

![SYS-FC-100 block graph](diagram.svg)

Eight blocks. `sensRef` is a `Discrete.Sampler` on the window period, so the
comparison is always against where the reading sat at the start of the current
window; `dev`/`devAbs`/`stillBand` turn that into "has not moved much". The
`Reals.LessThreshold` is strict, so a deviation of exactly `flatline_band` reads
as *moving* and the rule stays silent — the standing convention in this library
since PMP-FC-050, and pinned here from three sides
(`band_edge_exactly_on_the_line`, `band_edge_a_hair_under`,
`band_edge_a_hair_over`).

The activity gate sits **inside** the dwell rather than after it. `equip_active`
is one leg of `stillAndActive`, so `flatline_window` is a window of *running*
time: a plant that stops discards the elapsed time instead of pausing it, which
`equipment_stop_restarts_the_window` pins by putting a 10-minute stop at 5400 s
and landing the alarm a full window plus `alarm_delay` after the restart.
That is the honest reading of the fault. A flat signal on idle equipment is not
evidence of anything — it is what an idle duct is supposed to look like — so the
minutes it accumulates must not count.

`windowOk` is the second consumer of `equip_active` and the rule's NO_EVAL
story. It is not an echo of the boundary input: it asserts only once the
equipment has run continuously for a full `flatline_window`, which is the
shortest run this rule can form any verdict from. Below that, `yFault = false`
means the question has not been asked yet, and the host must not read it as a
healthy sensor. The invariant runs one way only: a true `yFault` implies a true
`yWindowOk` (`frozen_sensor_with_equipment_running` has the evaluability output
rise a window ahead of the alarm), and the reverse does not hold —
`equipment_stops_one_tick_after_the_window_tick` sets `yWindowOk` for exactly one
tick while `yFault` never fires at all.

**The worked example, for one concrete binding.** Take `sensor_value := sat` and
`equip_active := sf_status` on an air handler. `flatline_band = 0.25 °C` sits
above the 0.1 °C quantum most BAS report a duct temperature at — demanding
bit-identical samples finds nothing, because a real transmitter in a stable duct
still has quantisation noise — and well below the one to three degrees a
controlled supply-air temperature travels across two hours of occupied
operation. `flatline_window = 7200 s` is comfortably inside a single occupied
period, so the rule gets six complete windows out of a 06:00-18:00 schedule
rather than one. At those numbers a `sat` that has not moved a quarter of a
kelvin while the supply fan ran for two hours is a stuck reading, and the alarm
lands 15 minutes later. **Every other binding needs its own two numbers**; the
Deviations section works the arithmetic on why, and in which direction each
mis-tuning fails.

`persist` (15 min) is the only knob a host should touch for reporting reasons.
`flatline_window` is bound to three block parameters at once — the sampler
period and both dwell timers — because they express one physical quantity and
must move together.

## Possible Diagnoses

Library-authored; no published diagnosis list exists for this shape.

1. Failed sensing element. A thermistor or RTD whose element has opened or
   shorted into a fixed reading, or a transducer whose diaphragm has seized. The
   diagnosis the rule is named for and the only one whose repair is a part
2. Failed or saturated A/D channel on the controller. The element is fine; the
   input is not. Distinguishable on site in minutes by moving the sensor to a
   spare input
3. A controller holding last-known-good. Many BAS substitute the previous value
   on a read failure rather than flagging the point, which converts a comms
   fault into a perfect flatline that looks like hardware
4. A point re-served from cache after a lost subscription. The design doc's
   layering exists for this case: the host is supposed to catch it as a delivery
   fault before the rule ever sees it, and where the host does not, this rule
   reports flatline and cannot tell the difference (see Deviations)
5. A manual override or hand mode left on the point itself — an operator or a
   commissioning agent who wrote a fixed value into the object and never cleared
   it. Costs nothing to check and is the most common finding on a new deployment
6. A sensor installed where nothing happens. A duct probe in a dead leg, an
   immersion well without paste, a space sensor behind a closed door: the element
   works, the reading is real, and it genuinely never moves. The repair is
   relocation, and the rule is right to report it
7. Genuinely stable process. The false-positive case, and the one the thresholds
   exist to hold off — a tight loop on a light load can sit still for two hours.
   Raising `flatline_window` is the correct response; raising `flatline_band` is
   not, and makes the rule worse in both directions

## Energy Impact

PROTECTIVE, LOW confidence, QUALITATIVE_ONLY. There is no waste term. A frozen
transmitter burns nothing; what it costs is the diagnostic coverage of every
rule that reads it, and that cost is only realized as energy through the faults
it hides. AHU-FC-062 set this accounting convention — the value of a sensor gate
belongs to the rules it gates — and this card follows it rather than inventing
a savings range for a fault that has none.

The fan-out is the number that matters and it is per-instance. A flatlined `sat`
takes out the supply-air-temperature control rules, the reset rules and the
economizer's downstream checks on that one air handler. A flatlined `oat` on a
site that binds one outdoor sensor to six pieces of equipment takes out
considerably more. Neither is enumerated on this card, and deliberately so: the
host computes the closure from the `points` lists every card already carries,
which is exactly why `adjudicates` is keyed to the point rather than to a
hand-written rule list.

Confidence is LOW for two reasons and both are honest. The evidence is direct —
the rule reads the point it accuses — but diagnosis 6 and diagnosis 7 are real
and the rule cannot separate a stuck transmitter from a well-sited one watching
a genuinely still process. And the thresholds ship as placeholders: a deployment
that has not set them for its binding is comparing against a supply-air
temperature's numbers, which is not evidence at all.

## Emissions Impact

Scope 1 or 2 depending on what the adjudicated point serves, QUALITATIVE_EMISSIONS,
LOW confidence. Same argument as the energy claim: no direct term, and the
avoided emissions belong to whichever rules were restored to service when the
sensor was repaired. AHU-FC-062's `1|2` scope assignment is the precedent and
the reason for it is the same — a bad temperature can be hiding a gas-fired
heating fault or an electric cooling one, and the rule does not know which.

## Deviations

- **Library-authored, not a transcription.** The HVAC FDD Reference specifies no
  flatline rule in any chapter, so there is no reference algorithm to deviate
  from and no published test vectors to reproduce. The ID, the name, severity 3
  and `method: rule` are `faults/sys/README.md`'s; the graph, both thresholds,
  the evaluability output, the diagnosis list and all fourteen scenarios are
  argued on this card. Grounding is the accepted design plus Yang et al. (2008)
  and Liao et al. (2021).
- **The stance, in brief.** `yFault` here is a claim about data validity, which
  looks like a violation of *the graph computes fault-given-valid-data, and only
  that*. It is not, because two different things get called data quality.
  Delivery quality — arrival, `PointStatus`, gaps — stays host-side and is
  untouched; the graph is still emitting a boolean computed from its declared
  inputs, with no status, no staleness and no tri-state. Physical plausibility —
  the sample arrived clean and is wrong — is a property of the signal and a
  fault of a piece of equipment, because a sensor is equipment. AHU-FC-062 and
  RTU-FC-052 are the precedent (design doc §2).
- **The rule depends on host delivery quality and cannot substitute for it.**
  This is the load-bearing claim that keeps the layering acyclic, and it is
  stated in `preconditions` as well because it is the one way a deployment can
  make this card lie. Fed a value the host held over from a dead subscription,
  the rule reports flatline: right about the number it was given, wrong about the
  transmitter. It does not try to tell those apart, and the host must resolve
  staleness and gaps **before** this rule runs.
- **`adjudicates: {points: [sensor_value], verdict: invalid_while_active}`.**
  The verdict is `invalid_while_active` rather than `ambiguous` because this rule
  reads exactly one sensor and accuses exactly that one — there is no second
  member to be confused with, which is the difference between this card and
  SYS-FC-054. `equip_active` is consumed but **not** adjudicated: the rule says
  nothing about whether the run status is telling the truth, and listing it would
  claim an authority the graph does not have. The fan-out is not enumerated
  anywhere on this card by design; the host computes it as the rules on this
  equipment instance whose `points` intersect `adjudicates.points`, so it stays
  complete as rules are added. AHU-FC-062's hand-written `suppresses` list is the
  counter-example that motivated the field: correct today, and silently
  incomplete the first time someone authors a rule that reads `mat`.
- **`suppresses: []` and `suppressed_by: []`, and the second one is normative.**
  A card carrying `adjudicates` must not appear in any other card's
  `suppresses`: letting an equipment fault silence the sensor rule that
  invalidates it is a cycle with a wrong answer at both ends (design doc §2.3).
  `suppresses` is empty for a different reason — `adjudicates` is what this rule
  does instead, and the two fields are not interchangeable. `suppresses` says the
  silenced rule's verdict is true but redundant; `adjudicates` says the consuming
  rules' verdicts are meaningless, and per the reference's own gap handling their
  rolling state should be reset as well. Whose job that reset is remains an open
  question in the design doc §6 and is not settled here.
- **`equip_active` gating is in-graph, and the evaluability output is a dwell
  rather than an echo.** The design doc's second normative constraint asks for a
  `y…Ok` boundary output where the rule needs a second signal to be evaluable,
  and this card emits one — but a straight passthrough of a boolean boundary
  input would carry no information the host does not already have, and
  HW-FC-054's deviation on `yMildWeather` is explicit that such an output should
  be a computation rather than an echo. So `yWindowOk` is `equip_active` held for
  a full `flatline_window`: true exactly when the rule has had enough continuous
  running time to have a verdict at all. The gating itself is separately in the
  graph, inside the dwell, because the window must be a window of running time.
- **Both thresholds ship as per-binding placeholders, and the units are the
  bound point's.** This is the cost of the `sys` family paid out loud: one graph
  deploys against many real points, and a threshold in the role's units is not a
  number. VAV-FC-050's `ventilation_requirement` is the precedent for shipping a
  parameter that a host must set before the rule means anything. The worked
  example in Detection Logic is `sensor_value := sat`, where 0.25 °C over 2 h is
  a defensible pair. The counter-example that makes the point bite: bind the same
  rule to a duct static pressure and 0.25 Pa is *below* the noise floor of every
  transducer on the market, so `still` would essentially never be true and the
  rule would sit silent forever while reporting nothing wrong. That binding wants
  something nearer 5 Pa. The two failure directions are not symmetric — a band
  set too small produces silent misses, a band set too large converts a slowly
  moving healthy sensor into a flatline finding — and only the second one is
  visible from the alarm list.
- **`flatline_window = 7200 s` is ADOPTED, and short by this family's
  standards.** AHU-FC-057 uses a seven-day window for the same sampler-and-dwell
  structure, and copying it here would be wrong for three reasons. The activity
  gate is the decisive one: `flatline_window` is measured in *continuous running
  time*, and a scheduled air handler never runs for a week, so a multi-day window
  would simply never mature on the equipment this rule most needs to watch. Two
  hours fits inside a single occupied period with room to spare and matures six
  times over a 06:00-18:00 schedule. Second, the faults differ in kind: a reset
  sequence that was never programmed is a configuration fault whose evidence is
  statistical and accumulates over weeks, while a transmitter that has stopped
  moving is hardware, and every hour it goes unreported is an hour of blinded
  diagnostics on everything downstream — the fan-out is the argument for
  detecting fast. Third, above roughly four hours the window starts to exceed the
  uninterrupted run of ordinary scheduled plant, which is the practical ceiling
  on tuning it upward. The floor is diagnosis 7: below about an hour a tight loop
  on a light load will sit still legitimately.
- **`Discrete.Sampler`, not `Reals.MovingAverage`, and not `Reals.Derivative`.**
  Engine-verified at the pin. `MovingAverage` keeps a fixed 64-checkpoint ring,
  which imposes a minimum tick interval of `window/64` — 112.5 s for a two-hour
  window — and degrades silently rather than failing when a deployment ticks
  faster; AHU-FC-057 rejected it for the same reason and said so.
  `Reals.Derivative` is forbidden in this family outright: its `k` and `T` are
  input pins rather than parameters, and its implicit-Euler discretisation biases
  a ramp reading by a factor of `(1 + dt/T)`, which at a 300 s tick with
  `T = 300 s` reports twice the actual slope. The sampler is exact at any tick
  rate.
- **`Discrete.Sampler` emits the live input on its first tick, and that is
  pinned by an arrival time rather than asserted in prose.** The block's
  uninitialised branch returns the current reading, so there is no startup
  artifact of the kind `Discrete.UnitDelay` produces with `y_start = 0` (which is
  SYS-FC-101's problem, not this card's). The observable consequence is in
  `frozen_sensor_with_equipment_running`: the alarm lands at 8100 s, which is
  `flatline_window + alarm_delay` measured from t = 0 and is only reachable if
  the first baseline was the live 14.0. Had the first baseline been 0.0, the
  deviation would have read 14.0 until the t = 7200 s re-arm and the alarm would
  have landed at 15300 s instead. The scenario's `yFault` window separates those
  two arrival times by a full window.
- **The sampler grid is anchored to absolute model time, not to controller
  start.** The first sample instant is `floor(t_start/period)·period`, so a rule
  loaded at t = 137 s with a two-hour period takes its first grid instant at
  t = 0 and its next at 7200 s, not at 137 s and 7337 s. It does not change the
  verdict — the initial tick seeds the baseline from the live input regardless —
  but it does mean the vectors' `step_s` must divide `flatline_window`, and 300 s
  into 7200 s is why the clock is what it is.
- **The baseline re-arms every window, and that has two consequences worth
  stating.** First, at every sample instant the block emits the live input, so
  the deviation is exactly zero on that tick no matter how hard the signal is
  moving — a wildly moving reading shows a burst of apparent stillness after each
  re-arm. It cannot mature into a fault because the dwell needs a full window and
  the burst is bounded by the grid, and `rearm_stillness_never_matures` pins it.
  Second, a sensor that freezes partway through a window is not detected until
  the *next* re-arm re-baselines onto its stuck value, because until then the
  deviation is the size of the jump. Worst-case time to alarm from the moment of
  failure is therefore `2 × flatline_window + alarm_delay`, not
  `flatline_window + alarm_delay`; `signal_moves_one_tick_after_maturity` shows
  the mechanism, with the rule blind from the 8400 s jump until the 14400 s
  re-arm.
- **A slow drift reads as a flatline, and this is pinned rather than hidden.**
  The rule tests displacement from a baseline, so any reading moving slower than
  `flatline_band` per `flatline_window` satisfies it — a sensor drifting 0.1 °C
  per hour against a 0.25 °C band over two hours is reported as flatlined.
  `slow_drift_reads_as_flatline` pins that behaviour deliberately. It is not a
  false positive in the sense that matters — a supply-air temperature moving 0.2
  degrees in two hours while the fan runs is a sensor finding either way — but
  the *name* on the finding is wrong, and this rule cannot supply the right one.
  Naming drift is SYS-FC-054's job, which is the design doc's argument for why
  all three shapes are needed rather than two. A host running both should read a
  simultaneous SYS-FC-100 and SYS-FC-054 as drift, not as two faults.
- **Strict `<` on the band, pinned on the line and from both sides.** CDL
  `Reals` has no `LessEqual`, and the disagreement is measure-zero on a
  real-valued signal, so the comparison errs toward silence: a deviation of
  exactly `flatline_band` counts as movement. The three edge scenarios use dyadic
  values (14.0 against 14.25) so that the difference is exactly 0.25 in IEEE-754
  and the "on the line" case really is on the line rather than a rounding error
  away from it — a detail that matters more than usual here, because 14.2 − 14.0
  is *not* 0.2 in double precision and a naively written edge vector would have
  pinned the wrong side of its own threshold.
- **`delayOnInit = true` on all three `TrueDelay`s** (the CDL default is
  `false`), the library's standing choice. A controller restarting onto an
  already-frozen sensor waits out the full window rather than alarming on the
  first tick, and `windowOk` likewise refuses to claim a complete window it did
  not observe.
- **`TrueDelay` asserts at exactly `T + delayTime`,** so the realized test is
  "still and running for strictly more than the window, then strictly more than
  `alarm_delay`" at tick resolution. Four scenarios pin both delay edges from
  both sides: `signal_moves_on_the_maturity_tick` and
  `signal_moves_one_tick_after_maturity` for `persist` (the second asserting for
  exactly one tick at 8100 s), `equipment_stops_on_the_window_tick` and
  `equipment_stops_one_tick_after_the_window_tick` for the two window timers.
- **`alarm_delay` is a separate parameter from `flatline_window` on purpose.**
  It would be defensible to let the window be the whole persistence and drop the
  second timer; it is kept because the two numbers answer different questions.
  `flatline_window` is a physical claim about how long the bound process can
  legitimately sit still, and it also sets the baseline's re-arm period, so a
  host cannot shorten it for alarm-hygiene reasons without changing what the rule
  measures. `alarm_delay` is the knob that can move freely, and it is where every
  other card in this library puts the same control.
- **`clusters: []`, flagged not edited.** CLU-09 (Sensor Integrity Failure) is
  where this card belongs — its playbook is `sensor-drift`, its members are
  SYS-FC-054 and SYS-FC-055, and the design doc §3 notes that if the FC-100
  family lands, the cluster's trigger is arguably one of these rules and
  AHU-FC-062 becomes a member. `clusters/clusters.json` is a single-writer file
  and the design doc's instruction is to flag rather than edit, so this card
  claims no membership it is not listed for. Same for
  `playbooks/sensor-drift.md`, whose Applies-To row names SYS-FC-054 and
  SYS-FC-055 and not this card: the playbook's four steps apply to this finding
  as written, and adding the ID is the playbook owner's edit.
- **`category: PROTECTIVE`, which departs from the two precedent sensor gates.**
  AHU-FC-062 and RTU-FC-052 are both `COMFORT_ENERGY`, and consistency with them
  is the honest counter-argument. The design doc §6 leaves the choice open and
  calls this option the most honest and the least precedented, and it is taken
  here because the alternative misdescribes the card: there is no comfort effect
  and no energy term, the `energy_impact` block says so in as many words, and
  what the rule delivers is avoided false findings and preserved diagnostic
  coverage — which is what `PROTECTIVE` is for. Severity stays 3, matching both
  precedents and the chapter index, rather than being raised on fan-out grounds;
  the fan-out is real but it is the *host's* consequence of the verdict, not a
  property of the finding.
- **No published test vectors exist for this rule,** so all fourteen scenarios
  are authored, following the design doc §4.4's flatline list: the frozen signal
  asserting on schedule, a wobble under the band still asserting (the case that
  proves the band is not decorative), three sides of the band edge, the activity
  gate false, the re-arm blind spot, the slow-drift limit, and both delay edges
  on both timers.
- Operating states and preconditions are declared in frontmatter for host
  enforcement rather than encoded in the block graph, per the library's design
  stance.

## Notes

Read `yWindowOk` before reading `yFault`, and read `adjudicates` before doing
anything with either. A true `yFault` is not an instruction to dispatch a
technician and stop — it is an instruction to stop believing every other finding
on that equipment that touches the bound point, and the second half is worth
more than the first.

Check the cheap causes first. Diagnoses 3, 4 and 5 — a controller holding
last-known-good, a point re-served from cache, an override nobody cleared —
account for most of what this rule finds on a new deployment, cost nothing to
check from a desk, and all three are configuration rather than hardware. Only
once they are ruled out is the finding worth a truck.

Then look at where the sensor is before assuming the sensor is broken.
Diagnosis 6 is the one that survives recalibration: a probe in a dead leg or an
immersion well without heat-transfer paste reports a real temperature of a place
where nothing happens, and it will pass every bench test you give it. The tell
is a reading that is plausible and static while its neighbours move.

Tune the window, never the band, when the rule is too talkative. Raising
`flatline_band` widens what counts as "not moving" and pulls genuinely drifting
sensors into the finding, which makes the report noisier and less specific at
the same time. Raising `flatline_window` costs only detection latency, and this
family has latency to spare. See the
[sensor-drift](../../../playbooks/sensor-drift.md) playbook for the verification
and service workflow.
