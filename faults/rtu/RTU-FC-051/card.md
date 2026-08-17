---
schema: cxf-library/fault-card/v1
id: RTU-FC-051
name: Evaporator coil fouling — reduced temperature split
equipment: rtu
status: verified
phase: 2
method: statistical
severity: 3
category: EFFICIENCY_LOSS
confidence: MEDIUM
estimation_method: BASELINE_COMPARISON
source:
  - "HVAC FDD Reference v1.0 §11, RTU-FC-051"
  - "Catrini & Piacentino 2023"
  - "Ebrahimifakhar et al. 2020"
g36: null
clusters: []
suppresses: []
suppressed_by: [RTU-FC-052]
related: [RTU-FC-052, RTU-FC-100]
playbooks: [rtu-compressor-refrigerant]
operating_states: "mechanical cooling, one or two compressor stages"
preconditions: "The compressor must have run at its current stage for min_runtime_for_eval (15 min) before the split is read; the coil is still pulling down after a start or a stage change and reads falsely degraded. sat must pass its integrity gate: RTU-FC-052 (see suppressed_by) checks it against mat and silences this rule while it is active. Nothing validates rat on its own, so a drifted return-air sensor biases the split with no other symptom. Stage evaluability is signalled in-rule by yStageOk; when it is false the verdict is NO_EVAL, not healthy."
points:
  - rat
  - sat
  - comp_stage
outputs:
  - name: yFault
    description: True while the measured temperature split has stayed more than split_degradation_threshold below the baseline for the running stage, for at least alarm_delay
  - name: yStageOk
    description: Evaluability signal — true when comp_stage is 1 or 2, the stages this rule carries baselines for; false means NO_EVAL and the host must ignore yFault
params:
  split_degradation_threshold:
    default: 0.25
    unit: "1"
    description: Fractional shortfall of the measured split against the stage baseline that counts as fouling (0.25 = 25% below baseline)
    cxf: ratioHigh.t
  baseline_split_stage_1:
    default: 8.0
    unit: "°C"
    description: Expected rat − sat with one compressor stage running on a clean coil at design airflow
    cxf: base1.k
  baseline_split_stage_2:
    default: 12.0
    unit: "°C"
    description: Expected rat − sat with two compressor stages running on a clean coil at design airflow
    cxf: base2.k
  alarm_delay:
    default: 3600.0
    unit: s
    description: Continuous degradation required before the alarm asserts (60 min)
    cxf: persist.delayTime
energy_impact:
  affected_subsystem: RTU evaporator — reduced capacity plus fan power
  savings_range: 13.3% capacity reduction, up to 47% fan power increase (Catrini & Piacentino 2023)
  climate_sensitivity: cooling-dominant
  runtime_estimation: "waste_kw = (expected_split − actual_split) / expected_split × rtu_kw"
emissions:
  scope: "2"
  method: PROXY_EMISSIONS
verified:
  engine_rev: e2ff2f8
  content_id: "cxf:fnv1a128:da9a9817ba72e7a56a69ec6f4e2c7e9b"
  date: 2026-08-17
---

## Description

A clean evaporator coil at design airflow drops the air passing through it by a
predictable amount — roughly 8 °C on one compressor stage, 12 °C on two. When
that split shrinks while the same stage runs, the coil is no longer moving the
heat it should. Dust on the fins, a loaded filter, ice, or a charge that has
leaked away all produce the same reading, and they cost the same way: the unit
runs longer for the same cooling, and where the cause is restricted airflow the
fan spends more energy per unit of air delivered.

The measurement is two temperatures and a stage number, which is what makes it
practical on packaged equipment carrying no refrigerant instrumentation. It is
also why the rule is blind to cause — the diagnoses below run from a filter
change to a refrigerant leak and this rule cannot separate them. Catrini &
Piacentino (2023) measured 13.3% capacity loss and up to 47% additional fan
power on fouled units; the reference cites Ebrahimifakhar et al. (2020)
alongside it for the diagnostic.

## Detection Logic

```
actual_split   = rat − sat
expected_split = baseline_split_stage_2  if comp_stage = 2
                 baseline_split_stage_1  otherwise
degradation    = (expected_split − actual_split) / expected_split

yStageOk = comp_stage > 0 AND comp_stage ≤ 2       (false ⇒ host reports NO_EVAL)
yFault   = degradation > split_degradation_threshold AND yStageOk,
           sustained for alarm_delay
```

Block graph (`rule.cxf.jsonld`):

![RTU-FC-051 block graph](diagram.svg)

`expected` is a `Reals.Switch` picking between two `Sources.Constant` baselines
on the output of `isStage2`, an `Integers.Equal` against `kTwo`. Both baselines
are live on every tick and the selector chooses one, which follows AHU-FC-051's
economizer-type precedent; the difference is that its selector is a configured
boolean and this one is a comparison on a live point, so the baseline can
change under the rule mid-run. `expected` fans out to both `degr` (the
shortfall) and `ratio` (the normalizer), so the fraction is always taken
against the baseline the shortfall was measured from.

Because that denominator is a selected constant and never a live signal, the
division is safe by construction: 8 or 12, never zero, never noisy. The
library's other divider has to work for it — AHU-FC-055 computes an outdoor-air
fraction whose denominator is a temperature difference that can pass through
zero, and its evaluability branch exists partly to keep the resulting ±∞ out of
the alarm. The evaluability output here answers a different question: which
stages does the rule have baselines for? `stagePos` and `stageKnown` bracket
`comp_stage` to 1–2 (`stagePos` carries no `t` node — CDL's default integer
threshold is already the 0 this test wants, and the CXF contract sets only
non-default parameters), and `stageOk` both drives the boundary output
`yStageOk` and feeds the second input of `gate`. With the compressor off or on an unmodelled third
stage `yFault` is held down, and that false means "not evaluated", not "coil is
clean". Stage 0 is the case that matters in practice: with no compressor
running, `rat − sat` collapses toward zero and reads as near-total degradation.

The comparison is strict, so a split sitting exactly 25% below baseline is not
a fault and 25.1% is. `persist` requires 60 continuous minutes of degradation —
long enough to ride out short-lived swings in return air, and on a unit that
stages up and stays up, long enough for the split to settle well before the
timer matures.

## Possible Diagnoses

1. Evaporator coil fouled — dust and lint bridging the fins, usually
   downstream of a filter that was never changed. A loaded filter alone
   produces the same reading and is the cheapest thing on this list to rule
   out
2. Low refrigerant charge from a leak, which shrinks the split the same way
3. Evaporator fan motor or drive degradation cutting airflow — belt slip, a
   failing motor, or a dirty blower wheel
4. Iced evaporator coil, itself usually a symptom of low charge or low airflow

## Energy Impact

EFFICIENCY_LOSS, MEDIUM confidence, BASELINE_COMPARISON. The degradation
fraction the rule already computes is the estimator: `waste_kw = (expected_split
− actual_split) / expected_split × rtu_kw`, treating the shortfall in capacity
as proportional extra runtime at the unit's rated draw — a unit reading 30%
degraded books 0.30 × `rtu_kw` as waste. Catrini & Piacentino (2023) put the
measured effect at 13.3% capacity reduction and as much as 47% additional fan
power on the airflow-restricted cases. PNNL EEM-23 (advanced RTU controls) is
the related retrofit package. The estimate is proportional, not
measured — the baselines are population values, not this unit's commissioned
performance — which is what holds confidence at MEDIUM rather than HIGH.

## Emissions Impact

Scope 2, PROXY_EMISSIONS, MEDIUM confidence; typically 300–2,000 kg CO₂e/yr for
a commercial packaged unit, scaling with tonnage and cooling hours. Emissions
follow the added compressor and fan electricity, so the avoided-emissions basis
is the marginal operating emissions rate (MOER) — fouling costs most on hot
afternoons, when the grid is dirtiest and the unit runs longest.

## Deviations

- **The per-stage baseline function is a two-way `Switch`, not a lookup.** The
  reference writes `expected_split = baseline_split_for_stage(comp_stage)`,
  an open-ended mapping. The block set has no table lookup keyed by an integer,
  and the reference itself supplies exactly two baselines, so the rule
  implements the two it is given: `isStage2` selects `base2` when
  `comp_stage = 2` and `base1` otherwise. A host with three or more stages
  instantiates the rule once per stage pair, rebinding `base1`, `base2`,
  `kTwo.k`, and the two integer bounds together. Widening `stageKnown.t` on its
  own is the trap: it removes the NO_EVAL signal while stage 3 still falls
  through to the stage-1 baseline, turning a deliberate silence into a wrong
  answer.
- **Stage evaluability is an output, not just a precondition.** The stage range
  test is computable from this rule's own inputs, so per SCHEMA.md it is
  exposed as `yStageOk` rather than left implicit. `comp_stage = 0` is the
  motivating case: the reference lists "compressor running for min_runtime" as
  a precondition, and a rule that silently returned false there would be
  reporting a healthy coil on a unit that is not cooling at all.
- **`min_runtime_for_eval` (15 min) stays a host precondition.** It gates on a
  transition — time since the last stage change — which the block graph cannot
  see, and this library keeps state gating host-side. The 60-minute
  `alarm_delay` covers it in steady operation but does not substitute for it:
  the pull-down after a stage change starts the persistence timer rather than
  being excluded from it, so a coil taking 20 minutes to settle at its new
  split spends a third of the alarm window looking fouled. The vectors pin the
  timing (`stage_change_restarts_persistence`).
- **`method: statistical` describes the provenance of the baselines, not the
  graph.** The block graph performs one subtraction, one division, and one
  threshold comparison — nothing statistical happens at runtime. The
  classification is the reference's, and it is fair: the 8/12 °C baselines are
  population values from the fouling literature rather than a commissioned
  measurement of the unit in front of you, and the library records that
  provenance rather than relabelling the card.
- **Strict `>` at the degradation threshold, where the reference's playbook is
  inclusive.** The card's equation is strict — degradation *greater than* the
  threshold — but the RTU compressor playbook's verification step reads "a 25%
  or greater reduction in split indicates fouling". CDL Reals has no
  `GreaterEqual`, so the strict form is the one that is expressible, and a
  split sitting at exactly 25% below baseline reads healthy here. The
  disagreement is measure-zero on a real-valued signal; both sides are pinned
  by vectors (`edge_degradation_equals_threshold`,
  `edge_degradation_just_over_threshold`).
- **The threshold is carried as a fraction, not a percentage.** The reference
  writes the default as 25%; `ratioHigh.t` is `0.25`, matching the
  dimensionless quotient the graph computes. A host that set this parameter to
  `25` would disable the rule, so the card declares its unit as `1` rather than
  `%`.
- `persist.delayOnInit = true` (CDL default is `false`): a coil already
  degraded when the controller starts waits out the full hour rather than
  alarming on the first tick.

## Notes

The reference publishes no test vectors for this card, so every scenario in
`vectors.json` is library-authored. The pair worth reading is
`stage1_split_7_is_healthy` and `stage2_split_7_is_fouled`: the same 7 °C
split, the same two temperatures, opposite verdicts, because the stage picks
the baseline. That pair is the regression test for the `Switch` — wire it
backwards and both scenarios fail.

The [rtu-compressor-refrigerant](../../../playbooks/rtu-compressor-refrigerant.md)
playbook (transcribed from the reference alongside this card) orders the
fouling remediation: filter first ($50–$200 a bank, and the most common
cause), then coil cleaning ($200–$500), then the evaporator fan motor, then
ice. Its resolution test is the split returning to within 15% of baseline,
which is worth noting because that is tighter than the 25% this rule alarms
at — a coil cleaned back to 20% degraded clears the alarm without being
fixed.

Start at the filter, because it reproduces the fouled-coil signature exactly
and costs minutes to rule out. If a fresh filter does not restore the split,
the question is airflow versus refrigerant, and the two separate at the unit:
an airflow problem shows in static pressure across the coil and in measured
airflow, a charge problem shows in superheat and subcooling at the service
ports. Neither is visible from the points this rule reads, which is the honest
limit of a two-temperature diagnostic — it says the coil is not moving the heat
it should and nothing about why. RTU-FC-100 (condenser airflow restriction) is
the condenser-side counterpart and is deferred: its baseline depends on both
stage and outdoor temperature, which needs the baseline-curve infrastructure
this block set does not have.
