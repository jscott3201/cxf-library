---
schema: cxf-library/fault-card/v1
id: AHU-FC-011
name: OAT too low for mechanical cooling
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
  - "G36 §5.16.14 FC#11 (text per Addendum u public review)"
  - "NISTIR 7365 (defaults provenance)"
g36: "§5.16.14 FC#11"
clusters: [CLU-03]
suppresses: []
suppressed_by: []
related: [AHU-FC-051, AHU-FC-009]
playbooks: [economizer-failure]
operating_states: "OS#3 (mechanical + economizer cooling) — host-gated"
preconditions: "Evaluate only in G36 OS#3, which Table 5.16.14.2 defines by actuator signature: heating coil = 0, cooling coil > 0, OA damper = 100%. Per §5.16.14.11 the host suspends evaluation while the AHU is not operating and for ModeDelay (30 min) after a mode change in any zone group the AHU serves; per §5.16.14.12 fault conditions not applicable to the current OS are not evaluated at all. Verdicts outside OS#3, and verdicts inside a transition window, are NO_EVAL — never healthy. `sat_sp` must be the setpoint the economizer is controlling to (G36's SATsp for heating-coil and economizer control), not the cooling-coil setpoint SATsp-C. The 3.0 °C default threshold assumes a local OAT sensor at the unit; a site on a global OAT sensor must retune it before trusting the verdict."
points:
  - oat
  - sat_sp
outputs:
  - name: yFault
    description: True while outdoor air has stayed more than oat_deficit_threshold below the supply air setpoint continuously for at least alarm_delay
params:
  oat_deficit_threshold:
    default: 3.0
    unit: "°C"
    description: "Amount by which oat may fall below sat_sp before mechanical cooling counts as unnecessary. The default composes the G36 §5.16.14 internal variables as eOAT + eSAT + dTSF = 1 + 1 + 1 = 3.0 °C, using the local-sensor eOAT. Retuning any one term means recomputing the sum: a global OAT sensor (eOAT = 3 °C) gives 5.0 °C; a measured 2 °C fan rise gives 4.0 °C."
    cxf: gapBig.t
  alarm_delay:
    default: 1800.0
    unit: s
    description: Continuous fault persistence required before the alarm asserts (G36 AlarmDelay, 30 min)
    cxf: persist.delayTime
energy_impact:
  affected_subsystem: AHU mechanical cooling — chiller or DX doing work free cooling was already doing
  savings_range: "Sensor-dependent (reference §5.8.1 row, EEM 06); bounded above by the cooling energy spent while the unit sits in OS#3 instead of OS#2"
  climate_sensitivity: cooling-dominant
  runtime_estimation: "none — the rule sees two temperatures and no airflow or coil load, so no waste term is computable from its inputs"
emissions:
  scope: "2"
  method: QUALITATIVE_EMISSIONS
verified:
  engine_rev: e2ff2f8
  content_id: "cxf:fnv1a128:c58377cb68e22f9e5e9d4f66cc906bba"
  date: 2026-08-17
---

## Description

The unit is running mechanical cooling on top of a fully open outdoor air
damper while outdoor air is already colder than the supply setpoint by more
than the fan will add back. In OS#3 the dampers are at 100% and the chiller
trims what the economizer cannot deliver — a legitimate arrangement whenever
outdoor air alone cannot get the supply air down to setpoint. But once OAT is
more than `dTSF` below setpoint, free cooling alone would overshoot: the
economizer should be modulating back toward a mixed-air blend in OS#2, not
sitting wide open with a coil running against air that was cold enough on
arrival.

Something is holding the machine in the wrong state. Either the sequence never
changed over, or a sensor is lying about which side of setpoint the air is on,
or a heating coil is leaking warmth into a stream the chiller then removes —
which is the expensive version, two subsystems paying to cancel each other.
Within CLU-03 (Economizer Failure) this is the third face of the same
changeover problem: AHU-FC-051 catches a damper that stays shut when outdoor
air is useful, AHU-FC-009 catches an economizer still modulating when outdoor
air stopped being useful, and this one catches mechanical cooling still running
when the economizer alone had it covered.

## Detection Logic

```
G36 §5.16.14 FC#11, applies to OS#3:

    OAT_AVG + eOAT < SATSP − dTSF − eSAT

rearranged to gap form:

    sat_sp − oat > eOAT + eSAT + dTSF = 1 + 1 + 1 = 3.0 °C

yFault = (sat_sp − oat > oat_deficit_threshold), sustained for alarm_delay
```

Block graph (`rule.cxf.jsonld`):

![AHU-FC-011 block graph](diagram.svg)

Three blocks: `gap` subtracts outdoor air from the setpoint, `gapBig` compares
that difference against the composed threshold, and `persist` requires the
condition to hold for 30 minutes. G36 spreads the two sensor error bands and
the fan-heat correction across both sides of the inequality; the rearrangement
collapses them into the single positive number `gapBig.t`, so a host retunes
one parameter instead of tracking which side of the comparison each term sits
on.

Note the operand order: `gap` is `sat_sp − oat`, the reverse of AHU-FC-009's
`oat − sat_sp`. The two rules are looking at opposite ends of the same band,
and the gap is positive in each when its own end is violated.

Recovery is immediate — the alarm drops on the tick the gap falls back under
the threshold — while assertion waits the full delay. Either input can open the
gap: raising the supply setpoint pushes it open just as a cold front does, and
the vectors cover both.

## Possible Diagnoses

Per G36 §5.16.14 Table 5.16.14.8, FC#11:

1. SAT sensor error. A supply reading biased high keeps the cooling loop
   calling for capacity the air does not need, and the unit stays in OS#3
   because the loop believes it is not making setpoint.
2. OAT sensor error. A sensor reading high keeps the changeover logic from
   recognizing that free cooling would now overshoot.
3. Heating coil valve leaking or stuck open. Warmth entering upstream of the
   cooling coil is heat the chiller then has to remove, and it is the reason
   the unit needs mechanical cooling on air that arrived cold. The most
   expensive diagnosis on this list, and the one that also lights up FC#15
   (temperature rise across an inactive heating coil) if that rule is deployed.
4. Leaking or stuck economizer damper or actuator. A damper reported at 100%
   but physically short of it, or a return damper that will not close, delivers
   a warmer mixture than OAT implies — so the coil is doing work the reported
   damper position says should be unnecessary.

## Energy Impact

COMFORT_ENERGY, LOW confidence, QUALITATIVE_ONLY — the reference's §5.8.1
index row for this fault, which also maps it to PNNL EEM-06 (OA damper
faults). Mechanical cooling is
doing free cooling's job: every kilowatt at the chiller or the compressor in
this state buys a temperature drop the outdoor air had already made. The waste
is real and continuous while the fault is active, but it is not computable from
this rule's inputs — `oat` and `sat_sp` carry no airflow, no coil load, and no
counterfactual for what the correct state would have consumed, so nothing is
estimated. An upper bound is the cooling energy spent over the fault's
duration; a host with airflow and coil data can substitute the direct
measurement AHU-FC-051 uses. Cooling-dominant: the fault can only occur in an
operating state that exists to make cold air, and it appears most in shoulder
seasons when outdoor air swings across the changeover point.

## Emissions Impact

QUALITATIVE_EMISSIONS, LOW confidence, Scope 2. The waste is chiller or DX
compressor electricity, plus the fan energy already being spent. Diagnosis 3 (a
leaking heating valve) does add on-site combustion at the boiler, which would
be Scope 1 — but the heat is a symptom this rule infers rather than observes,
and the coil it feeds is commanded shut in OS#3, so the emissions this rule can
honestly claim are the purchased-electricity ones. Avoided-emissions basis:
N/A — no quantity is estimated.

## Deviations

- **The reference card is an index row, so this card is built from G36.** The
  HVAC FDD Reference abbreviates AHU-FC-011: §5.8.1 gives the code and the name
  and nothing else — no equation, no test vectors, no severity, no energy or
  emissions profile. The normative content here is transcribed from ASHRAE
  Guideline 36 §5.16.14 as it appears in Addendum u to Guideline 36-2018 (first
  public review, 2021), which is the text that became §5.16.14. The equation,
  the OS#3 applicability, the four diagnoses, and the internal-variable
  defaults are G36's; everything below is the library's.
- **Severity 3 is library-assigned.** The reference publishes no severity for
  this fault. Severity 3 matches the scaffold row in this chapter's README and
  the severity every other G36 001-range card in this library carries. G36
  itself grades all reported fault conditions as Level 3 alarms (§5.16.14.16),
  which is a reporting priority rather than a fault ranking, but it points the
  same direction.
- **Energy profile follows the reference's §5.8.1 index row** (COMFORT_ENERGY
  / LOW / QUAL, EEM 06, savings "sensor-dependent") — the reference's only
  statement for this fault, and the published row wins where one exists. A
  defensible alternative reading is EXCESS_CONSUMPTION: setpoint is being met
  here, so the unit is comfortable and wasteful rather than uncomfortable,
  with mechanical cooling doing work free cooling had already done. That
  reading is recorded, not adopted. The LOW / QUALITATIVE_ONLY grades also
  reflect that this rule consumes only two temperatures and can compute no
  waste quantity — unlike AHU-FC-055's flow-bearing formula. The emissions
  block remains library-assigned (the index has no emissions column).
- **Combined-epsilon threshold.** G36 writes the comparison with `eOAT` on the
  measured side and `dTSF` and `eSAT` on the setpoint side. Implemented that
  way, one card parameter would have to bind three block parameters. Rearranging
  to `sat_sp − oat > eOAT + eSAT + dTSF` puts one positive number on one CXF
  path (`gapBig.t`), algebraically identical, and the composition is recorded in
  the parameter description so a site that measures its own fan rise or moves to
  a global OAT sensor knows what to recompute. Same move as AHU-FC-062 and
  AHU-FC-009.
- **The default assumes a local OAT sensor.** G36 gives eOAT as 1 °C for a
  sensor at the unit and 3 °C for a global sensor. The library ships the local
  value, so `oat_deficit_threshold` = 3.0 °C. A site feeding this rule from a
  campus or weather-service OAT must set it to 5.0 °C (3 + 1 + 1); leaving it at
  3.0 °C makes the rule fire on sensor disagreement that G36 considers within
  tolerance.
- **No boundary deviation for this fault.** G36's FC#11 comparison is already
  strict (`<`), unlike the `≥`/`≤` forms elsewhere in Table 5.16.14.8 (FC#5,
  FC#12, FC#14, FC#15), so CDL's `GreaterThreshold` (`u > t`) on the rearranged
  gap reproduces the source exactly. A gap of exactly 3.0 °C reads healthy in
  both. The vectors pin the edge from both sides (3.0 clear, 3.1 faulted) to
  keep the choice legible if the threshold is ever retuned.
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
  sides of the strict boundary, the fan-heat sign demonstrated by a 2.5 °C gap
  that stays healthy only because dTSF is added, a setpoint step that opens the
  gap with weather held constant, a sub-delay transient, and a recovery-clears
  case.
- **Operating-state gating and NO_EVAL are frontmatter, not graph.** G36 scopes
  FC#11 to OS#3 (§5.16.14.9c), suspends evaluation for ModeDelay after a mode
  change, and suspends it entirely when the AHU is not operating
  (§5.16.14.11). None of that is in the block graph: the engine is
  status-blind and the graph computes fault-given-valid-data only. Precedent:
  AHU-FC-063. A host that evaluates this rule in OS#2 will see it assert on
  every cold morning, correctly by the equation and meaninglessly in fact —
  cold outdoor air with the dampers modulating is free cooling working.
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
sensor error alone would justify — hence the subtraction in FC#9. On the cold
side the same fan heat works the other way: it extends how cold outdoor air can
be before the economizer alone would overshoot, because the fan reheats it on
the way through, so the too-cold test waits longer — hence the addition here.
Same physical term, opposite sign, because it moves the ceiling and the floor
of the band in the same direction.

Both thresholds assume the local-sensor eOAT of 1 °C. A site on a global OAT
sensor recomputes both: 5.0 °C here and 3.0 °C for AHU-FC-009. They do not
scale together, which is another reason the composition arithmetic is written
out in each parameter description rather than buried in a constant.

The two rules cannot fire at once on the same unit — one needs OS#2 and the
other OS#3, and the host gates on that. But a unit that alternates between them
across a day is telling you something neither rule says on its own: the
changeover point is in the wrong place, or the OAT sensor feeding it is
unreliable. That is worth trending before anyone starts adjusting high limits.

Check the OAT sensor before anyone edits changeover logic. Step 1.2 of the
[economizer-failure](../../../playbooks/economizer-failure.md) playbook is the
right first move here: compare the unit's OAT against a nearby weather station.
A sensor reading high produces this fault's exact signature with the economizer
sequence working correctly, and replacing one runs $30–$80.
