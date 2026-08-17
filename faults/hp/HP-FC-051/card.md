---
schema: cxf-library/fault-card/v1
id: HP-FC-051
name: Defrost cycle anomaly
equipment: hp
status: verified
phase: 2
method: rule
severity: 3
category: EFFICIENCY_LOSS
confidence: MEDIUM
estimation_method: PROXY_ESTIMATION
source:
  - "HVAC FDD Reference v1.0 §11, HP-FC-051"
  - "HVAC FDD Reference v1.0, Remediation Playbooks pp. 169-170"
  - "Barandier 2023"
g36: null
clusters: []
suppresses: []
suppressed_by: []
related: [HP-FC-050, HP-FC-052]
playbooks: [heat-pump-faults]
operating_states: "heating mode"
preconditions: "The unit must be in heating mode with the compressor running — the reference's operating state, and outside it defrost_status carries no information this rule can read. The host must report NO_EVAL for the first count_window (1 h) after engine start: while the moving average's window fills, its divisor is elapsed time rather than the window, so the frequency branch reads an extrapolated rate instead of a completed-hour count, and alarm_delay (30 min) is too short to cover that hour on its own. The host tick interval must sit inside the band the count arithmetic and the edge counter jointly allow, and count_scale must be retuned with it (see Deviations). defrost_status must be the unit's own defrost-active flag sampled faster than its shortest cycle; a defrost shorter than one tick is invisible to the counter."
points:
  - defrost_status
  - oat
outputs:
  - name: yFault
    description: True while at least one of the three defrost defects — too many cycles in the trailing hour, one cycle running past max_defrost_duration, or a cycle running at a mild outdoor temperature — has held continuously for alarm_delay
params:
  max_defrost_frequency:
    default: 4.0
    unit: "1/h"
    description: Defrost cycles per hour above which the cadence counts as excessive. Must stay strictly below the edge counter's Nyquist ceiling of count_window / (2 × host tick) — 6/h at the default 3600 s window and 300 s tick
    cxf: freqHigh.t
  count_window:
    default: 3600.0
    unit: s
    description: Trailing window the defrost starts are counted over (1 h). It also fixes the units of max_defrost_frequency; a host that shortens it must retune count_scale with it and read the limit as cycles per window
    cxf: rate.delta
  count_scale:
    default: 12.0
    unit: "1"
    description: "Rescales the moving average of the one-tick pulse train back into a cycle count: k = count_window / host tick interval in seconds. The default 12.0 is 3600/300, correct only at a 300 s tick; a host on a different tick MUST retune this or every count is wrong by the ratio of the two intervals"
    cxf: count.k
  max_defrost_duration:
    default: 900.0
    unit: s
    description: Continuous defrost time above which one cycle counts as overlong (15 min)
    cxf: tooLong.delayTime
  defrost_unnecessary_temp:
    default: 7.0
    unit: "°C"
    description: Outdoor temperature above which a coil should not need defrosting at all, so a cycle running here indicts the defrost sensor or board. Adopted from the reference's remediation playbook, not from its tunables table
    cxf: mildOat.t
  alarm_delay:
    default: 1800.0
    unit: s
    description: Continuous fault persistence required before the alarm asserts (30 min)
    cxf: persist.delayTime
energy_impact:
  affected_subsystem: HP heating efficiency during defrost
  savings_range: 3-10% heating energy from excessive defrost
  climate_sensitivity: heating-dominant
  runtime_estimation: "waste_kw ≈ defrost_fraction × hp_heating_kw, where defrost_fraction is the share of heating hours spent in defrost above the cadence the coil actually needs"
emissions:
  scope: "2"
  method: PROXY_EMISSIONS
verified:
  engine_rev: e2ff2f8
  content_id: "cxf:fnv1a128:1cb2669baf4a0c1ac7e2d345e6854370"
  date: 2026-08-17
---

## Description

Defrost is a heat pump running backwards on purpose. The reversing valve swaps,
the outdoor coil becomes a condenser, ice melts off it, and for five to fifteen
minutes the unit is cooling the outdoors with the heat it was supposed to be
putting in the building — often with electric resistance heat propping up the
supply air so nobody notices. It is an expensive few minutes and a necessary
one, and the whole question is whether the unit is buying more of them than the
coil needs.

Three ways of buying too many, and the reference tests all three. A coil that
ices faster than it can be cleared cycles too often. A cycle that will not
terminate is stuck — the sensor that should end it has failed, or the board
never got the signal. And a cycle initiated at 10 °C is not clearing ice,
because there is no ice at 10 °C; it is the defrost control acting on bad
information. The three share a fault code because they share a service call:
somebody opens the outdoor unit and looks at the coil, the defrost sensor, and
the board, in that order.

None of them is visible from the space. The zone stays comfortable because the
supplementary heat covers the gap, which is precisely what makes this a
metered-energy fault rather than a complaint-driven one.

## Detection Logic

```
starts   = rising edges of defrost_status
count    = MovingAverage(starts, count_window) × count_scale     cycles in the trailing hour

too_often = count > max_defrost_frequency
too_long  = defrost_status held continuously for max_defrost_duration
needless  = defrost_status AND oat > defrost_unnecessary_temp

yFault    = (too_often OR too_long OR needless) sustained continuously for alarm_delay
```

Block graph (`rule.cxf.jsonld`):

![HP-FC-051 block graph](diagram.svg)

The frequency branch is AHU-FC-004's counter idiom applied to a boolean point.
`dfStart` reduces each defrost cycle to a single one-tick pulse on its rising
edge — how long the cycle runs is the next branch's business, not this one's —
and `pulseInt`/`pulseReal` carry that pulse into the real domain where the
arithmetic lives. `rate` is a continuous-time integral mean: it accumulates
`u·dt` and divides by the window, so a one-tick pulse of height 1.0 encloses
exactly one tick interval of area and `n` cycles inside the trailing hour give
`rate = n · dt / count_window`. Multiplying by `count_scale = count_window / dt`
= 3600/300 = 12 recovers `n` itself. The recovered count is exact at the
boundary rather than approximately exact: four cycles an hour at a 300 s tick
evaluates to precisely 4.0, so `four_cycles_per_hour_is_exactly_the_threshold`
pins a real edge and not a near miss.

`tooLong` is the duration branch and needs no counting: a `TrueDelay` on
`defrost_status` matures when one cycle has run continuously for
`max_defrost_duration`, and falls the instant the cycle ends. `mildOat` and
`needless` are the third branch, and the conjunction matters — a mild outdoor
temperature is not a fault, and a defrost cycle is not a fault; a defrost cycle
*at* a mild outdoor temperature is.

`anyDefect` and `anyFault` are the two-input `Or`s that build the reference's
three-way disjunction, and `persist` applies the single 30-minute `AlarmDelay`
to the result. That last arrangement has a consequence the reference does not
spell out and this card does, in Deviations: the third branch is true only while
a cycle is running, so at the reference's own defaults it cannot fill the
persistence window by itself. What it does is start the clock earlier — a stuck
defrost at 7.1 °C alarms at 1800 s where the same defrost at 7.0 °C waits until
2700 s.

## Possible Diagnoses

1. Outdoor coil heavily fouled or iced — the coil genuinely needs the cycles it
   is taking, and the fix is cleaning rather than controls
2. Defrost sensor failure. A failed coil-temperature sensor both initiates
   cycles that are not needed and fails to terminate the ones that are, so it is
   the single cause that can produce all three branches
3. Defrost control board malfunction, including a time-initiated defrost timer
   left at a setting the manufacturer no longer recommends
4. Refrigerant charge issue — low charge lowers coil temperature and brings on
   frost the coil would not otherwise form, which shows up here as cadence
   rather than as capacity (HP-FC-050 is the rule that sees it as capacity)

## Energy Impact

EFFICIENCY_LOSS, MEDIUM confidence, PROXY_ESTIMATION. Every defrost cycle costs
twice — the heat pulled back out of the building to melt the ice, and the
supplementary heat brought on to cover the gap — and the reference puts the
excess at 3–10% of heating energy. Estimation is PROXY because the rule counts
and times cycles without measuring either cost: `waste_kw ≈ defrost_fraction ×
hp_heating_kw` scales the unit's heating draw by the share of hours spent in
unnecessary defrost, which needs a view of what the coil actually required.

Heating-dominant by construction — the rule only evaluates in heating mode —
and worst in the humid part of the heating season, roughly 0 to 5 °C, where frost
forms fastest. Confidence is MEDIUM: the cycle counts themselves are solid, but
the share of them that were unnecessary is an inference, and a coil that is
genuinely icing is being correctly served by cycles this rule will flag.

## Emissions Impact

Scope 2, PROXY_EMISSIONS, MEDIUM confidence; typically 200–1,500 kg CO₂e/yr from
excess defrost energy. All electric, at the compressor and at whatever
supplementary heat covers the cycle, so the avoided-emissions basis is the
marginal operating emissions rate (MOER). Cold mornings are both when the fault
costs most and when the grid is dirtiest, which pushes the marginal figure above
the average one.

## Deviations

- **`comp_status` is dropped from the points list.** The reference's Required
  Points row lists it, but its equation never uses it: all three branches read
  `defrost_status` and `oat`. Compressor state is what makes the *operating
  state* (heating mode) true, and this library declares operating states in
  frontmatter for the host to enforce rather than binding a point the graph
  ignores. Precedent: VAV-FC-050 drops `zone_airflow` and AHU-FC-063 drops `oat`
  on the same grounds.
- **`defrost_unnecessary_temp` has no default in the reference's tunables
  table.** The card names the parameter in its equation and then lists only
  `max_defrost_frequency`, `max_defrost_duration` and `AlarmDelay`. The 7.0 °C
  shipped here comes from the same document's Remediation Playbooks (step 1.b:
  "Check for defrost initiating when OAT is above 7 °C (45 °F) — defrost should
  not be needed at mild temperatures"), which is the nearest in-document
  authority and the number a technician would use to verify the fault by hand.
- **The rolling count is built from a moving average, because the block set has
  no windowed counter.** `Integers.OnCounter` counts monotonically from a reset
  and has no window, so "cycles in the trailing hour" would need a host-driven
  hourly reset — which turns a rolling count into a tumbling one and makes the
  verdict depend on where the hour boundary fell. AHU-FC-004 established the
  idiom and this rule reuses it, with `Logical.Edge` in place of
  `Integers.Change` because the counted signal is boolean.
- **`count_scale` is coupled to the host's tick interval.**
  `k = count_window / dt`, and the default 12.0 is correct only at the 300 s tick
  the vectors use. A host ticking every 60 s must set `count_scale` to 60.0;
  leaving it at 12.0 reports a fifth of the true cadence and the branch never
  fires. The failure is silent — a mis-set scale produces a plausible-looking
  number — so it belongs on any deployment checklist.
- **The tick interval has a legal band, and the ceiling is half what a
  level counter would give.** This is an *edge* counter: a rising edge needs at
  least one false sample between two true ones, so the most cycles observable in
  a window is `count_window / (2 × dt)`, not `count_window / dt`. At the default
  3600 s window and a 300 s tick that ceiling is **6 cycles per hour**, and
  `max_defrost_frequency` must sit strictly below it or the branch can never
  fire. Rearranged, the shipped 4/h needs `dt < 3600 / (2 × 4) = 450 s`. The
  lower bound comes from `Reals.MovingAverage`, which keeps a fixed
  64-checkpoint ring and must retain one checkpoint at or before the window start
  plus every sample inside it: `dt ≥ count_window / 63 ≈ 57.1 s`. A legal
  deployment at the shipped defaults therefore ticks between **57.1 s and
  450 s**, with `count_scale = 3600 / dt`. The `excessive_defrost_frequency`
  vector runs the fastest resolvable cadence and shows the count settling at
  exactly 6.
- **Sampling floor on the point itself.** A defrost cycle shorter than one tick
  is invisible to the edge counter — the point may never be sampled true. The
  point dictionary flags this on `defrost_status`; at a 300 s tick against a
  5–10 minute cycle the margin is thin, and a host that can afford a 60 s tick
  should take it (and set `count_scale = 60.0`).
- **The first hour reads as a rate, not a count, and `alarm_delay` does not
  cover it.** While `t < count_window` the moving average divides by elapsed time
  rather than by the window, so the first defrost start of a run reads as 12/h —
  the pace, extrapolated. AHU-FC-004 has the same artifact but its `alarm_delay`
  equals its `count_window`, so `delayOnInit` blocks any verdict until the window
  has filled. Here `alarm_delay` is 1800 s against a 3600 s window and it does
  not, which is why the frontmatter precondition requires the host to report
  NO_EVAL for the first hour. The `normal_defrost_cadence` vector shows the
  artifact appearing and collapsing within two ticks on a perfectly healthy unit.
- **The duration branch is inclusive at its boundary, where the reference is
  strict.** The reference writes `defrost_duration > max_defrost_duration`;
  `Logical.TrueDelay` asserts when the accumulated true-time *reaches*
  `delayTime`, so the realized test is `≥`. The observable resolution is one
  tick either way: a cycle sampled false on the tick where the timer would have
  matured does not trip the branch, and the timer restarts from the next rising
  edge rather than resuming. `defrost_overlong` (alarm at 2700 s) and
  `defrost_released_on_the_maturity_tick` (alarm at 3900 s) pin the two sides,
  and the 1200 s difference between them is the whole boundary.
- **Strict `>` on the other two thresholds.** CDL Reals has no `GreaterEqual`,
  so exactly 4 cycles an hour reads clear and 5 alarms, and a cycle at exactly
  7.0 °C does not count as needless. The frequency boundary is unambiguous
  rather than measure-zero — the recovered count takes integer values in steady
  state — while the temperature boundary is genuinely measure-zero on a
  real-valued signal. Both are pinned from both sides
  (`four_cycles_per_hour_is_exactly_the_threshold`,
  `five_cycles_per_hour_is_the_first_faulted_cadence`,
  `oat_exactly_at_the_mild_threshold`, `mild_oat_advances_the_alarm`).
- **The third branch cannot reach a verdict on its own at the reference's
  defaults, and this is arithmetic rather than a wiring choice.** `needless` is
  true only while a defrost cycle is running, the reference's single `AlarmDelay`
  is 30 minutes, and a normal defrost is 5–15 minutes; a cycle long enough to
  fill the persistence window has already tripped the duration branch 15 minutes
  earlier. What the branch contributes is timing — it starts the persistence
  clock at the beginning of a mild-weather cycle instead of 900 s in, so the
  alarm lands 900 s sooner (`mild_oat_advances_the_alarm` at 1800 s against
  `oat_exactly_at_the_mild_threshold` at 2700 s) — and it is why repeated
  mild-weather defrosting is reported through the frequency branch rather than
  through this one. A host that wants unnecessary defrost called on its own
  evidence must shorten `alarm_delay` below a typical cycle length, and should
  expect the other two branches to become correspondingly twitchy if it does.
  `mild_oat_short_cycles_never_persist` is the vector that documents the limit.
- **One `AlarmDelay` on the disjunction, not three.** The reference states a
  single 30-minute `AlarmDelay` for the card and this rule applies it once, after
  the `Or` tree. Branches therefore accumulate: a cycle that is both overlong and
  needless does not need each branch to persist separately, only their union.
- **`Logical.Edge`'s `pre_u_start` is left at the CDL default (`false`).** The
  CXF contract sets only non-default parameters. The consequence is a spurious
  rising edge if the unit is already in defrost when the controller starts, and
  it costs nothing: the moving average integrates `u·dt` and `dt` is zero on the
  first tick, so that pulse encloses no area and never reaches the count. The
  `defrost_overlong` vector starts in defrost and its count stays at 0.
- `delayOnInit = true` on both `TrueDelay` instances (CDL default is `false`),
  the library's standing choice. On `persist` it means a unit already faulted at
  load waits out the full 30 minutes; on `tooLong` it means a defrost already
  running at load is timed from the controller start rather than being assumed
  to have run forever, which is the conservative reading.
- Operating state (heating mode) is declared in frontmatter for host enforcement
  rather than encoded in the block graph, per the library's design stance.
  Severity 3 and `method: rule` are the reference's chapter 11 card; its §5.8.4
  index carries no severity column.
- **No test vectors are transcribed, because the reference publishes none.**
  Every scenario in `vectors.json` is authored from the equation, and every
  assertion edge was derived by replaying the graph at the pinned engine rev
  rather than by closed-form arithmetic — the moving average's warm-up
  trajectory does not match hand-computed sample statistics.

## Notes

The three branches point at different service work even though they share a
playbook. Cadence with normal-length cycles is a coil or a charge problem — the
coil is genuinely icing and the defrost control is doing its job. A cycle that
will not terminate is the defrost sensor or the board, and it is the branch most
likely to be a single failed part. Cycles at mild outdoor temperatures are
almost always the sensor reading low. Step 2.b of the
[heat-pump-faults](../../../playbooks/heat-pump-faults.md) playbook works that
order: coil first, then the defrost temperature sensor, then the board, then the
timer settings on time-temperature units.

Its resolution test is stricter than this rule's alarm point — fewer than 4
cycles per hour *and* less than 10 minutes each, monitored over 48 hours, where
the rule alarms at more than 4 cycles or more than 15 minutes. A unit running 4
cycles an hour at 14 minutes apiece is spending roughly a fifth of its heating
hours in defrost and clears every branch here. That gap is deliberate on the
reference's part: the alarm thresholds are set where the evidence is
unambiguous, and the confirmation thresholds where the unit is actually healthy.

Check HP-FC-050 on the same unit before ordering a coil cleaning. Low refrigerant
charge produces excess defrost as a secondary symptom — a cold coil frosts
sooner — and if both rules are firing, the charge is the more likely root cause
and the cheaper thing to verify. This rule firing alone, with COP on its
baseline, points at the defrost control rather than at the refrigerant circuit.
