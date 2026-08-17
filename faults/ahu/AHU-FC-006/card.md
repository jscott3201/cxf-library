---
schema: cxf-library/fault-card/v1
id: AHU-FC-006
name: OA fraction deviation
equipment: ahu
status: verified
phase: 1
method: rule
severity: 3
category: EXCESS_CONSUMPTION
confidence: MEDIUM
estimation_method: DIRECT_MEASUREMENT
source:
  - "HVAC FDD Reference v1.0 §5.8.1 (index; card abbreviated)"
  - "G36 §5.16.14 FC#6 (text per Addendum u public review)"
  - "NISTIR 7365 (defaults provenance)"
  - "PNNL-25985 EEM-06 (OA damper faults), PNNL EEM-17 (demand control ventilation)"
g36: "§5.16.14 FC#6"
clusters: []
suppresses: []
suppressed_by: [AHU-FC-062]
related: [AHU-FC-055, AHU-FC-064, AHU-FC-051, AHU-FC-062]
playbooks: [economizer-failure]
operating_states: "OS#1 and OS#4 (minimum outdoor air states) — host-gated"
preconditions: "Supply fan running, and the unit in one of the two minimum-OA operating states G36 defines by actuator signature: OS#1 (HC > 0, CC = 0, OA damper at minimum) or OS#4 (HC = 0, CC > 0, OA damper at minimum). The rule must not be evaluated in OS#2 or OS#3, where the outdoor-air fraction is supposed to exceed the minimum — economizing looks identical to a stuck damper from these three temperatures — nor in OS#5, where no damper position is defined at all. Suspend evaluation for ModeDelay (30 min) after any mode or operating-state change in a zone group the AHU serves, while the dampers are still stroking and the mixing box has not settled. Silence the rule while AHU-FC-062 is active: the fraction is a ratio of temperature differences, so a MAT outside the OAT/RAT envelope moves it directly. `min_oa_fraction` must be retuned to track the active minimum-OA setpoint whenever the ventilation reset moves it (see Deviations). The temperature-difference conjunct is signalled in-rule by yTempDeltaOk; when it is false the verdict is NO_EVAL, not healthy, and the same is true whenever any of the gates above is unmet."
points:
  - mat
  - rat
  - oat
outputs:
  - name: yFault
    description: True while the outdoor air fraction has stayed further than oa_fraction_tolerance from min_oa_fraction, in either direction, for at least alarm_delay, with the outdoor-to-return temperature difference large enough to evaluate
  - name: yTempDeltaOk
    description: Evaluability signal — true when |rat − oat| exceeds delta_min (G36's dTMIN conjunct); false means NO_EVAL and the host must ignore yFault
params:
  min_oa_fraction:
    default: 0.15
    unit: "1"
    description: "The %OAmin the fraction is compared against — G36's active minimum-OA setpoint divided by actual total airflow, bound here as a static design minimum (0-1). Hosts that can read the ventilation reset should retune this through set_param as the active setpoint moves"
    cxf: minConst.k
  oa_fraction_tolerance:
    default: 0.30
    unit: "1"
    description: "How far the fraction may sit from min_oa_fraction in either direction before it counts as a fault. Default 0.30 is G36's eF (airflow error threshold, 30%), a NISTIR 7365 value the addendum notes is intentionally biased toward minimizing false alarms"
    cxf: devBig.t
  delta_min:
    default: 6.0
    unit: "°C"
    description: "Minimum |rat − oat| for the mixing-box energy balance to locate the fraction. Default 6.0 °C is G36's dTMIN, whose stated purpose is to keep the mixing-box tests meaningful — below it the denominator is small enough that sensor error dominates the quotient"
    cxf: deltaOk.t
  alarm_delay:
    default: 1800.0
    unit: s
    description: Continuous fault persistence required before the alarm asserts (G36 AlarmDelay, 30 min)
    cxf: persist.delayTime
energy_impact:
  affected_subsystem: AHU ventilation thermal energy
  savings_range: "2-10% of the subsystem (HVAC FDD Reference §5.8.1 index row, EEM 06 and 17)"
  climate_sensitivity: heating-dominant
  runtime_estimation: "High side only: excess_oa_kw = (oaf − min_oa_fraction) × supply_airflow_m3s × 1.2 kg/m³ × 1.005 kJ/kg·K × |oat − rat|, mirroring AHU-FC-055 — the thermal power spent conditioning outdoor air the ventilation calculation does not require. The low side has no energy term: under-ventilation costs less energy, not more, and the finding is an indoor-air-quality one. A host accumulating energy from this rule must therefore check the sign of (oaf − min_oa_fraction) before adding anything, and must not treat a low-side alarm as savings recovered by fixing it"
emissions:
  scope: "1+2"
  method: PROXY_EMISSIONS
verified:
  engine_rev: e2ff2f8
  content_id: "cxf:fnv1a128:89896c77a2581ab67082184d505bc7db"
  date: 2026-08-17
---

## Description

The unit should be sitting at its minimum outdoor-air setpoint, and the
mixing-box energy balance says it is not. Too much outdoor air costs money:
every extra cubic metre is heated or cooled to supply temperature for no
ventilation benefit. Too little is the opposite problem with no energy signature
at all — the building is under-ventilated, which is an indoor-air-quality
finding rather than a waste one. G36 tests both directions with one absolute
value, so this rule alarms on either.

This is G36 §5.16.14 FC#6, evaluated in the two operating states where the
outdoor-air damper is supposed to be at minimum — OS#1 (heating) and OS#4
(mechanical cooling on minimum outdoor air). In OS#2 and OS#3 the damper is
opening deliberately, and the same three temperatures would read as a fault, so
the host gate matters more here than the equation does.

The fraction is inferred from three temperatures rather than measured, which is
what makes the diagnostic cheap and what makes it conditional. When outdoor and
return air are close, the mixture cannot locate the fraction between them: the
quotient's denominator collapses and ordinary sensor error becomes an arbitrary
answer. G36 handles that by writing the minimum temperature difference into the
fault equation as a conjunct, which is why this rule carries both a gate and an
explicit evaluability output.

## Detection Logic

```
oaf          = (mat − rat) / (oat − rat)                      (G36 %OA)
yTempDeltaOk = |rat − oat| > delta_min                        (false ⇒ host reports NO_EVAL)
yFault       = (|oaf − min_oa_fraction| > oa_fraction_tolerance) AND yTempDeltaOk,
               sustained for alarm_delay
```

Block graph (`rule.cxf.jsonld`):

![AHU-FC-006 block graph](diagram.svg)

`matRat` and `oatRat` form the two differences and `oaf` divides them, which is
G36's `%OA = (MAT − RAT)/(OAT − RAT)` written out. `minConst` supplies `%OAmin`
as a constant so `dev` can reduce the comparison to a distance from zero;
`absDev` takes the absolute value G36's equation asks for and `devBig` tests it
against a single positive threshold. Keeping the setpoint in a
`Reals.Sources.Constant` rather than folding it into the threshold leaves
`min_oa_fraction` and `oa_fraction_tolerance` as independent single-value
`set_param` paths — which matters more here than on AHU-FC-055, because the
setpoint is the parameter a host is expected to move at runtime.

`oatRat` fans out a second time into `absDelta` and `deltaOk`. That branch is
G36's `|RAT_AVG − OAT_AVG| ≥ dTMIN` conjunct, and it goes to two places: into
`gate` as the second half of the equation, and out of the block as
`yTempDeltaOk`. Both destinations are deliberate. In the graph it is a term of
the fault condition, exactly as G36 writes it; at the boundary it is the
evaluability signal SCHEMA.md requires whenever a rule can compute its own
NO_EVAL test. A host that ignores the output still gets the right verdict from
the gate; a host that reads it learns the difference between "not faulted" and
"cannot tell", which the boolean alone does not carry.

That belt-and-braces arrangement is also what makes the division safe. CDL
`Divide` follows IEEE-754, so `oat = rat` yields ±∞ or NaN rather than an
error, and a near-zero denominator amplifies ordinary sensor noise into a
fraction of any magnitude. NaN compares false everywhere and can never raise
`devBig` — but ±∞ and a noise-inflated finite fraction both can, and `gate` is
what stops them, because a denominator small enough to misbehave is by
construction a denominator below `delta_min`. Garbage arithmetic cannot assert
a fault; it can only make the rule report itself unevaluable. The
`zero_denominator_infinite_fraction_silent` and
`small_delta_wild_fraction_silent` vectors pin both halves of that claim.

The fraction is signed consistently on both sides of the year — in winter both
differences are negative, in summer both positive, and the quotient reads the
same — so no seasonal branch is needed. `persist` requires 30 continuous
minutes, which rides out a damper stroke and the mixing transient after a mode
change; recovery is immediate on the tick the deviation falls back inside the
tolerance.

## Possible Diagnoses

Transcribed from G36 §5.16.14 FC#6:

1. RAT sensor error
2. MAT sensor error
3. OAT sensor error
4. Leaking or stuck economizer damper or actuator

Three of the four are sensor errors, and the reason is arithmetic. The fraction
is a ratio of two differences, and the denominator is small: a 1 °C bias in MAT
moves the apparent outdoor air by 5 percentage points across a 20 °C
outdoor-to-return spread, and by 17 points on a spread sitting at dTMIN. A
sensor within its rated accuracy can therefore account for most of a deviation
this rule reports. The low branch in particular is almost entirely a sensor
finding — see Notes.

## Energy Impact

EXCESS_CONSUMPTION, MEDIUM confidence, DIRECT_MEASUREMENT, savings 2–10% of the
subsystem: the §5.8.1 index row, which is the only energy statement the
reference makes about this fault. The high branch is directly computable from
live data — `excess_oa_kw = (oaf − min_oa_fraction) × airflow × cp ×
|oat − rat|`, with the excess fraction already on the wire as `dev.y` — and
correcting minimum ventilation pays back in the upper half of that range in
heating-dominant climates, where the outdoor-to-return difference and therefore
the cost of every extra cubic metre is largest. The index maps the fault to
PNNL-25985 EEM-06 (OA damper faults) and EEM-17 (demand control ventilation);
this rule screens both, since a unit that cannot hold its design fraction with
the dampers at minimum will not benefit from CO₂ control until the mechanical
problem is fixed.

The index's MEDIUM — against AHU-FC-055's HIGH on the same quotient — reads
right for two reasons that both come from this rule being two-sided. A low-side
alarm has no energy term at all: under-ventilating saves energy while failing
the occupants, so fixing it costs energy rather than recovering it, and a host
accumulating savings from `yFault` alone, without checking the sign of `dev.y`,
will bank a number that runs the wrong way. And three of G36's four diagnoses
are sensor errors, which waste nothing; the formula run on a drifted RAT sensor
returns a confident figure for excess air that does not exist.

## Emissions Impact

Scope 1 + 2, PROXY_EMISSIONS, MEDIUM confidence. On the high branch the split
follows the season, as it does for AHU-FC-055: excess outdoor air in winter
usually burns Scope 1 fuel at the heating coil, in summer it draws Scope 2
electricity at the chiller, and on an all-electric unit the whole exchange
collapses to Scope 2. On the low branch there is nothing to attribute — the
avoided emissions of under-ventilation are real and are not a benefit.

The emissions method is PROXY where the index's `estimation_method` is DIRECT,
and the mismatch is deliberate. The fraction is measured, but the mass flow it
has to be multiplied by to become energy is not: this rule is worth deploying
precisely on the units that have three temperature sensors and no airflow
station, so the airflow term is a design figure. The index is describing how
the fraction is obtained; this block is describing how the kilograms are.
Avoided-emissions basis: marginal operating emissions rate (MOER) for the
electric half, static combustion factor for the fuel half.

## Deviations

- **The reference card is abbreviated; G36 is the normative text here.** The
  HVAC FDD Reference carries AHU-FC-006 only as a §5.8.1 index row — a name and
  an energy profile. No chapter 9 card, so no equation, no internal variables,
  no test vectors, no severity, no diagnosis list, no preconditions. The
  detection logic, the internal-variable defaults, and the possible-diagnosis
  list are transcribed from ASHRAE Guideline 36 §5.16.14 FC#6 as it appears in
  Addendum u to Guideline 36-2018 (First Public Review, 2021). Where the two
  sources could conflict, G36 wins, because it is the only one that states the
  rule.
- **`%OAmin` is a static parameter, not the active setpoint.** This is the
  substantive departure. G36 defines `%OAmin` as the *active* minimum-OA
  setpoint divided by *actual* total airflow — a moving target that tracks the
  ventilation reset, zone population, and load, and that a VAV system
  recomputes continuously. This card binds it as a `Reals.Sources.Constant`,
  the same simplification AHU-FC-055 makes for `desired_oaf`, because the
  active setpoint and the total airflow are not among this library's canonical
  AHU points and adding them would change the rule from a three-temperature
  diagnostic into one that needs a flow station or a zone-flow rollup. Hosts
  have two honest options: retune `min_oa_fraction` through `set_param`
  whenever the active setpoint moves, which reproduces G36's intent exactly; or
  accept the design-minimum approximation and the error band it creates. That
  band is one-sided in effect — when the active setpoint is above the design
  minimum, a unit correctly delivering the higher fraction reads as a high-side
  deviation (false positive) while a genuinely under-ventilating one is
  measured against too low a bar (false negative). With G36's own defaults the
  approximation is worth up to 0.30 of fraction before either error surfaces,
  which is wide; it is not wide enough on a unit whose reset swings the
  setpoint by more than that.
- **The low branch is nearly unreachable at G36's defaults, and that is G36's
  arithmetic, not this card's.** With `%OAmin` = 0.15 and eF = 0.30, the
  low-side alarm point is a fraction below −0.15. A physical mixing box cannot
  produce a negative outdoor-air fraction, so no damper position — not even
  fully shut, which is zero ventilation — can trip it; the
  `damper_shut_no_ventilation_stays_silent` vector pins exactly that miss. The
  low branch fires only when the *inferred* fraction goes negative, which means
  MAT has landed outside the OAT/RAT interval and one of the three sensors is
  lying, or when a host has retuned `min_oa_fraction` above the tolerance for a
  high-outdoor-air unit. Both are legitimate findings; neither is the
  "ventilation deficit" reading the equation's shape suggests. The two-sided
  test is still worth having — see Notes for what it catches that AHU-FC-055
  cannot — but a site that wants a real under-ventilation alarm at a 15%
  minimum has to lower `oa_fraction_tolerance` well below eF, and should expect
  the false-alarm rate NISTIR 7365 chose eF to avoid.
- **G36's `≥` on the dTMIN conjunct becomes a strict `>`; the deviation
  comparison is already strict and matches exactly.** FC#6 is written with two
  different inequalities — `|RAT_AVG − OAT_AVG| ≥ dTMIN` and
  `|%OA − %OAmin| > eF` — and CDL `Reals` offers only strict comparisons. The
  deviation term therefore transcribes without deviation. The dTMIN term does
  not: a spread of exactly 6.000 °C is evaluable to G36 and unevaluable here.
  The disagreement has measure zero on a real temperature signal and errs
  toward silence on the one term whose whole purpose is to suppress
  meaningless verdicts, which is the right direction. Both boundaries are
  pinned from both sides in `vectors.json`
  (`delta_exactly_at_dtmin_holds_fault_down` /
  `delta_just_over_dtmin_alarms`, and the low-side tolerance pair).
- **The deviation boundary is not representable in binary, and the vectors say
  where the rounding falls.** A nominal high-side edge — %OA of exactly 0.45
  against a 0.15 setpoint and a 0.30 tolerance — cannot be tested as written:
  computed as (13 − 22)/(2 − 22) the fraction rounds to the double just above
  0.45, and subtracting the double nearest 0.15 lands one ulp above 0.30, so
  the rule alarms where decimal arithmetic says it should not. No double gives
  a deviation of exactly 0.30 on the high side. The low side is exact, because
  the double nearest 0.15 doubles exactly into the double nearest 0.30, so the
  strict comparison itself is pinned there
  (`low_deviation_exactly_at_tolerance` reads healthy at a deviation of exactly
  −0.30). The high edge is pinned a rounding-safe hundredth either side instead
  (0.29 clear, 0.31 faulted), with `high_nominal_boundary_rounds_into_alarm`
  recording the artifact rather than hiding it. A host binding coarsely
  quantized temperatures should keep this in mind before reading anything into
  a fraction sitting on the threshold.
- **Instantaneous samples instead of 5-minute rolling averages.** G36 §5.16.14
  defines five-minute rolling averages with one-minute sampling for every
  measured point, and FC#6's dTMIN conjunct is written on them (`RAT_AVG`,
  `OAT_AVG`). The `%OA` definition is not: it is written on unsubscripted MAT,
  RAT, and OAT in the same clause. This library consumes instantaneous points
  throughout and lets the 30-minute AlarmDelay stand in, which resolves the
  ambiguity by ignoring it. The two treatments are not equivalent, and the
  honesty note from AHU-FC-002 applies unchanged: averaging tolerates a signal
  whose mean sits outside the bound while it keeps crossing back, persistence
  does not — an oscillating deviation resets the timer on every compliant tick
  and can hide indefinitely. The `oscillating_deviation_never_alarms` vector
  demonstrates the miss on a hunting damper. A stuck damper and a drifted sensor
  are both steady offsets and read the same either way. The gap is wider here
  than on a single-signal rule, because the fraction is a quotient: averaging
  the three inputs and averaging the quotient give different numbers, and which
  one G36 means is what its notation leaves open.
- **Operating states and ModeDelay are host-side preconditions.** G36 scopes
  FC#6 to OS#1 and OS#4, suspends evaluation for ModeDelay (30 min) after a
  mode change in a served zone group, and suspends all fault evaluation while
  the AHU is not operating. None of it is in the graph, per the library's
  stance (precedent AHU-FC-063). The stakes are higher on this rule than on
  most: OS#2 and OS#3 are states in which a high outdoor-air fraction is the
  correct answer, so a host that evaluates FC#6 while the unit is economizing
  will get a sustained fault, and it will be the host's bug. AHU-FC-055 records
  the same hazard from the other direction. A verdict produced outside OS#1 or
  OS#4, or inside a transition window, is NO_EVAL, never healthy.
- **Severity 3 is the library's, not the reference's.** No chapter card exists
  to state one and the §5.8.1 index carries no severity column. The value
  matches this chapter's README scaffold row for "OA fraction deviation" and
  the other G36 comparison rules here. G36 §5.16.14 does say every reported
  fault condition "shall be a Level 3 alarm", but that is G36's alarm-priority
  scheme rather than this library's 1–4 severity scale, so it corroborates the
  number without supplying it.
- **The energy profile is the index row's; the emissions block and the runtime
  formula are the library's.** `category`, `confidence`, `estimation_method`,
  `savings_range`, and the EEM mapping are copied from §5.8.1
  (EXCESS_CONSUMP / MED / DIRECT / EEM 06 and 17 / 2–10% subsystem). The index
  publishes no emissions column, so scope `1+2` and `PROXY_EMISSIONS` are
  assigned here, following AHU-FC-055's reading of the same physics. The
  runtime formula is mirrored from AHU-FC-055 with the sign check added, since
  only one of this rule's two branches has an energy term at all.
- **No published test vectors.** The reference publishes none for this fault
  and G36 publishes none for any of them, so `vectors.json` is authored from
  the equation: both branches, both tolerance edges, both sides of the dTMIN
  boundary, the two arithmetic-degeneracy cases the gate exists to catch, a
  transient shorter than AlarmDelay, a recovery, and the oscillation the
  persistence substitution is known to miss.
- `persist.delayOnInit = true` (Modelica/CDL default is `false`), the library's
  standing choice: a deviation already present at load waits out the full 30
  minutes instead of alarming on the first tick after a controller restart.

## Notes

This rule and AHU-FC-055 measure the same quotient and are not redundant.
AHU-FC-055 is a one-sided energy test with a 0.10 tolerance, evaluated in any
non-economizing occupied hour; it is the sensitive instrument for the excess
case and will see a damper drifting open long before this rule's 0.30 band
notices. AHU-FC-006 is G36's symmetric test, evaluated only in the two
minimum-OA operating states, and its contribution is the branch AHU-FC-055 has
no block for: a fraction below the setpoint. What that branch actually catches
at G36's defaults is a fraction gone *negative* — MAT outside the interval its
two sources bracket, which is a mixing-box or sensor contradiction rather than
a ventilation number. AHU-FC-062 tests that contradiction directly and with a
shorter delay, which is why it suppresses this rule; when both are active the
sensor is the story and the fraction is noise. Expect the pair to fire together
and read AHU-FC-062 first. If a site wants a genuine under-ventilation alarm,
CO₂ or a measured outdoor-air flow will give it one; three temperatures and a
30-percentage-point tolerance will not.

The other two related rules read the same damper from different angles.
AHU-FC-064 is the excess measurement narrowed to heating, where each extra
cubic metre costs the most. AHU-FC-051 works the opposite failure — an
economizer that should have opened and did not — in OS#4, the one state the two
rules share.

Check the minimum position setpoint before sending anyone to the roof. The most
common cause of a high-side deviation is not a broken damper but a minimum
position dialled up during a ventilation complaint or left over from a
commissioning shortcut, and it is a $0 desk fix; the
[economizer-failure](../../../playbooks/economizer-failure.md) playbook's damper
and linkage steps come after that. The rule is deliberately blind to why the
fraction is wrong — a damper stuck at 40% and a building held under negative
pressure by an oversized exhaust fan produce the same number, and the second is
invisible from the AHU's own points. If commanding the damper closed does not
move the fraction, measure building pressure before replacing the actuator.
