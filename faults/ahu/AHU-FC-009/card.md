---
schema: cxf-library/fault-card/v1
id: AHU-FC-009
name: OAT too high for free cooling
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
  - "G36 §5.16.14 FC#9 (text per Addendum u public review)"
  - "NISTIR 7365 (defaults provenance)"
g36: "§5.16.14 FC#9"
clusters: [CLU-03]
suppresses: []
suppressed_by: []
related: [AHU-FC-051, AHU-FC-011]
playbooks: [economizer-failure]
operating_states: "OS#2 (free cooling, modulating OA) — host-gated"
preconditions: "Evaluate only in G36 OS#2, which Table 5.16.14.2 defines by actuator signature: heating coil = 0, cooling coil = 0, minimum OA position < OA damper < 100%. Per §5.16.14.11 the host suspends evaluation while the AHU is not operating and for ModeDelay (30 min) after a mode change in any zone group the AHU serves; per §5.16.14.12 fault conditions not applicable to the current OS are not evaluated at all. Verdicts outside OS#2, and verdicts inside a transition window, are NO_EVAL — never healthy. `sat_sp` must be the setpoint the economizer is controlling to (G36's SATsp for heating-coil and economizer control), not the cooling-coil setpoint SATsp-C. The 1.0 °C default threshold assumes a local OAT sensor at the unit; a site on a global OAT sensor must retune it before trusting the verdict."
points:
  - oat
  - sat_sp
outputs:
  - name: yFault
    description: True while outdoor air has stayed more than oat_excess_threshold above the supply air setpoint continuously for at least alarm_delay
params:
  oat_excess_threshold:
    default: 1.0
    unit: "°C"
    description: "Amount by which oat may exceed sat_sp before free cooling counts as unable to reach setpoint. The default composes the G36 §5.16.14 internal variables as eOAT + eSAT − dTSF = 1 + 1 − 1 = 1.0 °C, using the local-sensor eOAT. Retuning any one term means recomputing the sum: a global OAT sensor (eOAT = 3 °C) gives 3.0 °C; a measured 2 °C fan rise gives 0.0 °C."
    cxf: gapBig.t
  alarm_delay:
    default: 1800.0
    unit: s
    description: Continuous fault persistence required before the alarm asserts (G36 AlarmDelay, 30 min)
    cxf: persist.delayTime
energy_impact:
  affected_subsystem: AHU economizer changeover — free cooling asked to do work it cannot do
  savings_range: "Sensor-dependent (reference §5.8.1 row, EEM 06); the loss is cooling capacity unavailable until the unit changes over to OS#3"
  climate_sensitivity: cooling-dominant
  runtime_estimation: "none — the rule sees two temperatures and no airflow, so no waste term is computable from its inputs"
emissions:
  scope: "2"
  method: QUALITATIVE_EMISSIONS
verified:
  engine_rev: e2ff2f8
  content_id: "cxf:fnv1a128:cc6083da19e505bdcd1e46dd56352962"
  date: 2026-08-17
---

## Description

The unit is running as a modulating economizer while outdoor air is too warm to
reach the supply setpoint. In OS#2 both coils are shut and outdoor air is the
only cooling in the machine; it enters at OAT and picks up roughly 1 °C
crossing the supply fan. Once OAT is above `SATSP − dTSF`, no damper position
gets the supply air down to setpoint — 100% outdoor air still lands above it.
The unit belongs in OS#3, with mechanical cooling on top of a fully open
damper.

The fault names a changeover that did not happen. The economizer's high-limit
logic should have handed off to mechanical cooling and did not, or the OAT the
logic reads is not the OAT the unit is breathing, or something is quietly
supplying cooling that lets the unit stay in OS#2 while the SAT loop looks
satisfied. Within CLU-03 (Economizer Failure) this is the mirror image of
the trigger AHU-FC-051: FC-051 catches an economizer that will not open when
outdoor air is useful, this one catches an economizer still open when outdoor
air stopped being useful.

## Detection Logic

```
G36 §5.16.14 FC#9, applies to OS#2:

    OAT_AVG − eOAT > SATSP − dTSF + eSAT

rearranged to gap form:

    oat − sat_sp > eOAT + eSAT − dTSF = 1 + 1 − 1 = 1.0 °C

yFault = (oat − sat_sp > oat_excess_threshold), sustained for alarm_delay
```

Block graph (`rule.cxf.jsonld`):

![AHU-FC-009 block graph](diagram.svg)

Three blocks: `gap` subtracts the setpoint from outdoor air, `gapBig` compares
that difference against the composed threshold, and `persist` requires the
condition to hold for 30 minutes. Everything G36 spreads across both sides of
the inequality — the two sensor error bands and the fan-heat correction —
collapses into the single positive number `gapBig.t`, so a host retunes one
parameter rather than reasoning about which side of the comparison each term
lives on.

The gap is signed, and its sign is the physics: negative means outdoor air is
below setpoint and free cooling has headroom, positive means it is above and
the damper is out of moves. The threshold sets how far past zero the gap must
go before sensor error stops being a plausible explanation.

Recovery is immediate — the alarm drops on the tick the gap falls back under
the threshold — while assertion waits the full delay. Either input can open the
gap: a supply setpoint reset walking down toward a colder target crosses the
same line that a warming afternoon does, and the vectors cover both.

## Possible Diagnoses

Per G36 §5.16.14 Table 5.16.14.8, FC#9:

1. SAT sensor error. The SAT loop is chasing a reading that is not the supply
   air, so it holds the unit in economizer mode at a setpoint outdoor air
   cannot deliver.
2. OAT sensor error. A sensor reading low keeps the changeover logic convinced
   free cooling is still viable. Cheapest of the three to rule out, which is why
   the playbook checks it first.
3. Cooling coil valve leaking or stuck open. In OS#2 the cooling valve is
   commanded to 0, so leak-through is invisible to the command — but it is
   real cooling, and it can hold SAT near setpoint while outdoor air alone
   never could. The unit has no reason to change over because, as far as the
   SAT loop can tell, nothing is wrong.

## Energy Impact

COMFORT_ENERGY, LOW confidence, QUALITATIVE_ONLY — the reference's §5.8.1
index row for this fault, which also maps it to PNNL EEM-06 (OA damper
faults). The immediate symptom is lost
cooling capacity: the unit cannot make setpoint, zones drift warm, and the VAV
boxes below open up chasing supply air that never gets cold enough. There is no
waste term computable from `oat` and `sat_sp` alone — no airflow, no coil
state, no counterfactual for what the correct mode would have consumed — so
nothing is estimated. The secondary energy cost depends on the diagnosis: a
leaking cooling valve (diagnosis 3) is running a chiller against a coil nobody
commanded, while a delayed changeover mostly costs comfort until mechanical
cooling engages. Cooling-dominant by construction, since the fault can only
occur in an operating state that exists to make cold air.

## Emissions Impact

QUALITATIVE_EMISSIONS, LOW confidence, Scope 2. Every path out of this fault
runs on purchased electricity — chiller or DX capacity that engages late, fan
energy spent moving air that is not cold enough, and in the leaking-valve case
compressor work nobody asked for. No on-site combustion is involved: OS#2 has
the heating coil commanded shut, and a heating valve leaking in this state
would show up as FC#15 (temperature rise across an inactive heating coil), not
here. Avoided-emissions basis: N/A — no quantity is estimated.

## Deviations

- **The reference card is an index row, so this card is built from G36.** The
  HVAC FDD Reference abbreviates AHU-FC-009: §5.8.1 gives the code and the name
  and nothing else — no equation, no test vectors, no severity, no energy or
  emissions profile. The normative content here is transcribed from ASHRAE
  Guideline 36 §5.16.14 as it appears in Addendum u to Guideline 36-2018 (first
  public review, 2021), which is the text that became §5.16.14. The equation,
  the OS#2 applicability, the three diagnoses, and the internal-variable
  defaults are G36's; everything below is the library's.
- **Severity 3 is library-assigned.** The reference publishes no severity for
  this fault. Severity 3 matches the scaffold row in this chapter's README and
  the severity every other G36 001-range card in this library carries. G36
  itself grades all reported fault conditions as Level 3 alarms (§5.16.14.16),
  which is a reporting priority rather than a fault ranking, but it points the
  same direction.
- **Energy profile matches the reference's §5.8.1 index row** (COMFORT_ENERGY
  / LOW / QUAL, EEM 06, savings "sensor-dependent"); the emissions block is
  library-assigned (the index has no emissions column). The same grades also
  mirror AHU-FC-002 and AHU-FC-003,
  the other G36 001-range temperature-comparison cards in this library. The
  category fits because the immediate consequence is a supply setpoint the unit
  cannot meet — comfort first, energy second and indirectly — and because, like
  those two, the rule consumes only temperatures and can therefore compute no
  waste quantity. Scope 2 is narrower than the `1|2` those cards use, because
  unlike a mis-read MAT this fault cannot drive heating: OS#2 has the heating
  coil shut by definition.
- **Combined-epsilon threshold.** G36 writes the comparison with `eOAT` on the
  measured side and `dTSF` and `eSAT` on the setpoint side. Implemented that
  way, one card parameter would have to bind three block parameters with two
  different signs. Rearranging to `oat − sat_sp > eOAT + eSAT − dTSF` puts one
  positive number on one CXF path (`gapBig.t`), algebraically identical, and
  the composition is recorded in the parameter description so a site that
  measures its own fan rise or moves to a global OAT sensor knows what to
  recompute. Same move as AHU-FC-062 and AHU-FC-002.
- **The default assumes a local OAT sensor.** G36 gives eOAT as 1 °C for a
  sensor at the unit and 3 °C for a global sensor. The library ships the local
  value, so `oat_excess_threshold` = 1.0 °C. A site feeding this rule from a
  campus or weather-service OAT must set it to 3.0 °C
  (3 + 1 − 1); leaving it at 1.0 °C makes the rule fire on sensor
  disagreement that G36 considers within tolerance.
- **No boundary deviation for this fault.** G36's FC#9 comparison is already
  strict (`>`), unlike the `≥`/`≤` forms elsewhere in Table 5.16.14.8 (FC#5,
  FC#12, FC#14, FC#15), so CDL's `GreaterThreshold` (`u > t`) reproduces the
  source exactly. A gap of exactly 1.0 °C reads healthy in both. The vectors
  pin the edge from both sides (1.0 clear, 1.1 faulted) to keep the choice
  legible if the threshold is ever retuned.
- **Instantaneous samples instead of averaged signals.** G36 compares
  5-minute rolling averages sampled at 1-minute intervals (`OAT_AVG`). This
  rule compares the raw samples and leans on the 30-minute `persist` delay to
  reject noise. The two are not equivalent. Averaging tolerates a signal whose
  mean stays outside the bound while it keeps crossing back; persistence does
  not — an oscillating OAT resets the timer on every compliant tick and can
  hide indefinitely. The fault this rule is actually for is a steady offset
  between outdoor air and setpoint, which reads the same way under either
  treatment. (Honesty note carried from AHU-FC-002.)
- **No test vectors are published for this fault**, by the reference or by
  G36. Every scenario in `vectors.json` is authored from the equation: the two
  sides of the strict boundary, the fan-heat sign demonstrated by a 1.5 °C gap
  that only faults because dTSF is subtracted, a setpoint step that opens the
  gap with weather held constant, a sub-delay transient, and a
  recovery-clears case.
- **Operating-state gating and NO_EVAL are frontmatter, not graph.** G36 scopes
  FC#9 to OS#2 (§5.16.14.9b), suspends evaluation for ModeDelay after a mode
  change, and suspends it entirely when the AHU is not operating
  (§5.16.14.11). None of that is in the block graph: the engine is
  status-blind and the graph computes fault-given-valid-data only. Precedent:
  AHU-FC-063. A host that evaluates this rule in OS#3 will see it assert on
  every warm afternoon, correctly by the equation and meaninglessly in fact.
- `persist.delayOnInit = true` (Modelica/CDL default is `false`): a gap already
  open at load waits out the full 30 minutes rather than alarming on the first
  tick after a controller restart. Library-wide choice, per AHU-FC-050.

## Notes

The instructive property of this rule is only visible next to its pair.
AHU-FC-009 and AHU-FC-011 test the same two points against the same two sensor
epsilons, and both account for the same 1 °C fan rise — but FC#9 **subtracts**
fan heat (threshold 1.0 °C) while FC#11 **adds** it (threshold 3.0 °C).

Fan heat narrows the usable free-cooling band from the top. Outdoor air only
0.5 °C below setpoint is already useless, because the fan will hand that 0.5 °C
straight back and then some, so the too-warm test has to fire sooner than
sensor error alone would justify — hence the subtraction. On the cold side the
same fan heat works the other way: it extends how cold outdoor air can be
before the economizer alone would overshoot, because the fan reheats it on the
way through, so the too-cold test waits longer — hence the addition. Same
physical term, opposite sign, because it moves the ceiling and the floor of the
band in the same direction.

Both thresholds assume the local-sensor eOAT of 1 °C. A site on a global OAT
sensor recomputes both: 3.0 °C here and 5.0 °C for AHU-FC-011. They do not
scale together, which is another reason the composition arithmetic is written
out in each parameter description rather than buried in a constant.

Check the OAT sensor before anyone edits changeover logic. Step 1.2 of the
[economizer-failure](../../../playbooks/economizer-failure.md) playbook is the
right first move here: compare the unit's OAT against a nearby weather station.
A sensor reading low produces this fault's exact signature with the economizer
sequence working correctly, and replacing one runs $30–$80.
