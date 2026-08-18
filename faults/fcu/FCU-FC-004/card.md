---
schema: cxf-library/fault-card/v1
id: FCU-FC-004
name: Inactive cooling coil temperature drop (leak)
equipment: fcu
status: verified
phase: 1
method: rule
severity: 3
category: CRITICAL_WASTE
confidence: HIGH
estimation_method: DIRECT_MEASUREMENT
source:
  - "HVAC FDD Reference v1.0 §12, FCU-FC-004"
  - "G36 §5.22.6 FC#4 (the chapter's cited source; clause text not available — see Deviations)"
  - "G36 Addendum u, Table 5.16.14.5 (εRAT, εSAT, ΔTSF — the threshold composition) and §5.17.4.5 FC#3 (the RAT/SAT-proxied form of the same test)"
  - "PNNL EEM-03 (fix leaking valves)"
g36: "§5.22.6 FC#4"
clusters: []
suppresses: []
suppressed_by: []
related: [FCU-FC-005, FCU-FC-002]
playbooks: [fcu-faults]
operating_states: "OS#2 (no active coils) — host-gated"
preconditions: "The fan must be running. `rat` and `sat` are a coil entering and leaving temperature only while air is crossing the coil; on a cycling-fan FCU the discharge sensor sits in stagnant air over a coil full of chilled water between cycles and reads several degrees cold, which is this fault's exact signature and none of its meaning. The FCU point dictionary carries no fan status, fan command, or airflow point, so the host owns that gate entirely and cannot delegate it to the rule (`fan_off_standing_water_reads_as_a_leak` is the vector that pins the consequence). Suspend evaluation for a settling window after the cooling valve closes — a coil surrendering the chilled water standing in it shows the same drop for several minutes. The heating coil should also be off: a heating call warms the discharge and can only hide this fault, never fabricate it, so the masking is a miss rather than a false alarm, but a host that wants OS#2 as the reference scopes it should gate on `htg_vlv_cmd` too, which this rule does not read. Both sensors must be in the airstream and trustworthy: a `rat` bound to a wall-mounted space sensor, a discharge sensor in a plenum shared with another unit, or a cabinet drawing ducted outdoor air upstream of the coil all break the binding with no other symptom, and the outdoor-air case biases this rule toward false alarms in winter. Nothing in this rule cross-checks either sensor. When any gate is unmet the verdict is NO_EVAL, not healthy — as it is whenever the in-rule output yCmdOk reads false."
points:
  - clg_vlv_cmd
  - sat
  - rat
outputs:
  - name: yFault
    description: True while the valve has been commanded shut and sat has stayed more than inactive_coil_threshold below rat, continuously for at least alarm_delay
  - name: yCmdOk
    description: True while clg_vlv_cmd is below cmd_closed_threshold — the coil is commanded shut and the drop across it is therefore interpretable. False means the coil is allowed to be cooling and this rule has no verdict; the host reports NO_EVAL, not healthy
params:
  inactive_coil_threshold:
    default: 3.0
    unit: "°C"
    description: "Drop from entering to leaving air that stops being sensor error and starts being a leak. ADOPTED — the reference names the parameter in the equation and publishes no value for it (see Deviations). 3.0 °C is the rounded G36-style composition for FCU-grade instrumentation, sqrt(e_ret² + e_sup²) + dTSF, and it is deliberately the same number FCU-FC-005 ships because the reference names one parameter for both equations. Note the direction: on this cooling-side rule the fan's rise works against the measured drop, so the shipped value fires at about 4 °C of true coil work"
    cxf: dropBig.t
  cmd_closed_threshold:
    default: 1.0
    unit: "%"
    description: "Command below which the cooling valve counts as commanded shut. ADOPTED — the reference writes the test as clg_vlv_cmd = 0%, which is not a comparison a real-valued signal supports (see Deviations). 1.0% is deliberately tighter than AHU-FC-050's 5% open threshold: this rule needs the valve to be at rest, not merely nearly closed"
    cxf: vlvShut.t
  alarm_delay:
    default: 1800.0
    unit: s
    description: "Continuous violation required before the alarm asserts (30 min). ADOPTED — the reference publishes no tunables line for this card (see Deviations); the value is the AHU twin's G36 AlarmDelay"
    cxf: persist.delayTime
energy_impact:
  affected_subsystem: FCU cooling coil — parasitic cooling, and whatever warms the zone back up paying to undo it
  savings_range: "3-10% zone cooling energy from a leaking CHW valve (HVAC FDD Reference §12; PNNL EEM-03)"
  climate_sensitivity: heating-dominant
  runtime_estimation: "waste_kw = ((rat − sat) + dTSF) × fcu_airflow_m3s × 1.2 kg/m³ × 1.005 kJ/kg·K. The reference writes it as waste_kw = (entering_temp − leaving_temp) × fcu_airflow × cp_air; the air density and the addition of the fan's own rise are this card's. The fan sits between the two sensors and warms the air, so the measured drop is the coil's work *minus* the fan's — the mirror image of FCU-FC-005, where the same term is subtracted. At the shipped threshold that correction is a quarter of the answer. Design airflow stands in, since an FCU almost never has a flow station, and in the heating season the heating coil pays the same bill a second time to put the heat back"
emissions:
  scope: "2"
  method: DIRECT_EMISSIONS
verified:
  engine_rev: e2ff2f8
  content_id: "cxf:fnv1a128:40d3e69b8b4c5f2aa7e5f24c9981671b"
  date: 2026-08-17
---

## Description

A fan coil's chilled-water valve is a small two-way or three-way valve on a
small coil, and when its seat wears the leak is correspondingly small: a few
degrees of cooling on air the sequence believes is passing an inert coil. In the
heating season that is the expensive version of the fault. The heating coil
warms the air, the leaking cooling coil takes part of it back, the zone holds
setpoint, and the only evidence is a boiler and a chiller both working slightly
harder than the room requires. Nobody complains, so nobody looks.

This is why the fault is worth a rule rather than a walkthrough. Fan coils are
deployed by the dozen or the hundred, and one leaking seat wastes an amount too
small to see on a utility bill and too tedious to find by hand. The chapter puts
one leaking valve at 3–10% of the zone's cooling energy and 100–800 kg CO₂e a
year, mapped to PNNL EEM-03, and a hotel with a few bad seats on every floor is
where that becomes real money.

The rule is the temperature signature of the leak, gated on the command. It
reads the valve command, the return air, and the discharge air, and asks whether
air is losing heat while crossing a coil that was told to do nothing. Because it
reads temperatures rather than flows, it cannot separate a worn seat from an
actuator that never reaches its close position from a three-way bypass that is
not sealing. All three appear identically, and all three are on the diagnosis
list.

## Detection Logic

```
yCmdOk = clg_vlv_cmd < cmd_closed_threshold          (false ⇒ host reports NO_EVAL)
drop   = rat − sat

yFault = (drop > inactive_coil_threshold) AND yCmdOk,
         sustained continuously for alarm_delay
```

Block graph (`rule.cxf.jsonld`):

![FCU-FC-004 block graph](diagram.svg)

`drop` subtracts the leaving air from the entering air in the reference's own
order (`entering_temp − leaving_temp`), which is what makes the sign of this
rule the opposite of FCU-FC-005's, and `dropBig` compares it against the
allowance. `vlvShut` is the command half. Its output does two things: it feeds
`gate`, where the conjunction the reference writes is formed, and it leaves the
block as `yCmdOk`, so a host can tell the two ways this rule goes quiet apart. A
silent rule with `yCmdOk` true is a coil that is shut and behaving. A silent rule
with `yCmdOk` false is a coil that was asked to cool, about which this rule has
nothing to say — `valve_open_and_cooling_normally` is that vector, and its 10 °C
drop is the largest in the set.

The allowance is where the physics lives, and on this side of the pair the fan
is working for the coil rather than against it. With both valves shut, a healthy
unit reads `rat − sat` slightly *negative*: the fan puts its shaft work into the
air, so the discharge runs about a degree warm before any coil has done anything
(`healthy_unit_shows_fan_heat_only`). A leak has to overcome that rise before it
shows up at all, and then clear the sensor allowance on top of it. The
consequence is easy to miss and is stated again in Deviations: the shipped
3.0 °C is measured on `rat − sat`, so it takes roughly 4 °C of real coil work to
trip, where the same 3.0 °C on the heating-side twin trips at about 2 °C.
`drop_just_below_threshold` holds a genuine 4 °C coil drop that this rule never
reports.

`persist` requires 30 continuous minutes, which is what separates a leaking seat
from a coil giving up the chilled water standing in it after a call for cooling
ends (`transient_clears_before_alarm_delay`). Recovery has no such delay: on the
tick the drop falls back inside the allowance — or the tick the zone calls for
cooling and the valve opens — `yFault` drops and the accumulated time is
discarded. From a drop already present at load, `delayOnInit = true` puts the
alarm at exactly 1800 s; from an edge mid-run, at exactly 1800 s after that edge
(`leak_starts_mid_run` pins 2400 s).

## Possible Diagnoses

Transcribed from the reference's FCU-FC-004 card:

1. Cooling coil valve leaking through — the worn or eroded seat. The common
   case, and the one the playbook prices at $150–$600 to replace
2. Valve not fully closing (mechanical) — the actuator has lost its close
   position or is binding short of the seat. Cheaper to fix, and distinguishable
   on site by stroking the actuator against feedback
3. Three-way valve bypass not sealing — the port that is supposed to divert flow
   around the coil is passing some of it through instead. Nothing about the
   valve's travel looks wrong, which is why this one survives an actuator check

A fourth belongs in the operator's head even though the reference does not list
it: either sensor being wrong produces this trace with a perfectly good valve. A
return sensor reading high or a discharge sensor reading low is
indistinguishable here, and both are cheap to check against a portable
reference — which is why the AHU twin's source, G36 §5.16.14, puts the two
sensor errors ahead of the valve in its own diagnosis order.

## Energy Impact

CRITICAL_WASTE, HIGH confidence, DIRECT_MEASUREMENT, 3–10% of zone cooling
energy, mapped by the reference to PNNL EEM-03 (fix leaking valves).
DIRECT_MEASUREMENT is honest here in a way it is not for the chapter's
comparison rules: the two temperatures the rule already reads *are* the
measurement, and the runtime formula converts them to thermal power with one
substitution — design airflow for measured airflow, since an FCU has no flow
station. HIGH confidence because a sustained drop across a coil commanded shut
has no benign explanation other than a sensor or a stopped fan, and both of
those show up as a drop that never moves with load or season.

Heating-dominant, per the chapter, which reads oddly for a cooling fault until
the operating state is taken into account — and it is the same call AHU-FC-014
makes for the same reason. The hours in which a leaking chilled-water valve does
the most damage are the hours when a heating coil is fighting it, and those are
also the hours when the cooling valve is commanded shut for weeks at a time,
which is precisely the state `yCmdOk` requires. In deep cooling weather the same
leak hides behind legitimate calls for cooling and this rule is silent by
construction.

## Emissions Impact

Scope 2, DIRECT_EMISSIONS, HIGH confidence; typically 100–800 kg CO₂e/yr per unit
of parasitic cooling, on a marginal operating emissions rate (MOER) basis. The
unwanted cooling is purchased electricity at the chiller and the pumps, so the
cooling half of the exchange is Scope 2 on every site. The heating that cancels
it is not this card's to claim — it follows whatever the plant burns, Scope 1 for
a gas boiler and Scope 2 for electric resistance or a heat pump — and FCU-FC-005
carries that half for the mirror fault. When the cause turns out to be a sensor
or a stopped fan there is nothing to attribute at all, the same caveat the energy
formula carries.

## Deviations

- **`inactive_coil_threshold` is adopted, not transcribed.** The reference's
  equation names the parameter and its card publishes no tunables line at all —
  no value for the threshold, no alarm delay — unlike FCU-FC-001, which prints
  both of its. 3.0 °C is this library's, composed the way G36 composes the same
  fault on an air handler: root-sum-square of the two sensor errors plus a
  fan-heat term. The closest published form is Addendum u §5.17.4.5 FC#3, the
  inactive-coil test on a heating-only AHU, which is the one G36 equation that
  reads the coil through the *return* and supply sensors this card binds:
  `sqrt(εSAT² + εRAT²) + ΔTSF`. Its variables table puts εRAT and εSAT at 1 °C
  each and ΔTSF at 1 °C (0.5 °C on the single-zone unit), which gives
  sqrt(1² + 1²) + 1 = 2.41; with the ±1.4 °C-class sensors an FCU more typically
  carries it is sqrt(1.4² + 1.4²) + 1 = 2.98. 3.0 covers both compositions, and
  it is the value FCU-FC-005 ships — deliberately, because the reference names
  one `inactive_coil_threshold` for both equations. A site with matched ±0.5 °C
  sensors and a measured fan rise retunes down and finds leaks this default
  misses. One caveat on that citation: in the public-review text FC#3's operands
  read `RAT_AVG − SAT_AVG` under the description "temperature rise across
  inactive heating coil", which is a drop, not a rise — so only the right-hand
  side of that equation is borrowed here, and the sign of this card's test comes
  from the HVAC FDD Reference's own `entering_temp − leaving_temp`.
- **Fan heat is inside the measurement, and here it works against the signal.**
  Neither the chapter nor the `fcu-faults` playbook mentions fan heat; the term
  is carried in from G36's ΔTSF footnote via AHU-FC-014, because the physics does
  not care which document mentions it. Follow the arithmetic: the fan raises the
  discharge and the leaking coil lowers it, so `rat − sat` under-reports the true
  coil drop by one fan rise. A measured 3.0 °C is about 4 °C of real coil work,
  where the sensor bands alone would justify reporting at 2 °C. Sharing one
  threshold with FCU-FC-005 — which is what the reference asks for — therefore
  makes this rule roughly half as sensitive in coil terms as its heating-side
  twin, which trips at about 2 °C of coil rise. The asymmetry is real, not an
  authoring slip; a host that wants matched sensitivity should lower this rule's
  threshold by one fan-heat term rather than expect one number to serve both.
  `drop_just_below_threshold` is the vector that shows the cost: a genuine 4 °C
  coil drop, reported by nobody.
- **`clg_vlv_cmd = 0%` becomes `< 1.0%`.** The reference writes an equality
  against zero. A real-valued command cannot be tested for equality in CDL
  `Reals` — there is no such block, and equality on a float from a BAS would be
  the wrong test even if there were, since controllers write 0.0001% and
  round-tripped analog values land near but not on zero. `cmd_closed_threshold`
  is adopted at 1.0%, tighter than AHU-FC-050's 5% "open" threshold on the same
  point because the two rules want opposite things: AHU-FC-050 needs to know the
  valve is doing something, this rule needs to know it is doing nothing. Vectors
  pin all three sides (0.9% shut, exactly 1.0% not shut, 1.1% not shut). On a
  unit whose valve is a two-position solenoid rather than a modulating actuator
  the command is 0 or 100 and the test is exact.
- **`alarm_delay` is adopted at 30 minutes.** The reference publishes no delay
  for this card. FCU-FC-001's card prints AlarmDelay = 60 min, but that value
  belongs to a transition counter and has nothing to say about a coil. The
  adopted 1800 s is the AHU twin's G36 AlarmDelay for the identical fault, and it
  is doing identifiable work: it rides out the residual cold a just-closed coil
  gives up. A site whose FCU coils purge in five minutes can cut it and detect
  leaks sooner.
- **Strict comparisons at both boundaries.** CDL `Reals` has no `GreaterEqual` or
  `LessEqual`, so a drop sitting exactly on 3.0 °C is not a fault and a command
  sitting exactly on 1.0% is not shut. The reference writes `>` for the
  temperature test, so that side agrees with it; the command side is the adopted
  test above. Both disagreements have measure zero on real-valued signals and
  both err toward silence. The vectors pin every side: 2.9 / 3.0 / 3.1 °C and
  0.9 / 1.0 / 1.1%. A host binding coarsely quantized temperatures — integer °C,
  or a BAS rounding to 0.5 — should retune down rather than rely on the signal
  overshooting.
- **The G36 clause is the chapter's citation, carried forward unverified.** The
  reference sources this card to G36 §5.22.6 FC#4. That clause text was not
  available to this author — the library's G36 material is Addendum u to
  Guideline 36-2018 (First Public Review), which carries the AHU AFDD sections
  §5.16.14, §5.17.4, and §5.18.14 and no fan coil section — so everything in this
  card that claims to be transcribed comes from the HVAC FDD Reference's ch.12
  card, and the `g36` field is provenance the reference asserts rather than
  provenance this card verified. If §5.22.6 states averaging windows, epsilons,
  or an alarm delay, they will land here as corrections and the adopted values
  above are what they will correct.
- **`rat` and `sat` stand in for the coil entering and leaving temperatures.**
  That binding is the FCU point dictionary's, stated in its notes for exactly
  this pair, and it is what the chapter's `entering_temp` / `leaving_temp` mean
  on a unit with two temperature sensors. The cost is that the rule sees the
  whole air path rather than the coil: the fan is inside the measurement (handled
  by the threshold's fan-heat term) and so is any duct between the coil and the
  discharge sensor (not handled — on this fault duct gain biases the drop
  downward and makes the rule quieter). One configuration breaks the binding in
  the dangerous direction rather than the quiet one: a fan coil that draws
  outdoor air into its cabinet through a wall aperture upstream of the coil is
  presenting the coil with a mixture colder than the return air the sensor reads,
  so `rat − sat` shows a drop in winter with no leak at all — false alarms, in
  the season this rule is meant to work in. That configuration belongs in
  `preconditions` and is worth confirming before believing a fleet-wide result.
  FCU-FC-005 carries the same proxy with the sign reversed, where the same
  aperture produces misses instead.
- **The fan-running gate cannot be bound in v1.** The rule's most important
  precondition is that air is moving, and the FCU point dictionary carries no fan
  status, fan command, or airflow point to bind it to. So the gate lives in
  `preconditions` as host prose with nothing in the graph enforcing it, and a
  cycling-fan FCU evaluated between cycles is the realistic way to get a false
  alarm out of this rule — `fan_off_standing_water_reads_as_a_leak` pins that
  behaviour so it cannot change silently. Adding `fan_status` to the dictionary
  is the fix, and it is a dictionary change, not a rule change.
- **`yCmdOk` is the library's, not the reference's.** The reference writes the
  command test as a conjunct of the fault condition, and the graph computes
  exactly that. Exposing the conjunct as a boundary output adds no logic and
  changes no verdict; it lets the host distinguish "the coil is shut and quiet"
  from "the coil is cooling, ask me later", which are the same `yFault = false`
  and mean opposite things. Same stance and same wiring as FCU-FC-005's
  `yCmdOk`, RTU-FC-051's `yStageOk`, and AHU-FC-055's `yTempDeltaOk`.
- **Instantaneous samples instead of rolling averages.** G36's AHU set computes
  every signal as a 5-minute rolling average with 1-minute sampling; whether
  §5.22.6 does the same for FCUs is unknown here (see the clause-text deviation
  above). This library consumes instantaneous points and lets `alarm_delay` stand
  in. The two are not equivalent: averaging tolerates a signal whose mean sits
  outside the bound while it keeps crossing back, persistence does not.
  `oscillating_drop_never_alarms` pins that miss with a drop swinging between
  6 °C and −0.5 °C on a 20-minute period — a plausible trace for a leak modulated
  by riser pressure or by a valve hunting around its seat. A steady leak, which
  is what a worn seat produces, reads the same either way.
- **A leak is only visible between calls for cooling.** The rule is silent
  whenever the valve is open, so a cooling valve that leaks all summer is
  detected in autumn, and one on a unit that is in cooling continuously is never
  detected at all. `zone_calls_for_cooling_before_alarm` pins the behaviour: the
  drop never changes, the zone calls at t = 1200 s, and the accumulated time is
  discarded. This is inherent in the reference's equation, not a binding choice,
  and it is the structural reason the chapter calls the fault heating-dominant.
- **Operating state OS#2 is host-enforced, and only half of it is testable
  here.** The reference scopes this fault to OS#2 (no active coils). Per the
  library's design stance, operating-state applicability, transition windows, and
  NO_EVAL are host concerns declared in `preconditions`, never in the block
  graph. The graph's own command test covers the cooling half of "no active
  coils"; the heating half is not tested, and the direction of that gap is
  benign — an active heating coil raises `sat` and can only silence this rule,
  never trip it. So heating-demand masking costs detections, not credibility,
  which is why it stays a host precondition rather than becoming a fourth input.
- **The runtime formula is extended.** The chapter writes `waste_kw =
  (entering_temp − leaving_temp) × fcu_airflow × cp_air`. This card adds air
  density (the product needs mass flow, and an FCU airflow is quoted
  volumetrically) and adds the fan's rise back, because the measured drop is the
  coil's work reduced by it. At the shipped threshold that correction is a
  quarter of the answer, and it is the term FCU-FC-005 subtracts.
- **Severity 3 is the reference's, and it disagrees with the AHU twin.** The
  chapter's FCU-FC-004 card states severity 3 (warning) and the chapter README
  repeats it, so 3 is what this card carries. AHU-FC-014/015 — the same fault on
  a bigger machine — carry severity 2, assigned by this library because the AHU
  reference has no card to state one. The difference is defensible on scale (one
  FCU wastes less than one AHU) and it is recorded here rather than smoothed
  over, because a host ranking a mixed fleet by severity will see the same
  physics at two levels.
- **`clusters` is empty.** The chapter README calls FCU-FC-004/005 the
  zone-scale members of the simultaneous-conditioning family, but
  `clusters/clusters.json` lists only AHU rules under that cluster, and this card
  does not edit the cluster set to add itself. The relationship is carried by
  `related` and by the shared playbook.
- `persist.delayOnInit = true` (Modelica/CDL default is `false`), the library's
  standing choice: a leak already present when the controller restarts waits out
  the full 30 minutes instead of alarming on the first tick.
- **No published test vectors.** The reference publishes none for this card, so
  `vectors.json` is authored from the equation: the healthy fan-heat pin, three
  sides of the temperature boundary, three sides of the command boundary, the
  normal-cooling case, the motivating leak, a mid-run onset, a transient, a
  recovery through each term, the stopped-fan hole, and the oscillation the
  persistence substitution is known to miss.

## Notes

Read `yCmdOk` before reading `yFault`. On a unit in cooling season it will be
false most of the day, and every `yFault = false` under it means "not
evaluated", not "no leak".

This card is one half of a pair the reference states symmetrically, and the
asymmetries are the parts worth holding in mind. The sign of the subtraction is
reversed (`rat − sat` here, `sat − rat` in FCU-FC-005). Fan heat pushes the two
measurements in opposite directions, so the shared 3.0 °C threshold is not a
shared sensitivity — this rule needs about twice as much coil work to trip. The
emissions scope differs because the plants differ. Everything else — the command
test, the threshold value, the alarm delay, the strict comparisons, the `yCmdOk`
gate — is identical in both, because nothing in the chapter distinguishes them.

The [fcu-faults](../../../playbooks/fcu-faults.md) playbook orders the service.
Its step 1.3 is the manual version of this rule — command the valve to 0% and
measure across the coil, where *any* measurable change confirms the leak. That
is a sharper test than this rule ships, and deliberately so: a technician
standing at the unit knows the fan is running and can put a calibrated probe on
both sides of the coil, while this rule is reading two building sensors through
a fan and has to leave room for both. Step 2.3 is the remote workaround worth
knowing: lock the cooling valve out for the heating season, which stops the
waste while the unit waits for parts. Step 3.4 is the triage order for a fleet —
rank by `|temp_change| × airflow × cp_air`, which is this card's runtime
estimator, and replace the worst seats first.

Expect FCU-FC-002 on the same unit in heating weather. A coil quietly removing
heat is a coil the heating side has to overcome, and the first symptom a
zone-level rule sees is a discharge that will not come up with the heating valve
wide open. If both are active, this one is the cause and that one is the
consequence.
