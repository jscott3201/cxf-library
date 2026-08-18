---
schema: cxf-library/fault-card/v1
id: SYS-FC-101
name: Sensor spike / rate-of-change violation
equipment: sys
status: verified
phase: 3
method: rule
severity: 3
category: COMFORT_ENERGY
confidence: MEDIUM
estimation_method: QUALITATIVE_ONLY
source:
  - "Library-authored per the accepted sensor-health design: _research/fc100-sensor-health-design.md (§2 stance, §4.1-4.2 block choice, §4.4 vector strategy)"
  - "Yang, Cho, Tae, Zaheeruddin 2008, Energy Conversion and Management 49(8) 2291-2306, doi:10.1016/j.enconman.2008.01.029 — sequential rule-based temperature sensor fault detection in AHUs"
  - "Liao, Cai, Cheng, Dubey, Rajesh 2021, Sensors 21(13) 4358, doi:10.3390/s21134358 — a cheap deterministic sensor-rule layer under a heavier diagnostic layer"
  - "Dey & Dong 2016, Energy and Buildings 130 177-187, doi:10.1016/j.enbuild.2016.08.017 — the sensor-bias ambiguity this family removes before the equipment rules are read"
  - "Sibling precedent: AHU-FC-062 and RTU-FC-052 (physical-plausibility rules already shipping under the same stance), AHU-FC-057 (discrete baseline plus Subtract/Abs), VAV-FC-050 (per-binding placeholder parameter)"
  - "Engine pin e2ff2f8: crates/oce-blocks/src/discrete.rs (UnitDelay warmup and sample grid), logical_timing.rs (TrueDelay init branch)"
g36: null
clusters: [CLU-09]
suppresses: []
suppressed_by: []
adjudicates:
  points: [sensor_value]
  verdict: invalid_while_active
related: [SYS-FC-100, SYS-FC-054, AHU-FC-062, RTU-FC-052]
playbooks: [sensor-drift]
operating_states: "all — a step larger than the measured process can produce is implausible whether the equipment is running, idling, or off, and the rule takes no run-state conjunct (see Deviations)"
preconditions: "Delivery quality is resolved host-side before this rule runs, and this rule is unusually exposed to it: a value re-served from cache after a comms outage, a gap the host interpolated badly, and a poll interval that slipped all present as a sample-to-sample step that no graph reading one point can tell from a failing transmitter. The reference's ch.4 gap handling runs first and this rule sits on top of it — it is right about the number it was given and says nothing about how the number arrived. sample_period MUST equal the host's tick interval: the rule is written for, pinned at, and only means what it looks like it means at one sample of lookback (see Deviations). history_warmup MUST be set to exactly twice sample_period and re-set with it; it is not an independent tunable. max_step_per_sample is a per-binding number in the bound point's units, and the shipped default is a worked example for sensor_value := sat at a 60 s tick, not a site value — deployed unretuned on a pressure, flow, humidity or CO2 point it is comparing against an arbitrary number. Read yHistoryOk before yFault: while it is false the delay line still holds its y_start seed, and the verdict is NO_EVAL rather than a healthy sensor."
points:
  - sensor_value
outputs:
  - name: yFault
    description: True on each tick where the reading moved further from the previous sample than max_step_per_sample, once the startup inhibit has expired. Momentary by construction — a single-sample outlier asserts for two ticks, a level shift for one — and the host owns any dwell it wants on top
  - name: yHistoryOk
    description: Evaluability signal — false for the first history_warmup after load, the worst-case window in which Discrete.UnitDelay is still emitting its y_start seed and the computed step is a fabrication. False means NO_EVAL and the host must ignore yFault
params:
  max_step_per_sample:
    default: 10.0
    unit: "varies — the bound point's units"
    description: "Largest change the measured process can physically produce between two samples one sample_period apart. PER-BINDING SITE CONFIGURATION in the units of whatever sensor_value is bound to: the shipped 10.0 is the worked example for sensor_value := sat at a 60 s tick (argued in Detection Logic) and carries no authority on a Pa, L/s, %RH or ppm point. Re-derive it, never scale it, when sample_period changes."
    cxf: tooFast.t
  sample_period:
    default: 60.0
    unit: s
    description: "The rule's lookback — one sample of Discrete.UnitDelay history. MUST equal the host's tick interval; at any other ratio the delayed sample is between one and two periods old and the threshold stops meaning a sample-to-sample step (see Deviations)."
    cxf: prev.samplePeriod
  history_warmup:
    default: 120.0
    unit: s
    description: "Width of the startup inhibit that masks the UnitDelay y_start seed, and the window in which yHistoryOk is false. MUST be set to exactly 2 × sample_period and re-set whenever sample_period changes: a rule loaded between sample instants keeps emitting the seed until its second instant, so the seed can survive two full periods. Shorter lets a fabricated spike out; longer buys nothing."
    cxf: historyOk.delayTime
energy_impact:
  affected_subsystem: Sensor integrity gate — diagnostic coverage for every rule bound to this instance's sensor_value
  savings_range: sensor-dependent; the primary impact is downstream rule accuracy. PNNL EEM-01 (sensor recalibration) puts the recoverable range at 0-5% of site energy across a whole sensor population, ~15% prevalence, carried through playbooks/sensor-drift.md
  climate_sensitivity: neutral
  runtime_estimation: "none — there is no direct waste term. A spiking sensor costs whatever the control loops and diagnostic rules reading it do wrong while they believe it, and that cost is accounted for by those rules, not by this one"
emissions:
  scope: "1|2"
  method: QUALITATIVE_EMISSIONS
verified:
  engine_rev: e2ff2f8
  content_id: "cxf:fnv1a128:188c9fa8f8976ddf90245592e44abb9c"
  date: 2026-08-17
---

## Description

Every measured process in a building has mass behind it. Air in a duct is
dragged past a probe that takes half a minute to come to temperature; water in
a loop carries the thermal inertia of the pipe; a zone's CO₂ concentration is
the integral of people breathing into a volume. Each of those puts a ceiling on
how far a reading can move between two samples, and that ceiling is a property
of the physics rather than of the equipment: it does not change when the fan
stops. A reading that clears it did not come from the process. It came from a
failing element, an intermittent termination, a transmitter that changed range,
or a point that is now serving a different number than it used to.

This is the second of the library's sensor-health meta-rules. It reads one
point and judges that point, and its frontmatter says so: `adjudicates: {points:
[sensor_value], verdict: invalid_while_active}`. While `yFault` is true the host
must treat the bound point as invalid for every other rule on the same equipment
instance — the fan-out is computed from the other cards' own `points` lists, so
it stays complete as rules are added and no card here enumerates them. The
verdict is `invalid_while_active` rather than `ambiguous` because attribution is
not in doubt: one point went somewhere it could not have gone.

This does not break the library's stance that the graph computes
fault-given-valid-data. Two different things get called data quality. *Delivery*
quality — did a sample arrive, when, and what the field bus said about it — is
host-owned and stays that way; the engine is deliberately status-blind and this
rule inherits that blindness, which is why `preconditions` insists the host's gap
handling runs first. *Physical plausibility* — the sample arrived on time with
clean status and is wrong — is a property of the signal, computable from the
signal, and a fault of a piece of equipment, because a sensor is equipment. The
library already ships that second kind twice, as AHU-FC-062 (`mat` outside the
`oat`/`rat` envelope) and RTU-FC-052 (PNNL's AFDD0 consistency prerequisite).
This card is the same object with a narrower question.

It is also the only rule in the family whose fault is momentary. Flatline
accuses a sensor of standing still for hours and pair bias accuses two sensors
of disagreeing for a shift; a spike happens on one sample and is gone. That
single fact drives every timing decision below, and it is why this is the one
card in the library with no persistence timer on its fault path.

## Detection Logic

```
step        = |sensor_value − UnitDelay(sensor_value, sample_period)|
yHistoryOk  = true from history_warmup after load    (false ⇒ host reports NO_EVAL)
yFault      = step > max_step_per_sample  AND  yHistoryOk
```

Block graph (`rule.cxf.jsonld`):

![SYS-FC-101 block graph](diagram.svg)

Seven blocks in two strands. The upper strand is the measurement:
`Discrete.UnitDelay` holds the previous sample, `Reals.Subtract` and `Reals.Abs`
turn it into an unsigned step, and `tooFast` is a strict
`Reals.GreaterThreshold` — a step landing exactly on `max_step_per_sample` reads
clear, pinned from all three sides by `step_exactly_on_the_bound_reads_clear`
and its 0.1 K neighbours. The lower strand is a startup inhibit: a
`Logical.Sources.Constant` at `true` through a `Logical.TrueDelay` with
`delayOnInit = true`, false for the first `history_warmup` after load and true
forever after. `gate` conjoins them, and the inhibit is also the `yHistoryOk`
boundary output, so the host can see the one window in which this rule is not
answering the question.

**The worked example: `sensor_value := sat` at a 60 s tick.** The shipped
`max_step_per_sample = 10.0` is that binding and only that binding. Ask what
moves a supply-air temperature fastest and the answer is a step change in coil
output — a DX stage engaging, a chilled-water valve completing its stroke, an
economizer changeover swinging the mixed air behind the coil. On a single-zone
unit with one large compressor, coil-leaving air can fall 8–10 K within a minute
of a stage cutting in. The sensor then filters that: a duct probe in a 2.5 m/s
stream has a time constant of roughly 30–60 s, so one 60 s sample carries only
about 60–85% of a true step. The largest genuine one-minute excursion that
reaches the *reading* is therefore of order 6–8 K, and 10 K sits above every
transient the plant can produce while staying under the 15 K per minute the
design doc §1 calls "not a temperature". The faults it catches clear it by a
wide margin: a 55 °F supply temperature re-served on a °C point reads
12.8 → 55.0, a 42 K step
(`units_change_is_one_tick_wide`); an open thermistor railing to the
transmitter's range end does the same or more.

Nothing about that argument survives a change of binding, which is the whole
point of the placeholder. A duct static pressure moves tens of pascals in a
minute on an ordinary fan ramp and needs a much larger number in its own units;
a zone CO₂ sensor physically cannot move 200 ppm in a minute and wants a much
smaller one. Nor does the argument survive a change of `sample_period`: a 300 s
sample admits the entire stage transient, so a host ticking at five minutes must
re-derive the bound from the physics rather than multiply this one by five.

**The delay line's warmup is a fabricated spike and it is masked deliberately.**
`Discrete.UnitDelay` seeds both of its state words from `y_start` and emits
`y_start` until its *second* sample instant, so with the CDL default of 0.0 the
first computed step on a 22 °C duct is `|22 − 0| = 22` — a spike more than twice
the bound, on tick one, on every load and every restart.
`steady_reading_and_the_unit_delay_warmup_artifact` pins exactly that: a signal
that never moves, a computed step of 22 K, and `yFault` false while `yHistoryOk`
is false. `identical_step_after_the_warmup_gate_opens` is its pair — the same
22 K step arriving once the gate has opened, with the same arithmetic and the
opposite verdict — and `genuine_step_inside_the_warmup_gate_is_not_reported`
prices the arrangement: the gate is sized for the worst case, so on a load that
happens to land on a sample boundary it also costs one real sample. Together
they show the inhibit masking a fabrication rather than swallowing findings, and
say what it costs when it does swallow one.

**`yFault` is one or two ticks wide and that is the design, not an oversight.**
A single-sample outlier violates the bound twice, going out and coming back, so
`single_sample_outlier_reported_on_both_edges` asserts for two consecutive
ticks. A level shift that stays — the units change, the rescaled transmitter —
violates it exactly once, because the next sample is compared against the
shifted value. Both are reported here on the tick the physics broke. The
Deviations argue why no timer sits downstream of `gate`, and
`two_outliers_report_independently` pins the consequence: no latch, no
accumulated timer, each event judged on its own.

## Possible Diagnoses

Library-authored. Nothing published fixes a cause list for a step bound, and the
first four are what the shape actually finds in the field:

1. A failing sensing element — an intermittent thermistor or RTD, a cracked
   lead, a probe that opens when the duct vibrates. Classically shows as
   isolated outliers between long stretches of perfectly good data, which is the
   two-tick case
2. Loose, corroded or wet terminations, or a signal pair sharing conduit with
   something switching inductive load. The spikes correlate with the offending
   equipment's cycles rather than with anything the sensed process is doing
3. A transmitter or A/D channel that changed range or scaling — a 4–20 mA
   transmitter re-ranged during service, a jumper moved, a controller input
   reconfigured from 10 k to 1 k. Presents as a level shift, one tick wide
4. A units change nobody announced. A point re-served in °F on a °C-declared
   binding, or Pa where the card expects inches of water. Also one tick wide,
   and this rule is the only one in the library that notices
5. A point rebound to a different physical sensor by a controller download or a
   BAS integration edit. The reading is honest and it is no longer the sensor
   the rest of the rules think they are reading
6. A host-side delivery artifact wearing the costume of a sensor fault: a value
   re-served from cache when comms came back, an interpolation across a gap that
   landed badly, a poll that slipped a cycle. Not a sensor fault at all, and
   the reason `preconditions` puts the host's gap handling underneath this rule
   rather than beside it
7. A correct reading and a wrong threshold. On a fast binding, or after
   `sample_period` was changed without re-deriving the bound, a genuine plant
   transient clears it. Diagnose this one first if the alarms cluster on stage
   changes and mode transitions

## Energy Impact

COMFORT_ENERGY, MEDIUM confidence, QUALITATIVE_ONLY. There is no direct waste
term. A spiking sensor burns nothing by itself; its cost is entirely in what
reads it — a supply-air controller that takes one 40 K outlier as real and slams
a valve, an economizer that changes mode on a phantom outdoor reading, and the
diagnostic rules downstream that either miss a real fault or invent one.
PNNL EEM-01 (sensor recalibration) puts the recoverable range at 0–5% of site
energy across an entire sensor population at roughly 15% prevalence, which is
the figure the [sensor-drift](../../../playbooks/sensor-drift.md) playbook
carries and the honest ceiling for this whole family. The value this rule
delivers is the accuracy it restores to the rules it adjudicates, and that shows
up on their cards, not here.

Confidence is MEDIUM rather than LOW, which is a deliberate departure from
AHU-FC-062 and RTU-FC-052. Those two compare several sensors and cannot say
which of them is wrong; this one reads a single point and its finding is
unambiguous by construction, which is exactly why its verdict is
`invalid_while_active` and not `ambiguous`. It is not HIGH for two reasons that
are both real: the whole inference rests on a threshold that ships as a
placeholder and is worthless until someone derives it for the binding, and the
host's delivery layer can manufacture the identical step (diagnosis 6).

## Emissions Impact

QUALITATIVE_EMISSIONS, MEDIUM confidence; no direct emissions, because a reading
neither burns fuel nor draws power. Scope is recorded as `1|2` for the same
reason AHU-FC-062 records it that way: it depends on which subsystem the bad
number distorts. A spiking supply-air temperature that provokes preheat lands in
Scope 1; one that provokes mechanical cooling or drops an economizer out of
service lands in Scope 2, and the same sensor can do both in different seasons.
Avoided-emissions basis: N/A.

## Deviations

- **No persistence timer on the fault path, and that decision is the card.**
  In all seventy-one other rule documents in this library `yFault` is driven
  directly by a `Logical.TrueDelay` holding the condition for `alarm_delay`,
  because all seventy-one detect a condition that persists. A spike does not,
  and the timer would not merely be redundant — it would delete findings. At the
  pin, `TrueDelay` emits false on a rising edge and true on the next tick the
  input is still true, so *any* positive `delayTime` up to one tick means "two
  consecutive violating samples". That keeps the single-sample outlier, which
  violates the bound twice as it leaves and returns, and silently deletes the
  entire level-shift class: `units_change_is_one_tick_wide` violates the bound
  exactly once, and a units change, a re-ranged transmitter and a rebound point
  are between them the most common thing this rule finds. The design doc §4.2's
  suggested `alarm_delay ≥ 2·samplePeriod` masks the warmup artifact and loses
  both archetypes, and is rejected here for that reason. Nor can the delay be
  set to zero: `positive_duration` clamps at 0 and the `first` branch in
  `logical_timing.rs` honours `delayOnInit` only when `delayTime > 0`, so a
  zero-delay timer would pass the warmup artifact straight through to `yFault`.
  The timer therefore comes off the fault path entirely and goes on the startup
  inhibit instead, where its edge is a fact about the block graph rather than a
  tuning decision. What the library gives up is debounce: one noisy sample
  produces one tick of `yFault`. That is host policy, decided by the same host
  that must already choose how long an adjudicated NO_EVAL lasts and whether it
  resets the suppressed rules' rolling state — neither of which the schema
  assigns to the graph either.
- **The warmup artifact is masked by an explicit gate, and the gate is two
  sample periods wide because the seed can survive two.** `Discrete.UnitDelay`
  seeds its held and staged words from `y_start` and promotes staged→held only
  at sample instants. Its grid is anchored to absolute model time, so where the
  rule is loaded relative to that grid decides how long the seed lives. A load
  that lands *on* an instant stages the input immediately and emits a real
  sample one period later. A load that lands *between* instants stages nothing
  (`update_state`'s init branch only samples when `at_sample_instant` holds), so
  the next instant promotes seed→seed and the first real sample does not appear
  until the instant after that — up to `2 · samplePeriod` after load. A gate one
  period wide is therefore correct only for grid-aligned loads and lets a
  fabricated 22 K step through on every other one, which is a fault the rule
  invents on a restart nobody chose the timing of. `historyOk` is a
  `TrueDelay(delayTime = history_warmup, delayOnInit = true)` fed a constant
  `true`: false on the first tick by the `delayOnInit` branch, true from the
  first tick whose accumulated timer reaches `delayTime`. At
  `history_warmup = 2 · sample_period` it covers the worst case exactly, which
  is the design doc §4.2's factor of two applied to the gate rather than to the
  fault path. The cost is one real sample of blindness when the load happens to
  be aligned, pinned as
  `genuine_step_inside_the_warmup_gate_is_not_reported` rather than left
  implicit. `small_magnitude_binding_has_no_warmup_artifact_to_mask` records the
  other half: whether the seed fabricates anything at all depends on the bound
  point's magnitude, the gate does not care, and so the card does not have to
  reason about every binding's zero.
- **`y_start` is left at the CDL default of 0.0.** Seeding it to a plausible
  mid-scale reading would also hide the artifact, and the design doc §4.2
  rejects that: it buries a block-level fact instead of documenting it, and it
  turns a graph constant into a per-point site value that buys no diagnostic
  power. Leaving it at 0 keeps the fabricated first step loud and visible in the
  vectors, where it belongs.
- **`sample_period` and `history_warmup` are two card parameters carrying one
  decision, and the linter cannot enforce the ratio.** The multi-path
  `cxf: [...]` form AHU-FC-057 uses for its window is not available here,
  because the two block parameters take different *values* — `samplePeriod` and
  `2 · samplePeriod` — and that form sets every path it lists to the same
  number. So they are declared separately with the invariant stated in both
  descriptions, in `preconditions`, and here: `history_warmup = 2 ·
  sample_period`, always, re-set together. A host that retunes the sample period
  and forgets the gate gets a rule that fabricates a spike on some fraction of
  its restarts. This is the same class of coupled-parameter hazard as
  HP-FC-050's slope and intercept, and it is worth naming as loudly.
- **`sample_period` must equal the host's tick interval, and the vectors only
  pin that case.** `UnitDelay`'s grid is anchored to absolute model time —
  `t0 = round₆(⌊t_start/period⌋·period)`, so a rule loaded at t = 137 s with a
  60 s period samples on the 120 s grid, not from 137. Between sample instants
  the block holds, so at any tick the emitted value was taken between one and two
  periods ago: the effective lookback age runs over `[P, 2P)`. When `P` equals
  the tick it collapses to exactly one tick and the rule means what the equation
  looks like — a sample-to-sample step. When it does not, the rule means "an
  excursion exceeding the bound somewhere within one to two sample periods",
  which is a defensible test but a different one, with a per-window magnitude
  rather than a per-sample step for a threshold, and a warmup gate `2P/tick`
  ticks wide instead of two. `vectors.json` runs `clock.step_s = 60` against the
  shipped `sample_period = 60`, so what is pinned here is the recommended
  configuration and nothing else. The `[P, 2P)` arithmetic is read from
  `discrete.rs` at the pin and is deliberately *not* vector-pinned, because a
  vector that pinned it would have to ship the configuration this card tells
  hosts not to use.
- **`Reals.Derivative` is not used, and could not be.** It is the block the
  equation suggests and it is wrong here on the engine's own arithmetic (design
  doc §4.1, verified at the pin). Its `k` and `T` are `RealInput` connectors
  rather than parameters, so it needs two constant sources wired in and its
  tunables become parameters of those constants. Its filter discretizes to a
  steady-state output of `k·s·(1 + dt/T)` for a ramp of slope `s`, which at a
  300 s tick with `T = 300 s` reports twice the actual slope, and holding the
  error under 5% needs `T ≥ 20·dt` — a hundred minutes of lag in a spike
  detector. And its step response ignores `dt` entirely, so the same 5 K jump
  reads identically whether it took 60 s or 600 s. Subtracting two samples has
  none of those properties and costs three blocks.
- **Strict `>`, pinned on the line and both sides.** CDL `Reals` has no
  `GreaterEqual`. A step of exactly `max_step_per_sample` reads clear, which
  errs toward silence, and three vectors hold that line at 32.0, 31.9 and 32.1
  against a 22.0 baseline. Sites whose BAS quantises the bound point coarsely
  will land on the boundary often enough to notice and should set the threshold
  between two quantisation levels.
- **`Reals.Abs` discards the sign and the card does not try to recover it.**
  `downward_step_is_reported_the_same_as_an_upward_one` pins an 18 K collapse
  reading exactly as an 18 K jump would. A signal-conditioning failure that rails
  low and one that rails high are the same finding here. Splitting them would
  double the graph to distinguish two cases that lead to the same work order.
- **No `equip_active` conjunct, which is where this rule parts company with
  SYS-FC-100.** Flatline needs the gate: a still reading on idle equipment is
  the correct answer, and accusing it would be a fault of the rule rather than
  of the sensor. A spike needs no gate for the mirror-image reason — the ceiling
  on how fast a reading can move is set by the mass of the process, not by
  whether anything is driving it, and an idle system moves *slower* than a
  running one, so the running case is the permissive one. Binding a gate would
  make the rule blind exactly where it is most trustworthy: a 30 K jump on a
  duct temperature at three in the morning with the fan off is as impossible as
  one at noon, and more obviously a wiring fault. It would also cost the card a
  second binding obligation on a family whose binding cost is already the main
  argument against it (design doc §3).
- **`max_step_per_sample` ships as a per-binding placeholder, the VAV-FC-050
  arrangement.** That card ships `ventilation_requirement = 70.0 L/s` so the
  document is runnable, and says in capitals that it is not a site value; this
  one ships 10.0 in the units of whatever `sensor_value` is bound to, which is a
  stronger form of the same problem, because here even the *dimension* is
  unknown until binding. The number is defended above for one binding and for
  nothing else. Set it 3× too high and the rule never fires; set it 3× too low
  and it alarms on every stage change the plant makes. Role-point thresholds are
  the price the `sys` family pays for one graph serving every equipment type,
  and `points/sys.points.json` states it in `sensor_value`'s own notes.
- **The rule cannot see drift, ramps, or anything that stays under the bound.**
  `ramp_under_the_bound_every_tick_is_invisible` pins five consecutive 5 K steps
  carrying a reading from 22 to 47 °C — two and a half times the bound in total,
  physically absurd in a duct, and silent, because each individual step is
  legal. A step bound sees steps. Slow monotone drift is structurally invisible
  to both this rule and SYS-FC-100, which is the argument for SYS-FC-054 being a
  third shape rather than a variation on these two, and the reason all three are
  in the family.
- **`adjudicates` cards must not be suppressible, so `suppressed_by` is empty
  and must stay empty.** The design doc §2.3 proposes this as normative: if an
  equipment fault could silence the sensor rule that invalidates it, the
  suppression graph has a cycle with a wrong answer at both ends. `suppresses`
  is empty for a different reason — the fan-out of an adjudicated point is
  derived by the host from other cards' `points` lists, not hand-written here,
  which is the entire argument for keying the field to the point. AHU-FC-062's
  fourteen-entry `suppresses` list is the counter-example the design doc names:
  correct today, silently incomplete the first time someone authors an AHU rule
  that reads `mat`.
- **Severity 3 and COMFORT_ENERGY follow AHU-FC-062 and RTU-FC-052 rather than
  the fan-out argument.** The design doc's §6 Q1 leaves this open and floats
  raising adjudicating rules to severity 2 on the grounds that a bad sensor
  blinds a whole diagnostic set, or switching them to PROTECTIVE on the grounds
  that what they deliver is avoided false alarms rather than energy. Severity 3
  is `faults/sys/README.md`'s index value and is not this card's to change.
  PROTECTIVE is declined on evidence: in this library it means avoided physical
  damage — PMP-FC-050's dry-running seal, RTU-FC-050's short-cycled compressor —
  and stretching it to cover avoided false alarms would make one category mean
  two unrelated things. The honest reading is that this rule's impact is a
  fan-out rather than a kilowatt, and `energy_impact.runtime_estimation` says so
  in words instead of encoding it in a category.
- **`clusters: []`, and CLU-09 is the open question.** `clusters/clusters.json`
  gives CLU-09 (Sensor Integrity Failure) the trigger `AHU-FC-062` and lists
  SYS-FC-054 and SYS-FC-055 as members. With the FC-100 family landing, the
  trigger is arguably one of the sys rules and 062 becomes a member — a change
  to a single-writer file that the design doc §3 says to flag rather than make.
  Declaring membership from this side without the cluster file knowing about it
  would create a half-edge, so this card declares nothing and this bullet is the
  flag.
- **[`sensor-drift`](../../../playbooks/sensor-drift.md) is the right playbook
  and does not yet name this rule.** Its Applies-To row lists SYS-FC-054,
  SYS-FC-055, five AHU rules, AHU-FC-062, RTU-FC-052 and CLU-09; SYS-FC-100 and
  SYS-FC-101 belong in it and adding them is the playbook owner's edit. The workflow already fits: step 1's
  portable-reference comparison is the verification for a spiking sensor as much
  as a drifting one, and step 3's recalibrate-or-replace is the same repair. The
  one step that does not transfer is step 2's BAS offset — an offset corrects a
  bias and does nothing for a sensor that jumps, and a technician who applies
  one here has moved the noise rather than removed it.
- **Role-point binding breaks the library's canonical-name convention, on
  purpose.** Every other card's boundary input is a canonical point name from
  its family dictionary, which is what makes binding mechanical. `sensor_value`
  is a role: the host's instance configuration records which real point it is,
  and that same record is what resolves `adjudicates.points` and drives the
  NO_EVAL fan-out, so the binding is a required artifact of the design rather
  than an extra one. SCHEMA.md's points contract carries this as a documented
  exception, and the alternative — thirty copies of this graph, one per
  point-and-family pair — is thirty chances for the copies to drift apart with
  no cross-card diff check to catch it.
- **No published test vectors exist for this rule.** It is library-authored and
  no source fixes cases for it, so all twelve scenarios in `vectors.json` are
  written here: three on the warmup gate (the masked artifact, the same step
  once the gate opens, and the genuine step the gate costs), both spike
  archetypes, three sides of the threshold, the sign symmetry, the ramp blind
  spot, the independent-recovery case, and the small-magnitude binding that
  never had an artifact to mask.
- Operating states and preconditions are declared in frontmatter for host
  enforcement rather than encoded in the block graph, per the library's design
  stance.

## Notes

Read `yHistoryOk` first. It is false for two sample periods after the rule
loads, and in that window a false `yFault` is silence rather than a clean bill
of health. On a host that reloads rules on every configuration change, that
window recurs, and a host that logs `yFault` without it will eventually record a
clean sensor that was never examined.

When this rule fires, look at the trend before dispatching anyone, because the
shape of the event names the cause faster than any test does. Isolated single
samples between long stretches of clean data are an intermittent connection or a
failing element — chase terminations first, and note whether the spikes line up
with a compressor or a lighting contactor rather than with anything the sensed
process is doing. A single step that never comes back is not a sensor failure at
all in most cases: it is a re-ranged transmitter, a units change, or a point
rebound during a controller download, and the fix is a configuration edit rather
than a truck. Check what changed in the BAS that day before touching the sensor.

Then check the tick. A rule whose alarms cluster on stage changes and mode
transitions rather than falling at random is usually reporting that
`max_step_per_sample` was inherited from another binding or survived a change to
`sample_period` untouched. The
threshold is a physical claim about one sensor measuring one process at one
sample interval, and it does not travel — not between points, not between
equipment types, and not between tick rates.

Know what this rule cannot do. It sees steps, so it is blind to the drift that
most sensor work is actually about: a transmitter losing a degree a month never
violates a step bound and never will. SYS-FC-100 covers the opposite extreme, a
reading that stopped moving at all. The middle — slow,
monotone, plausible-looking error — needs a second sensor to compare against,
which is SYS-FC-054's job and the reason this family has three shapes instead of
two.
