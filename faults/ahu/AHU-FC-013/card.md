---
schema: cxf-library/fault-card/v1
id: AHU-FC-013
name: SAT too high at full cooling
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
  - "G36 §5.16.14 FC#13 (text per Addendum u public review)"
  - "NISTIR 7365 (defaults provenance)"
g36: "§5.16.14 FC#13"
clusters: []
suppresses: []
suppressed_by: []
related: [AHU-FC-012, AHU-FC-007, AHU-FC-057, AHU-FC-066, AHU-FC-067]
playbooks: []
operating_states: "OS#3-#4 (mechanical cooling) — host-gated"
preconditions: "Supply fan running, and the unit in one of the two mechanical-cooling operating states G36 defines by actuator signature: OS#3 (HC = 0, CC > 0, OA damper = 100%) or OS#4 (HC = 0, CC > 0, OA damper at minimum). Suspend evaluation for ModeDelay (30 min) after any mode or operating-state change in a zone group the AHU serves, while actuators are still stroking and the coil has not caught up. `clg_vlv_cmd` must be the command the AHU controller is issuing, not a position feedback: this rule asks whether the loop has run out of capacity to ask for, and a feedback that disagrees with its command is a stuck-actuator finding (AHU-FC-054), not this one. `sat_sp` must be the active setpoint, including any reset — comparing against a design value the sequence is no longer holding produces a fault every mild afternoon. When any gate is unmet the verdict is NO_EVAL, not healthy."
points:
  - sat
  - sat_sp
  - clg_vlv_cmd
outputs:
  - name: yFault
    description: True while SAT has stayed more than sat_error_threshold above its setpoint with the cooling valve commanded above cc_full_threshold, for at least alarm_delay
params:
  sat_error_threshold:
    default: 1.0
    unit: "°C"
    description: "Amount by which SAT may exceed its setpoint before the miss is real rather than sensor error. Default 1.0 °C is G36's eSAT, the supply-air sensor accuracy allowance (NISTIR 7365). A site with a calibrated SAT sensor may lower it; raising it to quiet a hunting loop hides AHU-FC-056 instead of fixing it"
    cxf: spMiss.t
  cc_full_threshold:
    default: 99.0
    unit: "%"
    description: Cooling coil command above which the loop is treated as having no capacity left to ask for (G36 `CC >= 99%`)
    cxf: clgFull.t
  alarm_delay:
    default: 1800.0
    unit: s
    description: Continuous fault persistence required before the alarm asserts (G36 AlarmDelay, 30 min)
    cxf: persist.delayTime
energy_impact:
  affected_subsystem: AHU cooling and the fan energy spent making up its deficit
  savings_range: "2-5% of AHU energy (HVAC FDD Reference §5.8.1 index row; no PNNL EEM mapped)"
  climate_sensitivity: cooling-dominant
  runtime_estimation: "Cause-dependent. Where a heat source is running against the coil (leaking HC valve, gas or electric heat stuck on), the waste is AHU-FC-050's simultaneous heating and cooling term and AHU-FC-012 is the rule that sees it directly. Where the coil is simply out of capacity or chilled water, the AHU wastes nothing at the coil and the cost moves downstream: shortfall_kw = supply_airflow_m3s × 1.2 kg/m³ × 1.005 kJ/kg·K × (sat − sat_sp), cooling the zones asked for and did not get, made up by extra airflow at fan power if it is made up at all"
emissions:
  scope: "2"
  method: PROXY_EMISSIONS
verified:
  engine_rev: e2ff2f8
  content_id: "cxf:fnv1a128:52a1f486bef61ee338ec4a5ec1338a05"
  date: 2026-08-17
---

## Description

The cooling valve is wide open and the supply air is still above setpoint. The
control loop has already asked for everything it has, so whatever is wrong is
not tuning: either the coil cannot deliver, the chilled water or refrigerant
behind it cannot deliver, or the sensor reporting the miss is wrong. Downstream
the effect is the ordinary one: zones that cannot get cold enough, VAV boxes
opening toward maximum flow, and a fan pushing more air to make up for the
degrees the coil failed to remove.

This is G36 §5.16.14 FC#13, and it is the exact mirror of AHU-FC-007 on the
heating side, where the heating valve saturates and SAT sits below setpoint.
Both rules are the same statement: an actuator at its stop with the controlled
variable still on the wrong side of its target is evidence of a defect, and
until the actuator saturates it is evidence of nothing.

## Detection Logic

```
sp_gap = sat − sat_sp
yFault = (sp_gap      > sat_error_threshold)   SAT above setpoint by more than sensor accuracy
     AND (clg_vlv_cmd > cc_full_threshold)     cooling loop has nothing left to ask for
         sustained continuously for alarm_delay
```

Block graph (`rule.cxf.jsonld`):

![AHU-FC-013 block graph](diagram.svg)

`spGap` subtracts the setpoint from the measurement and `spMiss` compares the
excess against `sat_error_threshold`, which is G36's `SAT_AVG > SATSP + eSAT`
rearranged so the allowance stays a single positive number at one CXF path.
`clgFull` is the half that gives the miss its meaning: SAT above setpoint at a
part-open valve is a control loop doing its job, and only a loop that has run
out of coil is evidence of a defect. Both comparisons are strict, so a miss
sitting exactly on 1.0 °C and a command parked exactly on 99.0% both read
healthy. `persist` requires 30 minutes of continuous violation, which is what
separates a failed coil from a morning pulldown or the minutes after a large
block of zones opens at once.

## Possible Diagnoses

Transcribed from G36 §5.16.14 FC#13:

1. SAT sensor error
2. Cooling coil valve stuck closed or actuator failure
3. Fouled or undersized cooling coil
4. CHW temperature too high or CHW unavailable
5. DX cooling unavailable
6. Gas or electric heat stuck on
7. Heating coil valve leaking or stuck open

The list is FC#12's minus the MAT sensor, which this rule does not read. Note
what the two share: entries 6 and 7 are heat sources fighting the coil, so a
unit that trips this rule and AHU-FC-012 together is pointing at those two
rather than at the coil.

## Energy Impact

EXCESS_CONSUMPTION, MEDIUM confidence, PROXY_ESTIMATION, with a savings range
of 2–5% of AHU energy — the §5.8.1 index row, which is the only energy
statement the reference makes about this fault (no chapter card, no EEM
mapping). What that range buys depends on which half of the diagnosis list is
true, so the runtime estimate is branched rather than a single term. If a heat
source is fighting the coil, the waste is real and immediate and it is
AHU-FC-050's term that sizes it. If the coil, the chilled water, or the
compressor is simply not delivering, the AHU wastes nothing at the coil — it is
under-delivering, and the cost lands downstream as zones driving their boxes
toward maximum flow and a plant running longer against a load it cannot meet.
`shortfall_kw = supply_airflow_m3s × 1.2 × 1.005 × (sat − sat_sp)` sizes that
undelivered cooling; design airflow substituting for a measured one is what
keeps it a proxy. MEDIUM confidence: the branch matters, and the rule does not
tell you which branch you are in. Cooling-dominant, since the rule is evaluated
only in mechanical-cooling states.

## Emissions Impact

PROXY_EMISSIONS, MEDIUM confidence. Scope 2: everything this fault spends is
purchased electricity — the chiller or DX compressor running longer, and the
fan power that moves extra air to make up the shortfall. Diagnoses 6 and 7 can
put a combustion stream behind the fault, but that is heat this rule cannot
see; AHU-FC-012 measures it directly and carries the Scope 1 half. Note that
emissions can rise rather than fall when the fault is fixed: a coil restored to
capacity finally delivers the cooling the building has been asking for. The
honest accounting is that this rule buys comfort and diagnosis, and the
avoided-emissions claim belongs to whatever waste the repair uncovers.
Avoided-emissions basis: marginal operating emissions rate (MOER), applicable
only to the fighting-heat-source branch.

## Deviations

- **The reference card is abbreviated; G36 is the normative text here.** The
  HVAC FDD Reference carries AHU-FC-013 only as a §5.8.1 index row — a name, an
  energy profile, and nothing else. No chapter 9 card, so no equation, no
  internal variables, no test vectors, no severity, no diagnosis list, no
  preconditions. The detection logic on this card is transcribed from ASHRAE
  Guideline 36 §5.16.14 FC#13 as it appears in Addendum u to Guideline 36-2018
  (First Public Review, 2021), including the possible-diagnosis list verbatim.
  Where the two sources could conflict, G36 wins, because it is the only one
  that states the rule.
- **Setpoint comparison rewritten as gap comparison.** G36 writes
  `SAT_AVG > SATSP + eSAT`. Implemented directly, eSAT would enter the graph as
  an offset added to the setpoint ahead of a two-signal comparison; subtracting
  first and testing `sat − sat_sp > eSAT` is the same statement with the
  allowance staying the positive number G36 publishes, retunable at one CXF
  path. Same rearrangement as AHU-FC-001 and AHU-FC-062. The threshold is a
  single G36 constant rather than a composition — eSAT = 1 °C, the supply-air
  sensor accuracy from NISTIR 7365 — so a site recalibrating that sensor changes
  `sat_error_threshold` to the new allowance directly, with no arithmetic. The
  two forms can differ by one ulp on a value straddling the threshold; at 1 °C
  on a sensor rated to ±1 °C this is not observable.
- **`CC >= 99%` becomes a strict `> 99.0`.** CDL `Reals` has no `GreaterEqual`
  or `GreaterEqualThreshold`, so a command parked at exactly 99.000% reads as
  not-saturated and the rule stays silent where G36 would evaluate it. Same
  deviation and same retune hint as AHU-FC-001 and AHU-FC-007: the exact-equality
  case has measure zero on a modulating command, and the strict form errs toward
  silence, which is the right direction for a rule whose alarm dispatches a
  technician. The vectors pin both sides (99.0% clear, 99.5% faulted). A host
  binding a coarsely quantized command — integer percent, or a controller that
  clamps its output to a rounded 99 — should retune `cc_full_threshold` down to
  98.9 rather than rely on the signal overshooting.
- **Instantaneous samples instead of 5-minute rolling averages.** G36 computes
  every signal in §5.16.14 as a 5-minute rolling average with 1-minute sampling
  (`SAT_AVG`); this library consumes instantaneous points and lets the 30-minute
  AlarmDelay stand in. The two are not equivalent, and the honesty note from
  AHU-FC-002 applies unchanged: averaging tolerates a signal whose mean sits
  outside the bound while it keeps crossing back, persistence does not — an
  oscillating signal resets the timer on every compliant tick and can hide
  indefinitely. A hunting SAT loop is the realistic instance of that miss here,
  and it is AHU-FC-056's fault to report. A steady miss against a saturated
  valve, which is what a failed coil or an unavailable chiller produces, reads
  the same under either treatment.
- **Operating states and ModeDelay are host-side preconditions.** G36 scopes
  FC#13 to OS#3-#4 and suspends evaluation for ModeDelay (30 min) after any mode
  change in a served zone group, and §5.16.14 also suspends all fault evaluation
  while the AHU is not operating. None of it is in the graph: per the library's
  stance (precedent AHU-FC-063) operating-state applicability, transition
  windows, and NO_EVAL are host concerns declared in `preconditions`. A verdict
  produced outside OS#3-#4 or inside a transition window is NO_EVAL, never
  healthy. Note that `CC > 0` is part of both applicable state definitions, so
  the host's gate already implies a cooling call; the graph's `clgFull` test is
  the stronger statement that the call has saturated.
- **Severity 3 is the library's, not the reference's.** No chapter card exists
  to state one and the §5.8.1 index carries no severity column. The value
  matches this chapter's README scaffold row and the other G36 comparison rules
  here. G36 §5.16.14 does say every reported fault condition "shall be a Level 3
  alarm", but that is G36's alarm-priority scheme rather than this library's
  1-4 severity scale, so it corroborates the number without supplying it.
- **The energy profile is the index row's; the runtime formula and scope are
  the library's.** `category`, `confidence`, `estimation_method`, and
  `savings_range` are copied from §5.8.1 (EXCESS_CONSUMP / MED / PROXY / 2-5%
  AHU, no EEM mapped) — the identical row the reference gives AHU-FC-007, which
  is this rule's heating-side mirror. The branched runtime formula is the
  library's, mirrored from AHU-FC-007's. Scope departs from that mirror: FC-007
  records `1|2` because the heat making up its deficit may be gas or electric,
  while nothing on the cooling side burns fuel, so this card records `2` and
  leaves the Scope 1 half of the shared diagnoses to AHU-FC-012.
- **No published test vectors.** The reference publishes none for this fault and
  G36 publishes none for any of them, so `vectors.json` is authored from the
  equation: both sides of each threshold pinned independently, a sustained
  saturated-and-missing case, a pulldown transient shorter than AlarmDelay, a
  recovery when chilled water returns, and a valve that backs off the stop
  before the delay expires and so resets persistence.
- `persist.delayOnInit = true` (Modelica/CDL default is `false`), the library's
  standing choice: a violation already present at load waits out the full 30
  minutes instead of alarming on the first tick after a controller restart.

## Notes

No playbook is referenced. `playbooks/` currently covers control-sequence and
sensor remediation, and nothing there addresses coil capacity or chilled water
supply work — coil cleaning, CHW temperature and flow verification, refrigerant
charge — which is what this fault dispatches. A coil-and-plant-capacity playbook
can adopt it when that family lands.

The setpoint this rule compares against is the one the sequence is actually
holding, which makes it quietly dependent on the reset strategy. On a unit where
SAT reset has been disabled or never commissioned — the condition AHU-FC-057
detects — the active setpoint may be a design value chosen for a design day, and
a coil that cannot reach it in August is being asked for capacity nobody
budgeted. Confirm the setpoint is one the sequence chose before believing the
capacity diagnoses.

Read this rule together with AHU-FC-012. Every diagnosis on this list appears on
that one, and what differs is what the two measure: FC#12 finds heat entering
the stream, FC#13 finds heat failing to leave it. A coil that has genuinely
lost capacity trips this rule alone; a heat source fighting the coil trips both,
and that pair is the cheapest discriminator available before anyone opens an
access panel.
