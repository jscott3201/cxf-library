---
schema: cxf-library/fault-card/v1
id: AHU-FC-010
name: OAT ≠ MAT in mechanical + economizer cooling
equipment: ahu
status: verified
phase: 1
method: rule
severity: 3
category: COMFORT_ENERGY
confidence: LOW
estimation_method: QUALITATIVE_ONLY
source:
  - "HVAC FDD Reference v1.0 §5.8.1 (index; card abbreviated)"
  - "G36 §5.16.14 FC#10 (text per Addendum u public review)"
  - "NISTIR 7365 (defaults provenance)"
  - "PNNL-25985 (EEM-01, sensor recalibration)"
g36: "§5.16.14 FC#10"
clusters: []
suppresses: []
suppressed_by: [AHU-FC-062]
related: [AHU-FC-002, AHU-FC-003, AHU-FC-008, AHU-FC-055, AHU-FC-062]
playbooks: [sensor-drift]
operating_states: "OS#3 (mechanical + economizer cooling, damper at 100%) — host-gated"
preconditions: "The unit must have a MAT sensor; G36 omits FC#10 where there is none. Evaluate only in OS#3, which G36 Table 5.16.14.2 defines by actuator signature: heating coil = 0, cooling coil > 0, OA damper at 100%. At any smaller damper position return air is supposed to be in the mixture and the equation is simply false. Supply fan running, since neither temperature describes a stream that is not moving. Per §5.16.14.11 the host suspends evaluation while the AHU is off and for ModeDelay (30 min) after a mode change in any zone group the AHU serves — a damper still stroking toward 100% leaves return air in the plenum that no fault caused. Silence this rule while AHU-FC-062 is active: MAT is an input here and FC-062 is its integrity gate. When any gate is unmet the verdict is NO_EVAL, not healthy."
points:
  - mat
  - oat
outputs:
  - name: yFault
    description: True while |mat − oat| has stayed above combined_error for at least alarm_delay
params:
  combined_error:
    default: 3.1623
    unit: "°C"
    description: "Largest disagreement between mixed and outdoor air that sensor accuracy alone can explain, composed as the root-sum-square of the two error bands: sqrt(eMAT² + eOAT²) = sqrt(3² + 1²) = sqrt(10) = 3.1623 °C with the G36 Table 5.16.14.5 defaults. Errors add in quadrature rather than linearly because two independent sensors are unlikely to be wrong in the same direction at once. The eOAT default is location-dependent — 1 °C for a sensor at the unit, 3 °C for a shared or global one — so a site reading campus or weather-service outdoor air recomputes sqrt(9 + 9) = 4.2426 °C."
    cxf: devBig.t
  alarm_delay:
    default: 1800.0
    unit: s
    description: Continuous fault persistence required before the alarm asserts (G36 AlarmDelay, 30 min)
    cxf: persist.delayTime
energy_impact:
  affected_subsystem: AHU mixing box on 100% outdoor air, and the outdoor/mixed air sensor pair
  savings_range: "sensor-dependent (HVAC FDD Reference §5.8.1 index row, mapped there to PNNL-25985 EEM-01)"
  climate_sensitivity: cooling-dominant
  runtime_estimation: "none — the rule sees two temperatures and no airflow, so the recirculation it may be reporting cannot be turned into a rate; the diagnosis has to land first, because a drifted sensor costs nothing directly and a leaking damper loads the cooling plant continuously"
emissions:
  scope: "2"
  method: QUALITATIVE_EMISSIONS
verified:
  engine_rev: e2ff2f8
  content_id: "cxf:fnv1a128:5eecdfa05c333292682916fecbc5d7f1"
  date: 2026-08-17
---

## Description

In OS#3 the unit has opened the outdoor air damper to 100% and closed the
return damper, and is running mechanical cooling on top. Mixed air is then not
a mixture at all — it is outdoor air, one plenum downstream. The two sensors
are measuring the same stream at two points, so they should read the same
number to within their combined accuracy.

When they do not, either a sensor is lying or the return damper is not where
the command says it is. The second case is the expensive one. Return air in a
building that needs cooling is warmer than the outdoor air the economizer just
chose, so every degree of leak-through arrives at the cooling coil as load the
unit did not need to buy. The damper feedback will not show it: a blade that
seats badly, a linkage that slips, or an actuator stalled a few degrees off
closed all report the commanded position.

This is the outdoor-air-side counterpart to AHU-FC-008. That rule audits the
supply and mixed-air sensors against each other in free cooling; this one
audits mixed against outdoor air on full outdoor air. Between them the two G36
equality tests cover most of the unit's temperature instrumentation using
nothing but operating states the sequence already visits.

## Detection Logic

```
G36 §5.16.14 FC#10, applies to OS#3 (omitted if the unit has no MAT sensor):

    | MAT_AVG − OAT_AVG | > sqrt(eMAT² + eOAT²)

with the Table 5.16.14.5 defaults and a local OAT sensor:

    | mat − oat | > sqrt(3² + 1²) = 3.1623 °C

yFault = (|mat − oat| > combined_error), sustained for alarm_delay
```

Block graph (`rule.cxf.jsonld`):

![AHU-FC-010 block graph](diagram.svg)

Four blocks: `dev` takes `mat − oat`, `absDev` folds the two signs together,
`devBig` compares the magnitude against the combined error band, and `persist`
requires 30 minutes of continuous violation before reporting.

There is no fan-heat term, and its absence is physics rather than omission.
Both sensors sit upstream of the supply fan, so whatever the fan adds is added
after the comparison and cancels out of it. AHU-FC-008 straddles the fan and
must correct for it; this rule does not.

The sign of `dev` carries the diagnosis even though the rule discards it.
Positive — mixed air warmer than outdoor — is the leaking return damper in
cooling weather. Negative is a sensor story: no amount of recirculated building
air can pull a mixture below the outdoor stream when the building is warmer
than outdoors, so mixed air reading colder than outdoor air means one of the
two readings is wrong. The rule reports neither, because G36's equation does
not; a host that wants the direction keeps the two temperatures alongside the
verdict.

## Possible Diagnoses

Per G36 §5.16.14 Table 5.16.14.8, FC#10:

1. MAT sensor error. Either out of calibration or reading a stratified slice of
   the plenum rather than the stream. AHU-FC-062 catches the gross version.
2. OAT sensor error. Cheapest to rule out, and the usual culprit is placement:
   a sensor on a sun-struck wall or above a condenser reads high all afternoon.
   Compare against a nearby weather station before anyone opens the mixing box.
3. Leaking or stuck economizer damper or actuator. The return damper is not
   sealing, or the outdoor damper never reached the 100% it reports. Both put
   return air into a plenum that is supposed to be on outdoor air alone.

## Energy Impact

COMFORT_ENERGY, LOW confidence, QUALITATIVE_ONLY — the grades in the
reference's §5.8.1 index row, which maps this fault to PNNL EEM-01 (sensor
recalibration) and publishes its savings as sensor-dependent. No quantity is
computed from the rule's inputs: `mat` and `oat` give a temperature difference
and no airflow, so there is no power term, and the difference is ambiguous
between a sensor that is lying and a damper that is leaking. Cooling-dominant
by construction, since OS#3 exists only when the unit is making cold air. On
the damper diagnosis the waste is direct and continuous — recirculated return
air arrives at the coil warmer than the outdoor air the economizer selected,
and the chiller pays for the difference for as long as the leak lasts. On the
sensor diagnoses the cost is indirect: the same bad reading feeds the
outdoor-air-fraction rules AHU-FC-055 and AHU-FC-064 and the economizer
changeover logic, and distorts all of them.

## Emissions Impact

QUALITATIVE_EMISSIONS, LOW confidence; the emissions block is library-assigned,
as the §5.8.1 index carries no emissions column. Scope 2: every path out of
this fault lands on the cooling plant, which is purchased electricity —
chiller or DX work spent on recirculated air, and fan energy moving it. No
on-site combustion is involved, since OS#3 has the heating coil commanded shut
and a heating valve leaking in this state reports as FC#15 (temperature rise
across an inactive heating coil) rather than here. That is why this card is
narrower than AHU-FC-008's `1|2`, which cannot tell which coil is leaking.
Avoided-emissions basis: N/A — no quantity is estimated.

## Deviations

- **The reference card is an index row, so this card is built from G36.** The
  HVAC FDD Reference abbreviates AHU-FC-010: §5.8.1 gives the code, the name,
  and the energy grades, with no equation, no test vectors, and no severity.
  The normative content here — the equation, the OS#3 applicability, the three
  diagnoses, the internal-variable defaults — is transcribed from ASHRAE
  Guideline 36 §5.16.14 as it appears in Addendum u to Guideline 36-2018
  (first public review, 2021), the text that became §5.16.14.
- **Severity 3 is library-assigned.** The §5.8.1 index has no severity column
  and G36 grades every reported fault condition as a Level 3 alarm
  (§5.16.14.16), which is a reporting priority rather than a ranking. Severity
  3 matches every other G36 001-range card in this library and the chapter
  README's scaffold row.
- **Energy profile follows the §5.8.1 index row** (COMFORT_ENERGY / LOW /
  QUAL, EEM 01, savings "sensor-dependent"); the emissions block is
  library-assigned, the index having no emissions column.
- **Root-sum-square threshold shipped as one number.** G36 writes the bound as
  `sqrt(eMAT² + eOAT²)`, an expression over two internal variables. The graph
  carries the evaluated result, 3.1623 °C, in `devBig.t`, so a host retunes one
  parameter instead of two and no square root is computed at runtime. The
  composition is written out in the parameter description because the
  arithmetic is not linear.
- **The default assumes a local OAT sensor.** G36 gives eOAT as 1 °C for a
  sensor at the unit and 3 °C for a global one. The library ships the local
  value, so `combined_error` = sqrt(9 + 1) = 3.1623 °C. A site feeding this
  rule from a campus sensor or a weather service must set it to sqrt(9 + 9) =
  4.2426 °C; leaving it at the local value makes the rule fire on sensor
  disagreement G36 considers within tolerance. Note that the two G36 equality
  tests do not retune together — this one moves from 3.1623 to 4.2426 °C on a
  global sensor, while AHU-FC-008's threshold does not move at all, since it
  contains no OAT term.
- **No boundary deviation for this fault.** G36's FC#10 comparison is already
  strict (`>`), unlike the `≥`/`≤` forms elsewhere in Table 5.16.14.8 (FC#5,
  FC#12, FC#14, FC#15), so CDL's `GreaterThreshold` (`u > t`) reproduces the
  source exactly and no measure-zero rewrite is involved. A deviation of
  exactly 3.1623 °C reads healthy in both. Same finding as the AHU-FC-009 and
  AHU-FC-011 cards. The vectors pin the edge from both sides and on both signs.
- **Instantaneous samples instead of averaged signals.** G36 compares 5-minute
  rolling averages sampled at 1-minute intervals (`MAT_AVG`, `OAT_AVG`). This
  rule compares the raw samples and leans on the 30-minute `persist` delay to
  reject noise. The two are not equivalent. Averaging tolerates a signal whose
  mean stays outside the bound while it keeps crossing back; persistence does
  not — an oscillating difference resets the timer on every compliant tick and
  can hide indefinitely. The faults this rule is actually for, a drifted sensor
  and a leaking damper, are steady offsets and read the same way under either
  treatment. (Honesty note carried from AHU-FC-002.)
- **No test vectors are published for this fault**, by the reference or by G36.
  Every scenario in `vectors.json` is authored from the equation: a healthy
  tracking case, a return-air leak, a sensor-error case in the opposite
  direction, both sides of the strict boundary on both signs, a sub-delay
  transient, and a recovery-clears case.
- **Suppression is declared, not encoded.** AHU-FC-062 gates MAT integrity and
  silences this rule while it is active. The block graph cannot express that —
  the engine is status-blind and each rule is an independent composite — so the
  relationship lives in `suppressed_by` and the host enforces it.
- **Operating-state gating and NO_EVAL are frontmatter, not graph.** G36 scopes
  FC#10 to OS#3 (§5.16.14.9c), suspends evaluation for ModeDelay after a mode
  change, and suspends it entirely when the AHU is not operating (§5.16.14.11).
  None of that is in the block graph, per the library's stance that the graph
  computes fault-given-valid-data only. A host that evaluates this rule at
  minimum outdoor air will see it assert on every cold morning, correctly by
  the equation and meaninglessly in fact, because mixing return air is what the
  damper is for.
- `persist.delayOnInit = true` (Modelica/CDL default is `false`): a deviation
  already present at load waits out the full 30 minutes rather than alarming on
  the first tick after a controller restart. Library-wide choice, per
  AHU-FC-050.

## Notes

This rule and AHU-FC-008 are the G36 pair that test whether two temperatures
that ought to be equal actually are. Both are close cousins of AHU-FC-062, and
the difference is worth keeping straight. FC-062 tests *containment* — MAT
inside the OAT–RAT envelope — which is a physical law that holds in every
operating state, so it runs everywhere with a single combined tolerance
covering all three sensors. This rule and FC-008 test *equality*, which holds
in one operating state each, and size their bands as the root-sum-square of
two specific sensors' error. FC-062 is the coarse gate that says the mixed-air
reading is usable at all; these two are the fine checks that only make sense
once it is. A unit whose MAT sits inside the envelope and still disagrees with
outdoor air by 4 °C on full outdoor air passes the gate and fails here, which
is the whole point of running both.

There is a second reason to care about the outcome. The outdoor air fraction
AHU-FC-055 and AHU-FC-064 compute is `(mat − rat) / (oat − rat)`, and a MAT or
OAT error large enough to trip this fault moves that ratio far more than it
moves either temperature, because it lands in the numerator and the
denominator at once. Step 1.3 of the
[sensor-drift](../../../playbooks/sensor-drift.md) playbook is the relevant
habit: when several rules fire on one AHU, suspect the shared sensor before
believing any of them.

Run that playbook before anyone opens the mixing box. Step 1.1 — a
NIST-traceable reference against the suspect sensor — settles the two sensor
diagnoses, and a temperature sensor runs $30–$80 against a damper actuator
service call. An outdoor sensor also deserves a look at where it is mounted:
sun on the housing or a condenser discharge nearby produces this fault's exact
signature with a perfectly calibrated element inside.
