---
schema: cxf-library/fault-card/v1
id: AHU-FC-014
name: Inactive cooling coil temperature drop
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
  - "G36 §5.16.14 FC#14 (text per Addendum u public review)"
  - "NISTIR 7365 (defaults provenance)"
  - "PNNL EEM-03 (leaking coil valves; the §5.8.1 index row's EEM mapping)"
g36: "§5.16.14 FC#14"
clusters: []
suppresses: []
suppressed_by: [AHU-FC-062]
related: [AHU-FC-050, AHU-FC-054, AHU-FC-015, AHU-FC-005, AHU-FC-062]
playbooks: [stuck-actuator]
operating_states: "OS#1-#2 (cooling coil commanded off) — host-gated"
preconditions: "Supply fan running, and the unit in one of the two states where G36 requires the cooling coil to be off: OS#1 heating (Table 5.16.14.2: HC > 0, CC = 0, OA damper at minimum) or OS#2 free cooling (HC = 0, CC = 0, minimum < OA damper < 100%). In OS#3 and OS#4 the coil is commanded to cool and a drop across it is the intended result, not a fault. Suspend evaluation for ModeDelay (30 min) after any mode or operating-state change in a zone group the AHU serves, and whenever the AHU is not operating (G36 §5.16.14.11) — a coil coasting down still shows its drop. This binding reads the coil through MAT and SAT, so a unit with no MAT sensor cannot run the rule as shipped: install dedicated coil sensors and rebind, or omit. Silence the rule while AHU-FC-062 is active: a MAT outside the OAT/RAT envelope is not a coil entering temperature. When any gate is unmet the verdict is NO_EVAL, not healthy."
points:
  - mat
  - sat
outputs:
  - name: yFault
    description: True while mat has stayed more than coil_drop_threshold above sat for at least alarm_delay
params:
  coil_drop_threshold:
    default: 4.1623
    unit: "°C"
    description: "Temperature drop across the cooling coil that stops being sensor noise and starts being cooling. Composed from the G36 §5.16.14 internal variables as sqrt(eCCET² + eCCLT²) + dTSF = sqrt(3² + 1²) + 1 = 4.1623, using the proxied epsilons Table 5.16.14.5 prescribes when the coil is read through MAT and SAT (eCCET = eMAT = 3 °C, eCCLT = eSAT = 1 °C) and the fan-heat term dTSF = 1 °C, which belongs here because the supply fan sits between the two sensors. Retunes: dedicated sensors bracketing the coil with the fan outside the pair drop the dTSF term and their own epsilons, giving sqrt(2)·1 ≈ 1.41 for a matched ±1 °C pair or 3.1623 if the entering sensor keeps a 3 °C band; keeping the mat/sat binding but testing the true coil drop against G36's noise floor alone gives sqrt(10) − 1 = 2.1623"
    cxf: dropBig.t
  alarm_delay:
    default: 1800.0
    unit: s
    description: Continuous fault persistence required before the alarm asserts (G36 AlarmDelay, 30 min)
    cxf: persist.delayTime
energy_impact:
  affected_subsystem: AHU cooling coil, and in OS#1 the heating coil paying to undo it
  savings_range: "0.5-5% of site energy (HVAC FDD Reference §5.8.1 index row, mapped there to PNNL EEM-03)"
  climate_sensitivity: heating-dominant
  runtime_estimation: "waste_kw = supply_airflow_m3s × 1.2 kg/m³ × 1.005 kJ/kg·K × ((mat − sat) + dTSF) — the thermal power the coil is removing from air no sequence asked it to cool. The fan's rise is added back because the measured drop is the true coil drop minus dTSF: the fan warms the air between the two sensors and hides that much of the coil's work. Design airflow stands in unless a measurement station is bound; in OS#1 the heating coil is paying the same bill a second time to put the heat back"
emissions:
  scope: "1+2"
  method: PROXY_EMISSIONS
verified:
  engine_rev: e2ff2f8
  content_id: "cxf:fnv1a128:9fb8c27579429e23f93c2f5a34e84d40"
  date: 2026-08-17
---

## Description

In OS#1 and OS#2 the cooling coil is closed by definition — G36 identifies both
states partly by `CC = 0`. Air crossing the unit in those states meets the
supply fan and nothing else, so it arrives at the supply sensor about a degree
warmer than it left the mixing box. When SAT instead reads several degrees
*below* MAT, something is pulling heat out of the stream: chilled water past a
valve that reports itself shut, or a DX circuit that never got the message to
stop.

The waste is worst in OS#1, where the heating coil is running. Every kilowatt
the leaking cooling coil removes is a kilowatt the heating coil is being paid to
put back, which is the AHU-FC-050 failure arriving through a different door. In
OS#2 the unit is on free cooling and there is no heating bill, but the chilled
water is still being made and pumped for air that the economizer was already
cooling for nothing.

This rule and AHU-FC-015 are AHU-FC-050's silent siblings. AHU-FC-050 reads the
two valve *commands* and needs both of them past 5% open to fire, so a valve
that reports 0% and flows anyway is invisible to it. This pair reads the temperature
signature instead and does not care what the command says, which is exactly the
case AHU-FC-050 is structurally blind to.

## Detection Logic

```
drop   = mat − sat
yFault = drop > coil_drop_threshold,
         sustained continuously for alarm_delay
```

Block graph (`rule.cxf.jsonld`):

![AHU-FC-014 block graph](diagram.svg)

G36 writes the test as `CCET_AVG − CCLT_AVG ≥ sqrt(eCCET² + eCCLT²) + ΔTSF*`,
with the footnote "Fan heat factor included or not depending on location of
sensors used for CCET and CCLT". Two decisions turn that into the graph above.

**Which sensors CCET and CCLT are.** G36 leaves the binding open: the coil
entering temperature "could be the MAT or a separate sensor for this specific
purpose", the leaving temperature "could be the SAT or a separate sensor"
(§5.16.14.5), and Table 5.16.14.5 then sets eCCET = eMAT and eCCLT = eSAT for
the proxied case. This library binds the no-dedicated-sensor configuration —
`CCET := mat`, `CCLT := sat` — because that is the instrumentation most air
handlers actually have. The epsilons follow the binding: 3 °C for the mixed-air
sensor, 1 °C for the supply-air sensor, root-sum-square to 3.1623 °C.

**Whether the fan-heat term applies.** It does, because the supply fan sits
between MAT and SAT on the unit G36 assumes ("the SAT sensor is located
downstream of the supply fan"). The threshold is therefore 3.1623 + 1 = 4.1623,
and the arithmetic is worth following, because for a *drop* the fan works
against the signal. Fan heat and coil cooling move the air in opposite
directions, so `mat − sat` measures the true coil drop *minus* one dTSF; a
measured 4.1623 °C is a real coil drop of about 5.16 °C. Including the term
makes the shipped test doubly conservative rather than merely conservative,
which is the direction the addendum says its defaults are chosen for. Sites that
want the sharper test retune (see Deviations).

`dropBig` is a strict `>`, so a drop sitting exactly on 4.1623 °C reads healthy.
`persist` requires 30 continuous minutes, which is what separates a leaking
valve from a coil giving up the chilled water still standing in it after a state
change; recovery is immediate on the tick the drop falls back inside the
allowance.

## Possible Diagnoses

Transcribed from G36 §5.16.14 FC#14:

1. CCET sensor error
2. CCLT sensor error
3. Cooling coil valve stuck open or leaking
4. DX cooling stuck on

Under this library's binding, diagnoses 1 and 2 read as MAT sensor error and SAT
sensor error, and they are the cheap ones to eliminate first. Diagnosis 3 is the
one that dominates in the field and the reason the card carries the
[stuck actuator](../../../playbooks/stuck-actuator.md) playbook: a two-way valve
whose seat has eroded, or an actuator that has lost its close position, passes
water at a command of 0% and no command-based rule will ever see it. Diagnosis 4
is the DX equivalent — a stuck contactor or a compressor a local safety has
latched on.

## Energy Impact

CRITICAL_WASTE, HIGH confidence, DIRECT_MEASUREMENT, savings 0.5–5% of site
energy mapped to PNNL EEM-03 (leaking coil valves) — the §5.8.1 index row, which
is the only energy statement the reference makes about this fault.
DIRECT_MEASUREMENT is honest here in a way it is not for the abbreviated
comparison rules: the two temperatures the rule already reads *are* the
measurement, and `waste_kw = supply_airflow_m3s × 1.2 × 1.005 × ((mat − sat) +
dTSF)` converts them into thermal power with one substitution, design airflow
for measured airflow. HIGH confidence for the same reason — a sustained drop
across a coil that is commanded shut has no benign explanation other than a
sensor, and the sensor case shows up as a drop that does not move with load.

Climate sensitivity is heating-dominant, which is not where a cooling fault
would be expected to land. It follows the operating states: OS#1 is a heating
state, and the hours when a leaking chilled-water valve does the most damage are
the hours when a heating coil is fighting it. In OS#2 the same leak wastes only
plant energy the economizer had already made unnecessary.

## Emissions Impact

PROXY_EMISSIONS, scope `1+2`. The §5.8.1 index publishes no emissions column, so
both fields are the library's, assigned to match the physics the rule detects:
the unwanted cooling is purchased electricity at the chiller or the DX
compressor (Scope 2), and in OS#1 the heating that cancels it follows whatever
the plant burns — Scope 1 for gas, Scope 2 for electric resistance or a heat
pump. On an all-electric site the whole exchange collapses to Scope 2. When the
cause turns out to be a sensor there is nothing to attribute at all, which is
the same caveat the energy formula carries. Avoided-emissions basis: marginal
operating emissions rate (MOER) for the electric half, static combustion factor
for the fuel half.

## Deviations

- **The reference card is abbreviated; G36 is the normative text here.** The
  HVAC FDD Reference carries AHU-FC-014 only as a §5.8.1 index row — a name and
  an energy profile. No chapter 9 card, so no equation, no internal variables,
  no test vectors, no severity, no diagnosis list, no preconditions. The
  detection logic and the diagnosis list are transcribed from ASHRAE Guideline
  36 §5.16.14 FC#14 as it appears in Addendum u to Guideline 36-2018 (First
  Public Review, 2021). Where the two sources could conflict, G36 wins, because
  it is the only one that states the rule.
- **CCET and CCLT are bound to MAT and SAT.** G36 defines the fault on coil
  entering and leaving temperatures and explicitly leaves their instrumentation
  open (§5.16.14.5). This library ships the proxied binding, and Table 5.16.14.5
  supplies the matching epsilons (eCCET = eMAT = 3 °C, eCCLT = eSAT = 1 °C). The
  consequence is that the rule sees the whole air path between the mixing box
  and the supply sensor, not just the coil: the fan is inside the measurement
  (handled by the dTSF term) and so is any duct heat gain between the coil and
  the sensor (not handled — it biases the drop downward and makes the rule
  quieter still). A site with dedicated coil sensors rebinds the two boundary
  inputs at deployment — the CXF input connectors are named `mat` and `sat` per
  the library's point convention — and retunes `coil_drop_threshold` with its
  own sensor errors in place of eMAT and eSAT. Because the fan is then outside
  the sensor pair, that retune also drops the dTSF term.
- **The fan-heat term is included, and for this fault it works against the
  signal.** G36 footnotes ΔTSF as included "or not depending on location of
  sensors used", and with the fan between MAT and SAT the printed term applies.
  Follow the arithmetic: fan heat raises SAT, coil cooling lowers it, so
  `mat − sat` under-reports the true coil drop by one dTSF. A measured 4.1623 °C
  at the threshold is a true coil drop of 5.16 °C, where the sensor bands alone
  would justify reporting at 3.16 °C — the shipped default demands a leak 63%
  larger than the noise floor does. That is the false-alarm-biased direction the
  addendum says the NISTIR 7365 defaults are chosen for, and the cost is real
  misses: the
  `modest_drop_below_shipped_default` vector holds a genuine 4.5 °C coil drop
  that this rule never reports. Two worked retunes for sites that want the
  sharper test: dedicated sensors bracketing the coil with the fan outside the
  pair drop the term entirely (3.1623 with a 3 °C entering band, ≈1.41 with a
  matched ±1 °C pair); keeping the mat/sat binding but accepting G36's noise
  floor on the *true* drop rather than the measured one gives
  sqrt(10) − 1 = 2.1623.
- **G36's `≥` becomes a strict `>`.** CDL `Reals` has no `GreaterEqual` or
  `GreaterEqualThreshold`, so a drop of exactly 4.1623 °C reads healthy where
  G36 would report the fault. The disagreement has measure zero on a real
  temperature signal and errs toward silence. The vectors pin both sides
  (4.1623 °C clear, 4.2623 °C faulted). A host binding coarsely quantized
  temperatures — integer °C, or a BAS that rounds to 0.5 — should retune the
  threshold down rather than rely on the signal overshooting.
- **The threshold is a rounded constant, not a root-sum-square computed in the
  graph.** sqrt(3² + 1²) + 1 = 4.16227766…, shipped as 4.1623 — high by
  2.2 × 10⁻⁵ °C, four orders of magnitude below the resolution of the sensors
  feeding it. Composing the sum at authoring time rather than in blocks gives
  the host one number to retune through `set_param` at `dropBig.t` instead of
  three, the same rearrangement AHU-FC-005 and AHU-FC-012 make for their linear
  compositions.
- **Instantaneous samples instead of 5-minute rolling averages.** G36 computes
  every signal in §5.16.14 as a 5-minute rolling average with 1-minute sampling
  (`CCET_AVG`, `CCLT_AVG`); this library consumes instantaneous points and lets
  the 30-minute AlarmDelay stand in. The two are not equivalent, and the honesty
  note from AHU-FC-002 applies unchanged: averaging tolerates a signal whose
  mean sits outside the bound while it keeps crossing back, persistence does
  not — an oscillating drop resets the timer on every compliant tick and can
  hide indefinitely. The `oscillating_drop_never_alarms` vector demonstrates
  exactly that miss, and a short-cycling DX stage is a realistic way to produce
  it. A steady leak, which is what a failed valve seat produces, reads the same
  either way.
- **Operating states, ModeDelay, and the not-operating suspension are host-side
  preconditions.** G36 scopes FC#14 to OS#1-#2, suspends evaluation for
  ModeDelay (30 min) after a mode change in a served zone group, and suspends
  all fault evaluation while the AHU is not operating. None of it is in the
  graph: per the library's stance, operating-state applicability, transition
  windows, and NO_EVAL are host concerns declared in `preconditions`. A verdict
  produced outside OS#1-#2 or inside a transition window is NO_EVAL, never
  healthy. G36 attaches no "omit if no MAT sensor" qualifier to FC#14 — it
  contemplates dedicated coil sensors — but this library's binding needs MAT, so
  the qualifier applies to the shipped rule and lives in `preconditions` with
  the rest of the deployment decisions.
- **Severity 2 is the library's, not the reference's.** The §5.8.1 index carries
  no severity column and there is no chapter card to state one. Severity 2 puts
  this fault with AHU-FC-050 and AHU-FC-054 rather than with the 001-range
  comparison rules at 3, which is where CRITICAL_WASTE and HIGH confidence point:
  a coil conditioning air in a state that requires it to be off is simultaneous
  heating and cooling that no sequence asked for, and this pair is the only
  001-range entry the chapter README carries at 2. G36 §5.16.14 does say every
  reported fault condition "shall be a Level 3 alarm", but that is G36's
  alarm-priority scheme, not this library's 1-4 severity scale.
- **The energy profile is the index row's; the runtime formula, the climate
  sensitivity, and the emissions block are the library's.** `category`,
  `confidence`, `estimation_method`, and `savings_range` are copied from §5.8.1
  (CRITICAL_WASTE / HIGH / DIRECT / EEM 03 / 0.5–5% site). The reference stops
  there: the proxy formula, the heating-dominant climate call, and both
  `emissions` fields are this card's, reasoned from the operating states the
  fault is evaluated in.
- **No published test vectors.** The reference publishes none for this fault and
  G36 publishes none for any of them, so `vectors.json` is authored from the
  equation: both sides of the 4.1623 °C edge, a healthy inactive coil showing
  only fan heat, a leaking valve in heating, a sensor error with the plant off,
  the sub-threshold leak the conservative default misses, a transient shorter
  than AlarmDelay, a recovery, and the oscillation the persistence substitution
  is known to miss.
- `persist.delayOnInit = true` (Modelica/CDL default is `false`), the library's
  standing choice: a violation already present at load waits out the full 30
  minutes instead of alarming on the first tick after a controller restart.

## Notes

In OS#1 this rule overlaps AHU-FC-005, which tests the same two sensors in the
same direction — `mat − sat` — against eSAT + eMAT − dTSF = 3.0 °C. The narrower
threshold means AHU-FC-005 alarms first on any leak large enough to trip both,
so on a unit running both rules the OS#1 value of AHU-FC-014 is its diagnosis
list rather than its sensitivity: AHU-FC-005's list is dominated by heating-side
capacity failures, while this one names the cooling coil and the DX circuit
directly. Where the rule is alone is OS#2, which AHU-FC-005 does not cover and
where AHU-FC-012 tests the opposite sign.

The threshold asymmetry between those two rules is not a disagreement about
physics but about how sensor bands compose. AHU-FC-005 adds them linearly
(1 + 3 = 4 °C, worst case, both sensors wrong in the directions that hurt);
FC#14 adds them in quadrature (sqrt(1² + 3²) = 3.1623 °C, assuming the two
errors are independent). Quadrature is the sharper and better-justified
composition for independent sensors; the linear sum is the safer one. The
fan-heat term then moves in opposite directions for the two rules — subtracted
by AHU-FC-005, added here — which is what leaves this rule the quieter of the
two despite the tighter sensor bands.

Start at the sensors: a MAT reading high or a SAT reading low produces this trace
with nothing wrong in the mechanical room, and both are cheap to check against a
portable reference. If AHU-FC-062 is also active the host should already be
suppressing this rule, because MAT is standing in for the coil entering
temperature and FC-062 is its integrity gate. If the sensors check out, the
question is whether the chilled-water valve is passing: isolate the coil and
watch the drop disappear. The stuck-actuator playbook takes it from there — its
verification step strokes the actuator through its full range against feedback,
which is what separates a failed actuator from an eroded seat that no command
will close.
