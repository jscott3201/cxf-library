---
schema: cxf-library/fault-card/v1
id: AHU-FC-063
name: AHU operating mode mismatch
equipment: ahu
status: verified
phase: 2
method: rule
severity: 3
category: CRITICAL_WASTE
confidence: MEDIUM
estimation_method: PROXY_ESTIMATION
source:
  - "HVAC FDD Reference v1.0 §9, AHU-FC-063"
  - "Torabi et al. 2022"
  - "Gunay et al. 2022"
  - "G36 §5.16"
  - "PNNL-25985 EEM-38"
g36: null
clusters: [CLU-01]
suppresses: []
suppressed_by: []
related: [AHU-FC-050, AHU-FC-059]
playbooks: [simultaneous-hc]
operating_states: "all occupied modes (host-gated)"
preconditions: "The host derives expected_mode per G36 §5.16 from OAT, zone demands, and the occupancy schedule, and reports NO_EVAL — never healthy — whenever that derivation is unavailable, the unit is in a mode this rule does not encode (warmup, cooldown, setback, unoccupied), or the unit is inside a mode-transition window where actuators are still stroking to their new positions. The OAT sensor feeding the derivation must be trustworthy: a biased reading yields the wrong expected mode and this rule then reports a mismatch that the sequence did not commit (diagnosis 4), so OAT data quality gates this rule even though oat is not an input to the graph."
points:
  - expected_mode
  - htg_vlv_cmd
  - clg_vlv_cmd
  - oa_dmpr_cmd
outputs:
  - name: yFault
    description: True while an actuator has contradicted the expected operating mode continuously for at least alarm_delay
params:
  heating_mode_code:
    default: 1
    unit: "1"
    description: Value of expected_mode meaning HEATING
    cxf: kHeat.k
  econ_mode_code:
    default: 2
    unit: "1"
    description: Value of expected_mode meaning ECONOMIZER
    cxf: kEcon.k
  mech_cooling_mode_code:
    default: 3
    unit: "1"
    description: Value of expected_mode meaning MECHANICAL_COOLING_MIN_OA
    cxf: kMech.k
  valve_open_threshold:
    default: 5.0
    unit: "%"
    description: Valve command above which a coil counts as active; binds both the heating and the cooling test
    cxf: [clgOpen.t, htgOpen.t]
  econ_damper_threshold:
    default: 30.0
    unit: "%"
    description: OA damper command above which the damper counts as economizing rather than sitting at its minimum position
    cxf: dmprEcon.t
  alarm_delay:
    default: 1800.0
    unit: s
    description: Continuous fault persistence required before the alarm asserts (30 min)
    cxf: persist.delayTime
energy_impact:
  affected_subsystem: AHU sequencing — wrong mode wastes active subsystem energy
  savings_range: 5-20% of the affected subsystem's energy while the unit runs in the wrong mode
  climate_sensitivity: both
  runtime_estimation: "Varies by mismatch type; worst case (both coils active) uses the AHU-FC-050 formula: waste_kw = htg_vlv_cmd/100 × ahu_htg_capacity_kw + clg_vlv_cmd/100 × ahu_clg_capacity_kw"
emissions:
  scope: "1+2"
  method: PROXY_EMISSIONS
verified:
  engine_rev: e2ff2f8
  content_id: "cxf:fnv1a128:502800a60ac3786128ffd6f563283d3b"
  date: 2026-08-17
---

## Description

Valve and damper positions contradict the operating mode the current conditions
call for: the cooling coil is open while the unit should be heating, the heating
coil is open while the unit should be economizing, the outdoor damper is
economizing while the unit should be holding minimum outdoor air. The equipment
is doing real work in the wrong direction, and because each individual actuator
is tracking its own loop faithfully, nothing looks broken from the equipment
side — only the sequencing that arbitrates between them is wrong. This is one
of the most common soft faults in commercial buildings, and one of the least
visible: comfort is usually maintained, at the cost of running two subsystems
against each other.

Within CLU-01 this rule complements the trigger AHU-FC-050. FC-050 sees both
coils fighting each other; FC-063 sees one subsystem fighting the mode. The two
overlap only partly: a cooling valve cracked open in heating weather while the
heating coil happens to be shut passes FC-050 untouched, and a damper
economizing during minimum-outdoor-air operation is invisible to it entirely —
FC-050 never looks at the damper.

## Detection Logic

```
clg_open  = clg_vlv_cmd > valve_open_threshold
htg_open  = htg_vlv_cmd > valve_open_threshold
dmpr_econ = oa_dmpr_cmd > econ_damper_threshold

mismatch = (expected_mode = heating_mode_code      AND (clg_open OR dmpr_econ))
        OR (expected_mode = mech_cooling_mode_code AND (htg_open OR dmpr_econ))
        OR (expected_mode = econ_mode_code         AND (clg_open OR htg_open))

yFault = mismatch sustained continuously for alarm_delay
```

Block graph (`rule.cxf.jsonld`):

![AHU-FC-063 block graph](diagram.svg)

`expected_mode` is the host's answer to "what should this unit be doing right
now", per G36 §5.16; the graph only asks whether the actuators agree with it.
Three integer constants (`kHeat`, `kEcon`, `kMech`) decode the mode into three
mutually exclusive booleans, and three threshold tests decode the actuators.
Each mode gate then ANDs its mode flag with the disjunction of the actuators
that contradict it — each test appears in exactly the two modes where it means
something: the cooling valve is wrong in HEATING and in ECONOMIZER but right in
MECHANICAL_COOLING_MIN_OA, and an open outdoor damper is wrong in HEATING and
in MECHANICAL_COOLING_MIN_OA but is the entire point of ECONOMIZER. All three
comparisons are strict, so a valve parked at exactly 5% or a damper at exactly 30%
is not a violation. `persist` requires 30 minutes of continuous mismatch, which
is long enough to ride out a mode change: when the mode flips, the actuators
have half an hour to catch up before the rule calls it a fault.

If `expected_mode` matches none of the three codes, every mode gate is false and
the rule is silent no matter what the actuators are doing. That silence is a
structural gap, not a health claim — see Deviations.

## Possible Diagnoses

1. Sequencing logic error in the BAS programming — the mode arbitration itself
   is wrong, so the unit is executing the wrong sequence correctly
2. Mode transition deadband too narrow: the unit hunts between modes and
   actuators never settle where the current mode wants them
3. Valve stuck in the wrong position — actuator or linkage failure, or a
   normally-open valve with no signal
4. Incorrect OAT sensor causing wrong mode selection: the sequence and the
   actuators are both fine and the derived expected mode is the thing that is
   wrong
5. Manual override left on a valve or damper command (BACnet priority array)

## Energy Impact

CRITICAL_WASTE, MEDIUM confidence, PROXY_ESTIMATION. There is no single waste
term because the waste depends on which subsystem is running against the mode:
a cooling valve open in heating weather costs chiller energy plus the heating
energy spent overcoming it, an outdoor damper economizing during minimum-OA
operation costs coil energy on the excess outdoor air. The reference gives
5–20% of the affected subsystem's energy while the unit runs in the wrong mode
(PNNL-25985 EEM-38, eliminate simultaneous heating and cooling), and for the
worst case — both coils active — the AHU-FC-050 formula bounds it:
`waste_kw = htg_vlv_cmd/100 × ahu_htg_capacity_kw + clg_vlv_cmd/100 ×
ahu_clg_capacity_kw`. Estimation is PROXY rather than DIRECT because the rule
observes commands and a derived mode, not the thermal quantities involved, and
because the counterfactual (what the right mode would have consumed) is not
measured. Sensitive to both heating and cooling climates: every mode in the
encoding is reachable in either.

## Emissions Impact

Scope 1 + 2, PROXY_EMISSIONS, MEDIUM confidence; typical 500–5,000 kg CO₂e/yr.
The split between inventories follows whichever subsystem is running in the
wrong mode — gas at the boiler is scope 1, chiller and fan electricity are
scope 2 — and a mismatch usually engages both. Avoided-emissions basis:
marginal operating emissions rate (MOER).

## Deviations

- The reference's required points are `oat`, `htg_vlv_cmd`, `clg_vlv_cmd`,
  `oa_dmpr_cmd`; this rule consumes `expected_mode` instead of `oat`. The
  reference lists `oat` because its logic opens with
  `expected_mode = determine_g36_mode(OAT, zone_demands, schedule)`, which the
  reference itself annotates as host-side. Deriving the mode needs zone demands
  and the schedule as well, neither of which is an AHU point, so the derivation
  lives in the host and the graph consumes its output. Precedent: AHU-FC-060
  consumes the host-evaluated `occ_schedule` boolean rather than a schedule
  object. OAT's role survives as a precondition, not an input.
- The integer encoding of `expected_mode` (1 = HEATING, 2 = ECONOMIZER,
  3 = MECHANICAL_COOLING_MIN_OA) is this library's convention. The reference
  names the three modes but does not number them, and G36 §5.16 states the
  sequence without an enumeration. The three codes are therefore exposed as
  parameters (`heating_mode_code`, `econ_mode_code`, `mech_cooling_mode_code`)
  so a host with its own mode enum rebinds the constants instead of editing the
  graph — the same move AHU-FC-051 makes with `econ_type_is_ddb`.
- **An `expected_mode` value outside the three codes leaves the rule
  structurally silent.** All three mode gates go false, so both coils and the
  damper can be wide open with no fault raised. That is NO_EVAL territory, not
  a health claim: warmup, cooldown, setback, unoccupied operation, and any
  host mode this encoding does not cover are states the rule cannot judge, and
  the host must report NO_EVAL for them rather than reading a false `yFault`
  as "mode is consistent". The alternative — an explicit "unmapped mode" output
  — was rejected because the host already knows which mode it derived; it does
  not need the rule to tell it.
- All three comparisons are strict (`>`). The reference writes `>` in its logic
  block and says nothing about boundary behavior; strict keeps a valve reported
  at exactly the 5% threshold and a damper sitting on its 30% minimum-position
  setpoint out of the alarm, and the vectors pin the choice from both sides
  (5.0/30.0 clear, 5.1/30.1 fault).
- `valve_open_threshold` is one card parameter bound to two CXF paths
  (`clgOpen.t`, `htgOpen.t`), matching the reference's single tunable. Hosts
  must set both together; a site needing per-coil thresholds retunes the paths
  individually and notes the divergence.
- The reference states three independent `IF expected_mode = …` branches. This
  rule ORs them into a single `yFault` behind one persistence timer, the shape
  every other card in this library uses. Only one mode gate can be true at a
  time, so nothing is lost logically, but the output does not say which mode or
  which actuator raised it — that comes from trending the four points. Separate
  per-mode outputs were considered and dropped: they would triple the alarm
  surface for one fix.
- `AlarmDelay = 30 min` from the reference tunables becomes
  `persist.delayTime = 1800 s` with `delayOnInit = true` (Modelica/CDL default
  is `false`), the library's standing choice: a mismatch already present at
  load waits out the full 30 minutes rather than alarming on the first tick
  after a controller restart.
- Severity 3 (warning) and the MEDIUM/PROXY energy and emissions grades come
  from the reference's chapter 9 card, its only severity statement for this
  fault (the §5.8.1 index carries no severity column). This chapter's README
  index still shows severity 2 for AHU-FC-063 and needs the same correction
  AHU-FC-059 received.
- Frontmatter `g36` is null even though G36 §5.16 is in `source`: SCHEMA.md
  reserves that field for the 001–049 G36-derived rules, and this is a
  research-backed 050-range rule that cites G36 for the mode definitions only.

## Notes

The rule tests only for actuators that are open when the mode says they should
be shut. It does not test the converse — a damper stuck at minimum while the
mode says ECONOMIZER, or a cooling valve that will not open under mechanical
cooling. Those are failures to deliver, not failures to sequence, and they
belong to AHU-FC-051 (economizer not operational when favorable) and the
temperature-control rules. Reading a clear `yFault` as "the unit is in the
right mode" is therefore too strong: it means no actuator is contradicting the
mode, nothing more.

Diagnosis 4 deserves a specific check before anyone edits a sequence. This rule
consumes a derived point, so a bad OAT reading arrives pre-laundered as a wrong
mode, and the mismatch will look exactly like a programming error. AHU-FC-062
is worth checking first for that reason: its envelope test is built from `oat`,
so an outdoor sensor bad enough to select the wrong mode often shows up there
too. Fix the sensor and re-evaluate before touching a sequence — the ordering
CLU-09 imposes on the rules it gates applies here by the same logic, even though
this rule is not one of them.

Fix order within CLU-01: clear the trigger (AHU-FC-050) first. A valve held
open by a fighting control loop also contradicts whichever mode is active, so
FC-063 will often clear on its own once the interlock or deadband that resolves
FC-050 is in place (playbook `simultaneous-hc`, steps 2.1–2.2).
