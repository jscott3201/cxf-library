---
schema: cxf-library/fault-card/v1
id: RTU-FC-054
name: Excess outdoor air intake
equipment: rtu
status: verified
phase: 2
method: rule
severity: 3
category: EXCESS_CONSUMPTION
confidence: HIGH
estimation_method: DIRECT_MEASUREMENT
source:
  - "HVAC FDD Reference v1.0 §11, RTU-FC-054"
  - "PNNL-23790 (RTU AFDD4/AFDD5)"
  - "PNNL EEM-17 (demand control ventilation)"
  - "PNNL EEM-23 (RTU advanced controls)"
g36: null
clusters: []
suppresses: []
suppressed_by: [AHU-FC-062]
related: [AHU-FC-055, AHU-FC-064, RTU-FC-055, RTU-FC-053]
playbooks: [economizer-failure]
operating_states: "occupied operation with the economizer locked out (host-gated); the reference's economizer_should_be_inactive(oat, mode) term lives in preconditions, not in the graph"
preconditions: "Supply fan running. The host must not evaluate while the economizer is legitimately open — drawing more than the design minimum is the point of economizing, and these three temperatures cannot tell that apart from a damper that never closed. MAT must pass its integrity gate (AHU-FC-062, see suppressed_by): the fraction is a ratio of temperature differences, so a biased mixed-air reading moves it directly. The temperature-difference gate is signalled in-rule by yTempDeltaOk; when it is false the verdict is NO_EVAL, not healthy."
points:
  - oat
  - rat
  - mat
outputs:
  - name: yFault
    description: True while the outdoor air fraction has stayed more than oa_excess_margin above design_min_oa_fraction for at least alarm_delay, with the temperature difference large enough to evaluate
  - name: yTempDeltaOk
    description: Evaluability signal — true when |oat − rat| exceeds min_delta; false means NO_EVAL and the host must ignore yFault
params:
  design_min_oa_fraction:
    default: 0.15
    unit: "1"
    description: Design minimum outdoor air fraction the unit should hold when it is not economizing (0–1)
    cxf: designConst.k
  oa_excess_margin:
    default: 0.15
    unit: "1"
    description: Tolerance above the design minimum before the excess counts as a fault
    cxf: marginHigh.t
  min_delta:
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
  affected_subsystem: RTU thermal energy spent conditioning excess ventilation air
  savings_range: 2-10% of unit thermal energy (HVAC FDD Reference §11; PNNL EEM-17, EEM-23)
  climate_sensitivity: heating-dominant
  runtime_estimation: "excess_oa_kw = (actual_oaf − design_min_oa_fraction) × airflow × cp × |oat − rat|"
emissions:
  scope: "1+2"
  method: DIRECT_EMISSIONS
verified:
  engine_rev: e2ff2f8
  content_id: "cxf:fnv1a128:403a34cdcdb48f2f6c7f4827a80b4ab9"
  date: 2026-08-17
---

## Description

The unit is drawing well over its design minimum outdoor air at an hour when it
has no business economizing. Every extra cubic metre arrives at outdoor
temperature and has to be dragged to supply temperature by the gas heat or the
compressors, and none of it buys any ventilation the code did not already have.
Nothing about it is uncomfortable — the space stays on setpoint, the unit simply
runs harder to keep it there — so the defect survives until someone reads the
fuel bill.

Packaged units make this failure common. The economizer, the minimum-position
setting, and the dampers all live in one weather-exposed cabinet on a roof
nobody visits, and Cowan's 2004 field survey found at least one economizer fault
on 54% of units. Two of this card's four diagnoses are numbers somebody typed and
two are hardware that weathered; the rule cannot tell them apart, which is what
the playbook's first step is for.

The outdoor air fraction is inferred from the mixing-box energy balance rather
than measured, which is what makes the diagnostic cheap: three temperature
sensors a packaged unit usually already has, no airflow station. It is also what
makes it conditional, which is why the rule carries an explicit evaluability
output.

## Detection Logic

```
oaf          = (mat − rat) / (oat − rat)
yTempDeltaOk = |oat − rat| > min_delta                  (false ⇒ host reports NO_EVAL)
yFault       = (oaf − design_min_oa_fraction > oa_excess_margin) AND yTempDeltaOk,
               sustained for alarm_delay
```

Block graph (`rule.cxf.jsonld`):

![RTU-FC-054 block graph](diagram.svg)

The fraction core is AHU-FC-055's, unchanged, bound to the RTU point
dictionary: `matRat` and `oatRat` form the two differences, `oaf` divides them,
and `margin` subtracts the design fraction so `marginHigh` tests the excess
against a single positive threshold. Both reference tunables stay independent
single-value parameters that way — the design fraction is `designConst.k`, the
tolerance is `marginHigh.t` — so a host can retune either through `set_param`
without touching the other and without a sign flip.

`oatRat` fans out a second time into `absDelta` and `deltaOk`, the evaluability
branch. Its output goes to two places: into `gate` as the second half of the
fault condition, and out of the block as `yTempDeltaOk`. A host that ignores the
output still gets the right verdict from the gate; a host that reads it learns
the difference between "not faulted" and "cannot tell", which the boolean alone
does not carry.

That arrangement is also what makes the unguarded division safe. CDL `Divide`
follows IEEE-754, so `oat = rat` yields ±∞ or NaN rather than an error, and a
near-zero denominator amplifies ordinary sensor noise into a fraction of any
magnitude. NaN compares false everywhere and can never raise `marginHigh` — but
±∞ and a noise-inflated finite fraction both can, and `gate` stops them, because
a denominator small enough to misbehave is by construction a denominator below
`min_delta`. Garbage arithmetic cannot assert a fault; it can only make the rule
report itself unevaluable. The `small_delta_not_evaluable` vector pins that: the
raw fraction there reads 0.50, `marginHigh` is true, and `yFault` stays down.

Both comparisons are strict. A fraction sitting exactly at
`design_min_oa_fraction + oa_excess_margin` is not a fault, and a temperature
difference of exactly `min_delta` is not evaluable. The quotient is signed
consistently on both sides of the year — in winter both differences are
negative, in summer both positive, and it reads the same — so no seasonal branch
is needed; `summer_excess_oat_above_rat` pins that. `persist` requires 30
continuous minutes, which rides out a damper stroke and the mixing transient
after a stage change; recovery is immediate on the tick the fraction falls back
inside the margin.

## Possible Diagnoses

1. OA damper minimum position set too high
2. OA damper not closing to the commanded minimum
3. Damper blade seals deteriorated
4. Economizer lockout not engaging

## Energy Impact

EXCESS_CONSUMPTION, HIGH confidence, DIRECT_MEASUREMENT. The waste is computable
from live data: `excess_oa_kw = (actual_oaf − design_min_oa_fraction) × airflow
× cp × |oat − rat|`, with the excess fraction already on the wire as
`oaf − designConst.k`. Correcting minimum ventilation is worth 2–10% of the
unit's thermal energy, the upper half of that range in heating-dominant climates
where the outdoor-to-return difference — and therefore the price of every extra
cubic metre — is largest for months at a time. The reference maps the fault to
PNNL EEM-17 (demand control ventilation) and EEM-23 (RTU advanced controls), and
this rule screens both: a unit that cannot hold its design fraction with the
dampers commanded to minimum will not benefit from CO₂ control or a new
economizer controller until the mechanical problem is fixed.

## Emissions Impact

Scope 1 + 2, DIRECT_EMISSIONS, HIGH confidence; typical 300–2,500 kg CO₂e/yr for
the excess ventilation load. The split follows the season and the unit: excess
outdoor air in winter burns scope 1 gas at the furnace section, in summer it
draws scope 2 electricity at the compressors, and on an all-electric packaged
unit the whole exchange collapses to scope 2. Avoided-emissions basis: marginal
operating emissions rate (MOER).

## Deviations

- **`min_delta` default adopted, not transcribed.** The reference states the
  fraction is computed only when `|OAT − RAT| > min_delta` but omits the
  parameter from its tunables table. This card adopts 6.0 °C, matching
  AHU-FC-055 and AHU-FC-064 so every rule in the library that runs this quotient
  agrees on when it is meaningful (PNNL-27338 uses 5 °F for the same
  computation). RTU-FC-055 adopts the same value for the same reason. A site
  that retunes one should retune all of them.
- **The reference's `economizer_should_be_inactive(oat, mode)` term is not in
  the block graph.** Economizer state is an operating state, not a measurement,
  and this library keeps operating-state gating host-side (precedent:
  AHU-FC-055, whose reference card carries the same term as
  `AND NOT econ_favorable`). It lives in `operating_states` and `preconditions`
  instead. The consequence is concrete: a host that evaluates this rule while
  the unit is economizing will get a sustained fault, and it will be the host's
  bug, not the rule's. `mode` is not a canonical RTU point in any case, so the
  term is not expressible here without inventing one.
- **Design fraction as a constant, excess as a threshold.** The reference writes
  the test as `oa_fraction > (design_min_oa_fraction + oa_excess_margin)`.
  Implemented that way the two tunables would have to be summed into one
  threshold value and a host could no longer retune either alone. Feeding the
  design fraction in as `Reals.Sources.Constant.k` and comparing the remaining
  margin against `oa_excess_margin` keeps both as independent single-value
  `set_param` paths with no sign flips. Algebraically identical.
- **Evaluability is an output, not just a precondition.** The `min_delta` test
  is computable from this rule's own inputs, so SCHEMA.md requires exposing it
  as a boolean output: `yTempDeltaOk`. It is additionally wired into `gate`, so
  `yFault` reads false throughout a non-evaluable period — but false `yFault`
  under false `yTempDeltaOk` means "unknown", not "healthy", and the host must
  treat it that way.
- **Both comparisons are strict** (`>`). The reference does not specify boundary
  behavior; CDL `Reals` offers no `GreaterEqual`, so the choice is made rather
  than inherited. Strict inequalities keep a fraction sitting exactly on the
  alarm point and a temperature difference sitting exactly on the evaluability
  limit out of the alarm. The disagreement with an inclusive reading has measure
  zero on a real temperature signal and errs toward silence; both boundaries are
  pinned from both sides in `vectors.json`.
- **No published test vectors.** The reference's chapter 11 card states the
  logic, the tunables, the diagnoses, and the energy and emissions profiles, but
  publishes no worked vectors for this fault. `vectors.json` is authored from
  the equation, following AHU-FC-055's suite shape: normal minimum ventilation,
  a clear excess, the summer sign case, both sides of the margin boundary, both
  sides of the evaluability boundary, the NO_EVAL case with a true `marginHigh`
  to prove the gate does the work, a transient shorter than `alarm_delay`, and a
  recovery.
- `persist.delayOnInit = true` (Modelica/CDL default is `false`), the library's
  standing choice: an excess already present at load waits out the full 30
  minutes instead of alarming on the first tick after a controller restart.

## Notes

`suppressed_by: [AHU-FC-062]` is transcribed verbatim from the reference's note
on this card, and it points across equipment families on purpose. AHU-FC-062
tests whether MAT lies inside the envelope its two sources bracket, and that
graph consumes nothing but `mat`, `oat`, and `rat` — it is equipment-agnostic,
exactly as AHU-FC-061's block graph is, and the host instantiates it against
this RTU's own three points rather than against an air handler somewhere else in
the building. Deploy the pair together. A MAT sensor reading 4.5 °C low in −5 °C
weather turns a compliant 0.15 fraction into 0.32 and manufactures this fault out
of nothing; on a milder day with a 10 °C outdoor-to-return spread, under 2 °C of
bias does the same. Checking a sensor is far cheaper than sending someone onto
the roof.

RTU-FC-055 is this rule's mirror and shares its three temperatures, adding
occupancy and fan status: this one alarms more than 0.15 above design, that one
more than 0.05 below. The margins are deliberately asymmetric, because the two
failures cost different things — excess air costs money, deficient air costs air
quality — and the reference sizes each for its own job. Neither can fire while
the other does.

If the fraction is genuinely high, the fastest discriminator is to command the
OA damper to minimum and watch the mixed-air temperature. It should climb toward
return temperature within a few minutes. If it does not move, the problem is
mechanical — actuator, linkage, or blade seals — and the
[economizer-failure](../../../playbooks/economizer-failure.md) playbook's
on-site steps apply. If it does move, the sequence never commanded minimum
position in the first place, and the fix is at a desk. Check the minimum
position setpoint before either: the most common cause is not a broken damper
but a number dialled up during a ventilation complaint, and that is a $0 fix.
