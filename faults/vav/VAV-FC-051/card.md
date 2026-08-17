---
schema: cxf-library/fault-card/v1
id: VAV-FC-051
name: Rogue zone driving AHU reset
equipment: vav
status: verified
phase: 2
method: rule
severity: 3
category: EXCESS_CONSUMPTION
confidence: MEDIUM
estimation_method: PROXY_ESTIMATION
source:
  - "HVAC FDD Reference v1.0 §10, VAV-FC-051"
  - "PNNL retuning measures"
  - "PNNL-25985 EEM-15"
g36: null
clusters: []
suppresses: []
suppressed_by: []
related: [AHU-FC-053, AHU-FC-057, AHU-FC-058]
playbooks: []
operating_states: "Cooling modes"
preconditions: "AHU running and serving multiple zones — a reset loop with two or three boxes on it has no majority to be rogue against. satisfied_zone_fraction must be fresh and computed over the zones on this AHU's reset loop; when the aggregate is stale, or covers too few zones for a fraction to mean anything, the verdict is NO_EVAL rather than healthy. The zone's own request must be reaching the AHU reset logic: a box whose requests never arrive cannot be driving anything, and its saturated request is a comms finding instead."
points:
  - zone_clg_request
  - satisfied_zone_fraction
outputs:
  - name: yFault
    description: True once this zone's cooling request has been saturated with more than satisfied_threshold of sibling zones satisfied, continuously for rogue_duration plus alarm_delay
params:
  request_max_threshold:
    default: 99.0
    unit: "%"
    description: Cooling request above which the zone counts as asking for maximum cooling
    cxf: reqMax.t
  satisfied_threshold:
    default: 0.8
    unit: "1"
    description: Fraction of sibling zones satisfied (0-1) above which this zone is the outlier rather than the messenger
    cxf: mostHappy.t
  rogue_duration:
    default: 3600.0
    unit: s
    description: Continuous duration of the saturated request with most sibling zones satisfied before the zone counts as rogue (60 min)
    cxf: rogue.delayTime
  alarm_delay:
    default: 1800.0
    unit: s
    description: Further persistence required after rogue_duration before the alarm asserts (30 min)
    cxf: persist.delayTime
energy_impact:
  affected_subsystem: AHU energy — one zone penalizes the whole system through the reset loop
  savings_range: 3-10% of AHU energy (PNNL-25985 EEM-15)
  climate_sensitivity: both
  runtime_estimation: "ahu_penalty_kw ≈ ahu_actual_energy − ahu_optimal_energy, the difference between the AHU running at the setpoint this zone forces and the setpoint the rest of the building would have allowed"
emissions:
  scope: "2"
  method: PROXY_EMISSIONS
verified:
  engine_rev: e2ff2f8
  content_id: "cxf:fnv1a128:37348fd287c6a793b5a1d0b6f46b350a"
  date: 2026-08-17
---

## Description

One zone holds its cooling request at maximum while the rest of the building
is comfortable. Trim-and-respond does what it was written to do: the AHU
answers the loudest zone, walking its supply air temperature or duct static
pressure setpoint to the aggressive end of the reset range and leaving it
there. The cost lands on every other box on that air handler — colder air than
they asked for, which they then reheat, or more static pressure than they need,
which the fan pays for cubed. The zone itself is usually still uncomfortable,
because whatever is wrong with it is not something more cooling fixes.

The rule's whole design turns on distinguishing a rogue zone from a messenger.
A saturated request means "I need more cooling", and quite often that is true
and the AHU should listen. What makes it a fault is the company it keeps: this
zone at maximum while more than 80% of its siblings sit inside their deadband.
When half the building is unsatisfied, the same saturated request is a correct
report of a building-wide shortfall — an AHU capacity, plant, or airflow
problem — and firing on it would send a technician to the wrong end of the
system. The reference's third test vector (request 100%, 50% satisfied,
NO_FAULT) pins exactly that case, and it is the vector worth reading first.

## Detection Logic

```
yFault = zone_clg_request > request_max_threshold
     AND satisfied_zone_fraction > satisfied_threshold
     sustained continuously for rogue_duration
     and then held a further alarm_delay
```

Block graph (`rule.cxf.jsonld`):

![VAV-FC-051 block graph](diagram.svg)

Two threshold tests feed one conjunction and then two delays in series.
`reqMax` asks whether this box is asking for everything it can ask for;
`mostHappy` asks whether anyone else agrees. `rogue` measures the duration —
it turns true only after the conjunction has been continuously true for
`rogue_duration` (60 min) — and `persist` requires a further `alarm_delay`
(30 min) on top, so a zone that never lets go alarms at 3600 + 1800 = 5400 s,
the 90 minutes the reference's FAULT vector holds. Any break, in either term,
drops both timers and discards the accumulated time: the alarm only ever
describes one continuous rogue episode, and a zone that recovers on its own
between morning warm-up peaks never raises it.

Both comparisons are strict. A request sitting exactly on 99.0% and a
satisfaction fraction of exactly 0.80 both stay clear, and the vectors pin
both edges from each side.

## Possible Diagnoses

1. Zone has an internal load the design never accounted for — a server closet,
   a copy room, a tenant fit-out that added people or equipment
2. Zone thermostat miscalibrated or badly sited — direct sun on the sensor, a
   supply diffuser blowing across it, or a drift the zone cannot argue with
3. VAV box undersized for the actual zone load, so full cooling airflow still
   cannot hold the setpoint
4. Stuck VAV damper: the box commands full open, the blade does not move, and
   the zone stays hot no matter what the AHU sends it (confirm with
   VAV-FC-053 before believing the load story)

## Energy Impact

EXCESS_CONSUMPTION, MEDIUM confidence, PROXY_ESTIMATION. The reference gives
3-10% of AHU energy, mapped to PNNL-25985 EEM-15. Estimation is PROXY because
the waste is a counterfactual: what the AHU would have consumed at the setpoint
the rest of the building would have permitted, versus what it consumed serving
this one zone — `ahu_penalty_kw ≈ ahu_actual_energy − ahu_optimal_energy`.
Neither term is measured directly, and the split between fan energy and coil
energy depends on which reset the zone is driving. Climate sensitivity is
both: a rogue zone dragging supply air temperature down costs chiller energy in
summer and reheat energy in winter, and a rogue airflow request costs fan
energy year-round. The multiplier is what makes it worth catching — one box
holds a reset that serves thirty or three hundred.

## Emissions Impact

Scope 2, PROXY_EMISSIONS, MEDIUM confidence; typical 100-800 kg CO₂e/yr for the
AHU-level penalty one zone imposes. The inventory is scope 2 because the
penalty is dominated by fan and chiller electricity; a site whose reheat is gas
or steam moves the reheat share of the consequential waste into scope 1, which
this card leaves to the downstream reheat rules (VAV-FC-052, VAV-FC-055) to
account for. Avoided-emissions basis: marginal operating emissions rate (MOER).

## Deviations

- **`zone_temp` and `zone_temp_sp` are dropped.** The reference's required
  points table lists both, but its equation consumes neither: they are the
  inputs to the host's derivation of "satisfied", which the equation reads only
  through the `satisfied_zones / total_zones` ratio. Inputs to a host
  derivation are not rule points (precedent: AHU-FC-063 consumes
  `expected_mode` rather than the `oat` its derivation reads). Which zones
  count as satisfied, what deadband they are judged against, and how stale
  readings are handled are host configuration; the graph consumes the one
  scalar that results.
- **`satisfied_zones / total_zones` becomes the host-derived point
  `satisfied_zone_fraction`.** Library v1 avoids array boundary points, so the
  host counts satisfied siblings and feeds one fraction, flagged `derived` in
  the point dictionary. Same pattern as `zone_reheat_fraction` in AHU-FC-053
  and `zone_dmpr_pos_max` in AHU-FC-058.
- **`satisfied_threshold` is a fraction 0-1, not a percent.** The reference
  states it as 80%; the point it compares against carries unit `1`
  (dimensionless, range 0-1), so the parameter default is 0.8. A host feeding a
  0-100 percentage will never fire this rule.
- **`MAX_COOLING` is implemented as a threshold at 99.0%, an adopted value the
  reference does not state.** The reference writes `zone_clg_request =
  MAX_COOLING` with no number. Equality against 100.0 is the wrong test for a
  real signal: a request scaled from a 16-bit analog value, or reported
  through a percent-of-span conversion, lands on 99.6 rather than 100.0 and an
  equality test would never fire. `> 99.0` reads "saturated at its ceiling" and
  keeps quantized 99.x signals in while excluding a genuine 99% request one
  count short of maximum. The threshold is exposed as `request_max_threshold`
  so a site with a coarser signal can lower it, and the vectors pin both sides
  (99.0 clear, 99.2 and 100 count).
- The `satisfied_zone_fraction` comparison is strict `>`, which is what the
  reference writes — no boundary deviation on that term. The vectors pin it
  anyway (0.80 clear, 0.81 fires) because the fraction is host-computed and the
  boundary is where two hosts' definitions of "satisfied" will disagree.
- **Two delays in series rather than one.** `rogue_duration` and `AlarmDelay`
  are separate tunables in the reference, so they stay separately tunable here
  even though a single 5400 s delay behaves identically at the defaults
  (precedent: AHU-FC-061). A site that wants a 30-minute rogue window changes
  one parameter.
- `rogue.delayOnInit` and `persist.delayOnInit` are both `true` (Modelica/CDL
  default is `false`), the library's standing choice: a rogue condition already
  present at load waits out the full 90 minutes rather than alarming on the
  first tick after a controller restart. The trade-off is that in-rule timing
  does not survive a restart, which is the conservative direction — the library
  never asserts a fault it has not observed.
- The reference tags this fault for VAV and AHU. This card is the VAV-family
  instance, bound to one box's request and its siblings' satisfaction
  (precedent: AHU-FC-059). The AHU-side view of the same defect is already
  covered by AHU-FC-053, AHU-FC-057, and AHU-FC-058, which see the reset stuck
  at its limit without knowing which zone is holding it there.
- Operating-state gating (cooling modes) and the multi-zone precondition are
  declared in frontmatter for host enforcement rather than encoded in the block
  graph, per the library's design stance.

## Notes

`playbooks` is empty because no playbook in this library covers the zone-side
diagnosis this fault opens — the four diagnoses split across a sensor
investigation, a load survey, and a box-mechanics check, and none of them is a
remote fix. The nearest relative is
[missing-reset](../../../playbooks/missing-reset.md), whose step 1.3 (do zone
requests reach the AHU controller?) is the precondition check for this rule
read from the other end.

Fix order matters when this rule fires alongside AHU-FC-057 or AHU-FC-058. A
rogue zone is the classic reason a reset that is programmed correctly still
looks dead in trend data: the setpoint sits at the aggressive end of its range
all day because one box keeps voting for it, and it never moves, which is
exactly the signature those two statistical rules detect. Fix the zone first.
Reprogramming a reset that is already working, or widening its range to make
the trend look livelier, only spreads the rogue zone's demand over a wider
band. Once the zone is fixed, the reset should start modulating within an
occupied day and the AHU-side faults clear on their own.

G36 sites run discrete cooling requests (an integer count of
requests-to-reset), not a continuous 0-100 signal. The point dictionary's
binding note for `zone_clg_request` covers the mapping: bind 100 to
importance-weighted requests at their maximum and record the convention with
the point. This rule only tests for saturation at the ceiling, so it survives
the translation as long as the ceiling is the same number on both sides of it.
