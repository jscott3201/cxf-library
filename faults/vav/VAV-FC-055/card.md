---
schema: cxf-library/fault-card/v1
id: VAV-FC-055
name: Reheat waste during cooling season
equipment: vav
status: verified
phase: 2
method: rule
severity: 3
category: CRITICAL_WASTE
confidence: HIGH
estimation_method: DIRECT_MEASUREMENT
source:
  - "HVAC FDD Reference v1.0 §10, VAV-FC-055"
  - "Torabi et al. 2022"
  - "PNNL-25985 EEM-15/EEM-16"
g36: null
clusters: [CLU-05]
suppresses: []
suppressed_by: []
related: [AHU-FC-053, VAV-FC-050, VAV-FC-052]
playbooks: [vav-min-flow-reheat]
operating_states: "Occupied cooling season. Outside the cooling season the rule reads false because the question is meaningless, not because the box is healthy — the host reports NO_EVAL there, from the same OAT the rule consumes."
preconditions: "Supply fan running and the box under occupied control; a night-setback reheat cycle is not this fault. `oat` must be the site outdoor air temperature, fresh and shaded — a sun-baked wall sensor reads warm enough to put the building in a cooling season the weather is not in. `zone_dmpr_pos` should be position feedback where the box provides it; on command-only boxes the damper term reads intent rather than blade position, and a blade stuck open under a minimum-flow command will read as this fault."
points:
  - rht_vlv_cmd
  - oat
  - zone_dmpr_pos
outputs:
  - name: yFault
    description: True once the reheat valve has stayed above reheat_active_threshold with the damper below damper_at_minimum_margin and OAT above cooling_season_oat, continuously for eval_duration plus alarm_delay
params:
  reheat_active_threshold:
    default: 10.0
    unit: "%"
    description: Reheat valve command above which the coil counts as actively consuming energy
    cxf: rhtOn.t
  cooling_season_oat:
    default: 18.0
    unit: "°C"
    description: Outdoor air temperature above which the building is in cooling season (65 °F)
    cxf: warmOut.t
  damper_at_minimum_margin:
    default: 35.0
    unit: "%"
    description: Damper position below which the box is passing minimum flow rather than answering a load
    cxf: dmprMin.t
  eval_duration:
    default: 3600.0
    unit: s
    description: Continuous duration of the reheat-at-minimum-flow condition before it counts as waste (60 min)
    cxf: hold.delayTime
  alarm_delay:
    default: 900.0
    unit: s
    description: Further persistence required after eval_duration before the alarm asserts (15 min)
    cxf: persist.delayTime
energy_impact:
  affected_subsystem: VAV zone reheat during cooling season
  savings_range: 5-20% of zone thermal energy; zone-level simultaneous heating and cooling
  climate_sensitivity: cooling-dominant
  runtime_estimation: "waste_kw = rht_vlv_cmd/100 × vav_rht_capacity_kw (reheat at minimum flow during cooling season)"
emissions:
  scope: "1"
  method: DIRECT_EMISSIONS
verified:
  engine_rev: e2ff2f8
  content_id: "cxf:fnv1a128:f9e05984e4f2c96f769f4460a41807b7"
  date: 2026-08-17
---

## Description

A reheat coil is running in July. The zone is passing the minimum airflow
its configuration insists on, that air arrives at the supply air temperature
the chiller worked to produce, and the box heats it back up before it reaches
the space. Every watt spent at the coil is a watt the plant already spent
cooling the same air — simultaneous heating and cooling, seen from the zone
end, which is where much of it happens in a VAV building.

The damper term is what separates waste from load. Reheat with the damper open
and modulating is a box answering a genuine heating demand: the zone is cold,
the sequence is doing what it should, and the finding — if there is one — sits
at the air handler, whose supply air is too cold for what this zone needs.
Reheat with the damper parked at its minimum is different in kind. Nothing is
asking for heat; the box is passing air it is required to pass and tempering it
so the space is not overcooled. That is a configuration defect, and it stays
there every occupied hour until someone changes a setpoint. The season term
keeps the rule from arguing with winter, when reheat at minimum flow is simply
the heating sequence working.

This rule is the trigger of CLU-05 (Zone Heating & Cooling Conflict). It fires
first; VAV-FC-052 and SYS-FC-056 are the members that should clear behind it
once the underlying minimum flow or supply air temperature is corrected.

## Detection Logic

```
yFault = rht_vlv_cmd > reheat_active_threshold
     AND oat > cooling_season_oat                     (cooling season)
     AND zone_dmpr_pos < damper_at_minimum_margin
     sustained continuously for eval_duration
     and then held a further alarm_delay
```

Block graph (`rule.cxf.jsonld`):

![VAV-FC-055 block graph](diagram.svg)

Three threshold tests, two conjunctions, two delays. `rhtOn` asks whether the
coil is consuming, `warmOut` whether the weather makes that indefensible, and
`dmprMin` whether the box is at minimum flow rather than answering a load;
`and1` and `and2` bring the three together in the order the reference writes
them. `hold` measures the duration — true only after the conjunction has been
continuously true for `eval_duration` (60 min) — and `persist` adds
`alarm_delay` (15 min) on top, so a box that reheats through the afternoon
alarms at 3600 + 900 = 4500 s, inside the 90 minutes the reference's FAULT
vector holds. Any break in any of the three terms drops both timers, so a
damper stroke, a passing cloud on the OAT sensor, or a valve that closes for
five minutes restarts the clock.

All three comparisons are strict, as the reference writes them. A valve
reported at exactly 10.0%, an outdoor air temperature of exactly 18.0 °C, and a
damper sitting exactly on 35.0% each fail their term, and the vectors pin all
three edges from both sides.

## Possible Diagnoses

1. VAV minimum airflow setpoint too high for this zone — the common case, and
   the one VAV-FC-050 confirms directly against the ventilation requirement
2. AHU supply air temperature setpoint too low, so every box on the air
   handler has to temper its minimum flow (AHU-FC-053)
3. SAT reset responding to a rogue zone: the reset is working, one zone is
   holding it at the cold end, and this box is paying for it (VAV-FC-051)
4. Zone has low internal loads but a high minimum flow requirement — a corner
   office or a perimeter zone sized for a load that never materialized

## Energy Impact

CRITICAL_WASTE, HIGH confidence, DIRECT_MEASUREMENT. The waste is on the wire:
`waste_kw = rht_vlv_cmd/100 × vav_rht_capacity_kw` for every hour the condition
holds, with no counterfactual to model — the coil's output during cooling
season is the waste, and the cooling energy spent making the air it undoes is
waste on top. The reference gives 5-20% of zone thermal energy, and PNNL-25985
maps the fix to EEM-15 (VAV minimum flow reduction) and EEM-16. Prevalence is
common in VAV-reheat systems. Cooling-dominant by climate, since the fault is
defined by the hours spent above the season threshold, though the multiplier is
what matters: a building runs dozens to hundreds of these boxes, and EEM-15 is
the single highest-impact individual measure across all building types in the
PNNL study, at 5-16% of site energy and 7.7% nationally, with medium and large
offices seeing the greatest benefit.

## Emissions Impact

Scope 1, DIRECT_EMISSIONS, HIGH confidence; typical 500-3,000 kg CO₂e/yr per
zone for reheat during cooling season. Avoided-emissions basis: marginal
operating emissions rate (MOER). The reference reports scope 1: hot-water
reheat is usually fed by a gas-fired boiler, so the waste is on-site
combustion. Boxes with electric reheat coils, or hot water from a heat pump or
district loop, move the same kilowatts into scope 2 — the quantity is
unchanged, the inventory line is not, and hosts should follow the heating
source rather than this default.

## Deviations

- **`cooling_season` is implemented as the OAT comparison the reference puts in
  parentheses, not as a host-supplied season flag.** The reference's equation
  reads `cooling_season = TRUE (OAT > cooling_season_oat)`, which is one
  comparison on a point the rule needs no help obtaining. Consuming a host
  "cooling season" boolean instead would hide `cooling_season_oat` from
  `set_param` and make the rule's behavior depend on a definition the library
  cannot see.
- **The reference's heating-season vector expects NO_EVAL, and this rule
  reports it as a false `yFault`.** Out of season the rule reads false because
  the question is meaningless, not because the box is healthy, and the
  distinction is the host's to publish: `operating_states` scopes the rule to
  the occupied cooling season and the host reports NO_EVAL outside it. No
  dedicated evaluability output is exposed, which is the difference between
  this rule and AHU-FC-055's `yTempDeltaOk`. There, the evaluability condition
  is *computed from* the rule's inputs — the host cannot check `|oat − rat| >
  threshold` without redoing the rule's arithmetic, so SCHEMA.md requires the
  rule to publish it. Here the gate *is* an input: the host already has `oat`
  and the threshold, and asking the graph to hand back a comparison the host
  can make on its own would add a boundary output that carries no information.
  The vector at 5 °C is pinned as a false `yFault` with the NO_EVAL reading
  spelled out in its description.
- The precondition `OAT > cooling_season_oat` is deliberately stated twice —
  once in `preconditions` and once in the block graph — because the reference
  states it twice. The in-graph term is what makes the rule safe to run
  continuously; the precondition is what tells the host when a false output
  means anything.
- **Two delays in series rather than one.** `eval_duration` and `AlarmDelay`
  are separate tunables in the reference, so they stay separately tunable here
  even though a single 4500 s delay behaves identically at the defaults
  (precedent: AHU-FC-061). A site on 15-minute trend data that wants a shorter
  evaluation window changes one parameter.
- All three comparisons are strict (`>`, `>`, `<`), matching the reference's
  own operators — no boundary reinterpretation. The vectors pin each edge from
  both sides (10.0/18.0/35.0 clear; 10.1/18.1/34.9 fire) because the exact
  values are where a retuned site will sit.
- `hold.delayOnInit` and `persist.delayOnInit` are both `true` (Modelica/CDL
  default is `false`), the library's standing choice: a condition already
  present at load waits out the full 75 minutes rather than alarming on the
  first tick after a controller restart.
- Operating-state gating (occupied cooling mode) and the fan-running
  precondition are declared in frontmatter for host enforcement rather than
  encoded in the block graph, per the library's design stance.
- The reference's Notes block is truncated in the source document mid-sentence.
  It is quoted below as far as the source runs and no further; the Torabi
  finding it was introducing is not recoverable from the chapter text and has
  not been reconstructed.

## Notes

Reference note, quoted as far as the source runs: "Check AHU SAT first —
Torabi et al. (2022) found zone-level reheat".

Fix order within CLU-05 follows that advice. Diagnoses 2 and 3 both live at the
air handler, and both are cheaper to check than anything at the box: pull the
supply air temperature setpoint and its reset trend first (AHU-FC-053,
AHU-FC-057), and check whether one zone is holding the reset at its cold end
(VAV-FC-051). A supply air temperature raised into its reset band can clear
this fault across every box on the air handler at once, while lowering one
box's minimum flow fixes one box. The playbook's counting rule in step 1.4 is
the discriminator: more than half the boxes flagged points at the air handler,
one to three boxes points at zone configuration.

Once the air-handler side is ruled out, the
[vav-min-flow-reheat](../../../playbooks/vav-min-flow-reheat.md) playbook's
step 2.3 — a summer reheat lockout that disables the reheat valve when outdoor
air is warm and the zone is satisfied — is the remote fix, and step 2.1 (bring
the minimum airflow setpoint down to the ASHRAE 62.1 ventilation requirement)
is the durable one. Both are $0 and both can be done in batch on most BAS
platforms.

The rule reads `zone_dmpr_pos` as evidence of what the box is doing, not of
what it was told. On boxes that expose only the damper command, a blade stuck
open while the command sits at minimum will satisfy the damper term and this
rule will report waste at a box that is actually passing full flow — the
airflow tracking rule (VAV-FC-053) is what separates those two, and the point
dictionary carries the same caveat on `zone_dmpr_pos` itself.
