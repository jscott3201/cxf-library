---
schema: cxf-library/fault-card/v1
id: VAV-FC-054
name: VAV damper hunting or oscillation
equipment: vav
status: verified
phase: 2
method: rule
severity: 3
category: COMFORT_ENERGY
confidence: LOW
estimation_method: QUALITATIVE_ONLY
source:
  - "HVAC FDD Reference v1.0 §10, VAV-FC-054"
  - "Torabi et al. 2022"
  - "Gunay et al. 2020"
g36: null
clusters: []
suppresses: []
suppressed_by: []
related: [AHU-FC-056, VAV-FC-053]
playbooks: []
operating_states: "all (fan running)"
preconditions: "Supply fan running — a damper in a dead air stream does not oscillate, and a box parked at a fixed position during unoccupied hours produces no crossings either way. Damper position feedback (or, failing that, the position command) available as a live analog signal; a point that only updates on change-of-value with a wide deadband will hide the oscillation entirely. The host must report NO_EVAL for the first eval_window (30 min) after engine start: while the three moving averages fill, each divides by elapsed time rather than by the window, so the crossing count reads as an extrapolated pace and the amplitude as a partial average. This gate is load-bearing, not a formality — alarm_delay (15 min) is half of eval_window, so delayOnInit cannot cover the warm-up and a short burst at startup can reach a verdict (`warmup_burst_asserts` pins it). Host tick interval must lie in [28.6 s, 180 s) with count_scale set to match; 60 s is recommended (see Deviations). When any gate is unmet the verdict is NO_EVAL, not healthy."
points:
  - zone_dmpr_pos
outputs:
  - name: yFault
    description: True while the damper has crossed its own rolling mean more than max_reversals_per_window times per eval_window, with a mean absolute deviation above min_oscillation_amplitude, for at least alarm_delay
params:
  eval_window:
    default: 1800.0
    unit: s
    description: Rolling window the crossings are counted over and the amplitude averaged over (30 min). It drives three moving-average stages — the mean, the crossing rate, and the deviation average — and a host must move all three paths together; count_scale must be retuned with it
    cxf: [muS.delta, xRate.delta, mad.delta]
  max_reversals_per_window:
    default: 10.0
    unit: "1"
    description: Mean crossings per eval_window above which damper motion counts as hunting rather than load following. Each oscillation cycle produces two crossings, so the default is five cycles per half hour
    cxf: xHigh.t
  min_oscillation_amplitude:
    default: 5.0
    unit: "%"
    description: "Rolling mean absolute deviation of damper position above which the swing is large enough to matter. MAD units, not peak-to-peak: the reference's 10% swing is ±5% about the mean, which is a MAD of 5.0 for a square oscillation and 3.2 for a sinusoidal one (see Deviations)"
    cxf: madHigh.t
  count_scale:
    default: 30.0
    unit: "1"
    description: "Rescales the moving average of the one-tick crossing pulse train back into a crossing count: k = eval_window / host tick interval in seconds. The default 30.0 is 1800/60, correct only at a 60 s tick; a host on a different tick MUST retune this or every count is wrong by the ratio of the two intervals"
    cxf: xCount.k
  alarm_delay:
    default: 900.0
    unit: s
    description: Continuous fault persistence required before the alarm asserts (15 min)
    cxf: persist.delayTime
energy_impact:
  affected_subsystem: VAV damper actuator wear
  savings_range: 1-3% of zone energy from inefficient control
  climate_sensitivity: neutral
  runtime_estimation: "none in-rule — QUALITATIVE_ONLY; size the opportunity per Energy Impact Reference §4.4 from hunting hours × zone fan and reheat energy, as for AHU-FC-056. The larger cost is actuator life, which this rule cannot price either"
emissions:
  scope: "2"
  method: QUALITATIVE_EMISSIONS
verified:
  engine_rev: e2ff2f8
  content_id: "cxf:fnv1a128:5f4289e7553426911e4a689b1e3c83a6"
  date: 2026-08-17
---

## Description

The damper never stops moving. A VAV box's flow loop is supposed to find a blade
position that delivers the setpoint and stay there until the setpoint moves; a
hunting box overshoots, corrects, overshoots the other way, and repeats every few
minutes, all day. The zone usually feels fine — the swings average out — so
nobody reports it, and the box quietly strokes its actuator tens of thousands of
extra times a year. That wear is the real cost. The energy penalty is small and
diffuse (the reference puts it at 1–3% of zone energy), but a floating actuator
that has been driven to death takes the zone with it when it fails.

The usual cause is a proportional gain set too high for the box's damper
authority, often a default left in place at commissioning or a controller
replaced with a differently sized part and never retuned. The other causes are
not tuning problems at all: a noisy airflow signal makes a perfectly tuned loop
chase phantom errors, and a duct-static loop fighting a zone-demand loop
produces the same picture with both loops working exactly as written. The
reference puts prevalence at roughly 5%.

The rule watches one point — damper position — and asks two questions about it.
How often does the position end up on the other side of its own half-hour
average, and how far from that average does it typically sit? Frequent crossings
with a large deviation is hunting. Frequent crossings with a small deviation is
dither on a feedback signal. A large deviation with few crossings is a box
following a load.

## Detection Logic

```
muS    = MovingAverage(zone_dmpr_pos, eval_window)            rolling mean position
above  = zone_dmpr_pos > muS                                  which side of the mean
pulse  = (above ≠ previous tick's above)                      one tick wide, one per crossing
count  = MovingAverage(pulse, eval_window) × count_scale       crossings in the trailing 30 min
mad    = MovingAverage(|zone_dmpr_pos − muS|, eval_window)     amplitude, in MAD units

yFault = (count > max_reversals_per_window)
     AND (mad   > min_oscillation_amplitude)
         sustained continuously for alarm_delay
```

Block graph (`rule.cxf.jsonld`):

![VAV-FC-054 block graph](diagram.svg)

`muS` is the spine: one rolling mean feeds both tests. The counting branch
compares the live position against that mean (`above`), and `flip`
(`Logical.Change`) emits a one-tick pulse whenever the answer changes — one
pulse per mean crossing. `pulseInt` and `pulseReal` carry the boolean into the
real domain, where the arithmetic lives.

`xRate` is where the counting happens, and it is worth being precise about how.
`Reals.MovingAverage` is a continuous-time integral mean: it accumulates `u·dt`
and divides by the window. A one-tick pulse of height 1.0 encloses exactly one
tick interval of area, so `n` crossings inside the trailing window give
`xRate = n · dt / eval_window`. Multiplying by `count_scale = eval_window / dt`
= 1800/60 = 30 recovers `n` itself. That trick is AHU-FC-004's, borrowed intact,
and its cost is that `count_scale` is coupled to the host's tick interval — see
Deviations, where the coupling is tighter here than in either predecessor.

The amplitude branch is AHU-FC-056's MAD proxy at one timescale instead of two:
`dev` subtracts the same rolling mean from the live position, `absDev` takes the
magnitude, and `mad` averages that deviation over the same window. The result is
a rolling mean absolute deviation — the engine has no rolling standard
deviation, and MAD is the closest elementary-block statistic (see Deviations for
the peak-to-peak conversion).

Both comparisons are strict. Exactly ten crossings in the window reads clear and
eleven alarms; a deviation sitting exactly on `min_oscillation_amplitude` reads
clear. Both boundaries are pinned exactly rather than by bracketing, because a
square oscillation on a tick-aligned period puts the statistics on exact
doubles: `count_exactly_at_threshold` reads 10.000000 and
`amplitude_exactly_at_threshold` reads 5.000000.

`both` requires the two conditions simultaneously, and `persist` requires that
conjunction to hold for 15 continuous minutes. On a box hunting at the
reference's severe rate that is three or four more cycles — long enough that a
morning warm-up sequence or one aggressive setpoint change does not report.

## Possible Diagnoses

1. PID loop tuning too aggressive — proportional gain too high for the damper's
   authority, or integral time too short for the box's response
2. Airflow sensor noise causing erratic setpoint tracking: the loop is chasing
   measurement noise, and no tuning change fixes a bad velocity pickup
3. Conflicting control signals — the AHU's duct static pressure loop and the
   zone demand loop acting on the same damper with overlapping response times
4. Damper actuator mechanical backlash: the blade lags the command, the loop
   over-drives to compensate, and the resulting limit cycle is mechanical, not
   computational
5. Zone load disturbance near the thermostat — an intermittent heat source
   (a copier, a projector, direct sun through a blind that opens and closes)
   producing a real load the box is genuinely following

## Energy Impact

COMFORT_ENERGY, LOW confidence, QUALITATIVE_ONLY. There is no waste term to
compute from this rule's inputs: it sees a damper position and nothing else, so
it cannot price a stroke. The reference puts the loss at 1–3% of zone energy
from inefficient control — the fan work and reheat energy spent on excursions
that cancel out — and names actuator wear as the affected subsystem, which is
the honest ordering. Confidence is LOW for the same reason as AHU-FC-056: no
controlled study isolates the losses of a hunting loop from the tuning change
that fixes it, and no PNNL measure covers loop stability. Climate-neutral — a
badly tuned loop hunts in any weather. Prevalence ~5%. Runtime estimation
follows Energy Impact Reference §4.4 (hunting hours × zone fan and reheat
energy) applied host-side; this rule contributes the hours.

Per zone the number is small enough to ignore, which is exactly why it goes
unfixed. A building with several hundred boxes and 5% of them hunting has a
dozen or more actuators being consumed years early, and the fix — a gain
setting, applied remotely — costs nothing but the engineer's attention.

## Emissions Impact

Scope 2, QUALITATIVE_EMISSIONS, LOW confidence. Minimal in absolute terms: the
direct emissions of a hunting damper are the marginal fan and reheat energy
above, and the reference records the concern as actuator wear rather than
emissions. The larger indirect term is embodied carbon in actuators replaced
early. Avoided-emissions basis: N/A.

## Deviations

- **Direction reversals → mean crossings, the substitution this rule is built
  on.** The reference counts direction changes of the position signal:
  `reversals = count_direction_changes(zone_dmpr_pos, eval_window)`. Detecting a
  direction change needs the previous sample, and the only block that provides
  one is `CDL.Discrete.UnitDelay`, whose `samplePeriod` is a second parameter
  that must be kept equal to the host's tick — a silent coupling of the same
  family as `count_scale` and one more thing to get wrong. Worse, a raw
  difference has no noise floor: a position feedback quantized to 1% reverses
  direction on essentially every tick it is not moving, so the counter would
  need a deadband the reference never specifies. This graph counts **mean
  crossings** instead: how often the position ends up on the other side of its
  own `eval_window` average.

  The two agree on the signals that matter. A sustained oscillation contains
  exactly two direction reversals and exactly two mean crossings per cycle, so
  for anything periodic the counts are identical — which is why all three
  reference vectors reproduce (`stable_control` counts exactly 3.0,
  `mild_hunting` 7–8, `severe_hunting` exactly 15.0, against the reference's 3,
  8 and 15). They diverge on drift. A monotonic ramp has zero reversals and zero
  crossings — agreement. A ramp with small ripple on it reverses on every ripple
  but may never cross the half-hour mean, so the crossing count under-reads.
  That error is one-directional: this rule goes quiet where a reversal counter
  would speak, and it never invents crossings that no oscillation produced. The
  amplitude test is what makes the trade acceptable — the cases the crossing
  count misses are small-amplitude ripple, which `min_oscillation_amplitude`
  would have rejected anyway.
- **`min_oscillation_amplitude` is restated in MAD units.** The reference's
  default is a 10% swing, which reads naturally as peak-to-peak. The engine has
  no peak detector and no rolling standard deviation; the available statistic is
  the rolling mean absolute deviation of AHU-FC-056. For a square oscillation of
  ±A about the mean, MAD = A exactly, so the reference's 10% peak-to-peak
  becomes **5.0 MAD** — the default. For a sinusoid of amplitude A,
  MAD = 2A/π = 0.637 A, so a 10% peak-to-peak sine has a MAD of 3.2 and would
  need to reach 15.7% peak-to-peak to trip this threshold. The default therefore
  matches the reference exactly for square-ish limit cycles (what a floating
  actuator driven by an on/off signal actually produces) and is conservative for
  smooth ones; a site that wants sine-equivalence sets
  `min_oscillation_amplitude` to 3.2. AHU-FC-056 restated its own threshold in
  MAD units for the same reason — from a standard deviation rather than a
  peak-to-peak swing — and its Deviations carry that factor table.
- **Nyquist: this rule cannot run at the library's usual 300 s tick.**
  `above` can change at most once per tick, so the fastest crossing rate a host
  can observe is one per tick and the ceiling on the count is `eval_window/dt`.
  At 300 s that ceiling is 6, below the threshold of 10, and the rule could
  never fire no matter how hard the box hunted — RTU-FC-050's failure mode
  exactly, caught here before the vectors were written. The vectors run at
  `step_s = 60`, where the ceiling is 30 (`fast_but_shallow` and the two
  amplitude-boundary vectors sit on it). A legal deployment needs
  `dt ≥ eval_window/63` ≈ **28.6 s** (the moving average's 64-checkpoint ring
  holds `eval_window/dt + 1` entries) and `dt < eval_window/max_reversals` =
  **180 s** for the threshold to be reachable at all. Detection well before the
  ceiling wants several times that headroom, so 60 s is the recommended value
  and the only one these vectors exercise.
- **`count_scale` is coupled to the host's tick interval, and the failure is
  silent.** `k = eval_window / dt`, so a host ticking every 120 s must set
  `count_scale` to 15.0. Left at 30.0 it would report double the true count and
  alarm on six crossings per window. This is AHU-FC-004's and RTU-FC-050's
  deployment constraint verbatim, and it is worse here because it interacts with
  the Nyquist band above: the tick, `count_scale`, and `eval_window` are three
  numbers that must be changed together, and a mis-set `count_scale` produces a
  plausible-looking count rather than an error.
- **`eval_window` binds three CXF parameter paths** — the mean (`muS.delta`),
  the crossing rate (`xRate.delta`), and the deviation average (`mad.delta`).
  AHU-FC-056 bound two paths per window for the same reason; a host must set all
  three together, and must recompute `count_scale` at the same time. Splitting
  them changes what the statistic means: a mean over one window compared against
  deviations averaged over another is not a MAD of anything.
- **Rolling count built from a moving average, because the block set has no
  windowed counter.** `Integers.OnCounter` counts monotonically from a reset and
  has no window, so "crossings in the trailing half hour" would need the host to
  drive a reset every half hour — which turns a rolling count into a tumbling
  one and makes the verdict depend on where the boundary fell. AHU-FC-004's
  reasoning and the same trade, including its half-open window: a crossing
  exactly `eval_window` old has just left the count.
- **`Reals.MovingAverage` is a continuous-time integral mean, not a sample
  mean.** The engine accumulates `u·dt` forward-Euler and divides by the window
  (`reals_filters.rs`), so hand-computed sample statistics do not match it
  exactly and every assertion edge in `vectors.json` was derived by replaying
  the graph at the pinned engine rev rather than by closed-form arithmetic.
- **Warm-up NO_EVAL is load-bearing, and a warm-up transient can assert.**
  While `t < eval_window` all three averages divide by elapsed time rather than
  by the window, so eight crossings in the first ten minutes read as a count of
  24 — the pace, extrapolated — and the deviation average is taken over a
  fraction of the window. `alarm_delay` (900 s) is half of `eval_window`, so
  `delayOnInit = true` cannot cover the gap the way it does in AHU-FC-004:
  `warmup_burst_asserts` shows `yFault` going true at t = 1140 s on the strength
  of eight crossings and clearing at t = 1440 s as the divisor grows, with the
  settled count reading 8 — the reference's own NO_FAULT case. The host
  precondition is what keeps that off an operator's screen, and it is not
  optional in this card (RTU-FC-050 precedent).
- **Startup artifact: a spurious first-tick pulse, which costs nothing.** On the
  first tick `muS` outputs 0.0 (it has integrated nothing), so any positive
  damper position makes `above` true, and `Logical.Change` compares that against
  `pre_u_start` and emits a pulse at t = 0. It does not reach the count: the
  moving average integrates `u·dt` and `dt` is zero on the first tick, so the
  pulse encloses no area. `flip.pre_u_start` is written explicitly as `false` in
  the CXF rather than left to the engine default (which is also `false`) and is
  deliberately not exposed as a card parameter, since nothing it can do survives
  past tick 0. AHU-FC-004 documents the same artifact.
- **A perfectly steady damper produces exactly one crossing.** While the window
  fills, `muS` runs a hair below a constant input (its divisor is elapsed time
  plus a 1 ms guard), so `above` is true; when the window fills, the mean equals
  the input exactly, the strict comparison goes false, and `flip` emits one
  pulse. `stable_position` pins it: the count reads 1.0 against a threshold of 10
  for one window, then ages back to zero. Harmless, but it is why the count of a
  quiet box reads 1 rather than 0 for the first half hour it is quiet.
- **Neither statistic drops when the hunting stops; both decay across the
  trailing window.** The count falls only as old crossings age out of
  `eval_window`, and `mad` falls only as the flat stretch dilutes the average, so
  the alarm outlives the fix by design and the release time is a property of the
  window rather than of the repair. In `recovery_clears` the count gets there
  first: five of the fifteen crossings must leave the window at one per 120 s, so
  it reaches exactly 10.0 and releases 600 s after the last swing, while `mad`
  needs 840 s. Which branch releases depends on how far above its threshold each
  statistic was sitting; the alarm clears on whichever crosses first. This is
  RTU-FC-050's "how long a crossing survives" property — what the rule reports is
  oscillation sustained above both thresholds, not every excursion through them.
- **The reference's three test vectors are statistical summaries, not tick
  traces** (3 reversals/5% NO_FAULT; 8 reversals/8% NO_FAULT; 15 reversals/20%
  FAULT). Each is re-expressed as a damper trajectory that produces the stated
  statistics — `stable_control`, `mild_hunting`, `severe_hunting` — following
  AHU-FC-056's treatment of the same problem. `mild_hunting` lands on 7–8
  crossings rather than exactly 8, because a symmetric square wave on a 60 s
  grid cannot place 8 crossings in a 1800 s window; the rolling count alternates
  between the two neighbouring integers. The remaining ten vectors — both
  boundary pairs, both single-condition pins, the startup artifact, the warm-up
  artifact, the transient, and the recovery — are authored here.
- **`count_just_over_threshold` uses an asymmetric duty cycle**, one tick high
  in every five, because a symmetric square wave on a 60 s tick jumps from 10
  crossings per window (360 s period) straight to 15 (240 s period) with nothing
  in between. Skewing the duty cycle places exactly 12 crossings in the window
  while keeping the mean between the two levels, which is what the crossing test
  requires.
- **`playbooks: []`.** Nothing in `playbooks/` covers control-loop tuning —
  the gap AHU-FC-056 recorded when it landed. A loop-tuning playbook can adopt
  both faults when it is written; the remediation is the same procedure at two
  scales.
- **`related` adds VAV-FC-053.** The reference's Related row lists AHU-FC-056
  only, which this card keeps — it is the same instability one level up, at the
  air handler's supply air temperature loop. VAV-FC-053 is added because the two
  are the box-mechanics pair: FC-053 asks whether the flow loop reaches its
  setpoint, FC-054 asks whether it can stay there.
- **Method stays `rule` per the reference**, even though the sibling AHU-FC-056
  is labelled `statistical` and this rule computes two rolling statistics. The
  distinction the reference is drawing is that the crossing count is a
  deterministic count of events, not an inference from a distribution; nothing
  here estimates a parameter or compares against a learned baseline. Severity 3
  (warning) and phase 2 are the chapter 10 card's; its §5.8.2 index carries no
  severity column.
- Operating states are declared, not gated: the reference marks the fault
  applicable in every state with the fan running, and the graph has nothing to
  exclude.
- `persist.delayOnInit = true` (Modelica/CDL default is `false`), the library's
  standing choice: an oscillation already in progress at load waits out the full
  15 minutes instead of alarming on the first tick after a controller restart.

## Notes

Bind position feedback where the box has it, and know what you lose when it does
not. Hunting is a property of the control signal, so a rule bound to the damper
*command* still catches diagnoses 1, 2, 3 and 5 — the loop is what is
oscillating. What command-binding cannot see is diagnosis 4: backlash produces a
blade that lags and overshoots while the command looks calmer than the motion.
The point dictionary carries the same caveat on `zone_dmpr_pos` generally; for
this rule specifically, a command-bound instance is a legitimate deployment with
one diagnosis removed from its reach.

Check the airflow signal before touching the gains. Diagnosis 2 produces
textbook hunting statistics with a perfectly tuned loop behind it, and the two
are indistinguishable from this rule's output alone — the same warning
AHU-FC-056 carries about its SAT sensor. Trend the box's measured flow next to
the position: control hunting is smooth and roughly periodic, a noisy velocity
pickup is neither. Retuning a loop to compensate for a bad measurement makes the
loop sluggish and leaves the noise where it was.

Diagnosis 5 is the case where nothing is broken. A conference room with a
projector, or a perimeter zone with a blind that opens at ten and closes at two,
presents a real intermittent load, and a box that follows it is doing its job.
The reference's 30-minute window helps here: a genuine load disturbance produces
a handful of large excursions, not ten crossings of the running mean. If the
count is marginal and the amplitude is large, look at the zone before looking at
the controller.

The cross-check for diagnosis 3 is the number of zones. One box hunting alone is
that box's tuning, its actuator, or its flow sensor. A dozen boxes on the same
trunk hunting together is the duct static pressure loop or its reset fighting
them all, and no amount of zone-level retuning will settle it. AHU-FC-056 is the
same pathology at the other altitude — scatter inside a single loop, measured at
the air handler's supply air temperature instead of at a damper — and a plant
that trips both is one badly tuned system, not two coincidences.
