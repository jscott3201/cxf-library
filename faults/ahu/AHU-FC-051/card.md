---
schema: cxf-library/fault-card/v1
id: AHU-FC-051
name: Economizer not operational when favorable
equipment: ahu
status: verified
phase: 1
method: rule
severity: 3
category: CRITICAL_WASTE
confidence: HIGH
estimation_method: DIRECT_MEASUREMENT
source:
  - "HVAC FDD Reference v1.0 §9, AHU-FC-051"
  - "PNNL-27338 §3"
  - "PNNL EEM-06"
  - "Cowan 2004 (54% of RTUs)"
g36: null
clusters: [CLU-03]
suppresses: []
suppressed_by: []
related: [AHU-FC-009, AHU-FC-011]
playbooks: [economizer-failure]
operating_states: "OS 4 (mechanical cooling)"
preconditions: "Supply fan running. The outdoor/return comparison must be evaluable: |oat - rat| >= TMIN (PNNL-27338 uses 5 °F for its outdoor-air-fraction work), since two sensors reading within their combined error of each other cannot establish which air is cooler. Hosts also gate on OAT sensor quality — a sensor reading high produces this fault's signature with the economizer control working correctly (diagnosis 4). When either gate is unmet the verdict is NO_EVAL, not healthy."
points:
  - oat
  - rat
  - clg_vlv_cmd
  - oa_dmpr_cmd
outputs:
  - name: yFault
    description: True while outdoor conditions have favored economizing, mechanical cooling has run, and the OA damper has stayed below econ_damper_threshold, all continuously for at least alarm_delay
params:
  econ_type_is_ddb:
    default: true
    unit: bool
    description: Economizer changeover type — true = differential dry-bulb (compare oat to rat), false = fixed high-limit dry-bulb (compare oat to econ_hl_temp)
    cxf: isDDB.k
  econ_hl_temp:
    default: 21.0
    unit: "°C"
    description: Fixed high-limit changeover temperature, used only when econ_type_is_ddb is false
    cxf: hlConst.k
  temp_deadband:
    default: 1.0
    unit: "°C"
    description: Margin the favorable comparison must clear before economizing counts as worthwhile; binds both changeover branches
    cxf: [ddbFav.t, hlFav.t]
  cooling_enabled_threshold:
    default: 10.0
    unit: "%"
    description: Cooling valve command above which mechanical cooling counts as active
    cxf: clgOn.t
  econ_damper_threshold:
    default: 25.0
    unit: "%"
    description: OA damper command below which the damper counts as parked at minimum position
    cxf: dmprLow.t
  alarm_delay:
    default: 1800.0
    unit: s
    description: Continuous fault persistence required before the alarm asserts (30 min)
    cxf: persist.delayTime
energy_impact:
  affected_subsystem: AHU mechanical cooling energy
  savings_range: 5-20% of cooling energy (PNNL-27338)
  climate_sensitivity: cooling-dominant
  runtime_estimation: "waste_kw = clg_vlv_cmd/100 × ahu_clg_capacity_kw (the mechanical cooling free cooling would have displaced)"
emissions:
  scope: "2"
  method: DIRECT_EMISSIONS
verified:
  engine_rev: e2ff2f8
  content_id: "cxf:fnv1a128:6bd93b0a587698d63e6263031a029829"
  date: 2026-08-17
---

## Description

Outdoor air is cool enough to do the cooling for free, but the outdoor-air
damper sits at or near its minimum position while the cooling coil runs. Every
kilowatt the compressor or chiller spends in that state buys cooling the
economizer was standing by to provide at fan power alone. The fault is common
and cheap to fix: Cowan's 2004 field survey found 54% of RTU economizers
carrying at least one fault, most often a disconnected damper linkage, and the
reference puts economizer faults at roughly 15% prevalence across buildings.
It is the trigger rule for CLU-03 (Economizer Failure) — clearing it should
clear AHU-FC-009 and AHU-FC-011 within a day or two, since a damper that never
leaves minimum also fails every mixed-air and OA-fraction test downstream.

## Detection Logic

```
econ_favorable = (rat - oat)          > temp_deadband   when econ_type_is_ddb
               = (econ_hl_temp - oat) > temp_deadband   otherwise

yFault = econ_favorable
     AND clg_vlv_cmd > cooling_enabled_threshold
     AND oa_dmpr_cmd < econ_damper_threshold
     sustained continuously for alarm_delay
```

Block graph (`rule.cxf.jsonld`):

![AHU-FC-051 block graph](diagram.svg)

Both changeover branches are computed on every tick and `favSel`
(`Logical.Switch`, `y = u2 ? u1 : u3`) picks one: `isDDB` selects the
differential branch (`rat - oat`, the default) or the fixed high-limit branch
(`econ_hl_temp - oat`). Subtracting first and thresholding the difference is
what lets one `temp_deadband` serve both branches — at the default 1.0 °C,
outdoor air must be a full degree cooler than the reference before the
economizer is expected to act, which keeps sensor noise around the changeover
point from producing an alarm. All three comparisons are strict, so a damper
parked at exactly 25%, a cooling valve at exactly 10%, or a 1.0 °C temperature
gap does not trip the rule. `persist` then requires 30 minutes of continuous
violation, long enough to ride out damper strokes, changeover transitions, and
the minimum-position dwell an economizer holds while its mixed-air loop settles.

## Possible Diagnoses

1. Economizer control sequence disabled or misconfigured in the BAS
2. OA damper stuck at minimum position (linkage disconnected, blades bound)
3. Damper actuator failure — no power, no air, or a burnt-out motor
4. OAT sensor error, reading higher than actual, which locks out changeover
5. Economizer lockout active when it should not be (seasonal or manual)

## Energy Impact

CRITICAL_WASTE, HIGH confidence, DIRECT_MEASUREMENT. The waste is the
mechanical cooling that free cooling would have displaced, readable straight
off the valve command: `waste_kw = clg_vlv_cmd/100 × ahu_clg_capacity_kw`.
Correcting economizer operation saves 5–20% of cooling energy (PNNL-27338 §3;
PNNL EEM-06, OA damper faults and controls). Confidence is HIGH — the fault
condition is read directly from commands and temperatures, needing no baseline
or model, and both the prevalence and the savings range come from field data
(Cowan 2004; PNNL-27338's AIRCx deployments) rather than simulation. Strongly
cooling-dominant in its climate sensitivity, and most valuable in mild
shoulder-season weather, which is exactly when the damper should be modulating
and exactly when nobody is watching it.

## Emissions Impact

Scope 2, DIRECT_EMISSIONS, HIGH confidence; typical 1,500–8,000 kg CO₂e/yr. The
displaced energy is electric compressor or chiller work, so the entire impact
lands in purchased electricity. Free-cooling hours cluster in mild daytime and
overnight weather, when the marginal generator differs sharply from the annual
average — use the marginal operating emissions rate (MOER), not an average
grid factor, or the estimate will miss by the width of the grid's daily swing.

## Deviations

- The reference's `econ_type` is an enum (`DDB` | `HL_DB`, default `DDB`). This
  rule carries it as the boolean parameter `econ_type_is_ddb` (default `true`)
  driving a `Logical.Switch`. Only two changeover types exist in the reference,
  so a boolean loses nothing, and it gains retunability: a host flips a boolean
  parameter through `set_param` on a deployed rule, whereas an enum would have
  to be smuggled in as an integer with a naming convention bolted on beside it,
  which two values do not earn. A site running enthalpy-based changeover needs
  a different rule, not a third enum value.
- The evaluability gate `|oat - rat| >= TMIN` and the OS-4 (mechanical cooling)
  operating-state restriction are declared as preconditions for host
  enforcement, not encoded in the block graph. Both are data-quality and
  gating concerns, which this library keeps out of the rule per its design
  stance; the rule computes the fault condition given valid data.
- All three comparisons are strict (`>`, `>`, `<`). The reference does not
  specify boundary behavior; strict inequalities keep a damper sitting exactly
  on its minimum-position threshold and a temperature gap sitting exactly on
  the deadband out of the alarm, and the vectors pin that choice.
- `temp_deadband` is one card parameter bound to two CXF paths (`ddbFav.t`,
  `hlFav.t`), matching the reference's single deadband. Only one branch is
  selected at a time, but hosts must still set both paths together — otherwise
  flipping `econ_type_is_ddb` silently changes the deadband.
- `persist.delayOnInit = true` (Modelica/CDL default is `false`), the library's
  standing choice: a violation already present at load waits out the full 30
  minutes instead of alarming on the first tick after a controller restart.

## Notes

With default parameters the vectors exercise only the DDB branch. `vectors/v1`
stages inputs, not parameters, so `isDDB` holds `true` for every scenario in
`vectors.json`: `hlConst`, `hlGap`, and `hlFav` are loaded, evaluated, and
structurally verified on each tick, but their result never reaches `yFault`
through `u3` of the switch. The HL_DB path is behaviorally exercised only by
hosts that set `econ_type_is_ddb = false` via `set_param`. The `u3` wiring was
smoke-tested during authoring by flipping `isDDB.k` to `false` and replaying
cases where the two branches disagree, but that check is not part of the
shipped vectors and did not produce the recorded content ID — a host adopting
the fixed high-limit changeover should run its own commissioning check rather
than inherit confidence from these vectors.

`econ_hl_temp` defaults to 21 °C, near ASHRAE 90.1's 70 °F high limit for
climate zones 4A–5A. Zones 1A–3A allow 75 °F (23.9 °C) and zones 5B–8 use
65 °F (18.3 °C) — retune per the playbook's step 2.2 rather than accepting the
default in a climate it does not fit. Differential dry-bulb, the default here,
sidesteps the question: free cooling enables whenever outdoor air is cooler
than return air, which is the correct test for a site without a humidity-driven
reason to do otherwise.

Verify order within CLU-03: fix this rule first. AHU-FC-009 and AHU-FC-011 read
mixed-air behavior, and a damper pinned at minimum makes both of them fire for
a reason that has nothing to do with their own sensors.
