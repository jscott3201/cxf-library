---
schema: cxf-library/fault-card/v1
id: AHU-FC-056
name: Supply air temperature hunting / oscillation
equipment: ahu
status: verified
phase: 2
method: statistical
severity: 3
category: COMFORT_ENERGY
confidence: LOW
estimation_method: QUALITATIVE_ONLY
source:
  - "HVAC FDD Reference v1.0 §9, AHU-FC-056"
  - "Research-backed; PID instability detection"
g36: null
clusters: []
suppresses: []
suppressed_by: []
related: [AHU-FC-004, VAV-FC-054]
playbooks: []
operating_states: "all (fan running)"
preconditions: "Supply fan running — SAT scatter means nothing in a dead air stream. No verdict within long_window (2 h) of engine start: both moving averages divide by elapsed time while their windows fill, so the baseline is not yet established and the ratio test can be satisfied by a warmup artifact — the host reports NO_EVAL for that period. SAT sensor integrity is a precondition, not a conclusion: a sensor that flatlines and then jumps produces this same scatter signature (diagnosis 4), so sensor checks clear first. When any gate is unmet the verdict is NO_EVAL, not healthy."
points:
  - sat
outputs:
  - name: yFault
    description: True while short-window SAT deviation has stayed above oscillation_threshold and above k × the long-window deviation for at least alarm_delay
params:
  oscillation_threshold:
    default: 1.2
    unit: "°C"
    description: "Short-window mean absolute deviation of SAT above which scatter counts as oscillation. MAD units, not standard deviation: the reference's 1.5 °C rolling std-dev corresponds to 1.20 MAD under a Gaussian reading (std = 1.2533 × MAD) and 1.35 under a pure-sine reading (std = 1.1107 × MAD); the default takes the lower bound"
    cxf: absHigh.t
  window:
    default: 900.0
    unit: s
    description: Short (scatter) window, 15 min — drives both the mean stage and the deviation-averaging stage; a host must move both paths together
    cxf: [muShort.delta, madShort.delta]
  long_window:
    default: 7200.0
    unit: s
    description: Long (baseline) window, 2 h — drives both the mean stage and the deviation-averaging stage; a host must move both paths together
    cxf: [muLong.delta, madLong.delta]
  k:
    default: 2.0
    unit: ratio
    description: Multiple of the long-window deviation the short window must exceed for scatter to count as a departure from the unit's own baseline
    cxf: scaledLong.k
  alarm_delay:
    default: 1800.0
    unit: s
    description: Continuous fault persistence required before the alarm asserts (30 min)
    cxf: persist.delayTime
energy_impact:
  affected_subsystem: AHU control loop efficiency
  savings_range: 1-3% of AHU energy while hunting, from valve and damper cycling losses
  climate_sensitivity: neutral
  runtime_estimation: "none in-rule — QUALITATIVE_ONLY; size the opportunity from Energy Impact Reference §4.4 (hunting hours × AHU coil and fan power), not from this rule's output"
emissions:
  scope: "2"
  method: QUALITATIVE_EMISSIONS
verified:
  engine_rev: e2ff2f8
  content_id: "cxf:fnv1a128:4a421aa419bd1f1fe626202c9cccf494"
  date: 2026-08-17
---

## Description

Supply air temperature swings around its setpoint instead of settling on it.
The signature is scatter, not offset: SAT may average exactly on setpoint while
crossing it every few minutes. An oscillating loop keeps its valve or damper
in continuous motion, wearing the actuator and burning coil energy on
overshoot it then has to undo. The usual cause is proportional gain set too
high (or integral time too short) for the coil's actual authority, often after
a valve or actuator was replaced with a differently sized part and the loop was
never retuned.

The rule compares the unit against itself. Short-window scatter alone is a poor
test — some AHUs simply run noisier than others — so a fault requires the
recent scatter to be both absolutely large and several times the unit's own
established baseline. Present in roughly 5% of buildings. Statistical method,
severity 3 (warning): nothing here is unsafe, and the comfort penalty is
usually mild, but the loop is doing work it does not need to do.

## Detection Logic

```
muShort  = MovingAverage(sat, window)                 muLong  = MovingAverage(sat, long_window)
madShort = MovingAverage(|sat − muShort|, window)     madLong = MovingAverage(|sat − muLong|, long_window)

yFault   = (madShort > oscillation_threshold)     absolute scatter test
       AND (madShort > k × madLong)               onset test: scatter far above this unit's baseline
           sustained continuously for alarm_delay
```

Block graph (`rule.cxf.jsonld`):

![AHU-FC-056 block graph](diagram.svg)

Two identical chains run at two timescales. Each takes the moving average of
SAT over its window (`muShort`, `muLong`), subtracts it from the live reading,
takes the absolute value (`errShort`/`devShort`, `errLong`/`devLong`), and
averages that deviation over the same window again (`madShort`, `madLong`).
The result is a rolling mean absolute deviation — the engine has no rolling
standard deviation, and MAD is the closest elementary-block proxy (see
Deviations for the conversion). `absHigh` applies the absolute threshold to the
short window; `scaledLong` and `relHigh` apply the ratio test. Both comparisons
are strict, so scatter sitting exactly on the threshold or exactly at k times
the baseline does not trip the rule. `persist` requires 30 minutes of
continuous violation, which rides out one-off step disturbances — an economizer
changeover or a setpoint reset spikes `madShort` for about one short window and
then flushes out, well short of the timer.

## Possible Diagnoses

1. PID loop poorly tuned (oscillating) — gain too high or integral time too
   short for the coil's authority
2. Valve or damper actuator hunting — worn linkage, sticking stem, or a
   positioner fighting its own feedback
3. Conflicting control loops — two sequences acting on the same air stream
   (e.g. a coil loop and a face-and-bypass or mixing loop with overlapping
   ranges)
4. Intermittent sensor signal — a loose SAT wire or failing transmitter reads
   as oscillation with no control defect present

## Energy Impact

COMFORT_ENERGY, LOW confidence, QUALITATIVE_ONLY. There is no direct waste term
to compute: an oscillating loop delivers roughly the right average temperature,
and the loss is in the cycling itself — valve and damper strokes that overshoot
and correct, coil energy spent on excursions that cancel out, and the fan and
pump work that follows them. The reference puts this at 1–3% of AHU energy
while the hunting lasts. Confidence is LOW because no controlled study isolates
oscillation losses from the tuning changes that fix them; there is no PNNL
measure for this fault. Climate-neutral — a poorly tuned loop hunts in any
weather. Prevalence ~5%. Runtime estimation follows Energy Impact Reference
§4.4 (hunting hours × AHU coil and fan power), applied by the host; this rule
contributes the hours, not the kilowatts.

## Emissions Impact

Scope 2, QUALITATIVE_EMISSIONS, LOW confidence. Minimal in absolute terms —
control-loop inefficiency, not a stuck-open coil. No avoided-emissions basis is
published for this fault; a host that wants a number should apply its standard
electricity factor to the fan and pump energy attributed above and treat the
result as an order-of-magnitude estimate.

## Deviations

- **Rolling standard deviation → rolling mean absolute deviation.** The
  reference's logic is `rolling_std(SAT, window) > oscillation_threshold AND
  rolling_std(SAT, window) > k × rolling_std(SAT, long_window)`. The engine's
  elementary block set has no variance or standard-deviation block. (Squaring
  inside a moving average IS expressible — `Reals.Multiply` feeding
  `Reals.MovingAverage`, the route SYS-FC-055 later took for its variance
  branch — but this card predates that idiom.) MAD is computed instead, from four `Reals.MovingAverage` instances plus a subtract
  and an absolute value per timescale, exactly as the block graph shows. MAD
  and std are proportional for any fixed waveform, so the **ratio test carries
  over unchanged** — the scale factor appears on both sides of
  `madShort > k × madLong` and cancels.
- **The absolute threshold does not carry over, so it is restated in MAD
  units.** For Gaussian noise `std = 1.2533 × MAD`; for a pure sine
  `std = 1.1107 × MAD`. The reference's 1.5 °C std therefore corresponds to a
  MAD of 1.20 (Gaussian) to 1.35 (sine). The default is **1.2, the lower
  bound**: it alarms at the same amplitude as the reference under the Gaussian
  reading and slightly earlier under the sine reading. A site that wants the
  conservative end of the band sets `oscillation_threshold` to 1.35. For a
  square wave — the waveform the vectors use — `std = MAD` exactly, so vector
  amplitudes read directly as MAD.
- **`Reals.MovingAverage` is a continuous-time integral mean, not a sample
  mean.** The engine accumulates `u·dt` forward-Euler and divides by the window
  (`reals_filters.rs`), so hand-computed sample statistics do not match it
  exactly and the vector expectations were derived by replaying the graph at
  the pinned rev rather than by closed-form arithmetic.
- **Minimum sample interval, from the same block.** Each `MovingAverage`
  instance keeps a fixed 64-checkpoint ring; more than 64 samples inside one
  window drops the oldest with a one-time warning. The tick interval must
  therefore be ≥ `long_window/64` = 7200/64 = **112.5 s** at the default
  windows. A host ticking faster than that silently shortens the baseline
  window — the fault still detects, but against a truncated baseline. The
  vectors step at 150 s rather than the library's usual 300 s: both clear the
  floor, but 150 s puts six samples in the short window and leaves two full
  steps of margin around every asserted transition.
- **Warmup NO_EVAL.** The reference's "sufficient data in both windows"
  precondition is implemented host-side, not in the graph: during the first
  `long_window` after engine start `madLong` divides by elapsed time, so it
  underestimates the true baseline and oscillation present from the moment of
  load can transiently satisfy the ratio test. `delayOnInit = true` on
  `persist` buys 30 minutes of that back; the remaining exposure is covered by
  the frontmatter precondition, which requires the host to report NO_EVAL for
  the first 2 h.
- **The short window is coarse at realistic tick rates.** 900 s at a 300 s BAS
  tick is three samples; `madShort` is a three-point statistic there and steps
  visibly. That is accepted — the threshold and the 30-minute persistence
  timer both absorb it — but a host with a faster trend interval gets a
  smoother short window at no cost (subject to the 112.5 s floor above).
- **`window` and `long_window` each bind two CXF parameter paths** (the mean
  stage and the deviation-averaging stage), like `valve_open_threshold` in
  AHU-FC-059. Hosts must set both paths of a window together; splitting them
  changes what the statistic means.
- **Both comparisons are strict** (`>`), and the boundary is pinned by
  bracketing rather than by an exact-equality tick: `madShort` is a computed
  statistic, not a staged input, so nothing can be parked exactly on 1.2 the
  way a valve command can be parked on 5%. The `small_oscillation` (±1.0 °C,
  `madShort` = 1.0) and `marginal_oscillation` (±1.35 °C, `madShort` = 1.35)
  vectors straddle the threshold from both sides.
- **The reference's test vectors are statistical summaries, not tick traces**
  (stable 0.3/0.4 NO_FAULT; oscillating 2.5/0.4 FAULT; noisy-but-consistent
  1.0/0.9 NO_FAULT). Each is re-expressed as a SAT trajectory that produces the
  stated scatter: `stable_operation`, `hunting_onset`, `noisy_but_consistent`.
  The noisy-but-consistent case is run at a larger amplitude (±3 °C rather than
  the reference's 1.0) so that the absolute test passes and the ratio test is
  the only thing blocking the fault — at the reference's own numbers both tests
  fail and the vector proves less.
- Severity 3 (warning) and method `statistical`, per the reference's chapter 9
  card — its §5.8.1 index carries no severity column, so nothing else in the
  reference speaks to severity. This chapter's README lists the fault as
  severity 4 / `rule`; the chapter 9 card governs and the index row needs
  correcting, as it did for AHU-FC-059.
- The reference tags this fault for AHU and RTU; this card is the AHU-family
  instance, and an RTU-FC-056 would restate it against the RTU's discharge-air
  sensor.
- `persist.delayOnInit = true` (Modelica/CDL default is `false`), the library's
  standing choice: a violation already present at load waits out the full 30
  minutes instead of alarming on the first tick after a controller restart.

## Notes

**This detector flags onset, not steady state.** The ratio test normalizes
against the unit's own recent history, so hunting that outlasts `long_window`
raises `madLong` itself until `madShort > k × madLong` no longer holds, and the
alarm clears with the loop still hunting. That is visible in `hunting_onset`:
the oscillation starts at t = 9000 s, both conditions latch at 9450 s, the
alarm asserts one `alarm_delay` later at 11250 s, and it releases at 12600 s —
3600 s after onset, the point at which half the 2 h baseline window is itself
oscillating and `madLong` has climbed past `madShort`/k. That release time is
`long_window`/2 regardless of amplitude, since both statistics scale together.
This is a property of the reference's own logic, not of the MAD substitution —
its FAULT vector (short 2.5 against long 0.4) can only exist near onset. A host
that wants a latched alarm holds the work order open after the first assert
rather than tracking `yFault` continuously.

The corollary is that a unit that has hunted for months reads as healthy until
something disturbs it. Catching those needs a cross-unit or absolute-scatter
comparison, which is a Phase 3 statistical rule, not this one.

No playbook is referenced: nothing in `playbooks/` currently covers control-loop
tuning. A loop-tuning playbook can adopt this fault when the VAV and
control-tuning family lands.

Diagnosis 4 deserves its precondition. A SAT transmitter with an intermittent
connection produces textbook oscillation statistics with a perfectly tuned loop
behind it, and the two are indistinguishable from this rule's output alone.
Read the raw trend before touching tuning parameters: control hunting is
smooth and roughly periodic, a failing sensor is neither.

Related: AHU-FC-004 (excessive operating state changes per hour) is the same
instability one layer up, at the sequencing logic rather than inside a single
loop. A loop hunting hard enough to swing the unit between operating states
trips both — AHU-FC-004 counts the state transitions, this rule measures the
temperature scatter driving them. Hunting confined to one coil trips this rule
alone.
