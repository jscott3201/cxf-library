---
schema: cxf-library/fault-card/v1
id: FCU-FC-003
name: SAT too high in full cooling
equipment: fcu
status: verified
phase: 1
method: rule
severity: 3
category: EXCESS_CONSUMPTION
confidence: MEDIUM
estimation_method: PROXY_ESTIMATION
source:
  - "HVAC FDD Reference v1.0 §12, FCU-FC-003"
  - "G36 §5.22.6 FC#3 (cited by the reference; clause text not in hand — see Deviations)"
  - "G36 Addendum u, Table 5.16.14.5 (εSAT = 1 °C, AlarmDelay = 30 min — the adopted defaults)"
  - "NISTIR 7365 (the provenance Addendum u gives for those defaults)"
g36: "§5.22.6 FC#3"
clusters: []
suppresses: []
suppressed_by: []
related: [FCU-FC-002, FCU-FC-004]
playbooks: [fcu-faults]
operating_states: "OS#3 (cooling) — host-gated"
preconditions: "The fan must be running and the unit in its cooling operating state. A fan coil with a stopped fan holds stagnant air on the discharge sensor, which reads at room temperature and looks exactly like a coil that has lost capacity. Suspend evaluation for a settling period after any mode change, occupancy transition, or valve-sequence changeover, while the coil has not caught up. `clg_vlv_cmd` must be the command the FCU controller is issuing, not a position feedback: this rule asks whether the loop has run out of capacity to ask for, and a feedback that disagrees with its command is a stuck-actuator finding. `sat_sp` must be a discharge setpoint the sequence is actually holding — many fan coils control to zone temperature and have no discharge setpoint at all, and a host that synthesizes one from the zone setpoint will manufacture faults every mild afternoon; on such a unit omit the rule rather than bind it. Where the host also runs FCU-FC-004, treat a concurrent cooling-coil leak as a separate finding rather than an explanation of this one; the leak makes the discharge colder, not warmer. When any gate is unmet the verdict is NO_EVAL, not healthy."
points:
  - sat
  - sat_sp
  - clg_vlv_cmd
outputs:
  - name: yFault
    description: True while sat has stayed more than sat_error_threshold above sat_sp with the cooling valve commanded above cc_full_threshold, for at least alarm_delay
  - name: yClgFullOk
    description: True while clg_vlv_cmd is above cc_full_threshold — the cooling loop has run out of capacity to ask for, so a setpoint miss is interpretable as a defect. False means the loop still has valve left to give and this rule has no verdict; the host reports NO_EVAL, not healthy
params:
  sat_error_threshold:
    default: 1.0
    unit: "°C"
    description: "The reference's ε_sat — the amount by which the discharge may exceed its setpoint before the miss is real rather than sensor error. ADOPTED: this card states no value (see Deviations). 1.0 °C is G36 Addendum u's εSAT, the supply-air sensor accuracy allowance whose provenance is NISTIR 7365, and is the same value AHU-FC-013 ships. A site with a calibrated discharge sensor may lower it; raising it to quiet a hunting loop hides a tuning problem instead of fixing it"
    cxf: spMiss.t
  cc_full_threshold:
    default: 99.0
    unit: "%"
    description: Cooling coil command above which the loop is treated as having no capacity left to ask for (the reference's `clg_vlv_cmd ≥ 99%`, as a strict `>` — see Deviations)
    cxf: clgFull.t
  alarm_delay:
    default: 1800.0
    unit: s
    description: "Continuous fault persistence required before the alarm asserts. ADOPTED: this card states no AlarmDelay (see Deviations). 1800 s is the AlarmDelay default in Addendum u's AHU AFDD tables and the value AHU-FC-013 ships; the reference's own FCU-FC-001 uses 3600 s, which is that rule's one-hour counting window rather than a chapter-wide default"
    cxf: persist.delayTime
energy_impact:
  affected_subsystem: FCU cooling performance
  savings_range: "2-5% zone cooling energy (HVAC FDD Reference v1.0 §12, FCU-FC-003; no PNNL EEM mapped)"
  climate_sensitivity: cooling-dominant
  runtime_estimation: "The reference gives waste_kw ≈ (sat − sat_sp) / sat_sp × fcu_clg_capacity_kw, transcribed here as published. Read it as a fractional-shortfall heuristic, and note that dividing by a Celsius setpoint makes the ratio depend on the temperature scale (13 °C and 286.15 K give answers a factor of 22 apart), so a host must evaluate it in the units the reference wrote it in. The scale-free form of the same quantity is shortfall_kw = fcu_airflow_m3s × 1.2 kg/m³ × 1.005 kJ/kg·K × (sat − sat_sp): the cooling the zone asked for and did not get. Where the cause is a heat source fighting the coil — a leaking heating valve, FCU-FC-005's fault — that shortfall is matched by an equal heating bill and the waste is real; where the coil or the chilled water is simply short of capacity, the unit wastes nothing at the coil and the cost lands downstream as a zone that never satisfies"
emissions:
  scope: "2"
  method: PROXY_EMISSIONS
verified:
  engine_rev: e2ff2f8
  content_id: "cxf:fnv1a128:f33110926b9fc6d206913b6ce4dea351"
  date: 2026-08-17
---

## Description

The chilled-water valve is wide open and the air leaving the fan coil is still
above its setpoint. The control loop has already asked for everything it has,
so whatever is wrong is not tuning: either the coil cannot deliver, the chilled
water behind it cannot deliver, the fan is not moving air across it, or the
sensor reporting the miss is wrong.

On a fan coil this fault is quiet in a way it never is on an air handler. One
unit under-cooling one hotel room produces a guest complaint, not a trend
review, and the reference's own chapter introduction is blunt about the reason:
fan coils are distributed by the dozens, are rarely instrumented well, and
faults on them persist for long periods before anyone notices. Two to five
percent of a zone's cooling energy is small until it is multiplied by three
hundred rooms.

This is the cooling-side member of the reference's FCU-FC-002/003 pair, and the
pair is the fan coil analog of AHU-FC-007/013. All four rules make the same
statement: an actuator at its stop with the controlled variable still on the
wrong side of its target is evidence of a defect, and until the actuator
saturates it is evidence of nothing.

## Detection Logic

```
yClgFullOk = clg_vlv_cmd > cc_full_threshold      (false ⇒ host reports NO_EVAL)
sp_gap     = sat − sat_sp

yFault = (sp_gap > sat_error_threshold) AND yClgFullOk,
         sustained continuously for alarm_delay
```

Block graph (`rule.cxf.jsonld`):

![FCU-FC-003 block graph](diagram.svg)

`spGap` subtracts the setpoint from the measurement and `spMiss` compares the
excess against `sat_error_threshold`, which is the reference's
`sat > (sat_sp + ε_sat)` rearranged so the allowance stays a single positive
number at one CXF path. `clgFull` is the half that gives the miss its meaning:
a discharge above setpoint at a part-open valve is a control loop doing its job,
and only a loop that has run out of coil is evidence of a defect. Its output
does two things — it feeds `both`, where the conjunction the reference writes is
formed, and it leaves the block as `yClgFullOk`, so a host can tell the two ways
this rule goes quiet apart. Silence with `yClgFullOk` true is a coil that is
keeping up. Silence with it false is a loop that still has valve left to give,
about which this rule has nothing to say — the miss may be real and belongs to a
loop-response rule instead (`valve_just_below_full_threshold` is that vector).

Both comparisons are strict, so a miss sitting exactly on 1.0 °C and a command
parked exactly on 99.0% both read healthy, and the vectors pin three sides of
each. `persist` requires 30 continuous minutes, which is what separates a failed
coil from a morning pulldown or the first minutes after a room comes out of
setback. From a miss already present at load, `delayOnInit = true` puts the
alarm at exactly 1800 s; from an edge mid-run, at exactly 1800 s after that edge
(`miss_opens_mid_run` pins 2400 s).

The graph is the mirror image of FCU-FC-002's, and deliberately so: the same
five blocks, the same two outputs, the same three parameters, the same order of
operations, with the subtraction and the valve swapped. Where the chapter is
asymmetric — the operating state, the climate sensitivity, the emissions scope,
and one entry in the diagnosis list — this card follows the chapter rather than
the symmetry.

## Possible Diagnoses

Transcribed from the reference's FCU-FC-003 card:

1. Cooling coil fouled
2. CHW supply temperature too high
3. Cooling valve stuck closed
4. Fan speed too low for cooling demand

Two notes on that list, because it is not the mirror of FCU-FC-002's.

The reference gives FCU-FC-002 "SAT sensor out of calibration" and does not
repeat it here, but a discharge sensor reading high produces this trace exactly,
it is the cheapest thing on the list to eliminate, and G36's own cooling-side
equivalent (§5.16.14 FC#13) leads its diagnosis list with SAT sensor error.
Check the sensor first; the omission looks like an oversight rather than a
judgment.

Diagnosis 4 needs reading carefully, because lower airflow across a fixed coil
makes the discharge *colder*, not warmer. A fan running slow is a zone-capacity
problem — not enough cold air delivered — which is a different fault from the
one this rule detects. The case where it does present here is the extreme one:
a fan that has stopped, lost its belt, or is blocked by a fouled filter leaves
near-stagnant air on the discharge sensor, which then reads close to room
temperature while the valve pins open. That is also why fan status is the first
precondition on this card.

## Energy Impact

EXCESS_CONSUMPTION, MEDIUM confidence, PROXY_ESTIMATION, with a savings range of
2–5% of zone cooling energy — the reference's own profile for this card, with no
PNNL EEM mapped. What that range buys depends on which diagnosis is true, which
is why confidence is MEDIUM and estimation is PROXY: the rule reads two
temperatures and a command, not airflow, capacity, or power, so both the
reference's `(sat − sat_sp) / sat_sp × fcu_clg_capacity_kw` and the scale-free
enthalpy form need a nameplate capacity or a design airflow that this rule
cannot see.

The branch that matters is whether anything is fighting the coil. If a heating
valve is leaking on the same unit, the shortfall is paid for twice and
FCU-FC-005 is the rule that sees it. If the coil is fouled or the chilled water
is too warm, the fan coil wastes nothing at the coil — it under-delivers, and
the cost moves to the zone, which stays warm, and to the plant, which runs
longer against a load it never satisfies. Cooling-dominant, following the
operating state the rule is evaluated in.

## Emissions Impact

Scope 2, PROXY_EMISSIONS, MEDIUM confidence; the reference gives a typical range
of 50–400 kg CO₂e/yr per fan coil for cooling underperformance, with a marginal
operating emissions rate (MOER) basis. Everything this fault spends is purchased
electricity at the chiller and the pumps. Note the direction of the accounting:
emissions can rise rather than fall when the fault is fixed, because a coil
restored to capacity finally delivers the cooling the room has been asking for.
The honest claim is that this rule buys comfort and diagnosis, and that the
avoided-emissions half belongs to whatever waste the repair uncovers — most
often a leaking heating valve on the same unit.

## Deviations

- **Both tunables are adopted, not transcribed.** The reference's FCU-FC-003
  card states an equation and an operating state and then stops: unlike
  FCU-FC-001 it carries no tunable-parameters row, so neither `ε_sat` nor an
  AlarmDelay has a published default. This card adopts 1.0 °C and 1800 s from
  G36 Addendum u, whose AHU AFDD tables give εSAT = 1 °C (2 °F) and
  AlarmDelay = 30 minutes, and whose defaults trace to NISTIR 7365.
  They are the values AHU-FC-013 ships, which is the rule the chapter README
  names as this one's parent. Both are judgment calls. The 30-minute delay is
  the more debatable: a fan coil has a fraction of an air handler's thermal
  mass and settles far faster, so a site that wants earlier notice can drop
  `alarm_delay` to 900 s without approaching pulldown transients — at the cost
  of catching the last minutes of a long setback recovery. Note that the
  chapter's one published AlarmDelay is FCU-FC-001's 60 minutes, which is that
  rule's one-hour transition-counting window rather than a chapter-wide
  convention, and is not evidence for this card.
- **`clg_vlv_cmd ≥ 99%` becomes a strict `> 99.0`.** CDL `Reals` has no
  `GreaterEqual` or `GreaterEqualThreshold`, so a command parked at exactly
  99.000% reads as not-saturated and the rule stays silent where the reference
  would evaluate it. The exact-equality case has measure zero on a modulating
  command, and the strict form errs toward silence, which is the right direction
  for a rule whose alarm dispatches a technician. The vectors pin all three
  sides (`valve_just_below_full_threshold` at 98.9% and
  `valve_exactly_at_full_threshold` at 99.0% clear,
  `valve_just_over_full_threshold` at 99.5% faulted). A host binding a coarsely
  quantized command — integer percent, or a controller that clamps its output to
  a rounded 99 — should retune `cc_full_threshold` down to 98.9 rather than rely
  on the signal overshooting. Fan coils are the worst offenders for this:
  three-speed unit controllers and two-position valves are common, and on a
  unit whose "valve" is a two-position solenoid this rule should be bound with
  `cc_full_threshold` at something like 50% or omitted entirely.
- **The setpoint comparison is rewritten as a gap comparison.** The reference
  writes `sat > (sat_sp + ε_sat)`. Implemented directly, ε_sat would enter the
  graph as an offset added to the setpoint ahead of a two-signal comparison;
  subtracting first and testing `sat − sat_sp > ε_sat` is the same statement
  with the allowance staying the positive number the reference names, retunable
  at one CXF path. Same rearrangement as AHU-FC-013 and AHU-FC-001. The two
  forms can differ by one ulp on a value straddling the threshold; at 1 °C on a
  sensor rated to ±1 °C this is not observable. It also keeps every literal in
  the rule a positive magnitude, per the library's standing avoidance of
  negative parameters.
- **The strict comparison at `spMiss` is pinned from both sides too.** A miss of
  exactly 1.0 °C reads healthy (`sat_error_exactly_at_threshold`); 1.1 °C
  alarms (`sat_error_just_over_threshold`). Measure zero on a real temperature
  signal, same direction of error as the valve threshold.
- **G36 §5.22.6 is cited but was not read.** The reference sources this card to
  G36 §5.22.6 FC#3, and the chapter README repeats that provenance. That clause
  text is not in hand — the G36 material available to this library is Addendum u
  to Guideline 36-2018 (First Public Review), which carries the AHU AFDD
  sections §5.16.14, §5.17.4, and §5.18.14 but not the fan coil section. So the
  equation, the operating state, and the diagnosis list here are the
  *reference's* transcription of G36, not a direct reading of it, and the
  adopted defaults come from the AHU tables of Addendum u rather than from
  §5.22.6's own internal-variables table, which may well publish different ones.
  This is the card's largest blind spot. If §5.22.6 turns out to specify
  5-minute rolling averages, its own εSAT, or a different AlarmDelay, the
  parameters retune without touching the graph, but the averaging question would
  be a structural change — see the next item.
- **Instantaneous samples, with no averaging.** The reference writes the
  equation on instantaneous points (`sat`, not `SAT_AVG`), and this card
  implements exactly that. Every AHU AFDD section of Addendum u computes its
  signals as 5-minute rolling averages with 1-minute sampling, so §5.22.6
  plausibly does too; if it does, this rule differs from it in the way
  AHU-FC-013 documents. Averaging tolerates a signal whose mean sits outside the
  bound while it keeps crossing back; persistence does not, because an
  oscillating signal resets the timer on every compliant tick and can hide
  indefinitely. The `hunting_loop_never_alarms` vector pins that miss with a
  discharge swinging either side of setpoint at a pinned-open valve. A steady
  miss against a saturated valve — what a fouled coil or warm chilled water
  produces — reads the same under either treatment.
- **Operating states and the settling window are host-side preconditions.** The
  reference scopes this fault to OS#3 (cooling). None of that is in the graph:
  per the library's design stance, operating-state applicability, transition
  windows, and NO_EVAL are host concerns declared in `preconditions`. A verdict
  produced outside the cooling state or inside a transition window is NO_EVAL,
  never healthy. Fan status matters more here than it does on an air handler and
  is the first thing in that list, because the FCU point dictionary carries no
  fan status or fan speed point for the graph to read.
- **`yClgFullOk` is the library's, not the reference's.** The reference writes
  the saturation test as a conjunct of the fault condition, and the graph
  computes exactly that. Exposing the conjunct as a boundary output adds no logic
  and changes no verdict; it lets the host distinguish "the coil is keeping up"
  from "the loop has not saturated, ask me later", which are the same
  `yFault = false` and mean different things — the second is a state in which a
  large setpoint miss can sit unreported by this rule. Same stance and wiring as
  FCU-FC-002's `yHtgFullOk` and FCU-FC-004/005's `yCmdOk`. The other conditions
  that make this rule interpretable — fan running, unit in cooling, `sat_sp` an
  active setpoint — are not computable from the three bound points and stay in
  `preconditions`.
- **The chapter's asymmetries are carried, not smoothed.** FCU-FC-002 and
  FCU-FC-003 are symmetric in equation and structure but not in profile, and
  this card follows the chapter on every point where they differ: emissions
  Scope 2 here against Scope 1 there (nothing on the cooling side burns fuel),
  cooling-dominant against heating-dominant climate sensitivity, OS#3 against
  OS#1, and a diagnosis list that trades FCU-FC-002's "SAT sensor out of
  calibration" for "fan speed too low for cooling demand". Only the diagnosis
  swap looks like an authoring slip rather than a deliberate distinction, and
  the Possible Diagnoses section says so in prose instead of editing the list.
- **The reference's runtime formula is transcribed with a caveat rather than
  corrected.** `waste_kw ≈ (sat − sat_sp) / sat_sp × fcu_clg_capacity_kw`
  divides a temperature difference by a temperature *level*, which makes the
  answer depend on whether the setpoint is expressed in °C, K, or °F. Read
  literally in the library's units (°C), it is a fractional-shortfall heuristic
  and nothing more. `energy_impact.runtime_estimation` keeps the published form,
  flags the scale dependence, and adds the scale-free enthalpy-flow expression
  that AHU-FC-013 uses for the same quantity.
- **Severity 3, category, confidence, and estimation method are the
  reference's.** The chapter card states all four (3/warning, EXCESS_CONSUMPTION,
  MEDIUM, PROXY_ESTIMATION) and the chapter README repeats the severity, so
  nothing here is the library's invention. Note that this fault's air-handler
  parent AHU-FC-013 also sits at 3, so the pair agrees.
- **No published test vectors.** The reference publishes none for this card, so
  `vectors.json` is authored from the equation: three sides of each threshold, a
  sustained saturated-and-missing case, a mid-run onset, a pulldown transient
  shorter than AlarmDelay, a recovery through each term, a setpoint reset that
  closes the gap without the air moving, and the hunting loop that persistence is
  known to miss.
- **`persist.delayOnInit = true`** (Modelica/CDL default is `false`), the
  library's standing choice: a violation already present at load waits out the
  full 30 minutes instead of alarming on the first tick after a controller
  restart. The alarm consequently lands at exactly 1800 s from a cold start in
  the fault, which is what the vectors pin.
- **Frontmatter `clusters`, `suppresses`, and `suppressed_by` are empty.** The
  cluster set defines no FCU cluster and this card does not edit it. The
  relationship to FCU-FC-002 (the mirror), FCU-FC-004 (a cooling leak, which
  makes the discharge colder and so cannot explain this fault), and FCU-FC-005
  (a heating leak, which can) is carried by `related` and by the shared
  playbook.

## Notes

Read `yClgFullOk` before reading `yFault`. On a modulating fan coil it is false
most of the day, and every `yFault = false` under it means "not evaluated", not
"the coil is keeping up".

The vectors are library-authored. The pair worth reading together is
`valve_backs_off_before_delay` and `setpoint_reset_upward_clears_the_miss`. Both
hold the discharge at a steady 18 °C for the whole run and both stay silent, for
different reasons: in the first the loop still has valve left to give, in the
second the sequence moved the target to where the unit already is. Neither is a
defect, and a rule built on the temperature alone would report both.

The setpoint this rule compares against is the one the sequence is actually
holding, which makes it quietly dependent on how the fan coil is controlled. A
unit that controls to zone temperature with no discharge setpoint has nothing to
bind to `sat_sp`, and a host that fabricates one — from the zone setpoint, or
from a design value nobody is holding — will produce a standing alarm on every
mild afternoon. The preconditions say to omit the rule on such a unit rather
than bind it, and that is the common case on older fan coils.

The [fcu-faults](../../../playbooks/fcu-faults.md) playbook orders the service.
Its step 1.2 is the manual version of this rule and its instruction is the right
one: rule out the plant first, because a CHW riser running warm produces this
fault simultaneously on every fan coil it serves, and the fleet-wide pattern is
the cheapest discriminator available. A single unit alarming alone points at the
coil, the valve, or the fan on that unit; step 3.1 covers the coil work.
