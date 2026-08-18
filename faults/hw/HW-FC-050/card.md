---
schema: cxf-library/fault-card/v1
id: HW-FC-050
name: Boiler short-cycling
equipment: hw
status: verified
phase: 2
method: rule
severity: 2
category: PROTECTIVE
confidence: MEDIUM
estimation_method: QUALITATIVE_ONLY
source:
  - "HVAC FDD Reference v1.0 §14 (ch. 'Hot Water Plants', pdf pp. 124-125), HW-FC-050"
  - "Shohet et al. 2020"
  - "Meng et al. 2021"
g36: null
clusters: []
suppresses: []
suppressed_by: []
related: [HW-FC-051, HW-FC-052, RTU-FC-050, AHU-FC-004]
playbooks: [hot-water-plant-faults]
operating_states: "heating season / HW plant enabled"
preconditions: "The host must report NO_EVAL for the first count_window (1 h) after engine start. While the moving average's window fills, its divisor is elapsed time rather than the window, so the count reports an extrapolated pace instead of a completed-hour tally, and alarm_delay (15 min) is far too short to cover the hour on its own — `warmup_pace_asserts_on_two_starts` shows a verdict reached at 1200 s on the strength of two starts. The plant must be enabled and in heating season: a boiler idle because nothing is calling for heat produces zero starts, and reporting that as healthy cycling is the opposite of information. boiler_status must be the burner's FIRING (flame) status, not the boiler's enable status — an enable that stays true across an entire morning hides every burner cycle inside it, which is the point dictionary's warning on this point. Bind it per boiler: on a multi-boiler plant the OR of the statuses never falls while any boiler is firing, so every lag-boiler start is invisible and each boiler's own cycling is undercounted. The host tick interval must sit inside the band the count arithmetic and the edge counter jointly allow — 57.15 s ≤ dt < 360 s — with count_scale retuned to match (see Deviations). When any gate is unmet the verdict is NO_EVAL, not healthy."
points:
  - boiler_status
outputs:
  - name: yFault
    description: True while the number of boiler starts in the trailing count_window has stayed above max_starts_per_hour for at least alarm_delay
params:
  max_starts_per_hour:
    default: 4.0
    unit: "1/h"
    description: Starts per hour above which the cycling counts as short-cycling rather than load-following. The reference's ceiling, equivalent to a 15-minute minimum interval between firings
    cxf: cntHigh.t
  count_window:
    default: 3600.0
    unit: s
    description: Trailing window the starts are counted over (1 h). It also fixes the units of max_starts_per_hour; a host that shortens it must retune count_scale with it and read the ceiling as starts per window rather than per hour
    cxf: rate.delta
  count_scale:
    default: 12.0
    unit: "1"
    description: "Rescales the moving average of the one-tick pulse train back into a start count: k = count_window / host tick interval in seconds. The default 12.0 is 3600/300, correct only at a 300 s tick; a host on a different tick MUST retune this or every count is wrong by the ratio of the two intervals"
    cxf: count.k
  alarm_delay:
    default: 900.0
    unit: s
    description: Continuous fault persistence required before the alarm asserts (15 min)
    cxf: persist.delayTime
energy_impact:
  affected_subsystem: Boiler mechanical life + efficiency
  savings_range: 3-5% efficiency loss while cycling, plus avoided boiler damage of $10K-$100K
  climate_sensitivity: heating-dominant
  runtime_estimation: "none in-rule — QUALITATIVE_ONLY; the rule sees one boolean and cannot price a start. Size the opportunity host-side from cycling hours × rated fuel input × the 3-5% penalty per Energy Impact Reference §4.4, and treat the avoided replacement as the larger term"
emissions:
  scope: "1"
  method: QUALITATIVE_EMISSIONS
verified:
  engine_rev: e2ff2f8
  content_id: "cxf:fnv1a128:504010d1861bbe0d8a10b7f90528e0b1"
  date: 2026-08-17
---

## Description

A boiler start is expensive in a way the fuel meter barely registers. Every
firing begins with a pre-purge that pushes the previous cycle's heat up the
stack, runs the burner through the part of its range where the fuel/air ratio is
worst, and ends with a post-purge that does the same thing again. In between,
the pressure vessel takes a thermal step: the fire side goes to flame
temperature in seconds while the water side lags, and the differential works the
tube sheet, the refractory, and the welds. Do that four times an hour for a
season and the efficiency loss is the small part of the bill.

The reference puts the efficiency penalty at 3–5% and the avoided damage at
$10K–$100K, which is the whole argument for severity 2 on a fault whose energy
number is modest. A boiler that cycles is being asked a question its mass cannot
answer — the load is smaller than the smallest fire, or the aquastat differential
is too tight to let a cycle finish, or two boilers are handing the load back and
forth. None of those is visible from the water temperature, which is exactly why
this shows up as a start count and not as a comfort complaint.

The diagnosis list runs from a setting changed in a minute to a sizing decision
made before the building opened, and the rule does not distinguish them. What it
reports is that the burner is being started more often than the plant should
need; the service call decides why.

## Detection Logic

```
start  = rising edge of boiler_status                      one tick wide
count  = MovingAverage(start, count_window) × count_scale   starts in the trailing hour
yFault = count > max_starts_per_hour, sustained continuously for alarm_delay
```

Block graph (`rule.cxf.jsonld`):

![HW-FC-050 block graph](diagram.svg)

`start` is the only block that touches the run status, and all it asks is
whether the burner just lit: `Logical.Edge` emits `u ∧ ¬pre(u)`, one tick wide,
on every OFF→ON transition. Firing durations are not measured and stops are not
counted. `pulseInt` and `pulseReal` carry that boolean into the real domain,
where the arithmetic lives.

`rate` does the counting, and the mechanism is worth stating precisely because
the parameters only make sense against it. `Reals.MovingAverage` is a
continuous-time integral mean: it accumulates `u·dt` and divides by the window.
A one-tick pulse of height 1.0 encloses exactly one tick interval of area, so
`n` starts inside the trailing hour give `rate = n · dt / count_window`.
Multiplying by `count_scale = count_window / dt` = 3600/300 = 12 recovers `n`
itself. The recovered count is exact rather than approximately exact — four
starts an hour at a 300 s tick evaluates to precisely 4.0 in IEEE-754 — so
`four_starts_per_hour_is_exactly_the_threshold` pins a real boundary and not a
near miss. The idiom is AHU-FC-004's, by way of RTU-FC-050, which is the same
fault on a compressor.

`cntHigh` applies the reference's strict `>`, so exactly four starts an hour
reads clear and five alarms. `persist` then requires the count to stay above the
ceiling for 15 minutes. On a boiler already cycling at 6/h that is one or two
more starts — long enough that a single morning warm-up burst does not report,
short enough that the alarm is still about today's operation.

## Possible Diagnoses

Transcribed from the reference's HW-FC-050 card:

1. Boiler oversized for the current load. The most common cause and the one with
   nothing to adjust: at 20% of design load a single-stage boiler can only meet
   the call by cycling, and the fix is staging, a lead boiler with a smaller
   turndown, or a buffer tank
2. Aquastat differential too small — the burner satisfies its setpoint and
   restarts a minute later. This is the setting worth checking first because it
   is free and remote
3. Staging logic cycling between boilers. On a multi-boiler plant the plant
   controller can produce short-cycling that no single boiler's own controls
   would ever cause, which is why this rule is bound per boiler
4. Short-circuiting in the piping — primary/secondary flow imbalance returning
   supply water to the boiler inlet, so the boiler sees its own output as load
   satisfaction and shuts down
5. Control valve hunting. An unstable heating-coil loop downstream modulates the
   plant load faster than the boiler can follow, and the cycling is the boiler
   chasing a signal that is itself oscillating (AHU-FC-004 is the AHU-side view
   of the same instability)

## Energy Impact

PROTECTIVE, MEDIUM confidence, QUALITATIVE_ONLY. The rule sees one boolean and
cannot price a start, so there is no waste term computable from its inputs. The
reference gives two figures of very different character: a 3–5% efficiency loss
while the cycling continues, and $10K–$100K of avoided boiler damage. The first
is small and continuous, the second is large and probabilistic, and the second
is why this card is severity 2 with a QUALITATIVE_ONLY estimator.

Confidence is MEDIUM. The mechanism is not in doubt and the sources are field
studies of boiler faults, but the efficiency figure depends on cycle length,
return water temperature, and how far the vessel gets from steady state on each
cycle — none of which this rule measures. Heating-dominant by construction: the
plant only runs in the heating season, and the fault's cost scales with the
hours it runs.

## Emissions Impact

Scope 1, QUALITATIVE_EMISSIONS, MEDIUM confidence. This is combustion at the
building, so the 3–5% efficiency loss is fuel burned on site rather than
purchased electricity, and the emissions land in Scope 1 whatever the grid is
doing. The reference records the range as "protective; indirect via boiler
degradation" and sets the avoided-emissions basis to N/A, which this card keeps:
the larger emissions term is the embodied carbon of a pressure vessel replaced
years early, not the marginal therms burned while the cycling continues.

## Deviations

- **`min_run_time` is in the tunables table and not in the graph, because it is
  not in the equation.** The reference lists `min_run_time = 10 min` beside
  `max_starts_per_hour`, and then prints exactly one line of logic:
  `boiler_starts_per_hour > max_starts_per_hour`. Nothing in the card says how
  the minimum run time enters the verdict — whether it gates evaluation,
  qualifies which starts count, or is a second branch — and a per-cycle
  duration test is a different measurement from a per-hour count. This is a
  transcription gap in the source, recorded here rather than filled in with
  invented logic. The starts-per-hour ceiling subsumes the protective intent in
  practice (five 4-minute firings an hour violates both tests at once), and a
  host that wants the per-cycle test can run a companion rule on the same point.
  RTU-FC-050 documents the identical gap in its 5-minute `min_run_time`.
- **The rolling count is built from a moving average, because the block set has
  no windowed counter.** `Integers.OnCounter` counts monotonically from a reset
  and has no window, so "starts in the trailing hour" would need a host-driven
  hourly reset — which turns a rolling count into a tumbling one and makes the
  verdict depend on where the hour boundary happened to fall. AHU-FC-004
  established the idiom, RTU-FC-050 carried it to a compressor, and this rule
  changes nothing but the threshold.
- **`count_scale` is coupled to the host's tick interval, and the failure is
  silent.** `k = count_window / dt`, so a host ticking every 60 s must set
  `count_scale` to 60.0. Left at 12.0 it reports a fifth of the true cadence and
  the rule never fires; set too high it alarms on a boiler that is behaving. A
  mis-set scale produces a plausible-looking number rather than an error, so it
  belongs on any deployment checklist beside the point binding.
- **The legal tick band is `57.15 s ≤ dt < 360 s`, and both ends have reasons.**
  The floor comes from `Reals.MovingAverage`, which keeps a fixed 64-checkpoint
  ring and must retain one checkpoint at or before the window start plus every
  sample inside it: `dt ≥ count_window / 63` ≈ **57.15 s**. The ceiling comes
  from the counter being an *edge* counter — a rising edge needs at least one
  false sample between two true ones, so the most starts observable in the
  window is `count_window / (2 · dt)`. Two different ceilings follow from that,
  and the shipped band takes the stricter one. For the threshold to be
  *exceedable at all* it is enough that `3600/(2·dt) > 4`, i.e. `dt < 450 s` —
  that is RTU-FC-050's formulation. But the first faulted cadence a boiler can
  actually run is five starts an hour, and observing five needs
  `5 ≤ 3600/(2·dt)`, i.e. **`dt ≤ 360 s`**. Between 360 s and 450 s the rule can
  only fire on a boiler whose fire and off intervals are each longer than one
  tick — a 4.5/h cadence with 6-minute firings — and misses the ordinary 5/h
  boiler entirely. 360 s is excluded rather than included because at exactly one
  half-period per tick, detection depends on the sampling phase: a 720 s cycle
  is only resolved when both the fire and the off interval are sampled, which at
  dt = 360 s requires each to be a full 360 s. **300 s is the recommended tick
  and the only one these vectors have exercised**, with `count_scale = 12.0`.
- **Nyquist is necessary, not sufficient: the real constraint is the shorter of
  the two intervals.** A firing shorter than one tick can be missed entirely —
  the point may never be sampled true — and so can a gap between two firings.
  The honest binding rule is `dt ≤ min(shortest firing, shortest off period)`,
  which for a boiler with a 10-minute minimum run time and a tight aquastat is
  the off period, not the fire. At the 300 s tick this rule ships, a boiler that
  restarts within 300 s of shutting down will have some of its starts swallowed,
  and the count reads low. The failure direction is silence, which is the right
  direction for a protective rule but is worth knowing when a technician insists
  the boiler is cycling and the count says otherwise.
- **The first hour reads as a pace, not a count, and `alarm_delay` does not
  cover it.** While `t < count_window` the moving average divides by elapsed
  time rather than by the window, so two starts in the first ten minutes report
  the extrapolated rate — well above four — and `persist` can mature on it.
  `warmup_pace_asserts_on_two_starts` pins that: `yFault` goes true at 1200 s on
  two starts and clears at 1800 s as the divisor grows. AHU-FC-004 is immune
  because its `alarm_delay` equals its `count_window`; this rule, like
  RTU-FC-050, is not, and the host NO_EVAL precondition for the first hour is
  load-bearing rather than decorative. A single start from cold does *not*
  produce a verdict at the 300 s tick, and neither does a healthy 2/h or 3/h
  cadence — it takes two starts inside ten minutes.
- **The startup edge pulse is spurious and inert.** `Logical.Edge` compares `u`
  against `pre_u_start` on the first tick, so a boiler already firing when the
  rule loads registers a start at t = 0. It never reaches the count: the moving
  average integrates `u·dt` and `dt` is zero on the first tick, so that pulse
  encloses no area (`steady_firing_never_counts`). `pre_u_start` is left at the
  CDL default rather than written out, per SCHEMA.md's "set only non-default
  values"; RTU-FC-050 writes the same default explicitly, and the two documents
  behave identically.
- **Strict `>` on a discrete count.** The reference writes
  `> max_starts_per_hour` and `Reals.GreaterThreshold` reads it literally, so
  four starts an hour is clear and five alarms. The boundary is unambiguous
  rather than measure-zero, because the recovered count takes integer values in
  steady state and the arithmetic is exact there: `12.0 × (4 × 300/3600)`
  evaluates to precisely 4.0. Both sides are pinned
  (`four_starts_per_hour_is_exactly_the_threshold`,
  `five_starts_per_hour_is_the_first_faulted_cadence`).
- **The counting window is half-open.** `rate` compares the accumulated integral
  now against its value one `count_window` ago, so a start exactly
  `count_window` old has just left the window. It matters only for a plant
  sitting right on the ceiling, it errs toward silence, and it is what makes the
  alarm outlive the cycling: in `cycling_stops_alarm_clears` the last start is
  at 10200 s and the alarm holds until 11400 s, because the count only falls
  back to four when the fifth-newest start ages out. The lag equals
  `count_window` minus the span of the last five starts, and is a full hour when
  the boiler stops after a single burst.
- **A rolling counter reports sustained cycling, not every excursion.** How long
  a crossing survives is `count_window` minus the span of the starts that caused
  it, so five starts packed into 40 minutes hold the count above the ceiling for
  1200 s and alarm, five spread over 45 minutes hold it for exactly
  `alarm_delay` and do not, and five spread over 55 minutes hold it for 300 s
  and are never close. Those are the three scenarios
  `five_starts_in_forty_minutes_alarms_for_one_tick`,
  `five_starts_in_forty_five_minutes_release_on_the_maturity_tick`, and
  `five_starts_in_fifty_five_minutes_never_alarms` — same starts in the same
  hour, three different verdicts, and none of it is visible in the printed
  equation.
- **`TrueDelay` asserts at exactly `T + delayTime`, which makes the middle
  scenario above the delay edge from below.** When the count falls on the same
  tick the timer matures, the input is already false and nothing is reported —
  the realized test is "above the ceiling for strictly more than `alarm_delay`",
  read at tick resolution. 300 s of burst spacing is the entire difference
  between an alarm and silence there.
- `persist.delayOnInit = true` (the CDL default is `false`), the library's
  standing choice: a plant already cycling above the ceiling when the controller
  restarts waits out the full 15 minutes rather than alarming on the first tick.
- **Operating state is declared, not gated.** "Heating season / HW plant
  enabled" is the reference's own operating-state line, and this library
  declares operating states in frontmatter for the host to enforce rather than
  binding points the equation does not use. There is no plant-enable point in
  the equation to gate on, and inventing one would change the rule's boundary.
- **`playbooks: []`.** Nothing in `playbooks/` covers boiler plant service; the
  nearest neighbours are `rtu-compressor-refrigerant` (the same fault on a
  compressor, wrong equipment and wrong trade) and `fcu-faults` (cycling, wrong
  scale). The schema tolerates an empty list, so this card ships one rather than
  pointing a technician at a playbook written for someone else's machine; the
  grounding is in `source` and in the diagnosis list above. VAV-FC-054 set the
  precedent for declining rather than stretching.
- **`clusters: []`.** `clusters/clusters.json` defines no cluster containing a
  hot water plant rule, and this card does not edit the cluster set. CLU-07
  (Unnecessary Plant Operation) is where HW-FC-052 would eventually belong; this
  fault is not part of that syndrome.
- **No test vectors are transcribed, because the reference publishes none for
  this card.** All eleven scenarios in `vectors.json` are authored from the
  equation, and every assertion edge was derived by replaying the graph at the
  pinned engine rev rather than by closed-form arithmetic — the moving average's
  warm-up and decay trajectories do not match hand-computed sample statistics.
- Severity 2, phase 2, `method: rule`, and the tunable defaults are the
  reference's chapter 14 card. `g36: null` — this is a research-derived rule
  (Shohet et al. 2020; Meng et al. 2021), not a G36 clause.

## Notes

Shohet et al. (2020) reached better than 90% accuracy classifying boiler faults
with a support vector machine over a much richer point set than this rule reads.
The reference cites that work as grounding for the fault, not as the detection
method, and the gap between the two is the honest limit of this card: a start
count says the boiler is cycling and says nothing about which of the five
diagnoses is causing it. The learned classifiers in that literature separate
causes; this rule raises the question.

Bind `boiler_status` to the flame or firing status, and bind it per boiler. Both
halves matter and they fail differently. An enable status that stays true all
morning while the burner cycles inside it reports zero starts — the fault is
invisible. An OR across a multi-boiler plant reports only the transitions of the
plant as a whole: a lag boiler that lights while the lead is already firing
never moves the signal, so a plant can hand a load back and forth all afternoon
and read as healthy. The point dictionary states the first constraint on
`boiler_status`; the second is RTU-FC-050's per-compressor argument applied to a
boiler room, and the correct deployment is one instance of this rule per boiler.

The one remote check worth doing before anyone drives out is diagnosis 2. Pull
the supply water temperature alongside `boiler_status` for a few hours: if the
burner is shutting down within a degree or two of its setpoint and relighting
almost immediately, the aquastat differential is the finding, and widening it
costs nothing. If the temperature swings widely and the boiler still cycles, the
load is smaller than the fire and the conversation is about staging or a buffer
tank instead.

HW-FC-051 reads the same boiler from the efficiency side and the two are worth
looking at together. Cycling depresses seasonal efficiency through purge losses,
so a plant that trips both rules may have only one problem; a boiler that trips
HW-FC-051 alone with a steady fire is a combustion or heat-transfer finding
instead.
