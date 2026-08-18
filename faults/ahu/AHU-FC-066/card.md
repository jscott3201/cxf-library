---
schema: cxf-library/fault-card/v1
id: AHU-FC-066
name: SAT too high vs RAT in cooling
equipment: ahu
status: verified
phase: 2
method: rule
severity: 3
category: EXCESS_CONSUMPTION
confidence: MEDIUM
estimation_method: PROXY_ESTIMATION
source:
  - "Bushby, Castro, Schein, House (2001), NIST task report for CEC PIER Project 2.3 'Air Handling Unit and VAV Box Diagnostics', §4.2 Table 1 rules 6, 12 and 17 — the rule expression, and Table 2's zone-subsystem grouping recording that the three are identical"
  - "Same report, §4.2.3 — the threshold defaults: εt = 1.7 °C (3 °F) for every temperature-comparison rule, ∆Trf = 1.1 °C (2 °F) for the return-fan rise"
  - "House, Vaezi-Nejad, Whitcomb (2001), 'An Expert Rule Set for Fault Detection in Air-Handling Units', ASHRAE Transactions 107(1) — the paper the PIER report credits with deriving APAR; not consulted for this card"
  - "Sibling precedent: AHU-FC-012 (the MAT-based rise test this card mirrors onto RAT), AHU-FC-005 (the same comparison with the heating-mode sign), HW-FC-053 (library-extension framing, assembled limit)"
  - "Library extension: the HVAC FDD Reference v1.0 index (§5.8.1) runs to AHU-FC-065 — see faults/ahu/README.md"
g36: null
clusters: [CLU-01]
suppresses: []
suppressed_by: []
related: [AHU-FC-012, AHU-FC-007, AHU-FC-013]
playbooks: [sensor-drift, simultaneous-hc]
operating_states: "APAR Modes 2-4, equivalently G36 OS#2-#4 (any cooling-side state) — host-gated"
preconditions: "Supply fan running, the unit occupied, and the unit in a cooling-side state identified the way APAR identifies it — from the actuator signals alone: heating valve closed and either the OA damper modulating between minimum and full with both coils off (Mode 2 / OS#2), or the cooling valve open with the OA damper at 100% (Mode 3 / OS#3) or at minimum (Mode 4 / OS#4). Suspend evaluation for a mode-transition window (30 min, G36's ModeDelay) after any change of mode or operating state, while the actuators are still stroking. `rat` must be the air actually coming back from the zones this AHU serves: a single return sensor on a multi-zone unit reads a flow-weighted mixture and this rule inherits that averaging, and a sensor sitting in a ceiling plenum reads roof and lighting heat rather than the space, which biases the comparison toward silence. `return_fan_rise` must match the installation, not the shipped 1.1 °C — set it to 0 on a unit with no return fan and on any unit whose return-air sensor is upstream of the return fan, since in both cases there is no fan heat in the reading to credit back. Both temperatures must be in °C; the rule converts nothing. Unlike its MAT-based cousins this rule needs no mixed-air sensor and is not disturbed by a faulted one, so AHU-FC-062 does not silence it. When any gate is unmet the verdict is NO_EVAL, not healthy."
points:
  - sat
  - rat
outputs:
  - name: yFault
    description: True while supply air has stayed more than epsilon_t above the return-air temperature corrected for return_fan_rise, continuously for at least alarm_delay. The rule's only output — it has no evaluability flag, because it has no in-rule gate; every condition under which the verdict is NO_EVAL is a host precondition
params:
  epsilon_t:
    default: 1.7
    unit: "°C"
    description: "Temperature-comparison allowance. 1.7 °C (3 °F) is the value APAR §4.2.3 applies flat to every one of its temperature-comparison rules, covering the combined uncertainty of the two sensors being compared. The report calls the number heuristic and names uncertainty composition (εt = εT1 + εT2) as the more rigorous replacement it had not yet adopted — a site with calibrated sensors composes its own sum, exactly as the G36-lineage cards in this chapter do"
    cxf: tooWarm.t
  return_fan_rise:
    default: 1.1
    unit: "°C"
    description: "Temperature rise across the return fan, credited back so the comparison is against the air the zones returned rather than the air after the fan has warmed it. 1.1 °C (2 °F) is APAR §4.2.3's typical value (∆Trf), which the report offers as a fixed stand-in for a model correlated to airflow or fan signal. SITE VALUE: set it to 0 on a unit with no return fan and on any unit whose return-air sensor is mounted upstream of the fan"
    cxf: excess.p
  alarm_delay:
    default: 1800.0
    unit: s
    description: "Continuous violation required before the alarm asserts (30 min). ADOPTED — APAR specifies no alarm persistence; it evaluates its rules on hourly data. 30 min matches the AHU comparison family in this chapter (AHU-FC-005, AHU-FC-012, AHU-FC-013)"
    cxf: persist.delayTime
energy_impact:
  affected_subsystem: AHU supply and return fans, and the cooling capacity being called for and not delivered
  savings_range: "2-5% of AHU energy, carried across from AHU-FC-012's §5.8.1 index row — the nearest published figure for the same physical finding read through a different sensor pair; APAR publishes no savings estimate for any of its rules"
  climate_sensitivity: cooling-dominant
  runtime_estimation: "undelivered_cooling_kw = supply_airflow_m3s × 1.2 kg/m³ × 1.005 kJ/kg·K × (sat − (rat − return_fan_rise)) — the sensible capacity the unit should be removing from the return stream and is instead adding to it, sized from design airflow because no measured airflow is bound. It is a floor rather than a total: the fan energy that moved the air buys nothing either way, and in Modes 3 and 4 there is chilled water or compressor work being paid for on top. When the cause turns out to be a sensor there is nothing to count"
emissions:
  scope: "2"
  method: PROXY_EMISSIONS
verified:
  engine_rev: e2ff2f8
  content_id: "cxf:fnv1a128:f49e1d4d822154e274cde27cdf1ec318"
  date: 2026-08-18
---

## Description

An air handler in a cooling mode has one job at the air stream: deliver air
colder than the space it serves. Return air is the best available measure of
that space, once the return fan's own heat is taken back off the reading. When
supply air is not below that corrected return temperature, the unit is running
its fans and — in the mechanical modes — its coil, and the building is getting
no cooling out of the exchange.

The distinct thing about this rule is the sensor it does not need. Its close
relative AHU-FC-012 tests the same physics across the coil section using mixed
air, and G36 marks that test `omit if no MAT sensor`; APAR's own accounting is
blunter still — of its 28 rules, nine (1, 2, 7, 10, 11, 16, 18, 26 and 27) drop
out entirely on a unit with no mixed-air sensor, which is most of the
temperature content of the rule set. This is the test that survives that, and it
is the reason to have it: on the large population of air handlers that were
never given a mixed-air sensor, a SAT-versus-RAT comparison is the only
whole-unit temperature check left.

What it buys in coverage it gives back in resolution. AHU-FC-012 brackets the
coil section and can say the heat arrived between the mixing box and the supply
sensor. This rule brackets the whole loop, return path included, so a fault
anywhere in it lands in the same alarm: the coil delivering nothing, a heating
source that never shut off, an economizer sitting on outdoor air warmer than the
building, or either of the two sensors being wrong.

This rule is a library extension. The HVAC FDD Reference's AHU index runs to
AHU-FC-065; the logic and both threshold defaults come from APAR's rules 6, 12
and 17, the graph shape from AHU-FC-012, and the numbers neither source fixes
are adopted and argued below.

## Detection Logic

```
gap    = sat − rat
excess = gap + return_fan_rise      (= sat − (rat − return_fan_rise))
yFault = excess > epsilon_t,
         sustained continuously for alarm_delay
```

Block graph (`rule.cxf.jsonld`):

![AHU-FC-066 block graph](diagram.svg)

APAR writes the rule as `Tsa > Tra − ∆Trf + εt`, which is a threshold on supply
air that moves with the return temperature. Moving ∆Trf to the other side turns
it into a threshold on a difference — `(Tsa − Tra) + ∆Trf > εt` — and that is
what the graph computes: `gap` for the difference, `excess` to credit the
return-fan rise back, `tooWarm` against the 1.7 °C allowance. The two source
constants stay separate parameters rather than collapsing into one 0.6 °C
threshold, because they are retuned for unrelated reasons: `return_fan_rise` is
a fact about the installation and is 0 on any unit without a return fan, while
`epsilon_t` is a sensor-uncertainty allowance.

`persist` requires 30 continuous minutes, which is what separates a unit that
cannot cool from a chilled-water valve still stroking after a mode change.
Recovery is immediate on the tick the comparison falls back inside the
allowance.

The comparison is strict, and at the shipped defaults it is strict about a line
no realistic pair of temperatures can land on exactly — see Deviations for what
that means at the boundary and why it does not matter above the millikelvin
scale.

## Possible Diagnoses

Library-authored. APAR is explicit that it detects rather than diagnoses: a
satisfied rule means a fault exists somewhere in the mode's assumptions, and
§4.2.2 lists only the broad classes its whole rule set can reach — stuck or
leaking dampers and coil valves, temperature-sensor faults, design faults such
as undersized coils, sequencing-logic errors, central-plant problems reaching
the AHU through its coils, and operator intervention. Read against this
particular comparison, those become:

1. Cooling coil valve stuck closed, or an actuator that no longer strokes
2. Chilled water unavailable or too warm at the coil — a plant problem arriving
   at the air handler, and the case where every AHU on the plant reports
   together
3. DX stage or compressor not running when the sequence says it should be
4. Coil fouled, air-bound, or too small for the load it has ended up serving
5. Heating source still active in a cooling mode: a valve leaking through, or a
   gas or electric stage that never shut off. This is the diagnosis that puts
   the fault in simultaneous-heating-and-cooling territory
6. Economizer holding outdoor air that is warmer than the building — free
   cooling that is not cooling, which AHU-FC-009 tests directly against setpoint
7. SAT sensor reading high, or RAT sensor reading low. Two sensors, one
   comparison, and nothing in the rule to say which of them moved
8. A return-air sensor that is not measuring the space: mounted in a ceiling
   plenum collecting light and roof heat, or on a unit whose zones no longer
   return through the path it sits in

Diagnoses 1 through 4 are the common ones and share a symptom this rule reads
well: the unit is calling for cooling and the air stream shows none. Diagnosis 5
is the one that also makes the fault a waste finding rather than a capacity
finding, and it is the overlap with AHU-FC-012 and the `simultaneous-hc`
playbook.

## Energy Impact

EXCESS_CONSUMPTION, MEDIUM confidence, PROXY_ESTIMATION. The fans run through
the whole occupied period regardless of what the coil is doing, so the first
cost of this fault is the entire fan energy of a unit that is not conditioning
anything. On top of that, in Modes 3 and 4 the sequence is calling for
mechanical cooling and something is being paid to produce it; and downstream,
VAV boxes that never see their zones satisfied drive their dampers open and
their reheat on, which pushes the fan harder still.

`undelivered_cooling_kw = supply_airflow_m3s × 1.2 × 1.005 ×
(sat − (rat − return_fan_rise))` sizes the sensible capacity the unit should be
taking out of the return stream and is instead putting back into it. Design
airflow standing in for a measured one is what keeps this a proxy. The
2–5% of AHU energy in `savings_range` is carried across from AHU-FC-012's
reference row — the same physical finding read through a different sensor pair —
because APAR publishes no savings figures at all.

MEDIUM rather than HIGH for the reason its MAT-based cousin is also MEDIUM: the
rule cannot separate its waste diagnoses from its sensor diagnoses. A SAT sensor
reading 3 K high draws exactly this trace and wastes nothing, and the formula
run on it returns a number for waste that does not exist. Cooling-dominant,
since the rule is evaluated only in cooling-side states.

## Emissions Impact

Scope 2, PROXY_EMISSIONS, MEDIUM confidence. The dominant term is purchased
electricity — fans moving air that does no work, plus chiller or compressor
energy in the mechanical modes — so a marginal operating emissions rate is the
right basis and the load lands across occupied daytime hours where that rate is
highest in most grids.

The exception is diagnosis 5. If what is warming the stream is a gas or electric
heating source that never shut off, the fault also owns a Scope 1 half and the
accounting matches AHU-FC-012's `1+2`. That contingency is not the common case
here, so the frontmatter records the scope this rule usually carries rather than
the one its worst diagnosis carries.

## Deviations

- **This rule is a library extension, not a transcription.** The HVAC FDD
  Reference's AHU index (§5.8.1) runs to AHU-FC-065 and stops; there is no
  reference row for this fault. The rule expression and both threshold defaults
  are APAR's; the ID, name, severity, phase, category, energy figures and
  diagnosis list are authored here, and each is argued in its own note below.
  Same framing as HW-FC-053 and the other library-authored cards.
- **The scope is cooling-only, and there is no heating mirror to write.** APAR
  places the return-air comparison in Modes 2, 3 and 4 and nowhere else: Table 1
  rules 6, 12 and 17 are written identically, and Table 2 groups them as the
  zone subsystem with the explicit note that the three are the same rule.
  Mode 1 (heating) has no return-air rule at all — its four rules test the coil
  against mixed air, the outdoor-air fraction, and the valve saturation. So the
  card ships one cooling-form graph and asserts nothing about heating. That
  matters because the neighbouring coil-subsystem group (rules 1, 7, 11, 16)
  *does* flip its relational sign by mode, which makes a signed-by-mode reading
  of this rule a natural but wrong guess; the source is unambiguous that this
  group does not.
- **Three APAR rules, one card.** Rules 6, 12 and 17 differ only in which mode
  they are evaluated under, and mode applicability is host-side here, so one
  graph covers all three. Precedent in this chapter: AHU-FC-012 spans rules 11
  and 16, AHU-FC-013 spans rules 13 and 19, AHU-FC-006 spans rules 2 and 18.
- **Rearranged into gap form, with the two constants kept separate.** APAR's
  `Tsa > Tra − ∆Trf + εt` becomes `(Tsa − Tra) + ∆Trf > εt`, one subtraction,
  one parameter addition, one threshold. The alternative — pre-composing the
  pair into a single 0.6 °C threshold, as AHU-FC-012 composes its three
  constants into 5.0 — was rejected here. On that card the composed number is
  retuned once by a site that has calibrated a sensor; here one of the two terms
  is 0 for an entire population (units with no return fan, and units whose
  return-air sensor sits upstream of the fan), and asking a host to recompute
  `1.7 − 0.0` by hand to serve them is worse than one extra block. Precedent for
  assembling a limit in-graph: HW-FC-053, CHW-FC-053, VFD-FC-051.
- **The strict `>` is APAR's own, but at the shipped defaults the boundary is
  not decidable.** Unlike the G36-lineage cards in this chapter there is no `≥`
  to convert — the source rule is already strict, so a comparison landing
  exactly on `εt` reads healthy in both. What the defaults do introduce is a
  floating-point artefact worth stating plainly: near room temperature the
  difference of two doubles moves in steps of roughly 3.6 × 10⁻¹⁵ K, and adding
  1.1 keeps that spacing, so the reachable values of `excess` straddle
  `fl(1.7)` without hitting it. A gap of nominally 0.60 K therefore reads
  healthy or faulted depending on which operands produced it: 24.7 − 24.1 lands
  at 1.699999999999998 and clears, 24.6 − 24.0 lands at 1.7000000000000015 and
  alarms. Both are pinned as vectors (`nominal_edge_operands_land_healthy` and
  `nominal_edge_operands_land_faulted`) so the behaviour cannot change silently.
  It is invisible on any real sensor — a 1.5 femtokelvin ambiguity on
  instruments rated to ±0.5 K — and the robust brackets at 0.59 K and 0.61 K
  are the vectors that actually characterise the threshold.
- **Instantaneous samples with a persistence timer, against APAR's hourly
  evaluation.** APAR is applied to hourly data and counts fault-hours; this
  library consumes instantaneous points and requires the violation continuously
  for `alarm_delay`. The two are not equivalent, and the miss is the usual one:
  `oscillating_excess_never_alarms` shows a supply temperature swinging on a
  10-minute period whose mean is well outside the allowance and which this rule
  never reports, because persistence restarts on every compliant tick. A steady
  offset — which is what a dead coil and a drifted sensor both produce — reads
  the same either way.
- **`alarm_delay = 1800 s` is ADOPTED.** APAR specifies no alarm persistence, so
  there is no number to transcribe. 30 minutes is what AHU-FC-005, AHU-FC-012
  and AHU-FC-013 use for the same class of comparison, and it is long enough to
  ride out a chilled-water valve stroking open after a mode change.
- **Mode gating is host-side, and the source's own architecture is why that is
  right.** APAR classifies its five modes from the heating-valve, cooling-valve
  and OA-damper signals alone, with no mode sensor and no mode input to the
  rules themselves — rules are selected by mode and then evaluated on
  temperatures. That is exactly this library's split between host-enforced
  `operating_states`/`preconditions` and a graph that computes
  fault-given-valid-mode. Nothing about the mode appears in this rule's graph,
  and a verdict produced outside Modes 2-4, outside occupancy, or inside a
  transition window is NO_EVAL rather than healthy. The correspondence is worth
  recording: this report predates G36 by two decades and reached the same
  architecture independently.
- **Severity 3 and phase 2 are the library's.** APAR assigns no severities; its
  rules are all equally "a fault exists". 3 (Warning) matches every other
  temperature-comparison rule in this chapter and is the honest level for a
  finding whose most likely single cause is a sensor. Phase 2 places it with the
  other research-backed 05x/06x extensions rather than with the phase-1
  reference transcription pass.
- **The energy profile is authored, and its savings range is borrowed.**
  `category`, `confidence` and `estimation_method` are this card's judgment;
  `savings_range` is AHU-FC-012's reference row carried across, which is the
  weakest number on the card and is labelled as such in its own field. APAR
  publishes no energy or emissions figures for any rule.
- **No evaluability output.** The rule is a single comparison with no in-rule
  gate, so `yFault` is the only boundary output; there is no `y…Ok` and hosts
  should not look for one. Everything that makes a verdict untrustworthy here —
  wrong mode, fan off, unoccupied, a return sensor that is not measuring the
  space — is a precondition the host enforces, and none of it is separable
  inside the graph.
- **No published test vectors.** APAR publishes rule expressions and threshold
  values, not cases, so all twelve scenarios in `vectors.json` are authored: two
  ordinary healthy cases, three characterising the threshold, the two nominal-edge
  operand pairs, the alarm-delay edge pinned to the tick, two faulted cases from
  different diagnosis families, the sub-delay transient, the recovery, and the
  oscillation the persistence substitution is known to miss.
- **The alarm-delay edge is asserted on the boundary tick, not one step away.**
  SCHEMA.md suggests leaving a step of margin around a timing edge;
  `alarm_delay_edge_asserts_at_1800s` deliberately does not, because
  `Logical.TrueDelay` asserts at exactly `T + delayTime` at the pinned engine
  revision and that is the fact the vector exists to pin. Every other scenario
  keeps the customary margin.
- `persist.delayOnInit = true` (the Modelica/CDL default is `false`), the
  library's standing choice: a violation already present at load waits out the
  full 30 minutes instead of alarming on the first tick after a controller
  restart.
- **`clusters: [CLU-01]`.** Diagnosis 5 is the simultaneous-H&C syndrome and
  AHU-FC-012 (this card's MAT-based cousin) is a CLU-01 member on the same
  grounds; membership was recorded on both sides at batch-16 closeout
  (`clusters/clusters.json`). The card's dominant reading remains cooling not
  delivered — CLU-01 groups the investigation, it does not redefine the fault.
- **`playbooks` cites two** (Applies-To rows updated at closeout).
  `sensor-drift` is first because diagnoses 7 and 8 are the cheapest to
  eliminate and among the most likely to be right; `simultaneous-hc` covers
  diagnosis 5. Both Applies-To rows are the index owner's edit, not this
  card's — the same sequencing HW-FC-053 recorded.
- **No suppression edge to AHU-FC-062.** The MAT-based rules in this chapter are
  silenced while the mixing-box rule is active, because a MAT outside the
  OAT/RAT envelope is not a number to compare against. This rule never reads
  MAT, so that edge does not apply — which is the same property that makes the
  card worth having, stated as a wiring decision.

## Notes

Read this rule and AHU-FC-012 as one test with two instruments. Where a
mixed-air sensor exists, FC-012 is the sharper of the two: it brackets the coil
section and can say the heat arrived between the mixing box and the supply
sensor. This rule brackets the whole unit including the return path, so it
covers more and localises less. On a unit with no MAT sensor there is no choice
to make — FC-012 is omitted by G36's own qualifier, and this is what remains.

The corollary is that a MAT fault does not disturb this rule at all. AHU-FC-062
silences its MAT-reading neighbours; it has no bearing here, so on a unit whose
mixing-box sensor has failed, this rule is still reporting while the rest of the
temperature family has gone quiet.

Check the two sensors before anything else. A portable reference against SAT and
RAT costs an hour and eliminates the two diagnoses that account for a large
share of these alarms; the [sensor drift](../../../playbooks/sensor-drift.md)
playbook covers the procedure. Pay particular attention to where the return
sensor is: a plenum-mounted sensor picking up lighting and roof heat reads high,
which biases this comparison toward silence, so a unit that has been quiet on a
plenum return has not necessarily been healthy.

If the sensors check out, the next question is whether heat is being added or
cooling is missing, and the fastest discriminator is the cooling valve command.
A wide-open valve with no temperature drop points at diagnoses 1 to 4 and at the
plant; a closed valve with the air warming anyway points at diagnosis 5 and the
[simultaneous heating and cooling](../../../playbooks/simultaneous-hc.md)
playbook. AHU-FC-050 reads that second case directly at the command layer, and a
site seeing both should treat this rule as the confirmation that the conflict is
reaching the air stream.
