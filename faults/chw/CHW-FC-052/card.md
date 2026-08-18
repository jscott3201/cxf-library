---
schema: cxf-library/fault-card/v1
id: CHW-FC-052
name: CHW loop DP reset not functioning
equipment: chw
status: verified
phase: 2
method: statistical
severity: 3
category: EXCESS_CONSUMPTION
confidence: HIGH
estimation_method: PROXY_ESTIMATION
source:
  - "HVAC FDD Reference v1.0 ch.13, CHW-FC-052 (pdf pp. 121-122)"
  - "PNNL RetuningOpps C03"
  - "PNNL-25985 EEM-10"
g36: null
clusters: []
suppresses: []
suppressed_by: []
related: [CHW-FC-051, CHW-FC-053, AHU-FC-058]
playbooks: [missing-reset]
operating_states: "CHW distribution running (variable-speed secondary or primary pumps enabled) with coils served"
preconditions: "dp_sp must be the setpoint the pumps actually control to, on the same loop as the coils feeding chw_valve_max. chw_valve_max is host-derived — the maximum across the CHW coil valves the loop serves — and the aggregate must span every coil on the loop: a maximum taken over a subset can sit at 55% while an unmonitored coil is wide open and starving, which is exactly the case the fault claims to have excluded. When the aggregate is stale, partial, or missing the verdict is NO_EVAL, not healthy; there is no in-rule evaluability output to catch it, because a stale feed is indistinguishable from a genuine low reading at the boundary. Prefer valve position feedback over valve command where both exist — a command reads low on a valve that is stuck open. The rule assumes modulating two-way valves; a loop on two-position valves or with three-way bypasses has no meaningful maximum position and must not be bound at all."
points:
  - dp_sp
  - chw_valve_max
outputs:
  - name: yFault
    description: True while the CHW loop differential-pressure setpoint has stayed flat over the evaluation window with every served coil valve below high_valve_threshold, for at least alarm_delay
params:
  evaluation_window:
    default: 259200.0
    unit: s
    description: Window over which setpoint flatness and low valve demand are assessed (3 days)
    cxf: [spRef.samplePeriod, spFlatHeld.delayTime, vlvLowHeld.delayTime]
  sp_flat_tolerance:
    default: 7.5
    unit: kPa
    description: Max deviation of dp_sp from its sampled baseline to count as flat (half the reference's 15 kPa min_expected_sp_range)
    cxf: spFlat.t
  high_valve_threshold:
    default: 90.0
    unit: "%"
    description: "Position below which the most-open coil valve still has authority, so the loop is not at maximum demand and the setpoint could have come down. Adopted — the reference names high_valve_threshold in the logic but ships no default (see Deviations)"
    cxf: vlvLow.t
  alarm_delay:
    default: 86400.0
    unit: s
    description: Fault persistence before alarm (24 h)
    cxf: persist.delayTime
energy_impact:
  affected_subsystem: CHW pump energy (cubic relationship)
  savings_range: 0.5-2% site energy; pump power ∝ pressure³ (PNNL-25985 EEM-10)
  climate_sensitivity: neutral
  runtime_estimation: "pump_waste_kw = chw_pump_kw × [1 − (1 − DP_reduction/100)³] — the reference's formula verbatim. The cube is what makes this worth chasing: a 20% setpoint reduction is roughly half the pump energy. Both inputs come from the host (measured pump kW, and the reduction a commissioned reset would have achieved)"
emissions:
  scope: "2"
  method: PROXY_EMISSIONS
verified:
  engine_rev: e2ff2f8
  content_id: "cxf:fnv1a128:89ddf1254d82b6820f9b536b32c1c5d9"
  date: 2026-08-17
---

## Description

The chilled water loop differential-pressure setpoint never moves, and every
coil valve on the loop is throttling. The pumps are holding a design-day
pressure against a building that is not asking for one, and the valves burn
the difference across their seats. Pump power goes with the cube of pressure,
so this is the cheapest large number in the plant: a 20% setpoint reduction is
about half the pump energy, and the reset that achieves it is a sequence, not
a purchase.

The valve conjunct is what makes the finding safe to act on. A flat DP
setpoint on its own is ambiguous — it is also what a correctly working reset
looks like when it has been driven to its upper limit and pinned there by a
coil that cannot get enough water. Requiring the most-open valve to sit below
`high_valve_threshold` for the whole window says no coil is starving, so the
setpoint is flat because nothing is moving it, not because everything is
asking for more.

Found in more than 30% of buildings (PNNL 151-building study), usually
alongside its supply-temperature twin CHW-FC-051 and for the same reason:
nobody commissioned the reset.

## Detection Logic

```
baseline(dp_sp) = dp_sp sampled and held every evaluation_window (3 days)
sp_flat         = |dp_sp − baseline(dp_sp)| < sp_flat_tolerance,
                  continuously for evaluation_window
low_demand      = chw_valve_max < high_valve_threshold,
                  continuously for evaluation_window

yFault = sp_flat AND low_demand, sustained for alarm_delay
```

Block graph (`rule.cxf.jsonld`):

![CHW-FC-052 block graph](diagram.svg)

The setpoint chain is AHU-FC-058's sampled-baseline flatness detector with the
plant's points bound to it: a `Discrete.Sampler` refreshed once per window
supplies the reference value, and `spFlatHeld` asserts only after the setpoint
has stayed within `sp_flat_tolerance` of it continuously for a full window.

The demand condition needs no baseline. The reference's
`max(chw_valve_positions) < high_valve_threshold` over the window is exactly
equivalent to "the most-open valve stays below the threshold continuously,"
which is one `LessThreshold` plus a dwell `TrueDelay` on the host-aggregated
maximum — an exact transformation of the reference test, not an approximation
of it. Worst-case time to alarm from cold start:
`evaluation_window + alarm_delay` — 4 days. A loop that goes quiet mid-run
alarms `evaluation_window + alarm_delay` after the valves settle, which
`valve_drops_mid_run` pins at exactly 388800 s for a 12 h startup transient.

## Possible Diagnoses

1. DP reset never programmed
2. DP reset disabled or overridden
3. Valve position feedback not connected
4. DP sensor at wrong location

## Energy Impact

EXCESS_CONSUMPTION, HIGH confidence, PROXY_ESTIMATION (EEM-10, PNNL-25985).
Savings 0.5–2% of site energy, climate-neutral, through the cubic pump law.
Prevalence: >30% of buildings. Diagnosis 4 — a DP sensor at the wrong location
— is the one that changes the economics: moving the sensor to the hydraulically
most remote coil is a pipe-fitting job, not a desk job, and the reference lists
it because a sensor at the pump discharge makes a correct reset impossible
rather than merely absent.

## Emissions Impact

Scope 2, PROXY_EMISSIONS, HIGH confidence; typical 300–3,000 kg CO₂e/yr
(excess pump energy, cubic law). Avoided-emissions basis: MOER (marginal).

## Deviations

- **`chw_valve_positions` (vector) → host-derived `chw_valve_max` (scalar).**
  The reference consumes every CHW coil valve position and takes the maximum;
  library v1 has no vector boundary points, so the host aggregates and feeds
  one scalar (`derived: true` in the point dictionary, which also records that
  the underlying coil-valve points carry their semantic tags in the AHU and FCU
  dictionaries). AHU-FC-058's `zone_dmpr_pos_max` is the precedent. The cost is
  in `preconditions`: the graph cannot tell a maximum over ten coils from a
  maximum over three.
- **Windowed range → deviation from a sampled baseline** on the setpoint
  chain, with `sp_flat_tolerance = min_expected_sp_range/2`, exactly as
  AHU-FC-057/058. CDL has no windowed min/max block. Detection is equivalent
  for a setpoint that moves and returns and slightly conservative for
  monotonic drift inside one window. The valve chain is not an approximation:
  `max over window < t` ⇔ `continuously below t`.
- **`Reals.MovingAverage` rejected, and the tick band that follows.** The
  engine implements it with a fixed 64-checkpoint ring, so it needs
  `dt ≥ evaluation_window/63` — 4,114 s (1 h 9 min) at 3 days — before the
  window stops silently dropping its oldest samples, and no BAS ticks that
  slowly. AHU-FC-057 found this; this card inherits both the finding and the
  sampler-and-dwell replacement, which has no lower bound on tick period. The
  upper bound is what you need to see: a setpoint excursion or a valve
  excursion shorter than one tick is invisible to the dwells, so trend at
  5–15 min. These vectors run at 5 min.
- **`high_valve_threshold` is adopted, not transcribed.** The chapter names it
  in the equation but its Tunable Parameters line lists only
  `evaluation_window = 3 days`, `min_expected_sp_range = 15 kPa`,
  `AlarmDelay = 24 hrs`. The shipped 90% is deliberately permissive on the
  fault side: the conjunct's only job is to exclude a loop genuinely pinned at
  maximum demand, and a modulating two-way valve at 90% is within a hair of
  having no authority left. It is a looser bar than AHU-FC-058's
  chapter-supplied 70% damper analog, which means more findings on loops with
  one moderately loaded coil; a site that wants the AHU-side margin should set
  70–80 via `set_param`. Note the direction — raising this number makes the
  rule fire more often, not less.
- **Strict comparisons, and both measure-zero boundaries pinned.**
  `Reals.LessThreshold` is `u < t`, so a valve sitting exactly at 90 % is not
  low demand and a setpoint deviating exactly 7.5 kPa from its baseline is not
  flat — both boundaries fall on the no-fault side. Equality is measure-zero
  in continuous data but perfectly reachable in a BAS that scales valve
  commands to whole percent, so the vectors pin both sides:
  `valve_at_threshold` / `valve_just_below_threshold` and
  `sp_at_flat_tolerance` / `sp_within_flat_tolerance`. The delay edges are
  pinned to the tick: the alarm asserts at exactly 345,600 s from a cold start
  and at exactly 388,800 s when the valves settle 12 h into the run.
- **No evaluability output.** The valve test is a conjunct of the reference's
  fault condition, not an evaluability gate (contrast CHW-FC-051's
  `yLoadVaried`, which mirrors the reference's own NO_EVAL semantics). An
  output carrying `chw_valve_max < high_valve_threshold` would only echo one
  boundary input through a threshold, so the rule ships `yFault` alone and the
  staleness question stays where it belongs, in `preconditions`.
- **`AlarmDelay` = 24 h implemented as `TrueDelay` on the fault
  conjunction**; the evaluation window itself is enforced by the two dwells.
  `delayOnInit = true` on every `TrueDelay` (startup conservatism per
  AHU-FC-050).
- **Transcription gaps in the source.** The chapter gives CHW-FC-052 no
  Description paragraph, no Operating States line, and no test vectors; all
  vectors here are constructed. Its Required Points line reads "DP_SP,
  chw_valve_positions" — the canonical names come from
  `points/chw.points.json`, which is where the binding contract lives. The
  chapter's heading for the fault is "CHW loop differential pressure reset not
  functioning"; `name` carries the shorter index spelling from
  `faults/chw/README.md`, which owns names.
- **Blind spots.** The rule sees the setpoint, not the pressure: a loop whose
  setpoint resets correctly while the pumps fail to track it is a different
  fault. Diagnosis 4 (DP sensor at the wrong location) is invisible here — a
  badly placed sensor produces a plausible flat setpoint and this rule reports
  it as a missing reset, which is why the playbook's first step is to check
  where the sensor is before programming anything. Diagnosis 3 (valve feedback
  not connected) is worse than invisible: it corrupts the input the rule leans
  on, and a host that binds a defaulted-to-zero feedback will see a permanent
  low maximum. And a loop whose pumps are off for the window holds both
  signals flat, which the host's operating-state gate must suppress; the graph
  has no way to know.

## Notes

Fix path is the [missing-reset](../../../playbooks/missing-reset.md) playbook.
Its worked examples are the AHU-side pair (SAT and DSP setpoint plots against
zone demand); the plant-side procedure is the same shape one system upstream —
plot `dp_sp` against the most-open coil valve over the window, confirm the DP
sensor is at the hydraulically most remote coil, then program the reset. The
index owner is extending the playbook's Applies-To to cover this rule and
CHW-FC-051.

`clusters` is deliberately empty: CLU-02 ("Missing Reset Strategy") is
currently AHU-scoped and triggered by AHU-FC-057, and membership is
`clusters/clusters.json`'s to declare. A plant failing both CHW-FC-051 and
CHW-FC-052 has one root cause and should be dispatched as one visit. Expect
CHW-FC-053 (low delta-T) nearby for the opposite reason: low delta-T drives
flow up and can hold coil valves open, which is the condition that legitimately
suppresses this fault.
