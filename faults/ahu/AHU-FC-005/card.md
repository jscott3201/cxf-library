---
schema: cxf-library/fault-card/v1
id: AHU-FC-005
name: SAT too low vs MAT in heating
equipment: ahu
status: verified
phase: 1
method: rule
severity: 3
category: EXCESS_CONSUMPTION
confidence: MEDIUM
estimation_method: PROXY_ESTIMATION
source:
  - "HVAC FDD Reference v1.0 §5.8.1 (index; card abbreviated)"
  - "G36 §5.16.14 FC#5 (text per Addendum u public review)"
  - "NISTIR 7365 (defaults provenance)"
g36: "§5.16.14 FC#5"
clusters: [CLU-01]
suppresses: []
suppressed_by: [AHU-FC-062]
related: [AHU-FC-050, AHU-FC-007, AHU-FC-062]
playbooks: [simultaneous-hc]
operating_states: "OS#1 (heating) — host-gated"
preconditions: "The unit must have a MAT sensor; G36 omits FC#5 where there is none. Evaluate only in OS#1, whose actuator signature per G36 Table 5.16.14.2 is heating coil > 0, cooling coil = 0, OA damper at minimum position — outside it a SAT below MAT is the intended result of cooling, not a fault. Supply fan running, since neither MAT nor SAT means anything in still air. Suspend evaluation for ModeDelay (30 min) after any operating-state change, while the coils and damper are still stroking and the sensors still report the previous state's mixture. Silence this rule while AHU-FC-062 is active: MAT is an input here and FC-062 is its integrity gate. When any gate is unmet the verdict is NO_EVAL, not healthy."
points:
  - mat
  - sat
outputs:
  - name: yFault
    description: True while SAT has stayed more than mat_sat_gap_threshold below MAT for at least alarm_delay
params:
  mat_sat_gap_threshold:
    default: 3.0
    unit: "°C"
    description: "Shortfall of SAT below MAT that counts as heat being removed rather than sensor and fan-rise uncertainty. Composed from the G36 §5.16.14 internal variables as eSAT + eMAT − dTSF = 1 + 3 − 1; a site that retunes any of the three recomputes the sum (a larger measured fan rise lowers the threshold, a looser sensor band raises it)"
    cxf: gapBig.t
  alarm_delay:
    default: 1800.0
    unit: s
    description: Continuous fault persistence required before the alarm asserts (G36 AlarmDelay, 30 min)
    cxf: persist.delayTime
energy_impact:
  affected_subsystem: AHU heating (and the cooling source cancelling it)
  savings_range: "1-4% of site energy (HVAC FDD Reference §5.8.1 index row, mapped there to PNNL-25985 EEM-05)"
  climate_sensitivity: heating-dominant
  runtime_estimation: "waste_kw >= supply_airflow_m3s × 1.2 kg/m³ × 1.005 kJ/kg·K × ((mat + dTSF) − sat) — the thermal power being removed from air the heating coil just paid to warm. A floor, not an equality: it credits the coil with no rise at all, and design airflow stands in for a measured one"
emissions:
  scope: "1+2"
  method: PROXY_EMISSIONS
verified:
  engine_rev: e2ff2f8
  content_id: "cxf:fnv1a128:23c2dc854e3fd583e7f98f40f298a24a"
  date: 2026-08-17
---

## Description

In heating, air leaves the unit warmer than it arrived. It crosses the supply
fan, which adds about a degree of shaft work, and then a heating coil the
sequence has called for. SAT sitting several degrees *below* MAT under those
conditions is not a control error — it means something in the unit is taking
heat back out. A cooling coil valve leaking or stuck open, a DX circuit stuck
on, or a sensor pair that disagrees by more than either instrument is rated for.

This is G36 §5.16.14 FC#5, applicable in OS#1 (heating) only. Elsewhere a SAT
below MAT is exactly what the sequence asked for. The leaking-cooling-coil
diagnosis is simultaneous heating and cooling seen from the air side, which is
why the fault sits in cluster CLU-01 behind AHU-FC-050: FC-050 catches the two
valve commands overlapping, this rule catches the case where only one command is
raised and the other device is passing water or refrigerant anyway.

## Detection Logic

```
gap    = mat − sat
yFault = gap > mat_sat_gap_threshold,
         sustained continuously for alarm_delay
```

Block graph (`rule.cxf.jsonld`):

![AHU-FC-005 block graph](diagram.svg)

`gap` subtracts SAT from MAT and `gapBig` compares that shortfall against
`mat_sat_gap_threshold`, which is G36's `SAT_AVG + eSAT <= MAT_AVG − eMAT +
dTSF` rearranged so one positive number carries the whole allowance (see
Deviations). The threshold is not a sensor tolerance: it is the two sensor
bands *minus* the fan rise the air is known to get for free, so it fires on
heat removal that neither instrument error nor the fan can explain. The
comparison is strict, so a gap sitting exactly on 3.0 °C reads healthy.
`persist` requires 30 minutes of continuous violation, which rides out the
minutes after a mode change, a hot-water loop coming up to temperature, and a
valve stroking through its span.

Nothing about the size of the heating call reaches this rule. A unit whose
heating coil does nothing at all still shows SAT about a fan rise above MAT, so
the gap runs slightly negative and this rule reads healthy; that failure belongs
to the inactive-coil rules. What this rule tests is the sign and size of the
temperature change across the unit, which is the one thing two temperature
sensors can settle between them.

## Possible Diagnoses

G36 §5.16.14 FC#5, transcribed:

1. SAT sensor error
2. MAT sensor error
3. Cooling coil valve leaking or stuck open
4. Heating coil valve stuck closed or actuator failure
5. Fouled or undersized heating coil
6. HW temperature too low or HW unavailable
7. Gas or electric heat unavailable
8. DX cooling stuck on

Diagnoses 4 through 7 — a dead heating coil, whatever killed it — explain a
missing temperature rise on their own, but not a rise of the wrong sign. They
reach this rule only in company: nothing is being added while something else is
taking heat out. So read the list as two groups. Either the sensors are lying
(1, 2), or a heat sink is running against the heating call (3, 8), and a dead
coil behind it (4–7) makes the gap wide enough to clear the threshold sooner.

## Energy Impact

EXCESS_CONSUMPTION, MEDIUM confidence, PROXY_ESTIMATION, all three taken from
the reference's §5.8.1 index row. The waste is a cancellation: the heating
source pays to warm air and a leaking cooling coil or a stuck DX circuit
immediately unpays it, so both sides of the exchange bill. The runtime proxy
sizes the removal rather than the addition, because the removal is what the two
temperatures observe:

```
waste_kw >= supply_airflow_m3s × 1.2 × 1.005 × ((mat + dTSF) − sat)
```

That is a floor rather than an equality, because it credits the heating coil
with no rise at all; whatever the coil did add is being removed on top of it.
Design airflow stands in for a measured one, and the split between "heat never
added" and "heat added then removed" is not observable from two temperatures —
between them, that is what keeps this an estimate. The same
formula shape carries AHU-FC-050's simultaneous heating and cooling waste term.
The index puts the recoverable range at 1–4% of site energy and maps the fault
to PNNL-25985 EEM-05 (supply air temperature reset), the nearest measure in
PNNL's catalog rather than a measure-specific study of this failure — the repair
this fault actually dispatches is a valve, coil, or sensor, so treat the range
as an order-of-magnitude bound. Heating-dominant by climate: the fault can only
be evaluated in OS#1, so its hours are heating hours.

## Emissions Impact

PROXY_EMISSIONS, MEDIUM confidence. Scope is recorded as `1+2` because the two
halves of the exchange run at once and land in different inventories: hot water from a gas boiler or a gas furnace section is Scope 1,
electric resistance or a heat pump is Scope 2, and the cooling side that eats
the heat is Scope 2 in nearly every building. A site with gas heat and electric
cooling is genuinely paying into both at once, which is the CLU-01 signature
the reference's §5A.8 table describes. Avoided-emissions basis: marginal
operating emissions rate (MOER) for the electric half, static combustion factor
for the fuel half.

## Deviations

- **The reference card for this fault is abbreviated; G36 is the normative
  source.** HVAC FDD Reference v1.0 carries AHU-FC-005 as a §5.8.1 index row —
  name, impact category, confidence, estimation method, EEM link, savings range
  — with no chapter 9 card behind it, so it publishes no equation, no tunable
  defaults, no diagnoses, no operating-state applicability, no severity, and no
  test vectors. Everything in Detection Logic and Possible Diagnoses is
  transcribed from ASHRAE Guideline 36 §5.16.14 FC#5 as it appears in Addendum u
  to Guideline 36-2018 (first public review, 2021), with the internal-variable
  defaults of Table 5.16.14.5 (NISTIR 7365 provenance, which the addendum notes
  are biased toward minimizing false alarms).
- **Severity 3 is the library's.** No reference card exists to state one and the
  §5.8.1 index carries no severity column. The value matches the scaffold row in
  this chapter's README and the treatment of every other G36 comparison rule
  here: a fault worth a work order inside a week, not a same-day dispatch.
- **The energy profile is the index row's; the emissions split is the
  library's.** `category`, `confidence`, `estimation_method`, and
  `savings_range` are copied from §5.8.1 (EXCESS_CONSUMP / MED / PROXY / 1–4%
  site), as every 001-range card verified before this one did. The index carries
  no emissions column, so `scope` and `method` are assigned here: `1+2` follows
  AHU-FC-050's convention for simultaneous heating-and-cooling waste — both
  inventories fill at once, and only the heating half's fuel varies by plant
  (matching mirror card AHU-FC-012). The runtime formula is the library's too, mirrored from AHU-FC-050's
  simultaneous-heating-and-cooling waste term.
- **Combined-epsilon threshold.** G36 states the test as `SAT_AVG + eSAT <=
  MAT_AVG − eMAT + dTSF` across three separate internal variables. Rearranged,
  that is `MAT − SAT >= eSAT + eMAT − dTSF`, so one positive threshold binds one
  CXF path: 1 + 3 − 1 = 3.0 °C at the Table 5.16.14.5 defaults. A site that
  retunes any input recomputes the sum rather than the parameter — measure the
  fan rise at 2 K on a high-static unit and the threshold drops to 2.0 °C
  (sharper, because more free heat is expected); loosen eMAT to 4 K for a
  poorly mixed plenum and it rises to 4.0 °C. Same rearrangement as AHU-FC-062
  and AHU-FC-001, and it can disagree with the four-term form by one ulp on a
  value straddling the threshold, which no temperature sensor resolves.
- **G36's `<=` becomes a strict `>`.** CDL `Reals` offers no greater-or-equal
  comparison, so a gap of exactly 3.0 °C reads healthy where G36 would call it a
  fault. The disagreement has measure zero on a real temperature pair and errs
  toward silence. The vectors pin both sides (3.0 clear, 3.1 faulted).
- **Instantaneous samples instead of averaged signals.** G36 computes every
  signal as a five-minute rolling average of one-minute samples (`SAT_AVG`,
  `MAT_AVG`). This rule compares raw samples and leans on the 30-minute
  `persist` delay to reject noise. The two are not equivalent: averaging
  tolerates a signal that keeps crossing back while its mean stays outside the
  band, and persistence does not — an oscillating gap resets the timer on every
  compliant tick and can hide indefinitely. The `oscillating_gap_never_persists`
  vector is that case, recorded rather than hidden. A steady offset, which is
  what a leaking valve or a drifted sensor produces, reads the same way under
  either treatment. Same note as AHU-FC-002.
- **Operating-state applicability and ModeDelay are frontmatter, not graph.**
  G36 scopes FC#5 to OS#1 and suspends every fault condition for 30 minutes
  after a mode change. Both are host concerns under this library's stance
  (precedent AHU-FC-063): the graph computes the fault given valid data, and a
  verdict outside OS#1 or inside the transition window is NO_EVAL, never
  healthy. The OS#1 signature the host gates on is G36 Table 5.16.14.2's:
  heating coil > 0, cooling coil = 0, OA damper at minimum position.
- **Suppression is declared, not encoded.** MAT is an input, so AHU-FC-062 — the
  mixing-box integrity gate that tests MAT against the OAT/RAT envelope —
  silences this rule while it is active. The engine is status-blind and cannot
  express that; it lives in `suppressed_by` and the host enforces it.
- **No published test vectors.** The reference publishes vectors only for faults
  with full chapter cards. Every scenario in `vectors.json` is authored from the
  G36 equation: both sides of the threshold edge, a transient shorter than
  `alarm_delay`, a recovery that clears, and the oscillation case above.
- `persist.delayOnInit = true` (Modelica/CDL default is `false`), the library's
  standing choice: a gap already present at load waits out the full 30 minutes
  rather than alarming on the first tick after a controller restart.

## Notes

This rule and AHU-FC-007 are the two G36 heating-side SAT tests, and they fail
differently on purpose. FC-007 compares SAT against its setpoint with the valve
saturated and answers "the unit cannot make the air it was asked for". This one
compares SAT against MAT and answers "the unit is making the air colder than it
found it". A fouled coil or a dead boiler trips FC-007 and leaves this rule
quiet, because nothing is removing heat. A leaking cooling valve trips both:
the unit is short of setpoint *and* running a heat sink. Both firing on the same
unit points at diagnosis 3 or 8 before anything else on the list.

Order of work: confirm MAT before believing the gap. AHU-FC-062 exists for
exactly this and runs a shorter delay, so if the mixing box or the MAT sensor is
the problem the operator sees that alarm first and this one is suppressed. If
MAT checks out, the [simultaneous-hc](../../../playbooks/simultaneous-hc.md)
playbook covers the leaking-valve half of the diagnosis list — the same
isolation-valve and actuator checks apply whether the overlap shows up as two
open valve commands (AHU-FC-050) or as air that mysteriously loses heat crossing
a unit in heating.
