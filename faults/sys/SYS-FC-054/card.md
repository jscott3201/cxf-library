---
schema: cxf-library/fault-card/v1
id: SYS-FC-054
name: Sensor drift via cross-validation (paired sensors)
equipment: sys
status: verified
phase: 2
method: rule
severity: 3
category: COMFORT_ENERGY
confidence: LOW
estimation_method: QUALITATIVE_ONLY
source:
  - "HVAC FDD Reference v1.0 §16, SYS-FC-054 (pdf pp. 142-144) — equation, both delays, drift_threshold `2°C / 5%`, the four diagnoses, and the whole impact profile"
  - "The reference's own provenance line for that card: PNNL-27338 §3; G36 sensor calibration checks"
  - "Yang, H., Cho, S., Tae, C.-S., Zaheeruddin, M. (2008). Sequential rule based algorithms for temperature sensor fault detection in air handling units. Energy Conversion and Management 49(8), 2291-2306. doi:10.1016/j.enconman.2008.01.029 — the published grounding for pairwise sensor comparison, and the source of this card's honesty about isolation"
  - "Accepted design: _research/fc100-sensor-health-design.md (§2 stance, §3 ID scheme, §4.4 pair-bias vector strategy, §5 usable pairs)"
  - "Library precedent: AHU-FC-062 and RTU-FC-052 (physical-plausibility rules that already ship), VFD-FC-050 (two published delays chained), VAV-FC-050 (per-binding placeholder parameter)"
g36: null
clusters: [CLU-09]
suppresses: []
suppressed_by: []
adjudicates:
  points: [sensor_value_a, sensor_value_b]
  verdict: ambiguous
related: [SYS-FC-055, SYS-FC-100, SYS-FC-101, AHU-FC-062, RTU-FC-052]
playbooks: [sensor-drift]
operating_states: "all, within the binding's own validity window — the two sensors must be measuring the same physical quantity at the moment of comparison, which for a stream-mixing pair is true only in particular damper or mode states (host-enforced; see preconditions)"
preconditions: "sensor_value_a and sensor_value_b are ROLE points, not canonical names: the host's instance configuration records which real point each is bound to, and that record is also what resolves this card's adjudicates target. Both must be bound to the same quantity kind in the same units — the rule subtracts two numbers and converts nothing, so a pair trended in °C against °F reads as a permanent 30-unit divergence and alarms forever. drift_threshold ships as a temperature placeholder and MUST be retuned to the binding (see Deviations); a percent-quantity pair left at the shipped 2.0 gets a band the reference never intended. The pair must genuinely see the same quantity during evaluation, which is a per-binding claim the graph cannot check: erv_oa_entering_temp against oat holds whenever both are in the outdoor air stream, but mat against rat holds only with the outdoor air damper shut and mat against oat only at full economizer, so the host must gate those bindings on damper position and exclude the minutes after a changeover exactly as AHU-FC-062 does. Delivery quality is resolved before this rule runs, not by it: a value the host held over from twenty minutes ago reads as a divergence, and the rule is right about the number it was given and wrong about the sensor. Per the design doc's normative constraint, no other card may list SYS-FC-054 in its suppresses — an equipment fault silencing the sensor rule that invalidates it is a cycle with a wrong answer at both ends."
points:
  - sensor_value_a
  - sensor_value_b
outputs:
  - name: yFault
    description: True while the two bound sensors have stayed more than drift_threshold apart, in the bound points' units, continuously for drift_duration plus alarm_delay. Which member drifted is not determined — see adjudicates.verdict
params:
  drift_threshold:
    default: 2.0
    unit: "varies (the bound points' own units)"
    description: "Maximum divergence the pair's combined accuracy explains. PER-BINDING SITE CONFIGURATION — the reference's default is `2°C / 5%`, one number per quantity kind, and a single CXF literal cannot be both. The shipped 2.0 is the temperature half; a percent-quantity binding (relative humidity, damper position, valve position) takes 5.0, and any other quantity takes a number nobody has published. Retune at binding."
    cxf: driftHigh.t
  drift_duration:
    default: 3600.0
    unit: s
    description: "Continuous divergence required before it counts as drift rather than one sensor lagging the other through a transient (60 min). The reference's own `drift_duration`."
    cxf: sustained.delayTime
  alarm_delay:
    default: 1800.0
    unit: s
    description: "Further persistence required after drift_duration before the alarm asserts (30 min). The reference's own separate `AlarmDelay`; 90 min to alarm at the shipped defaults."
    cxf: persist.delayTime
energy_impact:
  affected_subsystem: Sensing accuracy — cascading downstream impact
  savings_range: "Sensor-dependent; 0-5% site energy if the drift is causing downstream faults (EEM-01, sensor recalibration; ~15% prevalence)"
  climate_sensitivity: neutral
  runtime_estimation: "none — no direct waste term. The cost of a drifted sensor is the decisions taken on it and the diagnostic coverage lost while it is believed, which is accounted for by the rules this one adjudicates rather than by this card (Energy Impact Reference §4.4)"
emissions:
  scope: "1|2"
  method: QUALITATIVE_EMISSIONS
verified:
  engine_rev: e2ff2f8
  content_id: "cxf:fnv1a128:0f6dd4de2df9cd68164f18828e25c4b9"
  date: 2026-08-17
---

## Description

Two sensors that should be reading the same number are not. That is the whole
claim, and it is worth writing down because it is one of the few claims about a
sensor that two points can actually support: a single transmitter has nothing to
be checked against, and every rule in this library that reads one believes it.
Put a second sensor in the same air stream — or take a pair the physics already
constrains — and the disagreement between them is evidence no single-sensor rule
can produce.

The failure it catches is drift: the slow, monotone, unremarkable kind. A
transmitter that has been reading 1.5 °C high since March is not still, so a
flatline test never sees it, and it never moves fast, so a spike test never sees
it either. It looks exactly like a working sensor, which is why it survives for
years and why the reference puts its prevalence at 15%. What it costs is rarely
its own energy: a biased outdoor-air sensor disables an economizer, a biased
supply-air sensor drags a reset schedule off with it, and the finding that shows
up on the report is some other rule firing for a reason that is not true.

This card is the first in the library to carry `adjudicates`. It is a meta-rule:
its `yFault` is a finding with its own severity, its own playbook and its own
work order, and it is also an instruction to the host about how to read every
other rule bound to the same two points. The verdict is `ambiguous` and that is
the honest word. `|a − b|` says the pair disagrees; it does not say which member
is wrong, and no arrangement of two sensors can. Yang et al. (2008) is the
published version of that limit and also the upgrade path: a *sequence* of
overlapping comparisons isolates the member, and a future rule built that way
would adjudicate one point with `invalid_while_active` instead of two with
`ambiguous`.

That an in-graph rule may judge data at all is the design doc's §2 argument, in
one sentence: "data quality is the host's" is about *delivery* — did a sample
arrive, when, and what the field bus said about it — and this rule is about
*physical plausibility*, which is a property of the signal, computable from the
signal, and a fault of a piece of equipment, because a sensor is equipment. The
library already ships that argument twice without anyone objecting, as
AHU-FC-062 and RTU-FC-052. This card is the same object with the equipment
family taken out of it. The layering stays acyclic because this rule assumes its
own inputs were mechanically delivered: staleness and comms gaps are resolved
host-side *before* it runs, and it neither subsumes that work nor repeats it.

## Detection Logic

```
yFault = |sensor_value_a − sensor_value_b| > drift_threshold
         sustained continuously for drift_duration,
         then held a further alarm_delay
```

Block graph (`rule.cxf.jsonld`):

![SYS-FC-054 block graph](diagram.svg)

Five blocks and no gate. `diff` subtracts, `absDiff` throws the sign away, and
that discarded sign is the rule's defining property rather than an
implementation detail: `member_a_reads_high` and `member_b_reads_high` differ
only in which input carries the 4.0 offset and produce identical output on every
tick. That pair of vectors is `verdict: ambiguous` written as arithmetic.

`driftHigh` is a strict `Reals.GreaterThreshold` — CDL `Reals` has no
`GreaterEqual` — so a pair sitting exactly `drift_threshold` apart reads healthy.
All three sides are pinned: `divergence_exactly_at_the_threshold`,
`divergence_just_below_the_threshold`, `divergence_just_above_the_threshold`.

`sustained` and `persist` are the reference's two published delays, chained
rather than added together. The reference gives `drift_duration = 60 min` and a
separate `AlarmDelay = 30 min` for the same condition, so both are kept and both
stay tunable; 90 minutes to alarm at the defaults.
`divergence_shorter_than_both_delays` is the regression test for the structure —
a 75-minute divergence matures `sustained` and dies 15 minutes into `persist`,
where the reference's `drift_duration` alone would have alarmed at 3600 s.
Continuous means continuous in both timers: a ten-minute reconvergence discards
the elapsed time rather than pausing it, so
`divergence_dips_and_restarts_the_clock` lands its alarm a full 5400 s after the
*second* crossing.

The threshold literal is in the bound points' units, because the graph has none.
Worked example, using the pair the design doc §5 names as the cleanest available
today: on an energy recovery ventilator, bind `sensor_value_a :=
erv_oa_entering_temp` and `sensor_value_b := oat`. Two thermometers in the same
outdoor air stream, both already in `points/erv.points.json`, both °C, no host
derivation and no mode gating needed. `drift_threshold = 2.0` then means 2.0 K,
`19.0` against `15.0` in `member_a_reads_high` is a 4 K spread, and the alarm at
5400 s says one of those two thermometers is out. Bind the same graph to a pair
of humidity transmitters and the same 2.0 means two points of relative humidity,
which is not the reference's number and not a band anyone chose —
`percent_binding_at_the_shipped_default` pins that consequence rather than
leaving it to be discovered.

## Possible Diagnoses

The reference's four, in its order:

1. Sensor calibration drift — the intended target, and the one the playbook's
   Step 3 recalibration fixes
2. Sensor wiring fault: a long run picking up an offset, a loose terminal, or a
   3-wire RTD lead-resistance error that reads as a fixed bias
3. Sensor placement — the two sensors are not in the same air stream after all.
   A "spare" outdoor sensor on a sunlit wall, a duct probe downstream of a leak,
   or a pair split across a mixing plane. Nothing is broken and the pair is
   still not comparable, which makes this the diagnosis that turns into a
   binding correction rather than a work order
4. Sensor failure — a transmitter drifting toward a rail, on its way to the
   flatline SYS-FC-100 will catch when it arrives

Read them against `adjudicates.verdict: ambiguous`: every one of the four names
a single sensor, and this rule cannot tell you which of the two it is. The
playbook's Step 3.4 settles it the only way two points allow — take a reference
instrument to both members.

## Energy Impact

COMFORT_ENERGY, LOW confidence, QUALITATIVE_ONLY — the reference's own profile
for this card, transcribed. There is no runtime waste term and this card does
not invent one: a drifted sensor spends nothing by drifting. The
number in `savings_range` is EEM-01's recalibration figure — 0-5% of site energy
where the drift is causing downstream faults — and the conditional is doing the
work. A drifted sensor nobody acts on costs nothing at all; a drifted `oat`
feeding an economizer changeover costs a lot, and the amount belongs to the
economizer rule, not to this one.

Confidence is LOW, and the reason is specific rather than a hedge: the rule is
confident about the *pair* and says nothing at all about either *member*. Its
false-positive rate on "one of these two is wrong" is governed almost entirely
by whether the binding is sound. Diagnosis 3 is the standing false positive — two
sensors that were never comparable disagree honestly, forever, and no threshold
distinguishes that from a real drift.

## Emissions Impact

Scope 1 or 2 depending on what the mis-measurement ends up driving, method
QUALITATIVE_EMISSIONS, LOW confidence, avoided-emissions basis N/A — the
reference's assignment, and the ambiguity in `scope` is real rather than lazy.
A drifted sensor that biases a boiler is Scope 1; the same sensor biasing a
chiller or an economizer is Scope 2; the sensor itself emits nothing. The
quantity is entirely cascade, which is the same reason `runtime_estimation` is
empty.

## Deviations

- **First card in the library carrying `adjudicates`, and this is what it
  means.** `adjudicates: {points: [sensor_value_a, sensor_value_b], verdict:
  ambiguous}` says: while this fault is active, both bound points are unfit to
  be believed, and every rule on the same equipment instance that consumes
  either one is NO_EVAL. The host derives that set from the `points` list every
  card already carries — no rule list appears on this card, and none should,
  because a hand-written list is correct on the day it is written and silently
  incomplete the first time someone authors a rule that reads the same point
  (AHU-FC-062's hand-written thirteen-entry `suppresses` is the counter-example
  the design doc §2.3 names — and its own drift shows the point: two of those
  thirteen, RTU-FC-054 and RTU-FC-055, are not written yet, and the design doc
  counts the list as fourteen). `adjudicates` is card metadata like
  `suppresses` and `preconditions`: the block graph is unchanged and the engine
  never sees it.
- **The fan-out is larger than it looks, and the worked binding shows it.**
  Bound to an ERV as `erv_oa_entering_temp` / `oat`, this card's closure is
  ERV-FC-050 (which reads `erv_oa_entering_temp`) and ERV-FC-051 (which reads
  `oat`) — every rule the ERV family currently has. The unit goes dark on one
  finding. Whether a host should then go silent or keep reporting at reduced
  confidence is an open question the design doc §6 puts to the library owner and
  this card does not answer; what this card owes the host is an honest
  declaration of scope, which is both points, because it cannot narrow it.
- **`verdict: ambiguous` rather than picking a victim in prose.** The obvious
  alternative was to declare `sensor_value_b` the reference (the reference's own
  required-points table calls it "Reference sensor") and adjudicate only
  `sensor_value_a`. That would be a lie the schema helped tell: nothing in the
  graph distinguishes the two inputs, `absDiff` guarantees the outputs are
  identical under a swap, and `member_a_reads_high` / `member_b_reads_high` pin
  it. Naming the members "primary" and "reference" is a binding convention, not
  a property this rule can exploit.
- **`sensor_value_a` and `sensor_value_b` are role points, the documented
  exception to the canonical-name convention.** Every other card in this library
  binds by name matching alone; these three sensor rules cannot, because the
  same graph deploys against many real points and the reference's own
  required-points table for this card says "varies by application" in the units
  column. The cost is named rather than hidden (design doc §3): the host's
  instance configuration must record each binding. That record is not extra
  work — it is the same artifact `adjudicates` resolves against, so the design
  needs it either way.
- **`drift_threshold` ships as one number where the reference publishes two.**
  The reference's default is `2°C / 5%`, which is the reference acknowledging
  that its own threshold is per-quantity. A CXF `S231:value` literal is one
  double. The shipped 2.0 is the temperature half — the quantity the pair form
  is most often bound to, and the same value AHU-FC-062 uses for its
  `sensor_tolerance` — and the 5% alternative is documented in `params` and
  pinned as a consequence by `percent_binding_at_the_shipped_default`. Precedent
  for shipping an explicitly per-binding placeholder: VAV-FC-050's
  `ventilation_requirement`, whose card says in the same words that a host which
  leaves it unset is comparing against an arbitrary number.
- **Two delays in series, not one.** The reference lists `drift_duration`
  (60 min) and `AlarmDelay` (30 min) as separate tunables for one condition, so
  both are kept and chained, the VFD-FC-050 shape. A single 5400 s delay would
  behave identically as shipped; the chain is what lets a site keep a 30-minute
  drift window and a two-hour alarm hold, or the reverse, without re-authoring.
  `divergence_shorter_than_both_delays` is the vector that separates the chain
  from the shortcut: a 75-minute divergence alarms under the reference's
  `drift_duration` alone and stays silent here.
- **No activity gate, deliberately, and this is where the trio's three members
  diverge.** SYS-FC-100 needs `equip_active` because a signal that is not moving
  on idle equipment is not evidence of anything. A bias test needs no such
  permission: two thermometers in the same air disagree when one of them is
  wrong, whether or not a fan is running. Adding `equip_active` would buy
  nothing and cost a third binding obligation on every deployment. What this
  rule does need — that the two sensors are actually seeing the same quantity
  right now — is a per-binding claim about damper positions and modes that no
  boolean in `points/sys.points.json` expresses, so it is `preconditions` prose
  and host-enforced, the same call AHU-FC-062 made for its post-changeover
  exclusion.
- **No discrete blocks, so no startup artifact to mask.** The design doc §4
  spends its length on `Discrete.UnitDelay`'s tick-one artifact (`y` holds
  `y_start` until the *second* sample instant, so the first difference on a
  22 °C duct reads 22 °C) and on why `Reals.Derivative` is forbidden here (its
  `k` and `T` are input pins, and its discretization biases a ramp by
  `1 + dt/T`). Neither applies to this card. `Subtract` and `Abs` are
  combinational, and so is `GreaterThreshold` at the shipped `h = 0` — it takes
  a state word only when hysteresis is enabled, and it feeds through either
  way — so tick one compares two live readings and means it. SYS-FC-101 is
  where those mechanics have to be pinned; this card's only state is the two
  timers.
- **`delayOnInit = true` on both delays** (the CDL default is `false`), the
  library's standing choice: a pair already diverged when the controller
  restarts waits out the full 90 minutes rather than alarming on the first tick.
  Here it also removes the only restart artifact the graph could have had.
- **`TrueDelay` asserts at exactly `T + delayTime`,** so the realized test is
  "diverged for strictly more than `drift_duration + alarm_delay`" at tick
  resolution. `divergence_clears_on_the_maturity_tick` (pair reconverges at
  exactly 5400 s, never reported) and `divergence_clears_one_tick_later` (one
  tick of alarm, then clear) pin both sides of that edge. Verified against the
  engine at the pin rather than assumed: with `delayOnInit` the timer is zero on
  the first tick and accumulates `dt` from the second, so the assert lands on
  the tick at `delayTime`.
- **Common-mode drift is invisible and the vector says so.** Two sensors from
  one calibration batch, on one supply voltage, with one wrong scaling constant,
  drift together; the subtraction cancels it and this rule stays silent through
  all of it. `both_members_drift_together` pins that blind spot at 10 K of
  shared error. The rules that could see it are SYS-FC-055 (a virtual sensor
  built from other points) and the fleet-comparison form the design doc §5
  leaves open; neither is written.
- **Kept the reference's number instead of taking a new one.** The design doc
  §3 offered `SYS-FC-102` in a consecutive FC-100 family and flagged the
  collision as the library owner's call. 054 won, decided 2026-08-17: the
  reference's SYS-FC-054 *is* this rule, `clusters/clusters.json` already lists
  SYS-FC-054 in CLU-09, and `playbooks/sensor-drift.md` already names it twice.
  The cost is that the sensor family is 054 plus 100/101 rather than three
  consecutive IDs, which `faults/sys/README.md` states in its own words.
- **`clusters: [CLU-09]` is a declaration, not an edit.** CLU-09 (Sensor
  Integrity Failure) already carries SYS-FC-054 as a member, so this card is
  claiming a membership that was written before it was. The design doc §6 argues
  that once the sensor family exists, CLU-09's *trigger* is arguably one of its
  rules and AHU-FC-062 becomes a member — a single-writer file and someone
  else's edit. Flagged here, not made.
- **`suppresses: []`, and it must stay that way in both directions.** This card
  silences nothing through `suppresses`; the NO_EVAL fan-out is `adjudicates`'
  job and is derived per instance. The stronger constraint runs the other way
  and belongs to whoever writes the next card: per the design doc §2.3, a card
  carrying `adjudicates` MUST NOT appear in any other card's `suppresses`. An
  equipment fault that can silence the sensor rule invalidating it is a cycle,
  and the linter does not check this today.
- **`category: COMFORT_ENERGY` transcribed, not argued.** The design doc §6
  raises `PROTECTIVE` as the more honest label for an adjudicating rule, whose
  delivered value is avoided false alarms and preserved diagnostic coverage
  rather than energy. The reference's own profile for this card says
  COMFORT_ENERGY, AHU-FC-062 and RTU-FC-052 both say COMFORT_ENERGY, and a
  category convention for sensor faults is a library-wide decision rather than
  this card's. Severity 3 likewise: the reference's, and the fan-out argument
  for raising it to 2 is §6's open question.
- **The reference publishes no test vectors for this card,** so all fourteen
  scenarios in `vectors.json` are authored: the healthy pair, the symmetric
  drift pair, three sides of the threshold, the common-mode blind spot, the slow
  ramp that crosses, the short-of-both-delays miss, both sides of the maturity
  edge, the restart-the-clock case, the recovery edge, and the percent-binding
  consequence.
- Operating states and preconditions are declared in frontmatter for host
  enforcement rather than encoded in the block graph, per the library's design
  stance.

## Notes

Read this rule's finding as a work order for two sensors, not one. Step 3.4 of
the [sensor-drift](../../../playbooks/sensor-drift.md) playbook already says so —
"for paired installations (SYS-FC-054 cross-validation), recalibrate both sensors
in the pair" — and it is the only procedure two points can justify. A technician
sent to the member someone guessed at has a 50% chance of recalibrating a
correct sensor against a drifted reference, which makes the pair agree and the
building wrong.

Before dispatching, rule out diagnosis 3 from a trend, because it is free and it
is the most common false positive. Plot the two members for a week. Real drift
opens slowly and does not close; a placement mismatch opens and closes with the
weather, the schedule, or the damper — two "outdoor" sensors that agree at night
and separate every afternoon are telling you one of them is in the sun, and the
repair is a bracket, not a calibration.

The other two members of the family answer different questions about the same
sensor and are worth reading together. SYS-FC-100 catches the transmitter that
has stopped moving, SYS-FC-101 the one that jumps further than the process can,
and this one the one that is quietly wrong — the case both of the others are
structurally blind to, because drift is neither still nor fast. A sensor that
trips this rule and later trips SYS-FC-100 has finished failing.
