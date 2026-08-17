---
schema: cxf-library/fault-card/v1
id: AHU-FC-055
name: Excess outdoor air during occupied hours
equipment: ahu
status: verified
phase: 2
method: rule
severity: 3
category: EXCESS_CONSUMPTION
confidence: HIGH
estimation_method: DIRECT_MEASUREMENT
source:
  - "HVAC FDD Reference v1.0 §9, AHU-FC-055"
  - "PNNL-27338 §3"
  - "PNNL EEM-17 (demand control ventilation)"
g36: null
clusters: []
suppresses: []
suppressed_by: [AHU-FC-062]
related: [AHU-FC-006, AHU-FC-051, AHU-FC-064]
playbooks: [economizer-failure]
operating_states: "occupied, non-economizer operation (host-gated); reference OS 1, OS 4"
preconditions: "Supply fan running. The host must not evaluate during economizer operation — bringing in more than the design minimum is the point of economizing, and this rule cannot tell that apart from a stuck damper. MAT must pass its integrity gate (AHU-FC-062, see suppressed_by): the fraction is a ratio of temperature differences, so a biased mixed-air reading moves it directly. The temperature-difference gate is signalled in-rule by yTempDeltaOk; when it is false the verdict is NO_EVAL, not healthy."
points:
  - mat
  - rat
  - oat
outputs:
  - name: yFault
    description: True while the outdoor air fraction has stayed more than oaf_threshold above desired_oaf for at least alarm_delay, with the temperature difference large enough to evaluate
  - name: yTempDeltaOk
    description: Evaluability signal — true when |oat − rat| exceeds oaf_temp_threshold; false means NO_EVAL and the host must ignore yFault
params:
  desired_oaf:
    default: 0.15
    unit: "1"
    description: Design outdoor air fraction the unit should hold at minimum ventilation (0–1)
    cxf: designConst.k
  oaf_threshold:
    default: 0.10
    unit: "1"
    description: Tolerance above the design fraction before the excess counts as a fault
    cxf: marginHigh.t
  oaf_temp_threshold:
    default: 6.0
    unit: "°C"
    description: Minimum |oat − rat| for the fraction to be meaningful; below it the rule is not evaluable
    cxf: deltaOk.t
  alarm_delay:
    default: 1800.0
    unit: s
    description: Continuous fault persistence required before the alarm asserts (30 min)
    cxf: persist.delayTime
energy_impact:
  affected_subsystem: AHU ventilation thermal energy
  savings_range: 2-10% of AHU thermal energy (PNNL-27338)
  climate_sensitivity: heating-dominant
  runtime_estimation: "excess_oa_kw = (actual_oaf − desired_oaf) × airflow × cp × |oat − rat|"
emissions:
  scope: "1+2"
  method: DIRECT_EMISSIONS
verified:
  engine_rev: e2ff2f8
  content_id: "cxf:fnv1a128:a9c58cb4c0e46fe131faed48a0c8efc0"
  date: 2026-08-17
---

## Description

The unit is pulling in more outdoor air than its design minimum ventilation
requires, and it is not economizing — every extra cubic metre has to be heated
or cooled to supply temperature for no ventilation benefit. Unlike a failed
economizer, this fault is invisible from the zone: the space stays comfortable,
the coils simply work harder to keep it that way, and the overspend runs
continuously through every occupied hour.

The outdoor air fraction is inferred from the mixing-box energy balance rather
than measured, which is what makes the diagnostic cheap — three temperature
sensors most AHUs already have, no airflow station. It is also what makes it
conditional: the inference only holds when outdoor and return air differ enough
for the mixture to locate the fraction, which is why this rule carries an
explicit evaluability output. AHU-FC-064 is the same measurement narrowed to
heating operation, where the excess is most expensive. Present in roughly 15%
of buildings.

## Detection Logic

```
oaf          = (mat − rat) / (oat − rat)
yTempDeltaOk = |oat − rat| > oaf_temp_threshold     (false ⇒ host reports NO_EVAL)
yFault       = (oaf − desired_oaf > oaf_threshold) AND yTempDeltaOk,
               sustained for alarm_delay
```

Block graph (`rule.cxf.jsonld`):

![AHU-FC-055 block graph](diagram.svg)

`matRat` and `oatRat` form the two differences, `oaf` divides them, and
`margin` subtracts the design fraction so that `marginHigh` tests the excess
against a single positive threshold. Both tunables the reference exposes stay
independent single-value parameters this way: the design fraction is
`designConst.k` and the tolerance is `marginHigh.t`, each one number, neither
requiring a sign flip when a host retunes it through `set_param`.

`oatRat` fans out a second time into `absDelta` and `deltaOk`, the evaluability
branch. Its output is both the boundary output `yTempDeltaOk` and the second
input of `gate`, so the gate holds `yFault` down over exactly the interval the
host is told to disregard it. That belt-and-braces arrangement matters because
the division is unguarded: CDL `Divide` follows IEEE-754, so `oat = rat`
yields ±∞ or NaN rather than an error, and a near-zero denominator amplifies
ordinary sensor noise into a fraction of any magnitude. NaN compares false
everywhere, so a NaN can never raise `marginHigh` — but ±∞ and a noise-inflated
finite fraction both can, and `gate` is what stops them. Garbage arithmetic
cannot assert a fault; it can only make the rule report itself unevaluable.

Both comparisons are strict. An outdoor air fraction sitting exactly at
`desired_oaf + oaf_threshold` is not a fault, and a temperature difference of
exactly `oaf_temp_threshold` is not evaluable. The fraction is signed
consistently on both sides of the year — in summer both differences are
positive, in winter both negative, and the quotient reads the same — so no
seasonal branch is needed. `persist` requires 30 continuous minutes, which
rides out damper strokes and the mixing transient after a mode change.

## Possible Diagnoses

1. OA damper minimum position set too high
2. OA damper not closing to minimum — stuck, or the sequence never commands it
   back down after a purge or economizer period
3. Damper actuator issue: failed actuator, slipped linkage, or a position
   feedback that disagrees with the blade
4. Exhaust fan creating negative building pressure that pulls outdoor air in
   past the minimum position

## Energy Impact

EXCESS_CONSUMPTION, HIGH confidence, DIRECT_MEASUREMENT. The waste is
computable from live data: `excess_oa_kw = (actual_oaf − desired_oaf) ×
airflow × cp × |oat − rat|`, with the excess fraction already on the wire as
`oaf − designConst.k`. Correcting minimum ventilation saves 2–10% of AHU
thermal energy (PNNL-27338), the upper half of that range in heating-dominant
climates where the outdoor–return difference — and therefore the cost of every
extra cubic metre — is largest. PNNL EEM-17 (demand control ventilation) is
the related retrofit, and this rule is its screening test: a unit already over
its design fraction with the dampers at minimum will not benefit from CO₂
control until the mechanical problem is fixed. Prevalence ~15%.

## Emissions Impact

Scope 1 + 2, DIRECT_EMISSIONS, HIGH confidence; typical 500–4,000 kg CO₂e/yr
for the excess ventilation thermal load. The split follows the season: excess
outdoor air in winter usually burns scope 1 fuel at the heating coil, in
summer it draws scope 2 electricity at the chiller. Avoided-emissions basis:
marginal operating emissions rate (MOER).

## Deviations

- **The reference's `AND NOT econ_favorable` term is not in the block graph.**
  Economizer operation is an operating state, not a measurement, and the
  reference itself scopes this fault to non-economizer states. This library
  keeps operating-state gating host-side per its design stance (precedent:
  AHU-FC-051 keeps its OS-4 restriction in `preconditions`), so the term lives
  in `operating_states` and `preconditions` instead. The consequence is
  concrete: the reference's third test vector — economizer mode with an 80%
  outdoor air fraction, expected NO_FAULT — has no counterpart in
  `vectors.json`, because in this library that verdict is produced by the host
  gate rather than by the rule. A host that evaluates this rule during
  economizing will get a fault, and it will be the host's bug.
- **Design fraction as a constant, excess as a threshold.** The reference
  writes the test as `oaf > (desired_oaf + oaf_threshold)`. Implemented that
  way, the two tunables would have to be summed into one threshold value, and
  a host could no longer retune either alone. Feeding `desired_oaf` in as
  `Reals.Sources.Constant.k` and comparing the remaining margin against
  `oaf_threshold` keeps both as independent single-value `set_param` paths
  with no sign flips. Algebraically identical.
- **Evaluability is an output, not just a precondition.** The reference states
  the fraction is meaningful only when outdoor and return air differ enough
  (PNNL-27338 uses 5 °F for the same computation; the reference's
  `oaf_temp_threshold` default of 6 °C is adopted here). Because that test is
  computable from this rule's own inputs, SCHEMA.md requires exposing it as a
  boolean output: `yTempDeltaOk`. It is additionally wired into `gate`, so
  `yFault` reads false throughout a non-evaluable period — but false `yFault`
  under false `yTempDeltaOk` means "unknown", not "healthy", and the host must
  treat it that way.
- **Both comparisons are strict** (`>`). The reference does not specify
  boundary behavior; strict inequalities keep a fraction sitting exactly on
  the alarm point and a temperature difference sitting exactly on the
  evaluability limit out of the alarm, and the vectors pin both choices.
- `persist.delayOnInit = true` (Modelica/CDL default is `false`), the
  library's standing choice: an excess already present at load waits out the
  full 30 minutes instead of alarming on the first tick after a controller
  restart.

## Notes

Check the minimum position setpoint before sending anyone to the roof. The
most common cause is not a broken damper but a minimum position dialled up
during a ventilation complaint or a commissioning shortcut, and it is a
$0 desk fix; the [economizer-failure](../../../playbooks/economizer-failure.md)
playbook's damper and linkage steps come after that.

The rule is deliberately blind to why the outdoor air fraction is high. A
damper stuck at 40% and a building held under negative pressure by an
oversized exhaust fan produce the same number, and the second is invisible
from the AHU's own points — if commanding the damper closed does not move the
fraction, measure building pressure before replacing the actuator.
