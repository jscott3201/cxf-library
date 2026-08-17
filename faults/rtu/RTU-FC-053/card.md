---
schema: cxf-library/fault-card/v1
id: RTU-FC-053
name: Economizer not modulating properly
equipment: rtu
status: verified
phase: 2
method: rule
severity: 3
category: CRITICAL_WASTE
confidence: HIGH
estimation_method: DIRECT_MEASUREMENT
source:
  - "HVAC FDD Reference v1.0 §11, RTU-FC-053"
  - "PNNL-23790 AFDD1/AFDD3"
  - "California Title 24 economizer FDD"
  - "PNNL EEM-06, EEM-23"
  - "Cowan 2004 (54% of RTUs)"
g36: null
clusters: [CLU-03]
suppresses: []
suppressed_by: [RTU-FC-052]
related: [AHU-FC-051, RTU-FC-052, RTU-FC-054]
playbooks: [economizer-failure]
operating_states: "cooling call active"
preconditions: "comp_status gates both branches inside the graph, so the rule is already silent with no mechanical cooling running; a false yFault under a stopped compressor is no verdict, not a healthy economizer. Everything above that stays host-side: mode transitions, morning warm-up, and any period when the damper is under manual override or a commissioning test. The OAT sensor must be trustworthy — a sensor reading high produces branch 1's signature with the economizer control working exactly as designed (diagnosis 4), which is why RTU-FC-052 (PNNL's AFDD0 sensor-consistency check) suppresses this rule while it is active. Damper position is taken from the command, not a feedback signal: a unit whose actuator ignores the command reports the command's story here and is caught by RTU-FC-052 or by the playbook's step 3. When any gate is unmet the verdict is NO_EVAL, not healthy."
points:
  - oat
  - oa_dmpr_cmd
  - comp_status
outputs:
  - name: yFault
    description: True while either economizer fault condition — damper at minimum while free cooling is available, or damper open while the economizer should be locked out — has held continuously with the compressor running for at least alarm_delay
params:
  econ_lockout_temp:
    default: 21.0
    unit: "°C"
    description: Outdoor temperature below which the economizer is expected to be modulating open; branch 1 arms below it
    cxf: oatLow.t
  econ_relock_temp:
    default: 22.0
    unit: "°C"
    description: Outdoor temperature above which the economizer is expected to be at minimum position; branch 2 arms above it. Equals econ_lockout_temp + the reference's lockout_deadband (1 °C) — a host moving the lockout must move this parameter with it
    cxf: oatHigh.t
  min_oa_margin:
    default: 25.0
    unit: "%"
    description: Damper command that separates "parked at ventilation minimum" from "modulating for free cooling"; binds both branches
    cxf: [dmprLow.t, dmprHigh.t]
  alarm_delay:
    default: 1800.0
    unit: s
    description: Continuous fault persistence required before the alarm asserts (30 min)
    cxf: persist.delayTime
energy_impact:
  affected_subsystem: RTU mechanical cooling energy
  savings_range: 5-20% of cooling energy; 54% of RTU economizers carry at least one fault (Cowan 2004)
  climate_sensitivity: cooling-dominant
  runtime_estimation: "waste_kw = comp_status x rtu_cooling_kw — under branch 1 the whole compressor draw is mechanical cooling the economizer would have displaced; under branch 2 it is the extra load the open damper created"
emissions:
  scope: "2"
  method: DIRECT_EMISSIONS
verified:
  engine_rev: e2ff2f8
  content_id: "cxf:fnv1a128:ed12779429be89a3c61d6668681918c6"
  date: 2026-08-17
---

## Description

A packaged unit's economizer has two jobs and this rule watches both of them
fail. When outdoor air is cool, the damper should be open and the compressor
should be doing less; when outdoor air is hot, the damper should be back at its
ventilation minimum and the compressor should not be paying to cool air that
was brought in on purpose. Branch 1 catches the damper parked at minimum on a
mild day with mechanical cooling running — free cooling standing right there,
unused. Branch 2 catches the opposite: 30 °C outdoor air pouring through a
damper that should have closed an hour ago, with the compressor absorbing the
difference.

The two failures come from different places. Stuck-at-minimum is usually
mechanical — a popped rod end, a dead actuator, a controller with economizing
switched off — and it is the single most common RTU economizer fault in
Cowan's 2004 survey, which found 54% of units carrying at least one. Stuck-open
is more often a spring-return actuator that has lost its return, or a high
limit set so high it never locks out. Both waste compressor energy and both
are invisible from a monthly bill, which is why the reference gives this fault
a 5–20% cooling-energy range and PNNL wrote two AFDD routines for it.

## Detection Logic

```
fault_1 = oat < econ_lockout_temp AND comp_status AND oa_dmpr_cmd < min_oa_margin
fault_2 = oat > econ_relock_temp  AND comp_status AND oa_dmpr_cmd > min_oa_margin

yFault  = (fault_1 OR fault_2), sustained continuously for alarm_delay
```

Block graph (`rule.cxf.jsonld`):

![RTU-FC-053 block graph](diagram.svg)

The two branches are mirror images: `oatLow`/`dmprLow` for the economizer that
will not open, `oatHigh`/`dmprHigh` for the one that will not close, each
conjoined with `comp_status` before `either` combines them. `comp_status` is in
the graph rather than in the frontmatter because it is not a gate on data
quality — it is part of the fault definition. Neither branch describes waste
without a compressor running: a damper at minimum on a cool morning with the
unit coasting is a unit that does not need cooling, not a broken economizer.

Between `econ_lockout_temp` and `econ_relock_temp` the rule is deliberately
silent. Neither temperature test is true in that band, so a unit changing over
at 21.4 °C — damper opening, closing, hunting a little while the mixed-air loop
settles — produces no verdict at all. That silence is what the reference's
`lockout_deadband` buys, and it is why the deadband is folded into a second
absolute threshold rather than a symmetric window around one (see Deviations).

All four comparisons are strict, so a damper resting exactly on `min_oa_margin`
trips neither branch, and outdoor air resting exactly on either temperature
setpoint arms neither. `persist` then requires 30 minutes of continuous
violation, which rides out a damper stroke, a changeover, and the minimum-
position dwell an economizer holds while its own control loop settles.

## Possible Diagnoses

1. OA damper stuck at minimum — disconnected linkage, failed actuator, bound
   blades (branch 1, and the most likely one by a wide margin)
2. OA damper stuck open — spring return failed, actuator jammed off its seat
   (branch 2)
3. Economizer controller disabled or misconfigured in the unit controller
4. OAT sensor reading erroneously high, which locks out changeover while the
   control sequence works correctly (branch 1's most common false positive,
   and the reason RTU-FC-052 suppresses this rule)
5. Economizer high-limit setpoint set too low for the climate zone, so the
   unit locks out during weather it should be economizing in

## Energy Impact

CRITICAL_WASTE, HIGH confidence, DIRECT_MEASUREMENT. The waste is compressor
work the economizer position made unnecessary, and the compressor status is one
of this rule's own inputs: `waste_kw = comp_status × rtu_cooling_kw`. Under
branch 1 that is the mechanical cooling free cooling would have displaced;
under branch 2 it is the load the open damper added. The reference's 5–20% of
cooling energy is consistent with PNNL EEM-06 (OA damper and controls) and
EEM-23 (RTU advanced controls, 3–11% of unit electricity). Confidence is HIGH:
the condition is read directly from a temperature and two commands with no
baseline or model in between, and both the prevalence and the savings range
come from field data rather than simulation. Strongly cooling-dominant, and
worth the most in shoulder seasons — which is exactly when a stuck economizer
is least likely to be noticed from inside the building.

## Emissions Impact

Scope 2, DIRECT_EMISSIONS, HIGH confidence; typical 800–5,000 kg CO₂e/yr for a
single packaged unit. The wasted energy is compressor electricity, so the whole
impact lands in purchased power. Free-cooling hours cluster in mild daytime and
overnight weather, when the marginal generator differs sharply from the annual
average — use the marginal operating emissions rate (MOER), not an average grid
factor, or the estimate will miss by the width of the grid's daily swing.

## Deviations

- **`min_oa_margin`'s default is adopted, not transcribed.** The reference
  states both branches in terms of `min_oa_margin` but omits it from the
  tunables table. This card adopts 25.0%, the value chapter 9 uses everywhere
  a damper counts as parked at minimum (AHU-FC-051's `econ_damper_threshold`),
  so "at minimum" means the same thing across both economizer rules. The
  reference's own vectors (10% versus 75–80%) are decidable at any margin
  between those, so the choice does not change a published result. AHU-FC-064
  precedent for adopted defaults.
- **The reference's `lockout_deadband` is folded into a second absolute
  threshold.** The reference writes branch 2 as `oat > econ_lockout_temp +
  lockout_deadband`. A card parameter binds a single value per CXF path and
  the block set cannot add two parameters in-graph, so branch 2 compares
  against `econ_relock_temp`, defaulted to 22.0 °C = 21.0 + 1.0. The
  consequence for hosts: moving the lockout means retuning **both**
  parameters, and setting `econ_relock_temp` below `econ_lockout_temp` overlaps
  the two temperature tests into a rule that fires at every damper position but
  the margin itself. Combined-parameter precedent AHU-FC-005; AHU-FC-064 makes
  the same trade in the other direction by feeding one term in as a constant.
- **`min_oa_margin` is one card parameter bound to two CXF paths**
  (`dmprLow.t`, `dmprHigh.t`), matching the reference's single margin. Hosts
  must set both together. Split them and a band of damper positions is either
  tested by neither branch (`dmprLow.t` below `dmprHigh.t`) or read as parked
  at minimum in cool weather and as open in warm weather at once
  (`dmprLow.t` above `dmprHigh.t`). AHU-FC-059 precedent.
- **All four comparisons are strict** (`<`, `>`, `<`, `>`). The reference does
  not specify boundary behavior, and CDL's Reals family has no `GreaterEqual`,
  so the inclusive reading is not directly expressible anyway. The deviation
  is measure-zero — a damper command sitting on exactly 25.00% or an outdoor
  temperature on exactly 21.00 °C — and it errs toward silence.
  `damper_at_margin_is_silent` and `lockout_setpoints_are_silent` pin all four.
- **The changeover band is a blind spot, by construction.** Between 21 and
  22 °C neither branch can fire, whatever the damper is doing, so a unit whose
  economizer fails while the weather sits in that 1 °C band reports nothing
  until the weather moves. `changeover_band_is_silent` pins the behavior. The
  alternative — reporting inside the band — would alarm on every normal
  changeover, which is what the reference's deadband exists to prevent.
- **`comp_status` is in-graph; everything else about mode is not.** The
  reference lists "cooling call active" as the operating state and
  `comp_status` as a term of both equations. The term is implemented; the
  broader gating (unit mode, occupancy, manual override, RTU-FC-052's sensor
  check) stays host-side per this library's design stance, as in AHU-FC-051.
- **Damper command, not damper feedback.** The reference names
  `oa_dmpr_cmd` and the RTU dictionary carries no damper position feedback
  point, so an actuator that reports 80% while the blades sit closed is
  invisible to this rule. That failure belongs to the mixed-air checks
  (RTU-FC-052) and to step 3 of the playbook, which is why the two are linked
  by suppression rather than by a shared input.
- **Test vectors: the reference's four, plus six of our own.** The published
  vectors (15 °C/80%/ON clear, 15 °C/10%/ON fault, 30 °C/10%/ON clear,
  30 °C/75%/ON fault) are transcribed as the first four scenarios. The
  deadband pin, both boundary pins, the compressor-off case, the transient,
  and the recovery case are authored here.
- Severity 3 (warning), phase 2, method `rule`, and the tunable defaults are
  the reference's chapter 11 card; its §5.8.3 index corroborates and carries no
  severity column. `g36: null` — this is a PNNL/Title 24-derived rule, not a
  G36 §5.16.14 clause.
- `persist.delayOnInit = true` (Modelica/CDL default is `false`), the library's
  standing choice: a violation already present at load waits out the full 30
  minutes instead of alarming on the first tick after a controller restart.

## Notes

This is AHU-FC-051's fault seen through packaged-unit points. AHU-FC-051 reads
a modulating cooling valve and can compare outdoor air to return air for a
differential changeover; an RTU has a compressor contactor and, in most
installations, a fixed dry-bulb high limit, so this card tests against absolute
setpoints and a boolean. The reference keeps them as separate cards, and so do
we: a site running both an AHU and a fleet of RTUs wants the same fault named
the same way per equipment family. Both sit in CLU-03, with AHU-FC-051 as the
cluster trigger and this card as a member.

Retune `econ_lockout_temp` for the climate zone before trusting the default.
21 °C is near ASHRAE 90.1's 70 °F fixed high limit for zones 4A–5A; zones
1A–3A allow 75 °F (23.9 °C) and zones 5B–8 use 65 °F (18.3 °C). Step 2.2 of the
[economizer-failure](../../../playbooks/economizer-failure.md) playbook carries
the table. A high limit set for the wrong zone produces this fault's branch 1
signature with nothing mechanically wrong, which is diagnosis 5 and a remote
fix.

Verify order within CLU-03: RTU-FC-052 first (it suppresses this rule for a
reason — a supply/mixed-air sensor pair that disagrees makes every economizer
verdict on the unit suspect), then this rule, then RTU-FC-054, whose excess
outdoor air is often just branch 2 seen from the airflow side. On a multi-unit
roof, survey the rest of the fleet after the first confirmed fault; the
playbook's step 4.4 puts the odds of a sibling unit having the same problem at
30–50%.
