---
schema: cxf-library/fault-card/v1
id: FCU-FC-005
name: Inactive heating coil temperature rise (leak)
equipment: fcu
status: verified
phase: 1
method: rule
severity: 3
category: CRITICAL_WASTE
confidence: HIGH
estimation_method: DIRECT_MEASUREMENT
source:
  - "HVAC FDD Reference v1.0 §12, FCU-FC-005"
  - "G36 §5.22.6 FC#5 (the chapter's cited source; clause text not available — see Deviations)"
  - "PNNL EEM-03 (fix leaking valves)"
g36: "§5.22.6 FC#5"
clusters: []
suppresses: []
suppressed_by: []
related: [FCU-FC-004, FCU-FC-003]
playbooks: [fcu-faults]
operating_states: "OS#2 (no active coils) — host-gated"
preconditions: "The fan must be running. sat is only a coil leaving temperature while air is moving over the coil; on a cycling-fan FCU the discharge sensor sits in stagnant duct air between cycles and reads whatever the coil above it is doing, which is this fault's exact signature and none of its meaning. The FCU point dictionary carries no fan status or fan command, so the host owns this gate entirely and cannot delegate it to the rule (see Deviations). Suspend evaluation for a settling window after the heating valve closes — a coil giving up the hot water standing in it shows the same rise for several minutes, and alarm_delay is sized to ride out the usual case rather than to replace the gate. rat and sat must both be trustworthy and must both be in the airstream: this binding uses them as the coil entering and leaving temperatures, so a return sensor mounted on the wall as a space sensor, or a discharge sensor in a supply plenum shared with another unit, breaks the premise with no other symptom. Nothing in this rule cross-checks either sensor. When any gate is unmet the verdict is NO_EVAL, not healthy — as it is whenever the in-rule output yCmdOk reads false."
points:
  - htg_vlv_cmd
  - sat
  - rat
outputs:
  - name: yFault
    description: True while the valve has been commanded shut and sat has stayed more than inactive_coil_threshold above rat, continuously for at least alarm_delay
  - name: yCmdOk
    description: True while htg_vlv_cmd is below cmd_closed_threshold — the coil is commanded shut and the rise across it is therefore interpretable. False means the coil is allowed to be heating and this rule has no verdict; the host reports NO_EVAL, not healthy
params:
  inactive_coil_threshold:
    default: 3.0
    unit: "°C"
    description: "Rise from entering to leaving air that stops being fan heat and sensor error and starts being a leak. ADOPTED — the reference names the parameter in the equation and publishes no value for it (see Deviations). 3.0 °C is the rounded G36-style composition for FCU-grade instrumentation: sqrt(e_ret² + e_sup²) + dTSF with a ±1.4 °C-class sensor pair and 1 °C of fan heat. Because the fan sits inside the measurement, the shipped value fires at about 2 °C of true coil rise; a site that measures its own fan rise substitutes it in the sum directly"
    cxf: riseBig.t
  cmd_closed_threshold:
    default: 1.0
    unit: "%"
    description: "Command below which the heating valve counts as commanded shut. ADOPTED — the reference writes the test as htg_vlv_cmd = 0%, which is not a comparison a real-valued signal supports (see Deviations). 1.0% is deliberately tighter than AHU-FC-050's 5% open threshold: this rule needs the valve to be at rest, not merely nearly closed"
    cxf: vlvShut.t
  alarm_delay:
    default: 1800.0
    unit: s
    description: "Continuous violation required before the alarm asserts (30 min). ADOPTED — the reference publishes no tunables line for this card (see Deviations); the value is the AHU twin's G36 AlarmDelay"
    cxf: persist.delayTime
energy_impact:
  affected_subsystem: FCU heating coil — parasitic heating, and whatever cools the zone back down paying to undo it
  savings_range: "3-10% zone heating energy from a leaking HW valve (HVAC FDD Reference §12)"
  climate_sensitivity: cooling-dominant
  runtime_estimation: "waste_kw = ((sat − rat) − dTSF) × fcu_airflow_m3s × 1.2 kg/m³ × 1.005 kJ/kg·K. The reference writes it as waste_kw = (leaving_temp − entering_temp) × fcu_airflow × cp_air; the air density and the subtraction of the fan's own rise are this card's, because the fan sits between the two sensors and none of its heat is the coil's doing. At the threshold the fan is 1.0 of a 3.0 °C measured rise, so crediting it to the coil would overstate the waste by half. Design airflow stands in — an FCU almost never has a measurement station — and in the cooling season the zone's cooling pays the same bill a second time"
emissions:
  scope: "1"
  method: DIRECT_EMISSIONS
verified:
  engine_rev: e2ff2f8
  content_id: "cxf:fnv1a128:77f1afc9046249364d915e9e86936853"
  date: 2026-08-17
---

## Description

A fan coil unit's heating valve is a small two-way valve on a small coil, and
when its seat wears the leak is correspondingly small: a few degrees of rise
across a coil that the sequence believes is shut. Nothing about the unit looks
broken. The fan runs, the valve reports 0%, the zone holds setpoint — because
the cooling coil, or the neighbouring units, or the central plant, quietly take
the extra heat back out. Nobody complains, so nobody looks.

That is why this fault is worth a rule rather than a walkthrough. FCUs are
deployed by the dozen or the hundred in hotels, apartments, and perimeter
offices, each one wasting an amount too small to notice on a utility bill and
too tedious to find by hand. The chapter puts one leaking valve at 3–10% of the
zone's heating energy and 100–800 kg CO₂e a year; a hotel with two hundred rooms
and a handful of bad seats on every floor is where that becomes real money.

The rule is the temperature signature of the leak, gated on the command. It
reads the valve command, the return air, and the discharge air, and asks whether
air is picking up heat while crossing a coil that was told to do nothing.
Because it reads temperatures rather than flows, it cannot separate a worn valve
seat, a valve that never quite closes, and hot water thermosiphoning through a
vertically piped coil with the valve shut and blameless. All three appear
identically, and all three are on the diagnosis list.

## Detection Logic

```
yCmdOk = htg_vlv_cmd < cmd_closed_threshold   (false ⇒ host reports NO_EVAL)
rise   = sat − rat

yFault = (rise > inactive_coil_threshold) AND yCmdOk,
         sustained continuously for alarm_delay
```

Block graph (`rule.cxf.jsonld`):

![FCU-FC-005 block graph](diagram.svg)

`rise` subtracts the entering air from the leaving air in the reference's own
order (`leaving_temp − entering_temp`), which is what makes the sign of this
rule the opposite of FCU-FC-004's, and `riseBig` compares it against the
allowance. `vlvShut` is the command half. Its output does two things: it feeds
`gate`, where the conjunction the reference writes is formed, and it leaves the
block as `yCmdOk`, so a host can tell the two ways this rule goes quiet apart. A
silent rule with `yCmdOk` true is a coil that is shut and behaving. A silent
rule with `yCmdOk` false is a coil that is being asked to heat, about which this
rule has nothing to say at all — `valve_open_and_heating_normally` is that
vector, and its 13 °C rise is the largest in the set.

The allowance is where the physics lives. On a healthy FCU with both valves
shut, `sat − rat` is not zero: the fan sits in the airstream between the two
sensors and puts its shaft work into the air, so the discharge runs about a
degree warm before any coil has done anything. Add a pair of zone-grade
temperature sensors that are each allowed to be off by more than a degree, and a
healthy unit can read a rise of nearly 3 °C with both valves shut, which is what
the allowance has to cover. `healthy_unit_shows_fan_heat_only` pins the case
clear. The consequence is easy to miss: with the fan inside the measurement, the
shipped 3.0 °C fires when the coil's own contribution passes roughly 2 °C, and a
bigger fan raises the floor it has to clear. Sites that measure their fan rise
should put their number in the sum.

`persist` requires 30 continuous minutes, which is what separates a leaking seat
from a coil surrendering the hot water standing in it after a call for heat ends
(`transient_clears_before_alarm_delay`). Recovery has no such delay: on the tick
the rise falls back inside the allowance — or the tick the zone calls for heat
and the valve opens — `yFault` drops and the accumulated time is discarded. From
a rise already present at load, `delayOnInit = true` puts the alarm at exactly
1800 s; from an edge mid-run, at exactly 1800 s after that edge
(`leak_starts_mid_run` pins 2400 s).

## Possible Diagnoses

Transcribed from the reference's FCU-FC-005 card:

1. Heating coil valve leaking through — the worn or eroded seat. The common
   case, and the one the playbook prices at $150–$600 to replace
2. Valve not fully closing (mechanical) — the actuator has lost its close
   position or is binding short of the seat. Cheaper to fix, and distinguishable
   on site by stroking the actuator against feedback
3. Gravity circulation through the coil — hot water thermosiphoning up through a
   vertically piped coil with the valve genuinely shut. Nothing is broken, and
   replacing the valve fixes nothing; the fix is a check valve or a piping
   change. The `fcu-faults` playbook flags this specifically for multi-story
   buildings, and `gravity_circulation_overnight` is the vector for it

A fourth belongs in the operator's head even though the reference does not list
it: either sensor being wrong produces this trace with a perfectly good valve. A
return sensor reading low or a discharge sensor reading high is
indistinguishable here, and both are cheap to check against a portable
reference. That is why the AHU twin's source, G36 §5.16.14, puts the two sensor
errors ahead of the valve in its own diagnosis order.

## Energy Impact

CRITICAL_WASTE, HIGH confidence, DIRECT_MEASUREMENT, 3–10% of zone heating
energy, mapped by the reference to PNNL EEM-03 (fix leaking valves).
DIRECT_MEASUREMENT is honest here in a way it is not for the chapter's
comparison rules: the two temperatures the rule already reads *are* the
measurement, and the runtime formula converts them to thermal power with one
substitution — design airflow for measured airflow, since an FCU has no flow
station. HIGH confidence because a sustained rise across a coil commanded shut
has no benign explanation other than a sensor, and the sensor case shows up as a
rise that never moves with load or season.

Cooling-dominant, per the chapter, and the reason is worth stating because it
also explains when this rule can see anything. Heat leaking into a zone during
the cooling season is paid for twice — once at the boiler and once at whatever
removes it — and it is also the season in which the heating valve is commanded
shut for weeks at a time, which is precisely the state `yCmdOk` requires. In
deep heating weather the same leak hides behind legitimate calls for heat and
this rule is silent by construction.

## Emissions Impact

Scope 1, DIRECT_EMISSIONS, HIGH confidence; typically 100–800 kg CO₂e/yr per
unit of parasitic heating, on a marginal operating emissions rate (MOER) basis.
Scope 1 is the reference's assignment and it assumes a fuel-fired hot water
plant. On a site whose hot water comes from an electric boiler or a heat pump
the same leaked heat is Scope 2, and the cooling that removes it again is
Scope 2 either way, so an all-electric building reads the whole exchange as
Scope 2.
When the cause turns out to be a sensor there is nothing to attribute at all,
the same caveat the energy formula carries.

## Deviations

- **`inactive_coil_threshold` is adopted, not transcribed.** The reference's
  equation names the parameter and its card publishes no tunables line at all —
  no value for the threshold, no alarm delay — unlike FCU-FC-001, which prints
  both of its. 3.0 °C is this library's, and the composition behind it is the
  one G36 §5.16.14 uses for the same fault on an air handler: root-sum-square of
  the two sensor errors plus a fan-heat term. With the ±1.4 °C-class sensors an
  FCU typically carries and 1 °C of fan rise, that sum is
  sqrt(1.4² + 1.4²) + 1 = 2.98, rounded to 3.0.
  The AHU twin (AHU-FC-015) ships 4.1623 for the same
  composition because it is forced to read the coil through a mixed-air sensor
  G36 allows to be off by 3 °C; an FCU's return sensor is a better instrument
  than that, so the FCU threshold is legitimately tighter. Retunes: a site with
  matched ±0.5 °C sensors and a measured 0.4 °C fan rise gets
  sqrt(0.5² + 0.5²) + 0.4 ≈ 1.1, and will find leaks this card's default misses.
- **Fan heat is inside the measurement, and it is where this pair stops being
  symmetric.** Neither the chapter nor the `fcu-faults` playbook mentions fan
  heat; the term is carried in from G36's ΔTSF footnote via AHU-FC-015, because
  the physics does not care which document mentions it. The direction is what
  matters: on this heating-side rule the measured rise is the true coil rise
  *plus* the fan's, so the shipped 3.0 °C trips at about 2 °C of coil rise. On
  the cooling-side twin the fan's rise *hides* part of the drop, so the same
  threshold needs about 4 °C of true coil work. Sharing one number — which the
  reference asks for, naming a single `inactive_coil_threshold` in both
  equations — therefore makes the heating rule roughly twice as sensitive as the
  cooling rule in coil terms. That asymmetry is real, not an authoring slip, and
  a host that wants matched sensitivity should raise this rule's threshold or
  lower FCU-FC-004's by one fan-heat term rather than expecting one number to
  serve both.
- **`htg_vlv_cmd = 0%` becomes `< 1.0%`.** The reference writes an equality
  against zero. A real-valued command cannot be tested for equality in CDL
  `Reals` — there is no such block, and equality on a float from a BAS would be
  the wrong test even if there were, since controllers write 0.0001% and
  round-tripped analog values land near but not on zero. `cmd_closed_threshold`
  is adopted at 1.0%, tighter than AHU-FC-050's 5% "open" threshold on the same
  point because the two rules want opposite things: AHU-FC-050 needs to know the
  valve is doing something, this rule needs to know it is doing nothing. Vectors
  pin all three sides (0.9% shut, exactly 1.0% not shut, 1.1% not shut).
- **`alarm_delay` is adopted at 30 minutes.** The reference publishes no delay
  for this card. FCU-FC-001's card prints AlarmDelay = 60 min, but that value
  belongs to a transition counter and has nothing to say about a coil. The
  adopted 1800 s is the AHU twin's G36 AlarmDelay for the identical fault, and
  it is doing identifiable work: it rides out the residual heat a just-closed
  coil gives up. A site whose FCU coils are small enough to purge in five
  minutes can cut it and detect leaks sooner.
- **Strict comparisons at both boundaries.** CDL `Reals` has no `GreaterEqual`
  or `LessEqual`, so a rise sitting exactly on 3.0 °C is not a fault and a
  command sitting exactly on 1.0% is not shut. The reference writes `>` for the
  temperature test, so that side agrees with it; the command side is the adopted
  test above. Both disagreements have measure zero on real-valued signals and
  both err toward silence. The vectors pin every side: 2.9 / 3.0 / 3.1 °C and
  0.9 / 1.0 / 1.1%. A host binding coarsely quantized temperatures — integer °C,
  or a BAS rounding to 0.5 — should retune down rather than rely on the signal
  overshooting.
- **The G36 clause is the chapter's citation, carried forward unverified.** The
  reference sources this card to G36 §5.22.6 FC#5. That clause text was not
  available to this author — the library's G36 material covers §5.16.14 (the AHU
  set) and not the FCU set — so everything in this card that claims to be
  transcribed comes from the HVAC FDD Reference's ch.12 card, and the `g36`
  field is provenance the reference asserts rather than provenance this card
  verified. If §5.22.6 states averaging windows, epsilons, or an alarm delay,
  they will land in this card as corrections and the adopted values above are
  what they will correct.
- **rat and sat stand in for the coil entering and leaving temperatures.** That
  binding is the FCU point dictionary's, stated in its notes for exactly this
  pair, and it is what the chapter's `entering_temp` / `leaving_temp` mean on a
  unit with two temperature sensors. The cost is that the rule sees the whole
  air path, not just the coil: the fan is inside the measurement (handled by the
  threshold's fan-heat term) and so is any duct between the coil and the
  discharge sensor (not handled — on this fault it biases the rise upward and
  makes the rule slightly louder). Two site configurations break the binding
  outright rather than degrading it: a `rat` bound to a wall-mounted space
  sensor rather than the return airstream, and a four-pipe unit taking ducted
  outdoor air upstream of the coils. Both belong in `preconditions`, and both
  are worth checking before believing a fleet-wide result.
- **The fan-running gate cannot be bound in v1.** The rule's most important
  precondition is that air is moving, and the FCU point dictionary carries no
  fan status, fan command, or airflow point to bind it to. So the gate lives in
  `preconditions` as host prose with nothing in the graph enforcing it, and a
  cycling-fan FCU evaluated between cycles is the realistic way to get a false
  alarm out of this rule. This is the one place where the card would rather have
  a fourth input than a paragraph; adding `fan_status` to the dictionary is the
  fix, and it is a dictionary change, not a rule change.
- **`yCmdOk` is the library's, not the reference's.** The reference writes the
  command test as a conjunct of the fault condition, and the graph computes
  exactly that. Exposing the conjunct as a boundary output adds no logic and
  changes no verdict; it lets the host distinguish "the coil is shut and quiet"
  from "the coil is heating, ask me later", which are the same `yFault = false`
  and mean opposite things. Same stance and same wiring as RTU-FC-051's
  `yStageOk` and AHU-FC-055's `yTempDeltaOk`.
- **Instantaneous samples instead of rolling averages.** G36's AHU set computes
  every signal as a 5-minute rolling average with 1-minute sampling; whether
  §5.22.6 does the same for FCUs is unknown here (see the clause-text deviation
  above). This library consumes instantaneous points and lets `alarm_delay`
  stand in. The two are not equivalent: averaging tolerates a signal whose mean
  sits outside the bound while it keeps crossing back, persistence does not.
  `oscillating_rise_never_alarms` pins that miss with a rise swinging between
  6 °C and 1 °C on a 20-minute period — a plausible trace for a valve hunting
  around its seat. A steady leak, which is what a worn seat produces, reads the
  same either way.
- **A leak is only visible between calls for heat.** The rule is silent whenever
  the valve is open, so a heating valve that leaks all winter is detected in
  spring, and one on a unit that is in heating continuously is never detected at
  all. `zone_calls_for_heat_before_alarm` pins the behaviour: the rise never
  changes, the zone calls at t = 1200 s, and the accumulated time is discarded.
  This is inherent in the reference's equation, not a binding choice, and it is
  the structural reason the chapter calls the fault cooling-dominant.
- **Severity 3 is the reference's, and it disagrees with the AHU twin.** The
  chapter's FCU-FC-005 card states severity 3 (warning) and the chapter README
  repeats it, so 3 is what this card carries. AHU-FC-014/015 — the same fault on
  a bigger machine — carry severity 2, assigned by this library because the AHU
  reference has no card to state one. The difference is defensible on scale (one
  FCU wastes less than one AHU) and it is recorded here rather than smoothed
  over, because a host ranking a mixed fleet by severity will see the same
  physics at two levels.
- **Operating state OS#2 is host-enforced.** The reference scopes this fault to
  OS#2 (no active coils). Per the library's design stance, operating-state
  applicability, transition windows, and NO_EVAL are host concerns declared in
  `preconditions`, never in the block graph. The graph's own command test covers
  the heating half of "no active coils"; the cooling half is not tested and does
  not need to be, since an active cooling coil drives `sat` below `rat` and can
  only silence this rule, never trip it.
- **The runtime formula is extended.** The chapter writes `waste_kw =
  (leaving_temp − entering_temp) × fcu_airflow × cp_air`. This card adds air
  density (the product needs mass flow, and an FCU airflow is quoted
  volumetrically) and subtracts the fan's rise, which is in the measured
  difference and is none of the coil's doing. At the threshold that subtraction
  is a third of the answer.
- **`clusters` is empty.** The chapter README calls FCU-FC-004/005 the
  zone-scale members of the simultaneous-conditioning family, but
  `clusters/clusters.json` lists only AHU rules under CLU-01, and this card does
  not edit the cluster set to add itself. The relationship is carried by
  `related` and by the shared playbook.
- `persist.delayOnInit = true` (Modelica/CDL default is `false`), the library's
  standing choice: a leak already present when the controller restarts waits out
  the full 30 minutes instead of alarming on the first tick.
- **No published test vectors.** The reference publishes none for this card, so
  `vectors.json` is authored from the equation: the healthy fan-heat pin, three
  sides of the temperature boundary, three sides of the command boundary, the
  normal-heating case, a gravity-circulation leak, a mid-run onset, a transient,
  a recovery through each term, and the oscillation the persistence substitution
  is known to miss.

## Notes

Read `yCmdOk` before reading `yFault`. On a unit in heating season it will be
false most of the day, and every `yFault = false` under it means "not
evaluated", not "no leak".

This card is one half of a pair the reference states symmetrically, and the
places where the pair is *not* symmetric are the ones worth carrying into
FCU-FC-004: the sign of the subtraction (`sat − rat` here, `rat − sat` there),
the direction fan heat pushes the measurement (into this rule's threshold,
against that one's), and the emissions scope (Scope 1 here for a fuel-fired
plant, Scope 2 there for the chiller). The command test, the threshold value,
the alarm delay, the strict comparisons, and the `yCmdOk` gate should be
identical in both, because nothing in the chapter distinguishes them.

The [fcu-faults](../../../playbooks/fcu-faults.md) playbook orders the service.
Its step 1.3 is the manual version of this rule — command the valve to 0% and
measure across the coil, where *any* measurable change confirms the leak — and
it is also where the gravity-circulation check lives, which is the one diagnosis
on the list that a new valve will not fix. Step 2.3 is the remote workaround
worth knowing: lock the heating valve out for the season. That eliminates the
waste while the unit waits for parts, and on a fleet where this rule is firing
on a dozen units at once it is the difference between a summer of parasitic
heating and none. Step 3.4 is the triage order for that fleet — rank by
`|temp_change| × airflow × cp_air`, which is this card's runtime estimator, and
replace the worst seats first.

Expect FCU-FC-003 on the same unit in cooling weather: a coil quietly adding
heat is a coil the cooling side has to overcome, and the first symptom a
zone-level rule sees is a discharge that will not come down with the cooling
valve wide open. If both are active, this one is the cause and that one is the
consequence.
