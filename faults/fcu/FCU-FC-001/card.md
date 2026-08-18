---
schema: cxf-library/fault-card/v1
id: FCU-FC-001
name: Excessive operating state changes
equipment: fcu
status: verified
phase: 1
method: rule
severity: 3
category: COMFORT_ENERGY
confidence: LOW
estimation_method: QUALITATIVE_ONLY
source:
  - "HVAC FDD Reference v1.0 §12, FCU-FC-001"
  - "G36 §5.22.6 FC#1"
  - "G36 §5.16.14 Table 5.16.14.7 (ΔOS MAX provenance, per Addendum u public review)"
g36: "§5.22.6 FC#1"
clusters: [CLU-01]
suppresses: []
suppressed_by: []
related: [AHU-FC-004]
playbooks: [fcu-faults]
operating_states: "OS 1–4 (all)"
preconditions: "The operating_state encoding must be stable for the life of the deployment — re-mapping the enum mid-stream registers as a transition on every unit whose state moved, across the whole building at once. count_scale must equal count_window divided by the host's tick interval; the shipped 20.0 is right only on a 180 s tick, and a wrong value produces a plausible number rather than an error (see Deviations). The host tick must sit inside 57.15 s ≤ dt ≤ 450 s for the count to be both retained and reachable. Operator activity is not a fault: commissioning, manual mode forcing, and scheduled occupancy testing must be excluded host-side, since a deliberate mode change counts the same as an oscillation — this matters more on an FCU than on an AHU, because a guest or tenant at a wall thermostat produces exactly that signal. Warm-up evaluability is signalled in-rule by yWindowFull: while it is false the count is an extrapolated rate rather than a completed-hour count, and the verdict is NO_EVAL, not healthy. The same is true whenever any gate above is unmet."
points:
  - operating_state
outputs:
  - name: yFault
    description: True while the number of operating-state transitions in the trailing count_window has stayed above os_max for at least alarm_delay, counted over a window that has actually filled
  - name: yWindowFull
    description: Evaluability signal — true once model time has reached count_window, which is the tick the moving average starts dividing by the window rather than by elapsed time; false means NO_EVAL and the host must ignore yFault
params:
  os_max:
    default: 7.0
    unit: "1/h"
    description: Transitions per hour above which the unit counts as unstable rather than load-following (the chapter's OS_MAX, and G36's ΔOS MAX)
    cxf: cntHigh.t
  count_window:
    default: 3600.0
    unit: s
    description: Trailing window the transitions are counted over (1 h). It also fixes the units of os_max and the length of the warm-up gate, so both paths must move together; a host that shortens it must retune count_scale with it and read os_max as transitions per window rather than per hour
    cxf: [rate.delta, windowFull.delayTime]
  count_scale:
    default: 20.0
    unit: "1"
    description: "Rescales the moving average of the one-tick pulse train back into a transition count: k = count_window / host tick interval in seconds. The default 20.0 is 3600/180, correct only at a 180 s tick; a host on a different tick MUST retune this or every count is wrong by the ratio of the two intervals"
    cxf: count.k
  alarm_delay:
    default: 3600.0
    unit: s
    description: Continuous fault persistence required before the alarm asserts (the chapter's AlarmDelay, 60 min)
    cxf: persist.delayTime
energy_impact:
  affected_subsystem: FCU control loop efficiency
  savings_range: 1-3% zone energy from cycling losses
  climate_sensitivity: neutral
  runtime_estimation: "none in-rule — QUALITATIVE_ONLY; size the opportunity per Energy Impact Reference §4.4 from unstable hours × FCU coil and fan power, as for AHU-FC-004"
emissions:
  scope: "1+2"
  method: QUALITATIVE_EMISSIONS
verified:
  engine_rev: e2ff2f8
  content_id: "cxf:fnv1a128:db6929d05cee5a6cd064e2a6dcf3b1d3"
  date: 2026-08-17
---

## Description

A fan coil unit that walks between heating, deadband, cooling, and off more
than a few times an hour is not following load. Load does not move that fast in
a hotel room. What moves that fast is a threshold with nothing to hold the unit
on one side of it: a heating setpoint and a cooling setpoint too close
together, a zone sensor that jitters across the changeover point, or a wall
thermostat someone keeps adjusting.

Each transition costs a little. Valves stroke, the fan restarts or changes
speed, and air that was being warmed a minute ago is being cooled a minute
later. The energy is spent on work that cancels itself and the wear is real,
but on one unit the numbers are small — which is exactly why this fault
survives. Nobody watches one FCU. A building with three hundred of them has
some number oscillating right now, and the only way to find them is to count.

This is AHU-FC-004's rule at zone scale, and the arithmetic is the same. What
differs is the equipment: an FCU is faster, cheaper, and more numerous than an
air handler, so the tick this rule runs on has to be short enough to see zone
cycling and the count has to be honest about what it can and cannot resolve.

## Detection Logic

```
pulse        = (operating_state ≠ previous tick's operating_state)   one tick wide
count        = MovingAverage(pulse, count_window) × count_scale      transitions in the trailing hour
yWindowFull  = model time ≥ count_window                             (false ⇒ host reports NO_EVAL)
yFault       = (count > os_max AND yWindowFull), sustained continuously for alarm_delay
```

Block graph (`rule.cxf.jsonld`):

![FCU-FC-001 block graph](diagram.svg)

`chg` is the only block that touches the state value, and all it asks is
whether the value moved. Its `up` and `down` outputs are declared for
completeness and left unconnected — which state the unit moved to says nothing
about whether it is oscillating. `pulseInt` and `pulseReal` carry the one-tick
boolean into the real domain, where the arithmetic lives.

`rate` is where the counting happens. `Reals.MovingAverage` is a
continuous-time integral mean: it accumulates `u·dt` and divides by the window.
A one-tick pulse of height 1.0 therefore encloses exactly one tick interval of
area, so `n` transitions inside the trailing hour give
`rate = n · dt / count_window`. Multiplying by `count_scale = count_window / dt`
= 3600/180 = 20 recovers `n` itself. That is the whole trick, and its cost is
that `count_scale` is a property of the host's clock rather than of the
building — see Deviations.

`cntHigh` applies the strict threshold, so exactly seven transitions an hour
reads clear and eight alarms. On a signal that can only take integer values in
steady state that boundary is unambiguous rather than a measure-zero
technicality, and the arithmetic lands on it exactly: `20.0 × (7 × 180 / 3600)`
evaluates to precisely 7.0 in IEEE-754, which is what makes
`seven_per_hour_stays_clear` a real pin.

The branch across the top is the part AHU-FC-004 does not have. `alwaysOn`
feeds a `TrueDelay` of one `count_window`, so `windowFull` goes true at exactly
t = 3600 s — the same instant the moving average stops dividing by elapsed time
and starts dividing by the window. It goes two places: into `gate` as a term of
the fault condition, and out of the block as `yWindowFull`. A host that ignores
the output still gets the right verdict, because the gate holds the alarm down;
a host that reads it learns the difference between "not faulted" and "cannot
tell yet", which the boolean alone does not carry.

`persist` then requires the gated count to stay high for a full hour. The
earliest this rule can assert anything is therefore 7200 s: one hour to fill
the window, one hour of sustained excess. `eight_per_hour_trips` lands on
exactly that instant.

## Possible Diagnoses

1. Deadband between heating and cooling too narrow — the condition that ends
   the heating mode is the condition that starts the cooling one, so the unit
   flips back as soon as it has finished acting
2. Conflicting zone demands — a perimeter room with solar gain on one side and
   an exterior wall on the other asks for both, and the unit alternates
3. Sensor noise causing mode oscillation — one poorly located or intermittent
   zone sensor crosses the changeover threshold every few minutes and the
   sequencing logic faithfully obeys

## Energy Impact

COMFORT_ENERGY, LOW confidence, QUALITATIVE_ONLY. There is no waste term to
compute from this rule's inputs — it sees a state index and nothing else, so it
cannot say what any transition cost. The reference puts the loss at 1–3% of
zone energy, split between actuator wear and the transitions themselves, where
a coil is charged and then abandoned before the air stream has settled.
Confidence is LOW because no controlled study isolates cycling losses from the
deadband change that fixes them, and no PNNL measure covers zone-level
sequencing stability. Climate-neutral: a threshold with no deadband oscillates
in any weather, though the shoulder seasons are when a perimeter FCU spends the
most time near one. Runtime estimation follows Energy Impact Reference §4.4
(unstable hours × FCU coil and fan power) applied host-side; this rule
contributes the hours.

## Emissions Impact

Scope 1 + 2, QUALITATIVE_EMISSIONS, LOW confidence; on the order of
5–15 kg CO₂e/yr per FCU from cycling losses. Both scopes appear because the
transitions being counted cross between them — a unit oscillating between
heating and cooling burns a little gas at the boiler and a little electricity at
the chiller for the same hour of indecision. The magnitude is small enough that
the number is offered as an order of magnitude rather than an estimate, and the
reason to chase it is the fleet: three hundred units at 10 kg CO₂e/yr is three
tonnes, and the fix is a setpoint change. Avoided-emissions basis: N/A.

## Deviations

- **The reference card names no points; `operating_state` is our binding.** The
  chapter 12 card states the logic (`os_transitions_per_hour > OS_MAX`) and the
  tunables and stops, with no Required Points table. This rule binds the
  host-derived integer point `operating_state`, which the FCU dictionary
  already carries for exactly this purpose. Only transitions are consumed and
  no value is ever interpreted, so any stable enumeration binds; the dictionary
  recommends G36 §5.22's OS#1–#4 index for an FCU and requires only that the
  encoding not change under the rule's feet.
- **Rolling count built from a moving average, because the block set has no
  windowed counter.** `Integers.OnCounter` counts monotonically from a reset
  and has no window, so expressing "transitions in the trailing hour" with it
  would need the host to drive a reset every hour — which would turn the
  rolling count into a tumbling one and make the verdict depend on where the
  hour boundary fell. The moving average is genuinely rolling, at the price of
  the scale factor described next.
- **`count_scale` is coupled to the host's tick interval, and the default is
  not AHU-FC-004's.** `k = count_window / dt`, and 20.0 is correct only at the
  180 s tick the vectors use (3600/180). AHU-FC-004 ships 12.0 for a 300 s
  tick; the two cards are the same rule with different clocks, and copying a
  `count_scale` between them is the single most likely way to deploy this
  wrong. A mis-set value produces a plausible-looking number rather than an
  error: an FCU changing state 20 times an hour, read on a 60 s tick with
  `count_scale` left at 20.0, reports a steady 6.7 per hour and never alarms.
- **The legal tick band is 57.15 s ≤ dt ≤ 450 s, and both ends bite.** The
  lower end is the `MovingAverage` ring: each instance keeps 64 checkpoints and
  a window of `count_window` retains `count_window/dt + 1` of them, so
  `count_window/dt ≤ 63` and `dt ≥ 3600/63 = 57.15 s`. Past that the block
  warns once and silently drops the oldest in-window sample, which shortens the
  effective window and inflates the count. The upper end is the change counter:
  `Integers.Change` can observe at most one transition per tick, so a window
  holds at most `count_window/dt` of them, and a strict `count > 7` needs 8 to
  be reachable — `dt ≤ 3600/8 = 450 s`. At the shipped 180 s tick the window
  holds 20 checkpoints and the ceiling is 20 transitions an hour, comfortably
  inside both bounds.
- **AHU-FC-004 states the ring bound as 56.25 s (3600/64); the correct figure
  is 57.15 s (3600/63).** The retained set includes one checkpoint at or before
  the window's trailing edge, so a window spanning `n` ticks needs `n + 1`
  slots, not `n`. The difference matters only for a host ticking within a
  second of the bound, but the number in this card is the checked one.
- **A change counter aliases, and the count is clipped rather than wrong-signed.**
  Above the ceiling the rule under-reports: a unit genuinely changing state
  every 90 s on a 180 s tick shows at most 20/h, and a unit whose state returns
  to its previous value within one tick shows nothing at all.
  `sustained_thrash_at_nyquist_ceiling` pins the saturated case — the count
  reads exactly 20.0 and the alarm still lands at 7200 s, because the alarm
  path is limited by the window and the delay rather than by how far above
  `os_max` the count sits. Clipping therefore delays nothing and hides nothing
  at the shipped tick; it only makes the reported number a floor. A host that
  displays the count to an operator should say so.
- **Startup artifact (a): a spurious first-tick pulse, which costs nothing.**
  `Integers.Change` compares against `pre_u_start` on the first tick, so a unit
  that loads in OS#3 registers a change at t = 0. It does not reach the count:
  the moving average integrates `u·dt`, and `dt` is zero on the first tick, so
  the pulse encloses no area. The `startup_pulse_is_inert` vector pins this.
  `chg.pre_u_start` is written explicitly as 0 rather than left to the engine
  default (which is also 0) and is deliberately not a card parameter, since
  nothing it can do survives past tick 0.
- **Startup artifact (b): the first hour reads as a rate, and here the graph
  handles it rather than the host.** While `t < count_window` the moving
  average divides by elapsed time rather than by the window, so two changes in
  the first six minutes read as 20/h — the pace, extrapolated. AHU-FC-004
  leaves that to a frontmatter precondition and relies on `delayOnInit` to keep
  the artifact away from a verdict. This card computes the same condition in
  the graph, because it is computable: `alwaysOn` → `windowFull` is true
  exactly when `t ≥ count_window`. `warmup_burst_masked_by_window_gate` is the
  case that covers warm-up: nine transitions inside the first half hour hold
  `cntHigh` true from the second tick, `gate` stays down until 3600 s, and by
  3960 s the burst has aged out and the count has fallen back to 7.0 — so the
  extrapolated rate never contributes more than two ticks toward `alarm_delay`.
- **The window gate makes this rule slower than AHU-FC-004 and that is
  deliberate.** With `gate` in the path the earliest possible assertion is
  `count_window + alarm_delay` = 7200 s. AHU-FC-004, whose `cntHigh` feeds
  `persist` directly, can assert at 3900 s on the strength of a first-hour
  extrapolation that its frontmatter then tells the host to discard. Requiring
  a completed hour before the clock starts is what the reference's
  "transitions per hour" actually says, and it costs an hour of detection
  latency on a fault whose alarm delay is already an hour.
- **`BooleanToInteger` → `IntegerToReal` where `Conversions.BooleanToReal`
  would do it in one block.** The pair is kept for shape parity with
  AHU-FC-004, so the two cards read as the same rule and a reviewer comparing
  them sees only the differences that matter. It costs one block instance and
  no behavior.
- **Strict `>` on a discrete count.** `os_max` is compared with
  `Reals.GreaterThreshold`, so exactly 7 transitions an hour is clear and 8
  alarms — the chapter's `> OS_MAX` read literally. The arithmetic is exact at
  the boundary rather than approximately exact, and both sides are pinned
  (`seven_per_hour_stays_clear`, `eight_per_hour_trips`).
- **The counting window is half-open.** `rate` compares the accumulated
  integral now against its value one `count_window` ago, so a transition
  exactly `count_window` old has just left the window. Nothing in the reference
  speaks to this; it matters only for a unit sitting right on the threshold,
  and it errs toward silence.
- **`alarm_delay` equals `count_window`**, both at 60 min per the chapter's
  tunables line. Note this is not G36's 30-minute `AlarmDelay`: the chapter
  states 60 min for this card and the chapter governs.
- **`alwaysOn.k` is written explicitly and is not a card parameter.**
  `Logical.Sources.Constant` has no default for `k`, so the value is required
  in the document; exposing it for `set_param` would let a host switch the
  evaluability signal off, which is not a tuning decision.
- **No test vectors are transcribed, because the reference publishes none.**
  The chapter card carries no vector table, so the entire suite is authored
  from the equation. Every assertion edge was derived by replaying the graph at
  the pinned engine rev rather than by closed-form arithmetic — the moving
  average is a continuous-time integral mean, and its warm-up and decay
  trajectories do not match hand-computed sample statistics.
- **CLU-01 membership.** A zone unit swapping between heating and cooling
  every few minutes is doing both within any window long enough to matter, so
  AHU-FC-004's syndrome argument carries over. This card originally shipped
  the case as a proposal (the cluster index is not this card's to edit); the
  index owner accepted it, and `clusters/clusters.json` now lists FCU-FC-001
  in CLU-01, matching the frontmatter.
- `persist.delayOnInit = true` and `windowFull.delayOnInit = true` (Modelica/CDL
  default is `false`), the library's standing choice: a unit already cycling
  hard at load waits out both hours instead of alarming on the first tick after
  a controller restart. `windowFull` depends on it for its meaning — with
  `delayOnInit = false` the constant-true input would assert on tick 0 and the
  signal would say the window was full when it was empty.
- **`related` is the library's, not the reference's.** The chapter 12 card
  carries no Related row. AHU-FC-004 is named because it is the same rule one
  level up the air path; the link is one-way, since AHU-FC-004 was verified
  before this card existed and its frontmatter is not edited here. No intra-FCU
  link is claimed: a unit that cannot hold its discharge setpoint (FCU-FC-002)
  may well hunt, but that is a plausible story rather than an observed
  co-occurrence, and the shared playbook already carries the family.
- Severity 3 (warning) and method `rule`, per the reference's chapter 12 card
  and the FCU index; its §5.8.5 index carries no severity column.
- Operating states OS 1–4 are declared, not gated: the chapter marks the fault
  applicable in every state, and there is nothing for the graph to exclude.

## Notes

The fix is a deadband, and it is remote and free. Step 2.1 of the
[fcu-faults](../../../playbooks/fcu-faults.md) playbook puts the minimum at
2 °F (1 °C) between the heating and cooling setpoints and tells you to check for
sensor noise before you widen anything, which is the right order: widening a
deadband around a jittery input hides the noise without fixing it, and a sensor
that jumps will eventually jump wide enough to cross any deadband. Step 4.2 is
the confirmation — transitions back under 7/h — which is this rule reading
clear.

The reason to run this rule at all is fleet triage. A single oscillating fan
coil is worth a few dollars a year; the list of which forty units out of three
hundred are oscillating is worth an afternoon, because they will almost all
share one cause. Sort by count, not by alarm: the rule reports a boolean, but
the number behind it (`count.y`, available through the engine's point list) is
what ranks the work.

`count_scale` deserves a line in any deployment checklist. It is the only
parameter here whose correct value is a property of the host's clock rather
than of the building, and the failure mode is silent. The second line should be
the tick itself: 57.15 s at the bottom, 450 s at the top, and a value near the
middle if the units being watched are the fast ones.
