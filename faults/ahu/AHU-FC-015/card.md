---
schema: cxf-library/fault-card/v1
id: AHU-FC-015
name: Inactive heating coil temperature rise
equipment: ahu
status: verified
phase: 1
method: rule
severity: 2
category: CRITICAL_WASTE
confidence: HIGH
estimation_method: DIRECT_MEASUREMENT
source:
  - "HVAC FDD Reference v1.0 §5.8.1 (index; card abbreviated)"
  - "G36 §5.16.14 FC#15 (text per Addendum u public review)"
  - "NISTIR 7365 (defaults provenance)"
  - "PNNL EEM-03 (leaking coil valves; the §5.8.1 index row's EEM mapping)"
g36: "§5.16.14 FC#15"
clusters: []
suppresses: []
suppressed_by: [AHU-FC-062]
related: [AHU-FC-050, AHU-FC-054, AHU-FC-014, AHU-FC-012, AHU-FC-062]
playbooks: [stuck-actuator]
operating_states: "OS#2-#4 (heating coil commanded off) — host-gated"
preconditions: "Supply fan running, and the unit in one of the three states where G36 requires the heating coil to be off (Table 5.16.14.2): OS#2 free cooling (HC = 0, CC = 0, minimum < OA damper < 100%), OS#3 mechanical plus economizer cooling (HC = 0, CC > 0, OA damper = 100%), or OS#4 mechanical cooling on minimum OA (HC = 0, CC > 0, OA damper at minimum). In OS#1 the coil is commanded to heat and a rise across it is the intended result, not a fault. Suspend evaluation for ModeDelay (30 min) after any mode or operating-state change in a zone group the AHU serves, and whenever the AHU is not operating (G36 §5.16.14.11) — a coil coasting down still shows its rise, and a preheat coil in freeze protection shows one on purpose. This binding reads the coil through MAT and SAT, so a unit with no MAT sensor cannot run the rule as shipped: install dedicated coil sensors and rebind, or omit. Silence the rule while AHU-FC-062 is active: a MAT outside the OAT/RAT envelope is not a coil entering temperature. When any gate is unmet the verdict is NO_EVAL, not healthy."
points:
  - sat
  - mat
outputs:
  - name: yFault
    description: True while sat has stayed more than coil_rise_threshold above mat for at least alarm_delay
params:
  coil_rise_threshold:
    default: 4.1623
    unit: "°C"
    description: "Temperature rise across the heating coil that stops being fan heat and sensor noise and starts being heat. Composed from the G36 §5.16.14 internal variables as sqrt(eHCET² + eHCLT²) + dTSF = sqrt(3² + 1²) + 1 = 4.1623, using the proxied epsilons Table 5.16.14.5 prescribes when the coil is read through MAT and SAT (eHCET = eMAT = 3 °C, eHCLT = eSAT = 1 °C) and the fan-heat term dTSF = 1 °C, which belongs here because the supply fan sits between the two sensors and its rise would otherwise be charged to the coil. Retunes: dedicated sensors bracketing the coil with the fan outside the pair drop the dTSF term and their own epsilons, giving sqrt(2)·1 ≈ 1.41 for a matched ±1 °C pair or 3.1623 if the entering sensor keeps a 3 °C band; a site that measures a fan rise other than 1 °C substitutes it directly"
    cxf: riseBig.t
  alarm_delay:
    default: 1800.0
    unit: s
    description: Continuous fault persistence required before the alarm asserts (G36 AlarmDelay, 30 min)
    cxf: persist.delayTime
energy_impact:
  affected_subsystem: AHU heating coil, and in OS#3-#4 the cooling coil paying to undo it
  savings_range: "0.5-5% of site energy (HVAC FDD Reference §5.8.1 index row, mapped there to PNNL EEM-03)"
  climate_sensitivity: cooling-dominant
  runtime_estimation: "waste_kw = supply_airflow_m3s × 1.2 kg/m³ × 1.005 kJ/kg·K × ((sat − mat) − dTSF) — the thermal power the coil is adding to air no sequence asked it to heat. The fan's rise is subtracted because it is part of the measured rise and none of it is the coil's doing; the remainder is what the leak contributes. Design airflow stands in unless a measurement station is bound; in OS#3-#4 the cooling coil is paying the same bill a second time to take the heat back out"
emissions:
  scope: "1+2"
  method: PROXY_EMISSIONS
verified:
  engine_rev: e2ff2f8
  content_id: "cxf:fnv1a128:2e4a701f33e4a7b3245b96c9e5b6922a"
  date: 2026-08-17
---

## Description

In OS#2, OS#3, and OS#4 the heating coil is closed by definition — G36
identifies all three states partly by `HC = 0`. Air crossing the unit in those
states should pick up the supply fan's degree of shaft work and nothing more.
When SAT reads several degrees above MAT anyway, hot water is moving through a
valve that reports itself shut, or an electric or gas stage is energized that
nothing called for.

In OS#3 and OS#4 the cooling coil is running at the same time, so every kilowatt
the leaking heating coil adds is a kilowatt the chiller is being paid to remove:
the AHU-FC-050 failure arriving through a different door. In OS#2 the unit is on
free cooling, and the leak spends the economizer's savings by warming the outdoor
air that was supposed to do the cooling — often pushing the unit into mechanical
cooling it did not need.

This rule and AHU-FC-014 are AHU-FC-050's silent siblings. AHU-FC-050 reads the
two valve *commands* and needs both of them past 5% open to fire, so a valve
that reports 0% and flows anyway is invisible to it. This pair reads the temperature
signature instead and does not care what the command says, which is exactly the
case AHU-FC-050 is structurally blind to.

## Detection Logic

```
rise   = sat − mat
yFault = rise > coil_rise_threshold,
         sustained continuously for alarm_delay
```

Block graph (`rule.cxf.jsonld`):

![AHU-FC-015 block graph](diagram.svg)

G36 writes the test as `HCLT_AVG − HCET_AVG ≥ sqrt(eHCET² + eHCLT²) + ΔTSF*`,
with the footnote "Fan heat factor included or not depending on location of
sensors used for HCET and HCLT". Two decisions turn that into the graph above.

**Which sensors HCET and HCLT are.** G36 leaves the binding open: the coil
entering temperature "could be the MAT or a separate sensor for this specific
purpose", the leaving temperature "could be the SAT or a separate sensor"
(§5.16.14.5), and Table 5.16.14.5 then sets eHCET = eMAT and eHCLT = eSAT for
the proxied case. This library binds the no-dedicated-sensor configuration —
`HCET := mat`, `HCLT := sat` — because that is the instrumentation most air
handlers actually have. The epsilons follow the binding: 3 °C for the mixed-air
sensor, 1 °C for the supply-air sensor, root-sum-square to 3.1623 °C.

**Whether the fan-heat term applies.** It does, because the supply fan sits
between MAT and SAT on the unit G36 assumes ("the SAT sensor is located
downstream of the supply fan"), and here the term is doing real physical work
rather than bookkeeping. A healthy draw-through unit with both coils shut
already reads `sat − mat` = +1.0 °C: the fan put that degree in. Drop the term
and the test charges that degree to the coil — the threshold falls to 3.1623 °C,
a true coil rise of 2.17 °C reports as a leak, and on a unit whose fan adds more
than 3.16 °C the alarm never clears at all. With the term the arithmetic is
exact rather than merely
safe: measured rise = true coil rise + dTSF, so the shipped test fires precisely
when the coil's own contribution exceeds the 3.1623 °C sensor floor. The
`healthy_unit_shows_fan_heat_only` vector pins the 1.0 °C case clear forever.

`riseBig` is a strict `>`, so a rise sitting exactly on 4.1623 °C reads healthy.
`persist` requires 30 continuous minutes, which is what separates a leaking
valve from a coil giving up the hot water still standing in it after a state
change; recovery is immediate on the tick the rise falls back inside the
allowance.

## Possible Diagnoses

Transcribed from G36 §5.16.14 FC#15:

1. HCET sensor error
2. HCLT sensor error
3. Heating coil valve stuck open or leaking

The single-zone version of the same row (§5.18.14, the SZVAV table in Addendum
u) adds a fourth, "gas or electric heat stuck on", which applies to any unit
with a non-hydronic heat source and is worth carrying in the operator's head on
those units even though the VAV row omits it.

Under this library's binding, diagnoses 1 and 2 read as MAT sensor error and SAT
sensor error, and they are the cheap ones to eliminate first. Diagnosis 3 is the
one that dominates in the field and the reason the card carries the
[stuck actuator](../../../playbooks/stuck-actuator.md) playbook: a two-way valve
whose seat has eroded, or an actuator that has lost its close position, passes
water at a command of 0% and no command-based rule will ever see it.

## Energy Impact

CRITICAL_WASTE, HIGH confidence, DIRECT_MEASUREMENT, savings 0.5–5% of site
energy mapped to PNNL EEM-03 (leaking coil valves) — the §5.8.1 index row, which
is the only energy statement the reference makes about this fault.
DIRECT_MEASUREMENT is honest here in a way it is not for the abbreviated
comparison rules: the two temperatures the rule already reads *are* the
measurement, and `waste_kw = supply_airflow_m3s × 1.2 × 1.005 × ((sat − mat) −
dTSF)` converts them into thermal power with one substitution, design airflow
for measured airflow. Subtracting the fan rise is not a rounding detail: at the
threshold it is 1.0 of a 4.16 °C measured rise, so crediting it to the coil
would overstate the waste by about a third, and by more on any smaller leak.
HIGH confidence because a sustained rise across a
coil that is commanded shut has no benign explanation other than a sensor, and
the sensor case shows up as a rise that does not move with load.

Cooling-dominant, following the operating states: all three are cooling-side
states, and in OS#3 and OS#4 the leak is paid for twice — once at the boiler and
once at the chiller.

## Emissions Impact

PROXY_EMISSIONS, scope `1+2`. The §5.8.1 index publishes no emissions column, so
both fields are the library's, assigned to match the physics the rule detects:
the leaked heat is Scope 1 or Scope 2 depending on the plant (gas boiler versus
electric resistance or a heat pump), and the cooling that removes it again in
OS#3-#4 is purchased electricity, Scope 2. On an all-electric site the whole
exchange collapses to Scope 2. When the cause turns out to be a sensor there is
nothing to attribute at all, which is the same caveat the energy formula
carries. Avoided-emissions basis: marginal operating emissions rate (MOER) for
the electric half, static combustion factor for the fuel half.

## Deviations

- **The reference card is abbreviated; G36 is the normative text here.** The
  HVAC FDD Reference carries AHU-FC-015 only as a §5.8.1 index row — a name and
  an energy profile. No chapter 9 card, so no equation, no internal variables,
  no test vectors, no severity, no diagnosis list, no preconditions. The
  detection logic and the diagnosis list are transcribed from ASHRAE Guideline
  36 §5.16.14 FC#15 as it appears in Addendum u to Guideline 36-2018 (First
  Public Review, 2021). Where the two sources could conflict, G36 wins, because
  it is the only one that states the rule. The fourth diagnosis quoted under
  Possible Diagnoses comes from the addendum's single-zone table (§5.18.14) and
  is marked as such.
- **HCET and HCLT are bound to MAT and SAT.** G36 defines the fault on coil
  entering and leaving temperatures and explicitly leaves their instrumentation
  open (§5.16.14.5). This library ships the proxied binding, and Table 5.16.14.5
  supplies the matching epsilons (eHCET = eMAT = 3 °C, eHCLT = eSAT = 1 °C). The
  consequence is that the rule sees the whole air path between the mixing box
  and the supply sensor, not just the coil: the fan is inside the measurement
  (handled by the dTSF term), and so is any duct heat gain between the coil and
  the sensor (not handled — on this fault it biases the rise upward and makes
  the rule slightly louder, the opposite of its effect on AHU-FC-014). A site
  with dedicated coil sensors rebinds the two boundary inputs at deployment —
  the CXF input connectors are named `sat` and `mat` per the library's point
  convention — and retunes `coil_rise_threshold` with its own sensor errors in
  place of eMAT and eSAT. Because the fan is then outside the sensor pair, that
  retune also drops the dTSF term.
- **The fan-heat term is included, and for this fault it is what keeps healthy
  units quiet.** G36 footnotes ΔTSF as included "or not depending on location of
  sensors used", and with the fan between MAT and SAT the printed term applies.
  The direction matters and it is the opposite of AHU-FC-014's: fan heat and
  coil heat both raise SAT, so the measured rise is the true coil rise *plus*
  one dTSF and the threshold has to discount the fan's own contribution before
  charging anything to the coil. A healthy inactive coil on a draw-through unit
  sits at exactly +1.0 °C. With the term, the shipped test fires when the coil's
  own rise exceeds sqrt(10) = 3.1623 °C — the sensor floor and nothing more, so
  unlike its cooling-side twin this rule is not additionally desensitized by the
  binding and there is no sharper retune of the same kind to offer. Sites with a
  measured fan rise other than 1 °C substitute it in the sum directly.
- **G36's `≥` becomes a strict `>`.** CDL `Reals` has no `GreaterEqual` or
  `GreaterEqualThreshold`, so a rise of exactly 4.1623 °C reads healthy where
  G36 would report the fault. The disagreement has measure zero on a real
  temperature signal and errs toward silence. The vectors pin both sides
  (4.1623 °C clear, 4.2623 °C faulted). A host binding coarsely quantized
  temperatures — integer °C, or a BAS that rounds to 0.5 — should retune the
  threshold down rather than rely on the signal overshooting.
- **The threshold is a rounded constant, not a root-sum-square computed in the
  graph.** sqrt(3² + 1²) + 1 = 4.16227766…, shipped as 4.1623 — high by
  2.2 × 10⁻⁵ °C, four orders of magnitude below the resolution of the sensors
  feeding it. Composing the sum at authoring time rather than in blocks gives
  the host one number to retune through `set_param` at `riseBig.t` instead of
  three, the same rearrangement AHU-FC-005 and AHU-FC-012 make for their linear
  compositions.
- **Instantaneous samples instead of 5-minute rolling averages.** G36 computes
  every signal in §5.16.14 as a 5-minute rolling average with 1-minute sampling
  (`HCET_AVG`, `HCLT_AVG`); this library consumes instantaneous points and lets
  the 30-minute AlarmDelay stand in. The two are not equivalent, and the honesty
  note from AHU-FC-002 applies unchanged: averaging tolerates a signal whose
  mean sits outside the bound while it keeps crossing back, persistence does
  not — an oscillating rise resets the timer on every compliant tick and can
  hide indefinitely. The `oscillating_rise_never_alarms` vector demonstrates
  exactly that miss, and a short-cycling electric stage is a realistic way to
  produce it. A steady leak, which is what a failed valve seat produces, reads
  the same either way.
- **Operating states, ModeDelay, and the not-operating suspension are host-side
  preconditions.** G36 scopes FC#15 to OS#2-#4, suspends evaluation for
  ModeDelay (30 min) after a mode change in a served zone group, and suspends
  all fault evaluation while the AHU is not operating. None of it is in the
  graph: per the library's stance, operating-state applicability, transition
  windows, and NO_EVAL are host concerns declared in `preconditions`. A verdict
  produced outside OS#2-#4 or inside a transition window is NO_EVAL, never
  healthy. Freeze protection deserves its own mention there: a preheat coil
  driven open to protect itself produces this exact signature while doing its
  job. G36 attaches no "omit if no MAT sensor" qualifier to FC#15 — it
  contemplates dedicated coil sensors — but this library's binding needs MAT, so
  the qualifier applies to the shipped rule and lives in `preconditions` with
  the rest of the deployment decisions.
- **Severity 2 is the library's, not the reference's.** The §5.8.1 index carries
  no severity column and there is no chapter card to state one. Severity 2 puts
  this fault with AHU-FC-050 and AHU-FC-054 rather than with the 001-range
  comparison rules at 3, which is where CRITICAL_WASTE and HIGH confidence
  point: a coil conditioning air in a state that requires it to be off is
  simultaneous heating and cooling that no sequence asked for, and this pair is
  the only 001-range entry the chapter README carries at 2. G36 §5.16.14 does
  say every reported fault condition "shall be a Level 3 alarm", but that is
  G36's alarm-priority scheme, not this library's 1-4 severity scale.
- **The energy profile is the index row's; the runtime formula, the climate
  sensitivity, and the emissions block are the library's.** `category`,
  `confidence`, `estimation_method`, and `savings_range` are copied from §5.8.1
  (CRITICAL_WASTE / HIGH / DIRECT / EEM 03 / 0.5–5% site). The reference stops
  there: the proxy formula, the cooling-dominant climate call, and both
  `emissions` fields are this card's, reasoned from the operating states the
  fault is evaluated in.
- **No published test vectors.** The reference publishes none for this fault and
  G36 publishes none for any of them, so `vectors.json` is authored from the
  equation: the healthy fan-heat-only pin, both sides of the 4.1623 °C edge, a
  leaking valve during free cooling, a sensor error with the plant locked out, a
  transient shorter than AlarmDelay, a recovery, and the oscillation the
  persistence substitution is known to miss.
- `persist.delayOnInit = true` (Modelica/CDL default is `false`), the library's
  standing choice: a violation already present at load waits out the full 30
  minutes instead of alarming on the first tick after a controller restart.

## Notes

This rule and AHU-FC-012 test the same sign, on the same two sensors, in
overlapping states, and both exist on purpose. AHU-FC-012 is G36 FC#12, "SAT too
high; should be less than MAT", scoped to OS#2-#4 and thresholded at
eSAT + eMAT + ΔTSF = 5.0 °C — sensor bands added linearly, the worst case where
both sensors are wrong in the directions that hurt. This rule is FC#15, the same
physics stated as a coil signature, thresholded at
sqrt(eHCET² + eHCLT²) + ΔTSF = 4.1623 °C — the same bands added in quadrature,
which is the sharper and better-justified composition when the two sensor errors
are independent. So on a shared unit this rule alarms first, by 0.84 °C of rise,
and AHU-FC-012 follows if the leak grows. The diagnosis lists are what makes
running both worthwhile: FC#12's is broad and includes cooling-side capacity
failures, while FC#15 names the heating coil and its sensors and nothing else.
A host that wants one alarm rather than two should keep this one and treat
AHU-FC-012's extra diagnoses as the escalation.

Start at the sensors: a MAT reading low or a SAT reading high produces this trace
with nothing wrong in the mechanical room, and both are cheap to check against a
portable reference. If AHU-FC-062 is also active the host should already be
suppressing this rule, because MAT is standing in for the coil entering
temperature and FC-062 is its integrity gate. If the sensors check out, the
question is whether the hot-water valve is passing: isolate the coil and watch
the rise collapse to fan heat. The stuck-actuator playbook takes it from there —
its verification step strokes the actuator through its full range against
feedback, which is what separates a failed actuator from an eroded seat that no
command will close. On a unit with electric or gas heat, check the stage's
contactor or
safety interlock instead — the SZVAV diagnosis list names that failure
explicitly.
