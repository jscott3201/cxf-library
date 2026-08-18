---
schema: cxf-library/fault-card/v1
id: SYS-FC-052
name: Lighting on with no occupancy
equipment: sys
status: verified
phase: 2
method: rule
severity: 4
category: CRITICAL_WASTE
confidence: HIGH
estimation_method: DIRECT_MEASUREMENT
source:
  - "HVAC FDD Reference v1.0 §16, SYS-FC-052 (pdf pp. 140-141) — equation, AlarmDelay 30 min, severity 4 (info), the four diagnoses, and the whole impact profile"
  - "The reference's own provenance line for that card: Mazzetto 2025 — 1,149 occurrences in 10 months at one facility"
  - "PNNL EEM-18 (lighting occupancy sensors) — the reference's PNNL cross-reference for the 15-20% annual figure"
  - "Library precedent: AHU-FC-052 (the host-evaluated occupancy boolean, and the same Not/And/TrueDelay shape)"
g36: null
clusters: [CLU-04]
suppresses: []
suppressed_by: []
related: [AHU-FC-052, SYS-FC-053, SYS-FC-057]
playbooks: [after-hours-operation]
operating_states: "all — the conjunction is self-gating, since two of its three terms are the unoccupied test"
preconditions: "The occupancy sensor and the lighting circuit must cover the same space. This is a per-instance binding claim the graph cannot check, and getting it wrong is the rule's main false-positive path: a corridor PIR paired with an open-plan circuit reports a fault every time the corridor empties. occ_scheduled is host-evaluated from the lighting schedule for THAT space, not the AHU's — a building whose HVAC and lighting schedules differ needs the lighting one here, and schedule provenance that is stale or unknown is NO_EVAL rather than unoccupied. lighting_status should be a proven circuit status (current sensor, relay auxiliary contact, panel feedback) and not the command: a command point makes this rule an audit of the BAS's intent, which is exactly the thing diagnosis 1 says has already failed. Occupancy-sensor timeout is the host's to reconcile — a sensor whose timeout is long relative to alarm_delay delays the finding, and one that drops a stationary occupant produces a fault that is true given the data and wrong about the building."
points:
  - lighting_status
  - occ_sensor
  - occ_scheduled
outputs:
  - name: yFault
    description: True while the lighting circuit has been energized with the occupancy sensor unoccupied and the schedule closed, continuously for alarm_delay
params:
  alarm_delay:
    default: 1800.0
    unit: s
    description: "Continuous persistence required before the alarm asserts (30 min). The reference's only tunable for this rule."
    cxf: persist.delayTime
energy_impact:
  affected_subsystem: Lighting electrical energy
  savings_range: "100% of lighting energy while active; 15-20% annually (EEM-18, lighting occupancy sensors)"
  climate_sensitivity: neutral
  runtime_estimation: "waste_kw = lighting_circuit_kw"
emissions:
  scope: "2"
  method: DIRECT_EMISSIONS
verified:
  engine_rev: e2ff2f8
  content_id: "cxf:fnv1a128:763feed2eb268c080053a6ce13419359"
  date: 2026-08-17
---

## Description

Lights burning in an empty building after hours. The rule wants two independent
witnesses before it says the space is empty — the occupancy sensor and the
schedule — because either one alone is wrong often enough to be useless: a
schedule says nothing about the person working late, and a PIR says nothing
about the person sitting still. Requiring both is what makes a finding worth
dispatching, and it is also why this rule under-reports. Lights on all night in
a room whose sensor has failed to a permanent "occupied" are invisible here.

The reference's prevalence note is the reason it is in the library at all:
Mazzetto (2025) logged 1,149 occurrences in ten months at a single facility.
That is not a fault that happens; it is a fault that is running, most nights, in
most buildings, and every hour of it is 100% waste — no comfort is being
delivered to anyone.

Lighting is not HVAC, and this is the only card in the library that leaves the
mechanical plant entirely. It earns its place three ways: the schedule that is
wrong here is usually the same master schedule AHU-FC-052 is failing on (which
is why both are CLU-04), the fix is the same BAS work order, and the overnight
hours where it runs are exactly the hours the marginal grid generator is dirtiest.

## Detection Logic

```
yFault = lighting_status
     AND NOT occ_sensor
     AND NOT occ_scheduled
     sustained continuously for alarm_delay
```

Block graph (`rule.cxf.jsonld`):

![SYS-FC-052 block graph](diagram.svg)

Five blocks, no arithmetic and no thresholds — every input is already a boolean,
so the rule has nothing to compare and nothing to tune but the delay. `notSensed`
and `notSched` invert the two occupancy witnesses, `unoccupied` requires both to
agree that the space is empty, `litUnocc` adds the circuit, and `persist` is the
reference's 30-minute AlarmDelay.

Each of the three conjuncts can block the fault by itself and the vectors pin
that separately: `lights_on_in_an_empty_room_during_scheduled_hours` (schedule
open), `lights_on_after_hours_with_someone_present` (sensor occupied), and
`lights_off_after_hours` (circuit off). Any of the three going the other way
also drops a live alarm on the same tick — `TrueDelay` delays the rising edge
only, so a schedule that opens at 3000 s clears the finding at 3000 s, which
`schedule_resumes_then_ends_again` follows through a second alarm at 5400 s.

Thirty minutes of continuous emptiness is the whole test, and continuous means
continuous: someone crossing the room at 900 s discards the elapsed time rather
than pausing it, so `occupancy_detected_restarts_the_clock` alarms at 3000 s
rather than 1800 s. That is the intended trade — a full timer restart per PIR
trip means an intermittent sensor produces silence rather than a stream of
30-minute findings.

## Possible Diagnoses

The reference's four, in its order:

1. Lighting control override active — someone put the panel in HAND, or a BACnet
   priority-array entry is holding the circuit on. The most common and the
   cheapest to fix
2. Occupancy sensor bypassed — the sensor is physically disconnected, taped
   over, or its input has been decommissioned in software after nuisance
   switching complaints
3. Timer or photocell failure — a local astronomic timeclock drifted or lost its
   battery, or a photocell reading a lit interior keeps its own circuit on
4. BAS schedule misconfiguration — the lighting schedule was never edited from
   the default, or holidays and time zone are wrong (the same root cause as
   AHU-FC-052, which is why they cluster)

## Energy Impact

CRITICAL_WASTE, HIGH confidence, DIRECT_MEASUREMENT — the reference's own
profile, transcribed. While the fault is active the whole circuit is waste:
`waste_kw = lighting_circuit_kw`, with no thermal term to argue about and no
baseline to model, which is why the confidence is HIGH on a rule this simple.
EEM-18 puts occupancy-based lighting control at 15-20% of annual lighting energy.
Climate-neutral: the waste scales with unoccupied hours, not weather.

The severity is the reference's 4 (info) and it sits oddly against
CRITICAL_WASTE — 100% waste at the lowest urgency. Read them as answering
different questions: the category says every kilowatt-hour is unnecessary, the
severity says nothing breaks and nobody is uncomfortable while it does. It is a
work order for the next scheduled visit, not a callout.

## Emissions Impact

Scope 2, DIRECT_EMISSIONS, HIGH confidence; the reference's range is 500-5,000 kg
CO₂e/yr, and its parenthetical is the point — "lighting waste, high MOER
overnight." Avoided-emissions basis MOER (marginal). This fault runs almost
entirely in the hours when solar is off the grid and the marginal generator is
gas or coal, so its emissions rank routinely beats its energy-cost rank in
regions with cheap overnight power.

## Deviations

- **Severity 4, from the chapter, against the family README's 3.**
  `faults/sys/README.md` lists this rule at severity 3, and its own note says the
  SYS-FC-050-057 rows are provisional transcriptions to be re-verified against
  the chapter when each card is authored. The chapter says "Severity: 4 (info)"
  and the chapter wins; the README row needs updating by whoever owns that file.
- **`occ_scheduled` replaces the reference's schedule-evaluation call.** The
  reference writes `NOT in_occupied_schedule(current_time, occ_schedule)` — a
  function over a calendar and a schedule object. The block graph has neither a
  clock nor a calendar, so the host evaluates the schedule (time zone, holidays,
  exceptions) and feeds the boolean. Same treatment as AHU-FC-052, and
  `points/sys.points.json` records it as a derived point.
- **The point is named `occ_scheduled` here and `occ_schedule` in
  `points/ahu.points.json`.** Both are the same host-derived boolean and the SYS
  dictionary's name is the one that says so. Cards bind by exact name against
  their own family dictionary, so nothing is broken, but the two names for one
  concept are a library-wide inconsistency worth resolving once rather than
  per card.
- **One delay, not two.** AHU-FC-052 carries a `grace_period` on top of its
  alarm delay because the reference gives that rule one. This card's reference
  entry lists a single tunable — `AlarmDelay = 30 min` — so there is one
  `TrueDelay` and the time to alarm is 30 minutes flat. No grace period was
  invented to match the sibling card's shape.
- **No thresholds, so the library's strict-comparison deviation does not
  apply here.** Every input is a boolean and the graph contains no `Reals` block
  at all; there is no `<=` in the source logic to reproduce with a strict
  operator, and nothing to retune per binding.
- **`delayOnInit = true`** (the CDL default is `false`), the library's standing
  choice: a controller restart into an already-lit empty building waits out the
  full 30 minutes rather than alarming on the first tick.
- **`TrueDelay` asserts at exactly `T + delayTime`,** so the realized test is
  "lit and unoccupied for strictly more than `alarm_delay`" at tick resolution.
  `lights_switch_off_on_the_alarm_tick` (circuit drops at exactly 1800 s, never
  reported) and `lights_switch_off_one_tick_later` (one tick of alarm) pin both
  sides of that edge.
- **The reference publishes no test vectors for this card**, so all nine
  scenarios in `vectors.json` are authored: the occupied normal case, each of the
  three conjuncts blocking alone, the reference condition, both sides of the
  delay boundary, the PIR trip that restarts the clock, and a recovery followed
  by a second alarm.
- **The rule sees status, never power.** `lighting_circuit_kw` in
  `runtime_estimation` is a host-side nameplate or metered value; no such point
  is bound and the graph produces a boolean, not an energy figure. Accumulation
  is the host's per the library's design stance.
- Operating states and preconditions are declared in frontmatter for host
  enforcement rather than encoded in the block graph, per the library's design
  stance. There is no NO_EVAL logic in the graph: it computes the fault given
  valid data.

## Notes

Two failure paths are worth separating before dispatching anyone, because they
lead to different trades. If `occ_sensor` and `occ_scheduled` disagree with each
other night after night, the schedule is the suspect and the fix is a BAS edit
at $0. If they agree and the circuit stays on anyway, the suspect is downstream
of the BAS — a HAND switch at the panel, a welded relay, a local timeclock — and
the fix needs an electrician.

Where this rule fires alongside AHU-FC-052 on the same nights, treat it as one
finding, not two. The [after-hours-operation](../../../playbooks/after-hours-operation.md)
playbook is shared for that reason, and CLU-04 exists to make the shared master
schedule the thing that gets fixed rather than three symptoms of it.
