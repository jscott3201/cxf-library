---
schema: cxf-library/fault-card/v1
id: ERV-FC-050
name: Sensible effectiveness degradation
equipment: erv
status: verified
phase: 2
method: statistical
severity: 3
category: EFFICIENCY_LOSS
confidence: MEDIUM
estimation_method: BASELINE_COMPARISON
source:
  - "HVAC FDD Reference v1.0 §15, ERV-FC-050"
  - "Nehasil et al. 2021"
  - "Mattera et al. 2020"
  - "PNNL EEM-37 (optimized heat recovery wheel)"
g36: null
clusters: []
suppresses: []
suppressed_by: []
related: [ERV-FC-051]
playbooks: [erv-effectiveness]
operating_states: "ERV enabled with both supply and exhaust fans running"
preconditions: "Both fans must be running. The graph consumes erv_enabled and holds the alarm down while it is false, but an enable command is not proof that air is moving: a unit enabled with a failed exhaust fan reads as low effectiveness, correctly in arithmetic and wrongly in diagnosis, and the ERV dictionary carries no fan-status point to separate the two. The host must also not evaluate during frost protection — a unit in preheat, wheel-speed reduction, or bypass is recovering less on purpose, and erv_frost_prot (ERV-FC-051's point) is the flag to gate on. All three temperature sensors must be trustworthy and correctly positioned: entering upstream of the recovery device, leaving downstream of it and upstream of any coil, exhaust on the building side. A leaving-air sensor mounted after the preheat coil measures the coil, not the wheel. Temperature-difference evaluability is signalled in-rule by yTempDeltaOk; when it is false the verdict is NO_EVAL, not healthy."
points:
  - erv_oa_entering_temp
  - erv_oa_leaving_temp
  - erv_exhaust_temp
  - erv_enabled
outputs:
  - name: yFault
    description: True while the measured sensible effectiveness has stayed more than effectiveness_threshold below baseline_effectiveness for at least alarm_delay, with the ERV enabled and the temperature difference large enough to evaluate
  - name: yTempDeltaOk
    description: Evaluability signal — true when |erv_exhaust_temp − erv_oa_entering_temp| exceeds min_delta_for_eval; false means NO_EVAL and the host must ignore yFault
params:
  baseline_effectiveness:
    default: 0.75
    unit: "1"
    description: Design sensible effectiveness of the recovery device (0–1). Per-unit configuration — the shipped 0.75 is the reference's population default, not this unit's rating (see Deviations)
    cxf: base.k
  effectiveness_threshold:
    default: 0.15
    unit: "1"
    description: Shortfall below baseline that counts as degradation (0.15 = 15 effectiveness points)
    cxf: shortHigh.t
  min_delta_for_eval:
    default: 5.0
    unit: "°C"
    description: Minimum |exhaust − entering| for the effectiveness ratio to be meaningful; below it the rule is not evaluable and the division is not trustworthy
    cxf: deltaOk.t
  alarm_delay:
    default: 1800.0
    unit: s
    description: Continuous degradation required before the alarm asserts (30 min)
    cxf: persist.delayTime
energy_impact:
  affected_subsystem: Energy recovery — lost heat/cool recovery
  savings_range: 10-30% of recovery energy lost
  climate_sensitivity: both
  runtime_estimation: "lost_kw = (baseline_eff − actual_eff) × airflow × cp × |erv_exhaust_temp − erv_oa_entering_temp|"
emissions:
  scope: "1+2"
  method: PROXY_EMISSIONS
verified:
  engine_rev: e2ff2f8
  content_id: "cxf:fnv1a128:968e1ca7cc234dd1107a381f01adb7b2"
  date: 2026-08-17
---

## Description

An energy recovery device is a heat exchanger between two air streams, and its
whole value is the fraction of the available temperature difference it manages
to move. That fraction is measurable from three temperatures: how far the
incoming outdoor air was dragged toward the exhaust temperature, over how far
it could have been dragged. A wheel that has stopped turning, a plate core
packed with dust, a bypass damper stuck open, or a run-around loop that has
lost its pump all read the same way — the outdoor air arrives at the coils
almost as cold (or as hot) as it started.

The fault is quiet in every other respect. Ventilation air is still delivered,
the space is still conditioned, and the extra load lands on the heating and
cooling coils downstream where it looks like ordinary weather. That is what
makes the effectiveness computation worth doing: it is the only reading that
distinguishes a recovery device from a duct.

The measurement is only as good as the temperature difference behind it. When
outdoor and exhaust air are close — mild shoulder-season afternoons, which is
much of the year — the denominator collapses, sensor error dominates, and the
ratio reports whatever it likes. This rule therefore carries an explicit
evaluability output rather than pretending the number is always meaningful.
Nehasil et al. (2021) report a 90% detection rate for this diagnostic; the
reference cites Mattera et al. (2020) alongside it.

## Detection Logic

```
effectiveness = (erv_oa_leaving_temp − erv_oa_entering_temp)
                / (erv_exhaust_temp − erv_oa_entering_temp)
shortfall     = baseline_effectiveness − effectiveness

yTempDeltaOk  = |erv_exhaust_temp − erv_oa_entering_temp| > min_delta_for_eval
                                                    (false ⇒ host reports NO_EVAL)
yFault        = shortfall > effectiveness_threshold AND yTempDeltaOk AND erv_enabled,
                sustained for alarm_delay
```

Block graph (`rule.cxf.jsonld`):

![ERV-FC-050 block graph](diagram.svg)

`rise` is the temperature the device actually delivered, `avail` the
temperature it had to work with, and `eff` divides them. `base` carries the
design effectiveness as a constant so `shortfall` can subtract the measured
value from it and `shortHigh` can test the remainder against one positive
threshold — the AHU-FC-055 arrangement, and for the same reason: both tunables
stay independent single-value `set_param` paths, and the threshold never needs
a sign flip.

`avail` fans out a second time into `absDelta` and `deltaOk`, which does two
jobs at once. It is the reference's `min_delta_for_eval` precondition, exposed
as the boundary output `yTempDeltaOk` because the test is computable from this
rule's own inputs. It is also the guard on the division: CDL `Divide` follows
IEEE-754, so an exhaust temperature equal to the entering temperature yields
±∞ or NaN rather than an error, and a near-zero denominator turns a tenth of a
degree of sensor noise into an effectiveness of any magnitude at all.
`zero_delta_divide_guard` is that case made concrete — the quotient is −∞, the
shortfall is +∞, `shortHigh` goes true, and `gate` holds the alarm down anyway.
Arithmetic garbage can make this rule unevaluable; it cannot make it fire.

`armed` adds the enable state, so a unit that is switched off is not accused of
recovering nothing. Both comparisons are strict. The temperature-difference
boundary is exact and pinned from both sides (5.0 °C is not evaluable,
5.1 °C is); the effectiveness boundary is not exactly representable in binary
floating point at all, which is its own small story — see Deviations.
`persist` requires 30 continuous minutes, long enough to ride out a brief
frost-control excursion; a sustained one still alarms, which is a host gating
question rather than a timing one (see Deviations).

## Possible Diagnoses

1. Energy recovery wheel fouled or contaminated — dust and particulate bridging
   the media, the most common cause and the cheapest to correct ($200–$1,000
   for cleaning)
2. Energy recovery wheel motor stopped — a failed drive motor or a broken belt
   leaves the wheel stationary, which recovers almost nothing and produces the
   most extreme readings this rule sees
3. Bypass damper stuck open, routing air around the core entirely
4. Plate heat exchanger fouled — same failure, no moving parts to check
5. Run-around coil pump failure or glycol degradation, on the loop-type
   installations where the two air streams never meet

## Energy Impact

EFFICIENCY_LOSS, MEDIUM confidence, BASELINE_COMPARISON. The reference gives
10–30% of recovery energy lost and the estimator `lost_kw = (baseline_eff −
actual_eff) × airflow × cp × |exhaust − entering|`, whose first factor is the
shortfall this rule already computes. Airflow and `cp` are not among the rule's
inputs, so the conversion from an effectiveness shortfall to kilowatts is the
host's — supply the design ventilation rate and the estimate follows directly.
PNNL EEM-37 (optimized heat recovery wheel) is the related measure, and the
playbook's framing is the useful one: a wheel at half its rated effectiveness
is not saving half as much energy, it is handing the coils half of the
ventilation load it was bought to eliminate. Sensitive to both heating and
cooling climates, most valuable where the outdoor-to-exhaust difference is
largest — which is exactly when the rule is most evaluable.

## Emissions Impact

Scope 1 + 2, PROXY_EMISSIONS, MEDIUM confidence; typically 400–3,000 kg
CO₂e/yr for lost recovery. The split follows the season and the plant: the
unrecovered winter load usually burns scope 1 fuel at a heating coil, the
summer load draws scope 2 electricity at a chiller, and an all-electric
building puts both in scope 2. Avoided-emissions basis: marginal operating
emissions rate (MOER).

## Deviations

- **`min_delta_for_eval` is 5.0 °C, and the reference disagrees with itself
  about that number.** The chapter's tunables table gives 5 °C; the
  `erv-effectiveness` playbook's verification step gives the same gate as
  |OAT − RAT| > 10 °F, which is 5.56 °C. The two differ by 0.56 °C — about
  10% — because one is a rounded metric restatement of the other's Fahrenheit
  rule of thumb, and the reference never reconciles them. This card adopts the
  card's own tunables value (5.0 °C), the library's standing precedent when a
  chapter card and its playbook disagree numerically (RTU-FC-051 does the same
  with its 25% split threshold). The consequence is a narrow band, 5.0–5.56 °C,
  where this rule evaluates and the playbook would tell a technician the
  measurement is not yet trustworthy; hosts that prefer the playbook's stance
  set `deltaOk.t = 5.56`. The playbook also names the difference as
  |OAT − RAT| while the rule uses |exhaust − entering|: the exhaust air
  entering the ERV *is* the return air measured at the device, and it is the
  ratio's denominator, which is the quantity that actually has to be large.
- **The evaluability gate is also the divide guard, and the card claims both
  roles deliberately.** SCHEMA.md requires exposing an in-rule evaluability
  test as a boolean output, which is `yTempDeltaOk`. Wiring the same signal
  into `gate` is the second, independent reason it exists: without it a zero or
  near-zero denominator can put ±∞ or a noise-amplified finite value into
  `shortHigh`. NaN compares false everywhere and can never raise the alarm, but
  +∞ can, and does — `zero_delta_divide_guard` pins exactly that. A host that
  reads `yTempDeltaOk` as advisory and ignores the gate would be relying on
  arithmetic that has no defined answer.
- **The effectiveness boundary is not representable, and the nominal case lands
  on the fault side.** With `baseline_effectiveness = 0.75` and
  `effectiveness_threshold = 0.15` stored as IEEE-754 doubles, no measured
  effectiveness makes the shortfall exactly equal the threshold: for
  effectiveness near 0.6 the subtraction `0.75 − eff` is exact (Sterbenz), so
  equality would require `eff = 0.75 − 0.15` to be a double, and it is not.
  An effectiveness of exactly 60.0% — the nominal alarm point — computes a
  shortfall of 0.15000000000000002, one ulp above the stored threshold, so the
  strict `>` fires where the arithmetic on paper says it should not. Both sides
  of the machine crossing are pinned
  (`shortfall_at_nominal_boundary_alarms` and
  `shortfall_one_ulp_under_threshold`, the latter with a leaving temperature one
  ulp above 12.0 °C), along with the human-scale pair at 59.5% and 60.5%. In
  practice this is invisible — temperature sensors resolve 0.1 °C at best and
  half a point of effectiveness is far inside the noise — but a host that reads
  "exactly 15 points below baseline is safe" from the strict comparison is
  wrong by one ulp, and the direction of the error is toward alarming.
- **`erv_enabled` is in the block graph, not only in the frontmatter.** The
  reference lists "ERV enabled, both supply and exhaust fans running" as an
  operating state, and this library normally keeps operating-state gating
  host-side. The enable half is carried in-graph anyway because it is a point
  in the ERV dictionary that ERV-FC-051 already consumes in its own equation,
  and because the failure mode is nightly: a disabled unit recovers nothing by
  construction, so an ungated rule alarms every unoccupied period on every
  healthy ERV in the building. Precedent: RTU-FC-055 consumes `sf_status` and
  `occ_schedule` in its graph for the same reason. The fans-running half stays
  a host precondition — the dictionary has no ERV fan-status point, and an
  enable command is not evidence that both wheels of air are moving.
- **`baseline_effectiveness` ships the reference's default, which is a
  population value.** 75% is a reasonable sensible effectiveness for a
  well-specified wheel, and it is what the reference publishes, so it carries
  more authority than a placeholder. It is still not this unit's rating.
  Devices in service run from roughly 50% to 80% rated, and the interaction
  with the threshold is unforgiving at the low end: a unit rated 60% operating
  exactly at its rating computes a 15-point shortfall against the shipped
  baseline and alarms (by the one ulp above). Hosts should set `base.k` to the
  unit's certified sensible effectiveness at design airflow, or to the
  commissioning measurement, which is what the playbook's step 1.2 compares
  against.
- **The comparison is written as `baseline − measured > threshold`, not
  `measured < (baseline − threshold)`.** Algebraically identical to the
  reference's form; implemented this way so both tunables stay independent
  single-value parameters (a host retuning either does not have to recompute a
  combined constant) and so the threshold stays positive, which keeps the rule
  clear of the library's prohibition on negative parameters.
- **`method: statistical` describes where the baseline comes from, not what the
  graph does at runtime.** Two subtractions, a division, a comparison — nothing
  statistical happens on a tick. The classification is the reference's and it
  is fair: the baseline is a design or commissioning figure rather than
  something this rule fits, and the detection literature behind the card
  (Nehasil et al. 2021, Mattera et al. 2020) is statistical. Same stance as
  RTU-FC-051.
- **Latent recovery is out of scope.** The reference specifies sensible
  effectiveness, and this rule computes only that. On an enthalpy wheel the
  sensible ratio understates total recovery, so a unit whose desiccant coating
  has failed while its sensible transfer is intact passes this test. Humidity
  points are not in the ERV dictionary; the gap is recorded, not papered over.
- **Frost protection is not excluded in-graph.** A unit in its frost sequence
  is recovering less on purpose. The 30-minute `alarm_delay` rides out short
  excursions (`transient_degradation_clears_before_delay` pins 20 minutes of
  degradation producing no alarm), but a long cold snap with frost control
  active for hours will alarm. `erv_frost_prot` exists in the dictionary for
  ERV-FC-051; hosts with sustained frost operation should gate on it. This card
  does not add it as a fourth input because the reference does not list it for
  this fault.
- **Strict `>` on both comparisons**, as CDL requires — there is no
  `GreaterEqual` in Reals. The temperature-difference boundary is exactly
  representable and pinned from both sides
  (`delta_exactly_at_eval_threshold` at 5.0 °C is not evaluable,
  `delta_just_above_eval_threshold` at 5.1 °C is).
- `persist.delayOnInit = true` (CDL default is `false`), the library's standing
  choice: a wheel already degraded when the controller starts waits out the
  full 30 minutes rather than alarming on the first tick.

## Notes

All three of the reference's published test vectors are reproduced —
`reference_good_effectiveness` (74.1%, no fault),
`reference_degraded_effectiveness` (18.5%,
fault) and `reference_insufficient_delta` (2 °C available, NO_EVAL) — and their
computed effectiveness matches the reference's stated values to the digit,
which is the cheapest confirmation available that the ratio is wired the right
way up.

`summer_reverse_delta_degraded` is the scenario worth understanding. With
32 °C outdoor air and 24 °C exhaust the available difference is −8 °C and a
working wheel *pre-cools* the intake, so both the numerator and the denominator
are negative and the ratio reads exactly as it does in winter. The rule needs
no seasonal branch, and the absolute value in the evaluability branch exists so
that the gate does not care either.

The [erv-effectiveness](../../../playbooks/erv-effectiveness.md) playbook orders
the service: clean the wheel or plate core first, then — on wheel units — check
that the wheel is actually turning, because a failed drive motor or slipped
belt is the failure that produces the most extreme readings and the one a
cleaning visit will not fix. Check the bypass damper before condemning the
core. The playbook's resolution target is effectiveness back within 15% of the
commissioned value, which is the same 15 points this rule alarms at: a device
cleaned to just inside the alarm point has met the target by exactly the margin
that clears the alarm, and is worth re-measuring next season.
