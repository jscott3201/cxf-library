---
schema: cxf-library/fault-card/v1
id: FCU-FC-002
name: SAT too low in full heating
equipment: fcu
status: verified
phase: 1
method: rule
severity: 3
category: EXCESS_CONSUMPTION
confidence: MEDIUM
estimation_method: PROXY_ESTIMATION
source:
  - "HVAC FDD Reference v1.0 §12, FCU-FC-002"
  - "G36 §5.22.6 FC#2"
  - "G36 §5.16.14 FC#7 and Table 5.16.14.7 (εSAT and AlarmDelay provenance, per Addendum u public review)"
g36: "§5.22.6 FC#2"
clusters: []
suppresses: []
suppressed_by: []
related: [AHU-FC-007]
playbooks: [fcu-faults]
operating_states: "OS 1 (Heating) — host-gated"
preconditions: "Evaluate only in OS#1, the heating state: in deadband or cooling the discharge is meant to sit below any heating setpoint, and the rule would be comparing against a number nothing is chasing. The fan must be running and delivering air, since a discharge temperature means nothing in a still coil — an FCU whose fan has failed while its loop pins the valve open can produce exactly this signature, with a downstream sensor drifting toward duct ambient, and that is a fan fault, not a coil fault. Suspend evaluation for a mode delay after any change of operating state, while the valve is stroking and the coil is still charging; G36 uses 30 min for an AHU and an FCU coil settles faster, but the graph carries no such timer. sat_sp must be the discharge setpoint the unit is actively controlling to, not a design constant, or the comparison is against a fiction. sat must be trustworthy; nothing in this rule cross-checks it, and a discharge sensor reading 6 °C low fabricates this fault on a healthy unit every heating hour. Coil saturation is signalled in-rule by yHtgFullOk: when it is false the rule is making no claim, and the verdict is NO_EVAL rather than healthy."
points:
  - sat
  - sat_sp
  - htg_vlv_cmd
outputs:
  - name: yFault
    description: True while sat has stayed more than epsilon_sat below sat_sp with the heating valve commanded above hc_full_threshold, for at least alarm_delay
  - name: yHtgFullOk
    description: Evaluability signal — true when htg_vlv_cmd exceeds hc_full_threshold, i.e. the coil has no capacity left to give; false means the unit is not in full heating, so the verdict is NO_EVAL and the host must ignore yFault
params:
  epsilon_sat:
    default: 1.0
    unit: "°C"
    description: "Shortfall below the discharge setpoint that counts as a real miss rather than sensor error (the chapter's ε_sat). ADOPTED — the chapter states no value; 1.0 °C is G36's εSAT at its Table 5.16.14.7 default and the library's house convention (see Deviations)"
    cxf: spMiss.t
  hc_full_threshold:
    default: 99.0
    unit: "%"
    description: "Heating valve command above which the coil is treated as having no capacity left (the chapter's `htg_vlv_cmd ≥ 99%`). Hosts whose valve command is quantized to whole percent should retune to 98.9, since the comparison is strict"
    cxf: htgFull.t
  alarm_delay:
    default: 1800.0
    unit: s
    description: "Continuous fault persistence required before the alarm asserts. ADOPTED — the chapter states no AlarmDelay for this card; 1800 s is G36's AlarmDelay default (30 min), the same value the AHU sibling AHU-FC-007 carries"
    cxf: persist.delayTime
energy_impact:
  affected_subsystem: FCU heating performance
  savings_range: 2-5% zone heating energy
  climate_sensitivity: heating-dominant
  runtime_estimation: "waste_kw ≈ (sat_sp − sat) / sat_sp × fcu_htg_capacity_kw, transcribed from the chapter — see Deviations for its unit sensitivity. The defensible form is the makeup term: makeup_kw = fcu_airflow_m3s × 1.2 kg/m³ × 1.005 kJ/kg·K × (sat_sp − sat), the heat the zone is not getting and something else has to supply"
emissions:
  scope: "1"
  method: PROXY_EMISSIONS
verified:
  engine_rev: e2ff2f8
  content_id: "cxf:fnv1a128:59e930986b1feb94a2708f0b1cb1f1e1"
  date: 2026-08-17
---

## Description

The valve is wide open and the air coming off the coil is still too cold. That
is the whole finding, and it is worth reporting because it is the one heating
complaint a fan coil unit cannot argue with: the loop has spent everything it
has and the discharge is still short. Whatever the cause, the unit is now
running its fan for less heat than it was designed to move, and the zone makes
up the difference from a baseboard, a space heater, or not at all.

The causes divide cleanly by where they sit. Upstream of the unit: hot water
arriving too cold, which is a plant or distribution finding and affects every
FCU on the riser at once. At the unit: a coil fouled on the air side, air
trapped in the water side, or a valve that reports open and is not. At the
sensor: a discharge thermistor that has drifted low and is inventing the whole
thing. The playbook works that list from cheapest to most invasive, and it
starts with the plant for a reason — one hot water reset gone wrong makes every
unit in the building report this fault, and none of them need service.

This is AHU-FC-007's rule at zone scale. What changes is the sensor set. An air
handler has a mixed-air temperature to check the coil against, so G36 can pair
FC#7 with FC#5; an FCU has return air and discharge air and nothing between
them, so the shortfall is measured against setpoint alone.

## Detection Logic

```
yHtgFullOk = htg_vlv_cmd > hc_full_threshold        (false ⇒ host reports NO_EVAL)
yFault     = ((sat_sp − sat) > epsilon_sat AND yHtgFullOk)
             sustained continuously for alarm_delay
```

Block graph (`rule.cxf.jsonld`):

![FCU-FC-002 block graph](diagram.svg)

`spGap` subtracts in the direction that keeps the threshold positive:
`sat < sat_sp − ε` and `sat_sp − sat > ε` are the same statement, and the
second one needs no negative constant. `spMiss` then applies `epsilon_sat` as a
plain positive threshold.

`htgFull` is the other half of the chapter's conjunction, and it goes two
places. Into `both`, where it is a term of the fault condition exactly as the
chapter writes it; and out of the block as `yHtgFullOk`, because it is also the
answer to "was this rule in a position to say anything?". Those are the same
test read two ways, and the second reading is the one that keeps a host honest.
A valve at 60% with the discharge 6 °C short is not a healthy unit — it is a
unit this rule has no opinion about, because the loop still has capacity and
the shortfall could be a slow morning. `part_load_missing_setpoint` is that
scenario, and `yHtgFullOk` false is what distinguishes it from
`full_heating_still_on_setpoint`, where the same `yFault` false means the unit
is genuinely fine.

Both comparisons are strict. A shortfall of exactly 1.0 °C is not a fault and a
valve reporting exactly 99.0% is not full; the vectors pin all four sides.
`persist` requires 30 continuous minutes, which rides out a morning recovery
from night setback — `morning_warmup_clears_before_delay` is that case — and
recovery is immediate on the tick the condition clears, because `TrueDelay` has
no off-delay.

## Possible Diagnoses

1. Heating coil fouled or air-locked — the air side blocked with lint and dust,
   which an FCU filter in a hotel room reliably supplies, or the water side
   holding an air pocket that a bleed valve clears in minutes
2. HW supply temperature too low — a plant or reset-schedule finding, not a
   unit finding. Check this first: it explains every unit on the riser at once
3. Heating valve stuck closed — the command reads 100% and the plug has not
   moved. The reason this rule cannot separate it from a fouled coil is that
   both look like "open valve, cold air"; the temperature across the coil
   piping tells them apart in thirty seconds at the unit
4. SAT sensor out of calibration — a thermistor reading low invents this fault
   and nothing in the rule can see it. Suspect it first when one unit reports
   and its neighbours on the same riser do not

## Energy Impact

EXCESS_CONSUMPTION, MEDIUM confidence, PROXY_ESTIMATION. The reference gives
2–5% of zone heating energy. Estimation is PROXY because the rule sees three
signals and none of them is airflow or power: the heat not being delivered is
`fcu_airflow × ρ × cp × (sat_sp − sat)`, and airflow comes from the unit's
nameplate rather than from this rule. Confidence is MEDIUM for the reason the
reference holds it there — the shortfall is unambiguous once detected, but what
it costs depends on what picks up the load, and an unheated hotel room at 3 a.m.
costs nothing at all while the same room with an electric space heater under the
desk costs a great deal. Heating-dominant by construction: the rule only
evaluates in the heating state.

## Emissions Impact

Scope 1, PROXY_EMISSIONS, MEDIUM confidence; typically 50–400 kg CO₂e/yr per
FCU. Scope 1 because the heat a fan coil fails to deliver is heat a boiler
burned gas to make — the emissions are the combustion the plant did on this
unit's behalf, whether or not the air ever carried it. The avoided-emissions
basis is the marginal operating emissions rate (MOER) where the makeup heat is
electric; where it is more of the same hot water, the saving is fuel at the
boiler and the basis is the plant's own efficiency.

## Deviations

- **The chapter states no tunables for this card at all.** FCU-FC-001's card
  carries a Tunable Parameters line; FCU-FC-002's carries the equation, the
  operating state, and nothing else. All three parameters here are therefore
  adopted rather than transcribed, and each is named as such in `params`.
- **`epsilon_sat` = 1.0 °C, adopted from G36.** The chapter's equation names
  `ε_sat` and never defines it. G36 Table 5.16.14.7 puts εSAT at 1 °C (2 °F)
  for the AHU fault set, AHU-FC-007 carries that value, and it is this
  library's house convention for a discharge-temperature error threshold. It is
  a sensor-error allowance, not a performance target: raising it makes the rule
  tolerant of a genuinely underperforming coil, and lowering it makes it a
  thermistor-accuracy alarm.
- **`alarm_delay` = 1800 s, adopted from G36 and not from the chapter.** The
  chapter gives FCU-FC-001 an AlarmDelay of 60 min and gives this card none, so
  the sibling's number is not automatically the right one here. 1800 s is
  G36's own AlarmDelay default and matches AHU-FC-007. Thirty minutes is long
  for a zone unit — an FCU coil charges in a few minutes, not half an hour — so
  a site that wants faster reporting can safely shorten it once the mode-delay
  precondition is enforced.
- **`hc_full_threshold` compares strictly, so the chapter's `≥ 99%` is read as
  `> 99%`.** CDL Reals has no `GreaterEqual`, and a valve reporting exactly
  99.0% therefore reads as not-full. On an analog signal the disagreement is
  measure-zero, but valve commands are frequently quantized to whole percent,
  which turns a measure-zero technicality into a real blind spot: a host whose
  command can only take integer values and whose loop saturates at 99 will
  never evaluate this rule. Such a host must set `hc_full_threshold` to 98.9.
  `valve_exactly_at_full_threshold` and `valve_just_over_full_threshold` pin
  both sides.
- **`epsilon_sat` compares strictly too**, so a shortfall of exactly 1.0 °C is
  clear and 1.1 °C alarms (`error_exactly_at_threshold`,
  `error_just_over_threshold`). Measure-zero on a real-valued temperature, and
  it errs toward silence.
- **The subtraction runs `sat_sp − sat`, not `sat − sat_sp`.** The chapter
  writes `sat < (sat_sp − ε_sat)`, which read literally would need a negative
  threshold on a signed difference. Reversing the operands makes `epsilon_sat`
  a positive parameter and keeps the library's standing rule against negative
  constants; the two forms are algebraically identical.
- **`yHtgFullOk` is exposed as a boundary output; AHU-FC-007 exposes only
  `yFault`.** The valve conjunct is computable in-rule and is the whole
  applicability test for this card — the chapter's own Operating States row
  says OS 1 (Heating), and full valve command is the in-rule proxy for it — so
  SCHEMA.md's rule for in-rule evaluability conditions applies. It is a
  threshold comparison, not an echo of the input: a host reading `yHtgFullOk`
  learns that the coil is saturated, which is not what `htg_vlv_cmd` alone
  tells it without knowing `hc_full_threshold`. The precedent for the shape is
  VFD-FC-050's `yCmdOk`. The interpretive cost is stated plainly in the
  frontmatter: false means the rule made no claim, not that the unit is well.
- **The brief for this card described the valve conjunct as "commanded open";
  the chapter says `htg_vlv_cmd ≥ 99%`.** The chapter governs, and the
  difference matters — a rule that fired on any open valve would report every
  FCU in its morning pull-up, which is what `part_load_missing_setpoint` and
  the 99% threshold exist to prevent.
- **The chapter's runtime estimator is transcribed but is not scale-invariant.**
  `waste_kw ≈ (sat_sp − sat) / sat_sp × fcu_htg_capacity_kw` divides a
  temperature difference by a temperature, so its value depends on whether the
  setpoint is expressed in °C or K or °F: a 6 °C shortfall against a 35 °C
  setpoint reads 17% of capacity, and the same physical state in kelvin reads
  1.9%. The formula is kept in `energy_impact.runtime_estimation` because the
  chapter is the source of record, with the dimensionally sound makeup term
  beside it. A host accumulating energy from this rule should use the second.
- **No coil-entering temperature is available, so there is no companion test.**
  G36 pairs FC#7 with FC#5 (SAT should be higher than MAT) on an air handler,
  which catches a coil that is doing nothing at all rather than merely doing
  too little. The FCU dictionary carries `rat` as the coil entering proxy —
  FCU-FC-004/005 use it that way — but the chapter's equation for this card
  does not, and this card does not add points the reference did not give it.
  Recorded as the obvious upgrade: `sat > rat` in heating needs no adopted
  constants at all.
- **Operating-state gating and the mode delay live in frontmatter, not in the
  graph**, per the library's design stance. The graph is silent outside full
  heating only because the valve conjunct happens to be false there; that
  coincidence is not a substitute for the host's OS#1 gate, since a unit can
  saturate its heating valve while the sequence is in a state where the
  discharge setpoint means something else.
- **No test vectors are transcribed, because the reference publishes none.**
  The whole suite is authored from the equation, and every assertion edge was
  checked by replaying the graph at the pinned engine rev. The discharge
  setpoint used throughout is 35 °C, which is a hot-water fan coil's
  discharge rather than an air handler's 21 °C supply — it is illustrative, and
  no rule parameter depends on it.
- **Frontmatter `clusters` is empty.** The reference lists no cluster for this
  fault, and this card does not edit the cluster set to invent one. The
  relationship to the rest of the FCU family is carried by the shared playbook.
- `persist.delayOnInit = true` (Modelica/CDL default is `false`), the library's
  standing choice: a unit already short of setpoint at full valve when the
  controller restarts waits out the alarm delay instead of alarming on the
  first tick.
- Severity 3 (warning) and method `rule`, per the reference's chapter 12 card
  and the FCU index; its §5.8.5 index carries no severity column.

## Notes

The vectors worth reading together are `full_heating_still_on_setpoint` and
`part_load_missing_setpoint`. Both report `yFault` false and they mean opposite
things. In the first the valve is wide open, the discharge is within
`epsilon_sat` of setpoint, and the unit is doing its job at its design point.
In the second the discharge is 6 °C short and the rule has simply declined to
judge, because the loop has capacity left. `yHtgFullOk` is the only thing that
separates them, which is the argument for the second output in one line.

Order the service by scope. Step 2.2 of the
[fcu-faults](../../../playbooks/fcu-faults.md) playbook is the plant check —
is the hot water supply temperature adequate? — and it belongs first because it
is free, remote, and explains the correlated case. If every FCU on a riser
reports at once, no coil is fouled; a reset schedule is. If one unit reports and
its neighbours do not, step 3.1 is the visit: bleed the coil, then clean it,
then verify the valve actually strokes. Diagnosis 4 sits outside that order —
a drifted discharge sensor produces a lone reporting unit that is
mechanically perfect, and the cheapest way to rule it in is to compare the
discharge reading against return air with the valve closed.

Expect FCU-FC-005 on the same units in the opposite season. A heating valve
that has worn enough not to seat is a valve that will also fail to open fully,
and the same seat that leaks in July starves the coil in January.
