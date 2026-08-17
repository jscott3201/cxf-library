---
schema: cxf-library/fault-card/v1
id: AHU-FC-008
name: SAT ≠ MAT in economizer mode
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
  - "G36 §5.16.14 FC#8 (text per Addendum u public review)"
  - "NISTIR 7365 (defaults provenance)"
  - "PNNL-25985 (EEM-01, sensor recalibration)"
g36: "§5.16.14 FC#8"
clusters: []
suppresses: []
suppressed_by: [AHU-FC-062]
related: [AHU-FC-002, AHU-FC-003, AHU-FC-010, AHU-FC-062]
playbooks: [sensor-drift]
operating_states: "OS#2 (free cooling, modulating OA) — host-gated"
preconditions: "The unit must have a MAT sensor; G36 omits FC#8 where there is none. Evaluate only in OS#2, which G36 Table 5.16.14.2 defines by actuator signature: heating coil = 0, cooling coil = 0, minimum OA position < OA damper < 100%. Outside that state a coil is legitimately working and SAT is supposed to differ from MAT, so the equation means nothing. Supply fan running, since neither temperature describes a stream that is not moving. Per §5.16.14.11 the host suspends evaluation while the AHU is off and for ModeDelay (30 min) after a mode change in any zone group the AHU serves, while the coils and damper are still stroking. Silence this rule while AHU-FC-062 is active: MAT is an input here and FC-062 is its integrity gate. When any gate is unmet the verdict is NO_EVAL, not healthy."
points:
  - sat
  - mat
outputs:
  - name: yFault
    description: True while |sat − fan_rise − mat| has stayed above combined_error for at least alarm_delay
params:
  fan_rise:
    default: 1.0
    unit: "°C"
    description: "Temperature rise across the supply fan (G36 dTSF). Subtracted from the raw SAT − MAT difference so the comparison is about coil and sensor behavior rather than shaft work. A site that measures its own fan rise — a high-static or direct-drive plenum fan can be well off 1 °C — sets this to the measured value; the threshold is unaffected, since fan rise centers the band and sensor error sizes it."
    cxf: fanConst.k
  combined_error:
    default: 3.1623
    unit: "°C"
    description: "Half-width of the band the fan-heat-corrected difference may occupy, composed as the root-sum-square of the two sensor error bands: sqrt(eSAT² + eMAT²) = sqrt(1² + 3²) = sqrt(10) = 3.1623 °C with the G36 Table 5.16.14.5 defaults. Errors add in quadrature rather than linearly because two independent sensors are unlikely to be wrong in the same direction at once. A site with a different MAT accuracy recomputes the root-sum-square: eMAT = 4 °C gives sqrt(1 + 16) = sqrt(17) = 4.1231 °C."
    cxf: devBig.t
  alarm_delay:
    default: 1800.0
    unit: s
    description: Continuous fault persistence required before the alarm asserts (G36 AlarmDelay, 30 min)
    cxf: persist.delayTime
energy_impact:
  affected_subsystem: AHU coil valves and the supply/mixed air sensor pair
  savings_range: "sensor-dependent (HVAC FDD Reference §5.8.1 index row, mapped there to PNNL-25985 EEM-01)"
  climate_sensitivity: neutral
  runtime_estimation: "none — the rule sees two temperatures and no airflow, so the leak-through it may be reporting cannot be turned into a rate; the diagnosis has to land first, because a drifted sensor costs nothing directly and a leaking valve costs plant energy continuously"
emissions:
  scope: "1|2"
  method: QUALITATIVE_EMISSIONS
verified:
  engine_rev: e2ff2f8
  content_id: "cxf:fnv1a128:9a1a1d3f2efeeaa385ba4336b64530a2"
  date: 2026-08-17
---

## Description

In OS#2 the air handler is running as a modulating economizer: both coils are
commanded shut, so the only thing between the mixed-air sensor and the
supply-air sensor that is doing any work is the supply fan. Air should
therefore leave at the temperature it arrived plus the degree or so the fan
puts in. When SAT and MAT
disagree by more than the two sensors' combined error after that fan rise is
taken out, something in between is adding or removing heat, or one of the
sensors is not reporting the stream it is mounted in.

This is the state where the two sensors can be audited against each other at
no cost. Everywhere else in the unit's operating envelope a coil is doing work
and SAT is supposed to differ from MAT, which leaves the disagreement
unattributable. In free cooling the expected difference is a known constant,
so any residual is evidence — and it is evidence about a valve that reads
closed, which no command-following check can produce.

The fault is deliberately non-committal about direction. Air that leaves too
warm points at hot water leaking through a seated heating valve; air that
leaves too cold points at chilled water doing the same. Either way the plant is
serving a coil nobody commanded, and the operator's first move is the same:
find out whether the sensors agree with a reference before believing either
story.

## Detection Logic

```
G36 §5.16.14 FC#8, applies to OS#2 (omitted if the unit has no MAT sensor):

    | SAT_AVG − dTSF − MAT_AVG | > sqrt(eSAT² + eMAT²)

with the Table 5.16.14.5 defaults:

    | sat − 1.0 − mat | > sqrt(1² + 3²) = 3.1623 °C

yFault = (|sat − fan_rise − mat| > combined_error), sustained for alarm_delay
```

Block graph (`rule.cxf.jsonld`):

![AHU-FC-008 block graph](diagram.svg)

`rawDev` takes the raw difference `sat − mat`, `fanConst` emits the fan rise as
a signal, and `dev` subtracts it, leaving the deviation G36 tests. `absDev`
folds the two signs together, `devBig` compares the magnitude against the
combined error band, and `persist` requires the condition to hold for 30
minutes before it is reported.

The fan-heat term is routed through a constant source and a `Subtract` rather
than an `AddParameter` with a negative parameter. Both compute `sat − mat −
1.0`, but only one of them survives a host retuning `fan_rise` through
`set_param`: with an `AddParameter` the stored value would have to be `−1.0`,
and a site that measured a 1.4 °C rise and set `1.4` would silently invert the
correction. `fanConst.k` holds the physical quantity with its physical sign.
Same reasoning as AHU-FC-055's `designConst`.

Fan rise and sensor error do different jobs here, which is why they are
separate parameters. `fan_rise` positions the center of the acceptance band —
the difference the unit is expected to show — and `combined_error` sets its
half-width. Retuning one does not imply retuning the other.

## Possible Diagnoses

Per G36 §5.16.14 Table 5.16.14.8, FC#8:

1. SAT sensor error. Cheapest to rule out, and the reading is easy to check
   against a hand-held reference in the supply duct.
2. MAT sensor error. Harder: a mixed-air sensor can be in calibration and
   still wrong, because it may be reading a stratified slice of the plenum
   instead of the mixture. AHU-FC-062 is the rule that catches the gross
   version of this.
3. Cooling coil valve leaking or stuck open. Chilled water flowing through a
   valve commanded to 0 shows up here as supply air colder than the fan-heat
   correction can explain, and nowhere in the command stream at all.
4. Heating coil valve leaking or stuck open. The mirror case, and the more
   expensive one in this operating state: the unit chose free cooling because
   outdoor air was useful, and a leaking heating valve is spending boiler
   energy to undo it.

## Energy Impact

COMFORT_ENERGY, LOW confidence, QUALITATIVE_ONLY — the grades in the
reference's §5.8.1 index row, which maps this fault to PNNL EEM-01 (sensor
recalibration) and publishes its savings as sensor-dependent. Nothing is
estimated from the rule's inputs: `sat` and `mat` give a temperature
difference and no airflow, so there is no power term, and the difference
itself is ambiguous between a sensor that is lying and a valve that is
leaking. Those two have very different costs. A drifted sensor burns nothing
directly; its cost is the economizer and coil decisions it distorts. A valve
leaking through in free cooling burns plant energy continuously, and worse
than the same leak elsewhere, because the unit entered OS#2 precisely on the
finding that outdoor air could do the job unaided. Climate-neutral, since
either coil can be the culprit and the fault does not depend on the season.

## Emissions Impact

QUALITATIVE_EMISSIONS, LOW confidence; the emissions block is library-assigned,
as the §5.8.1 index carries no emissions column. Scope is recorded as `1|2`
because the equation cannot tell which coil is leaking: a hot water valve
passing flow lands in Scope 1 (on-site combustion, or Scope 2 for electric
resistance and heat pump heat), while a chilled water valve or a DX circuit
stuck on lands in Scope 2. The sensor-error diagnoses have no direct emissions
at all. Avoided-emissions basis: N/A — no quantity is estimated.

## Deviations

- **The reference card is an index row, so this card is built from G36.** The
  HVAC FDD Reference abbreviates AHU-FC-008: §5.8.1 gives the code, the name,
  and the energy grades, with no equation, no test vectors, and no severity.
  The normative content here — the equation, the OS#2 applicability, the four
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
  `sqrt(eSAT² + eMAT²)`, an expression over two internal variables. The graph
  carries the evaluated result, 3.1623 °C, in `devBig.t`, so a host retunes one
  parameter instead of two and no square root is computed at runtime. The
  composition is written out in the parameter description because the
  arithmetic is not linear: a site with a 4 °C mixed-air sensor recomputes
  sqrt(1 + 16) = 4.1231 °C, not 1 + 4.
- **No boundary deviation for this fault.** G36's FC#8 comparison is already
  strict (`>`), unlike the `≥`/`≤` forms elsewhere in Table 5.16.14.8 (FC#5,
  FC#12, FC#14, FC#15), so CDL's `GreaterThreshold` (`u > t`) reproduces the
  source exactly and no measure-zero rewrite is involved. A deviation of
  exactly 3.1623 °C reads healthy in both. Same finding as the AHU-FC-009 and
  AHU-FC-011 cards. The vectors pin the edge from both sides and on both signs.
- **Fan heat enters as a constant signal, not a negative parameter.** An
  `AddParameter` with `p = −1.0` would compute the same deviation but would
  store the fan rise with an inverted sign, so a host setting the measured
  value through `set_param` would double the error instead of correcting it.
  `Reals.Sources.Constant` plus `Subtract` keeps `fan_rise` a positive quantity
  in the units an engineer would measure. Precedent: AHU-FC-055's
  `designConst`.
- **Instantaneous samples instead of averaged signals.** G36 compares 5-minute
  rolling averages sampled at 1-minute intervals (`SAT_AVG`, `MAT_AVG`). This
  rule compares the raw samples and leans on the 30-minute `persist` delay to
  reject noise. The two are not equivalent. Averaging tolerates a signal whose
  mean stays outside the bound while it keeps crossing back; persistence does
  not — an oscillating difference resets the timer on every compliant tick and
  can hide indefinitely. The faults this rule is actually for, a drifted sensor
  and a leaking valve, are steady offsets and read the same way under either
  treatment. (Honesty note carried from AHU-FC-002.)
- **No test vectors are published for this fault**, by the reference or by G36.
  Every scenario in `vectors.json` is authored from the equation: the
  fan-rise-exact case where the deviation is zero, both leak directions, both
  sides of the strict boundary on both signs, a sub-delay transient, and a
  recovery-clears case.
- **Suppression is declared, not encoded.** AHU-FC-062 gates MAT integrity and
  silences this rule while it is active. The block graph cannot express that —
  the engine is status-blind and each rule is an independent composite — so the
  relationship lives in `suppressed_by` and the host enforces it.
- **Operating-state gating and NO_EVAL are frontmatter, not graph.** G36 scopes
  FC#8 to OS#2 (§5.16.14.9b), suspends evaluation for ModeDelay after a mode
  change, and suspends it entirely when the AHU is not operating (§5.16.14.11).
  None of that is in the block graph, per the library's stance that the graph
  computes fault-given-valid-data only. A host that evaluates this rule in OS#1
  or OS#4 will see it assert continuously and correctly by the equation, and
  meaninglessly in fact, because a working coil is exactly what the difference
  is measuring.
- `persist.delayOnInit = true` (Modelica/CDL default is `false`): a deviation
  already present at load waits out the full 30 minutes rather than alarming on
  the first tick after a controller restart. Library-wide choice, per
  AHU-FC-050.

## Notes

This rule and AHU-FC-010 are the G36 pair that test whether two temperatures
that ought to be equal actually are. They are close cousins of AHU-FC-062 and
differ from it in two ways worth keeping straight. FC-062 tests *containment*
— MAT inside the OAT–RAT envelope — which is a physical law that holds in
every operating state, so it runs everywhere with a single combined tolerance
covering all three sensors. This rule and FC-010 test *equality*, which only
holds in one state each, and size their bands as the root-sum-square of two
specific sensors' error. FC-062 is the coarse gate that says the mixed-air
reading is usable at all; these two are the fine checks that only make sense
once it is.

The pair also splits the AHU into halves at the fan. FC-010 compares MAT
against OAT, both upstream of the fan, and carries no fan-heat term at all.
This rule compares SAT against MAT, straddling the fan, and must correct for
it. That is the whole reason `fan_rise` appears in one card and not the other,
and it is worth checking before assuming a missing term is an oversight.

Run the [sensor-drift](../../../playbooks/sensor-drift.md) playbook before
touching a valve. The sensor diagnoses are the cheap ones to eliminate — a
hand-held reference in the supply duct settles the SAT question in minutes,
and a temperature sensor runs $30–$80 — and eliminating them is what turns
this fault from an ambiguous reading into a work order for a valve.
