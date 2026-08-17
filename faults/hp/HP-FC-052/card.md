---
schema: cxf-library/fault-card/v1
id: HP-FC-052
name: Reversing valve fault
equipment: hp
status: verified
phase: 2
method: rule
severity: 2
category: CRITICAL_WASTE
confidence: MEDIUM
estimation_method: PROXY_ESTIMATION
source:
  - "HVAC FDD Reference v1.0 §11, HP-FC-052"
  - "Barandier & Mendes 2024"
g36: null
clusters: []
suppresses: []
suppressed_by: []
related: [HP-FC-050, HP-FC-051]
playbooks: [heat-pump-faults]
operating_states: "heating and cooling, compressor running (host-gated)"
preconditions: "The compressor must be running. A heat pump idling on its indoor fan drifts its discharge toward room temperature, which reads as too warm for cooling and too cold for heating at the same time, so an unrunning unit must not be evaluated. The host must map its own mode enum onto heating_mode_code and cooling_mode_code and must report NO_EVAL — not healthy — for every other mode it can command (off, auto, emergency heat, dehumidify): the graph is structurally silent on codes it does not carry. Defrost is the sharp case: during a defrost cycle the unit deliberately runs the reversing valve in cooling while mode_command still reads HEATING, so the host should gate this rule on defrost_status. The rule survives a normal defrost only because alarm_delay outlasts it — see Deviations. sat must be trustworthy; nothing in this rule cross-checks it, and a discharge sensor reading 15 °C low fabricates a heating-mode fault on a healthy unit."
points:
  - mode_command
  - sat
outputs:
  - name: yFault
    description: True while the discharge temperature has contradicted a settled mode command continuously for at least alarm_delay
params:
  heating_mode_code:
    default: 1
    unit: "1"
    description: Value of mode_command meaning HEATING
    cxf: kHeat.k
  cooling_mode_code:
    default: 2
    unit: "1"
    description: Value of mode_command meaning COOLING
    cxf: kCool.k
  sat_cooling_max:
    default: 18.0
    unit: "°C"
    description: Discharge temperature above which the unit is not cooling, judged after the mode has settled. ADOPTED — the reference states no default (see Deviations)
    cxf: satHigh.t
  sat_heating_min:
    default: 28.0
    unit: "°C"
    description: Discharge temperature below which the unit is not heating, judged after the mode has settled. ADOPTED — the reference states no default (see Deviations)
    cxf: satLow.t
  mode_switch_settle_time:
    default: 600.0
    unit: s
    description: How long a mode command must stand before the discharge temperature is judged against it (10 min); binds both selector timers
    cxf: [heatSettled.delayTime, coolSettled.delayTime]
  alarm_delay:
    default: 900.0
    unit: s
    description: Continuous contradiction required before the alarm asserts (15 min)
    cxf: persist.delayTime
energy_impact:
  affected_subsystem: Heat pump — running in the wrong mode
  savings_range: 20-50% of mode energy while the unit runs against its command
  climate_sensitivity: both
  runtime_estimation: "waste_kw = hp_capacity_kw × (1 + 1/COP) — the delivered heat (or cooling) that has to be undone plus the electricity spent delivering it"
emissions:
  scope: "2"
  method: PROXY_EMISSIONS
verified:
  engine_rev: e2ff2f8
  content_id: "cxf:fnv1a128:cca57c9ed8973afd8c50972d6e595dda"
  date: 2026-08-17
---

## Description

A heat pump is one refrigeration circuit run in either direction, and the
reversing valve is what chooses the direction. When the valve does not shift,
the unit keeps doing what it was doing last: cooling a building that asked for
heat, or heating one that asked to be cooled. Nothing about the unit looks
broken — the compressor runs, the fans run, the controller reports the mode it
commanded — and the zone thermostat responds by asking for more of what it is
already not getting.

That feedback loop is why this is a severity 2 fault and why it is expensive.
The reference puts the cost at 20–50% of mode energy, but the waste is worse
than a percentage suggests: the unit is not merely inefficient, it is adding
load in the wrong direction, so whatever else serves the space — perimeter
heat, a second stage, the zone's neighbours — pays to undo the work. The
reference's runtime estimator `hp_capacity_kw × (1 + 1/COP)` is exactly that
accounting: the misdirected thermal output plus the electricity that produced
it.

The rule is two points wide. It reads the commanded mode and the discharge air
temperature, and asks whether the air agrees with the command. It cannot see
the valve, the solenoid, or the refrigerant, so it cannot separate a stuck
valve from a failed solenoid from a charge too low for the valve to shift —
that separation is the playbook's job, and its first step is to listen for the
solenoid click.

## Detection Logic

```
in_heating = (mode_command = heating_mode_code) held for mode_switch_settle_time
in_cooling = (mode_command = cooling_mode_code) held for mode_switch_settle_time

heat_bad   = in_heating AND sat < sat_heating_min
cool_bad   = in_cooling AND sat > sat_cooling_max

yFault     = (heat_bad OR cool_bad) sustained continuously for alarm_delay
```

Block graph (`rule.cxf.jsonld`):

![HP-FC-052 block graph](diagram.svg)

`kHeat` and `kCool` decode `mode_command` through two `Integers.Equal`
selectors, and each selector passes through its own `TrueDelay` before it is
allowed to judge anything. That settle delay is the whole reason the rule can
be this simple: for ten minutes after a changeover the duct is still full of
air from the previous mode, and a unit that switched correctly looks exactly
like a unit that did not. `settle_window_masks_pulldown` is that scenario — the
discharge holds 30 °C for another nine minutes after the unit is put into
cooling, and the rule says nothing because `coolSettled` has not matured.

The two temperature tests are absolute limits rather than a comparison against
return air, because `rat` is not among the points the reference gives this
rule. `satHigh` and `satLow` are strict, so a discharge sitting exactly at
18.0 °C in cooling or exactly at 28.0 °C in heating reads healthy, and the
vectors pin all four sides. Between the two limits is a deliberate dead band:
lukewarm air — 22 °C in either mode — satisfies neither test and raises
nothing. A valve that shifts partially, or a unit so short of charge that it
barely moves heat in either direction, can live in that band; HP-FC-050 is the
rule that sees it.

`anyBad` ORs the two branches so one output covers both directions, and
`persist` requires 15 continuous minutes. The chain matters more than either
delay alone: from a cold start in a bad mode, `heatSettled` matures at 600 s
and `persist` 900 s after that, so the alarm lands at 1500 s. Nothing shorter
than 25 minutes of continuous wrong-direction operation can raise this fault,
which is what keeps normal defrost cycles out of it — barely.

## Possible Diagnoses

1. Reversing valve stuck or failed — the valve body itself, usually
   mechanically seized; replacement runs $500–$2,000 plus refrigerant recovery
2. Reversing valve solenoid failure — the cheap end of the list ($100–$300),
   and the one the playbook's click test isolates in a minute
3. Wiring issue between the controller and the solenoid: the valve is fine and
   never got the signal
4. Refrigerant charge too low for the valve to shift — the valve needs a
   pressure differential to move, so an undercharged unit can fail to change
   over with nothing wrong in the valve at all. Check charge before condemning
   the valve
5. Sequencing error upstream of the valve: the unit is faithfully executing a
   mode the building did not want. The rule reads the command, so this case
   only appears when the command itself contradicts the discharge — a stuck
   `mode_command` in the BAS priority array is the usual form

## Energy Impact

CRITICAL_WASTE, MEDIUM confidence, PROXY_ESTIMATION. The reference gives
20–50% of mode energy and the estimator `waste_kw = hp_capacity_kw ×
(1 + 1/COP)`, which counts both the misdirected thermal output and the
electricity that produced it. Estimation is PROXY because the rule sees a
command and a temperature, not capacity or power: `hp_capacity_kw` and `COP`
come from the unit's nameplate or from HP-FC-050's fitted baseline, not from
this rule's inputs. Confidence is MEDIUM for the same reason the reference
holds it there — the fault itself is unambiguous once detected, but how much
it costs depends on how long it ran and what else in the building was
compensating. Sensitive to both heating and cooling climates: a heat pump has
two ways to be in the wrong mode and this rule watches both.

## Emissions Impact

Scope 2, PROXY_EMISSIONS, MEDIUM confidence; typically 1,000–6,000 kg CO₂e/yr
while a unit runs in the wrong mode — the largest single-fault range in the
heat pump chapter. An all-electric heat pump puts the entire impact in scope 2,
and the avoided-emissions basis is the marginal operating emissions rate
(MOER): a valve stuck in heating on a hot afternoon draws its worst power at
the hour the grid is dirtiest.

## Deviations

- **`sat_cooling_max` and `sat_heating_min` are adopted, not transcribed.**
  The reference's equation names both, but its tunables table for this card
  lists only `mode_switch_settle_time` (10 min) and `AlarmDelay` (15 min), so
  neither limit has a published default. The `heat-pump-faults` playbook states
  the test differently — in cooling the discharge should be well below return
  air, in heating well above it — but `rat` is not one of this card's required
  points, so the comparison the playbook describes is not available to the
  graph. This card therefore adopts fixed limits that stand in for it: 18.0 °C
  is above any plausible cooling discharge (10–14 °C on a working unit) and
  below any occupied space temperature, and 28.0 °C is below any plausible
  heating discharge (30–45 °C) and above room temperature. Both are judgment
  calls, and both are wrong for some units: low-lift and inverter-driven heat
  pumps running at part load produce discharge temperatures much closer to room
  temperature, and a site that sees them must retune or accept silence. The
  dead band between the limits is the honest cost of not having `rat` — a unit
  producing 22 °C air in either mode raises nothing here.
- **The reference's "`mode_command` changed AND after `mode_switch_settle_time`"
  becomes a dwell test, not an edge test.** The reference writes the settle as
  a window after a change event. The block graph has no "time since the last
  change" quantity, so the same condition is expressed as: the selector must
  have been continuously true for `mode_switch_settle_time`. For the case that
  matters the two agree — any change in `mode_command` flips at least one
  selector and restarts its timer — and the dwell form is stronger at the
  boundary the edge form ignores: with `delayOnInit = true`, a unit already
  sitting in a mode when the controller boots still waits out the settle rather
  than being judged on its first tick. Changes that leave both selectors false
  (one unmapped code to another) restart nothing, which costs nothing, because
  the rule is silent in those states anyway.
- **A normal defrost cycle is ridden out by `alarm_delay`, and only just.**
  During defrost the unit reverses into cooling while `mode_command` still
  reads HEATING, so `heatSettled` is already mature and `satLow` goes true the
  moment the discharge cools. Only the 15-minute `persist` stands between a
  defrost and a false alarm — and HP-FC-051 puts `max_defrost_duration` at
  exactly 15 minutes, so a defrost at the edge of normal sits on this rule's
  alarm point. That is uncomfortably tight, and the card does not pretend
  otherwise: hosts should gate on `defrost_status` (the point exists in the HP
  dictionary for HP-FC-051), or raise `alarm_delay` above their unit's longest
  legitimate defrost. A defrost that runs long enough to trip this rule is
  itself a fault, and HP-FC-051 will be reporting it.
- **`rat` is not consumed.** The reference's required points for this card are
  `mode_command` and SAT only. Adding return air would give a relative test
  with no dead band and no site-specific limits, and it is what a technician
  does by hand at the unit — but it would depart from the card's own point
  list, and the HP dictionary carries no `rat` entry to bind. Recorded here as
  the obvious upgrade if the dictionary gains one: the comparison
  `sat > rat` in cooling / `sat < rat` in heating needs no adopted constants at
  all.
- **The 1/2 mode encoding is this library's convention**, matching the point
  dictionary's `mode_command` entry, and both codes are exposed as parameters
  (`kHeat.k`, `kCool.k`) so a host with its own enum rebinds the constants
  rather than editing the graph. Precedent: AHU-FC-063's `expected_mode`.
- **An unmapped `mode_command` leaves the rule structurally silent.** Both
  selectors go false and no temperature can raise a fault, however wrong it is
  (`unmapped_mode_code_is_silent` pins this with a 24 °C discharge). That
  silence is NO_EVAL, not a health claim, and the host must treat it as such —
  the same stance and the same wording as AHU-FC-063, which faces the identical
  gap.
- **Strict comparisons at both limits.** CDL Reals has no `GreaterEqual` or
  `LessEqual`, so a discharge sitting exactly on a limit is not a fault. The
  disagreement is measure-zero on a real-valued signal and the vectors pin both
  sides of both limits (`cooling_sat_exactly_at_max` /
  `cooling_sat_just_above_max`, `heating_sat_exactly_at_min` /
  `heating_sat_just_below_min`).
- `delayOnInit = true` on all three timers (Modelica/CDL default is `false`),
  the library's standing choice: a unit that was already in the wrong mode when
  the controller restarted waits out the settle and the alarm delay instead of
  alarming on the first tick.
- Operating states (compressor running) and the defrost exclusion live in
  frontmatter for host enforcement rather than in the block graph, per the
  library's design stance.
- Frontmatter `clusters` is empty. The reference lists no cluster for this
  fault, and this card does not edit the cluster set to invent one. The
  relationship to HP-FC-050 and HP-FC-051 is carried by `related` and by the
  shared playbook.

## Notes

The vectors are library-authored; the reference publishes no test vectors for
this card. The pair worth reading is `mode_chatter_never_settles` and
`settled_after_mode_switch`. Both hold the discharge at 24 °C — a temperature
that is simultaneously too warm for cooling and too cool for heating, so an
ungated rule would alarm continuously. In the first the mode flips every 540 s
and nothing is ever judged; in the second the mode is held from t=600 s and the
alarm arrives 1500 s later, at t=2100 s — the settle and the persistence delay
in series. Wire the settle timers past the selectors instead of after them and
the first scenario fails immediately.

The [heat-pump-faults](../../../playbooks/heat-pump-faults.md) playbook orders
the service. Step 1.3 is the manual version of this rule — command a mode
change, wait ten minutes, compare the discharge against return air — and step
2.3 is the diagnosis: listen for the solenoid click first, because no click is
a $100–$300 solenoid rather than a $500–$2,000 valve body; then check the
wiring; then check charge, since a valve short of pressure differential will
not shift no matter how healthy it is. Confirmation is step 3.3: command
several changeovers and watch the discharge respond to each.

Expect company. A valve that is failing to shift cleanly usually degrades COP
first, so HP-FC-050 may be reporting on the same unit, and a unit whose charge
is too low to move the valve is the same unit whose charge is too low to hold
its COP — Barandier (2023) found undercharge to be the most frequent heat pump
fault of all. Fix the charge before replacing anything.
