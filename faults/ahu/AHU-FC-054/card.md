---
schema: cxf-library/fault-card/v1
id: AHU-FC-054
name: Stuck or failed actuator
equipment: ahu
status: verified
phase: 1
method: rule
severity: 2
category: CRITICAL_WASTE
confidence: MEDIUM
estimation_method: PROXY_ESTIMATION
source:
  - "HVAC FDD Reference v1.0 §9, AHU-FC-054"
  - "PNNL retuning"
  - "Bie et al. 2025"
g36: null
clusters: []
suppresses: []
suppressed_by: []
related: [AHU-FC-014, AHU-FC-015]
playbooks: [stuck-actuator]
operating_states: all
preconditions: "Both the command and the position feedback must be available and bound to the same physical device — a feedback point wired to a different actuator than the command produces a permanent false alarm. When the feedback point is absent, stale, or its device pairing is unverified, the verdict is NO_EVAL, not healthy."
points:
  - actuator_cmd
  - actuator_pos
outputs:
  - name: yFault
    description: True while command and position feedback have differed by more than position_error_threshold continuously for stuck_duration plus alarm_delay
params:
  position_error_threshold:
    default: 10.0
    unit: "%"
    description: Command-vs-position delta above which the actuator counts as not tracking
    cxf: errBig.t
  stuck_duration:
    default: 1800.0
    unit: s
    description: How long the delta must persist before the actuator is judged stuck (30 min)
    cxf: stuck.delayTime
  alarm_delay:
    default: 300.0
    unit: s
    description: Additional debounce held after stuck_duration before the alarm asserts (5 min)
    cxf: persist.delayTime
energy_impact:
  affected_subsystem: The subsystem the stuck device serves — ventilation for a damper, coil thermal energy for a valve
  savings_range: 5-20% of the affected subsystem's energy, depending on the position the actuator is stuck in
  climate_sensitivity: depends on the stuck device — heating-dominant for a stuck heating valve, both directions for a stuck OA damper
  runtime_estimation: "stuck valve: the AHU-FC-014/015 inactive-coil formulas (waste_kw from the coil ΔT across the stuck valve); stuck damper: the AHU-FC-055/060 outdoor-air formulas, waste_kw = (actuator_pos/100) × design_oa_flow × cp × |OAT − RAT|"
emissions:
  scope: "1|2"
  method: PROXY_EMISSIONS
verified:
  engine_rev: e2ff2f8
  content_id: "cxf:fnv1a128:42b5629649240985c2d9776995d8b4de"
  date: 2026-08-17
---

## Description

An actuator's command and its measured position disagree by more than the
tracking allowance and stay disagreed for half an hour. Whatever the sequence
told the device to do, it is not doing: the linkage has come off, the motor has
failed, the stem is seized in scale or debris, or the control signal never
reaches the actuator at all.

This is the chapter's one template rule. `actuator_cmd` and `actuator_pos` name
no particular device — they are a command/feedback pair the host binds per
monitored actuator, so the rule is instantiated once per actuated device rather
than once per air handler. A typical AHU carries three instances: outdoor air
damper, heating valve, cooling valve. Their dictionary entries carry no Brick or
223P class by design, because the class differs per instance
(`Damper_Position_Command` on one, `Valve_Position_Command` on another); the
semantics live on the bound point, and the template stays device-agnostic.

Severity 2 follows from what a stuck actuator does to the rest of the chapter: it
defeats whatever sequence commands it, including the lockouts, resets, and
unoccupied closures the other rules check for. When this fires alongside
AHU-FC-050, AHU-FC-051, or AHU-FC-059 on the same subsystem, those rules are
reporting the symptom and this one is naming the cause — which is why fixing one
stuck actuator commonly clears two to five other alarms.

## Detection Logic

```
yFault = |actuator_cmd − actuator_pos| > position_error_threshold
         sustained continuously for stuck_duration,
         then held for a further alarm_delay
```

Block graph (`rule.cxf.jsonld`):

![AHU-FC-054 block graph](diagram.svg)

`err` takes the signed difference and `absErr` strips the sign, so the test is
direction-blind: an actuator that will not open and one that will not close trip
the same threshold, as does a reverse-wired feedback signal that reports 80%
against a 20% command. `errBig` compares strictly, so a delta sitting exactly on
10% reads healthy — the threshold is a tracking allowance, and an actuator at the
edge of it is within spec.

The two timers are the reference's two timers, chained rather than merged.
`stuck` requires 30 minutes of continuous mistracking, which is longer than any
real stroke: a full 0–100% damper travel takes 90–150 s, so a normal move never
approaches it. `persist` adds the reference's 5-minute debounce on top, putting
the worst-case time to alarm at 2100 s. Either timer resets the moment feedback
comes back inside the allowance, and recovery is immediate — the alarm drops on
the tick the actuator starts tracking again.

## Possible Diagnoses

1. Actuator mechanical failure — motor, gear train, or spring return
2. Actuator linkage disconnected (the most common finding, and the cheapest fix)
3. Incorrect wiring — command and feedback bound to different devices
4. Valve or damper seized by corrosion or debris
5. Control signal not reaching the actuator (broken wire, blown fuse, failed
   pneumatic transducer)

## Energy Impact

CRITICAL_WASTE, MEDIUM confidence, PROXY_ESTIMATION. The waste depends entirely
on which actuator is stuck and where it stopped: a heating valve stuck at 40%
burns fuel year-round, the same valve stuck closed costs nothing in energy and
shows up as a comfort complaint instead. Estimating the loss therefore means
falling back on the affected subsystem's own formula — AHU-FC-014/015 for a coil
valve, AHU-FC-055/060 for an outdoor air damper — with the stuck position read
from `actuator_pos` rather than from the command, which is the reason this card
is PROXY_ESTIMATION and not DIRECT_MEASUREMENT. Across the population, repairing
a stuck actuator returns 5–20% of the affected subsystem's energy (PNNL retuning
measures, various: EEM-03 for leaking coil valves, EEM-06 for OA damper faults).
Climate sensitivity follows the device: a stuck heating valve bites in the
heating season, a stuck OA damper in whichever season makes |OAT − RAT| large.

## Emissions Impact

PROXY_EMISSIONS, MEDIUM confidence; typical 200–2,000 kg CO₂e/yr, the wide band
reflecting the same device dependence as the energy estimate. Scope is recorded
as `1|2` because it follows the affected subsystem rather than the fault: a stuck
heating valve wastes on-site combustion (scope 1), a stuck cooling valve or a
damper dragging in outdoor air for the chiller to handle wastes purchased
electricity (scope 2), and a stuck OA damper in a gas-heated building can do both
across a year. Hosts should attribute against the subsystem the bound device
serves, not against this rule. Avoided-emissions basis: marginal operating
emissions rate (MOER).

## Deviations

- **NO_EVAL is a host precondition, not an output.** The reference's fourth test
  vector (command 50%, position feedback absent → NO_EVAL) tests data absence,
  which the block graph cannot represent: the engine is status-blind and a
  missing input is not a value the rule can compare. Nothing in this graph
  distinguishes "no feedback" from "feedback reads 0", and an unbound feedback
  point held at 0 against a 50% command would alarm within 35 minutes. The host
  must therefore verify that both points are present, fresh, and bound to the
  same device before it interprets `yFault`; that vector maps to the
  `preconditions` field and has no counterpart in `vectors.json`.
- **Template points.** `actuator_cmd` and `actuator_pos` are the dictionary's
  first template entries — one rule instance per actuated device, bound by the
  host to that device's own pair. The reference states the rule generically; this
  card keeps it generic rather than forking a per-device variant (an
  `oa_dmpr_cmd`/`oa_dmpr_pos` rule, a `htg_vlv_cmd`/`htg_vlv_pos` rule, and so
  on), which would triple the card count and drift out of step. The cost of the
  choice is that the CXF document alone does not say which device it watches;
  the host binding does.
- **Two timers, not one.** `stuck_duration` and `alarm_delay` sum to a single
  2100 s time-to-alarm and could have been collapsed into one `TrueDelay`. They
  are kept separate because the reference tunes them separately and they answer
  different questions — how long before an actuator is judged stuck, versus how
  much alarm-noise suppression the site wants on top — so hosts can retune either
  through `set_param` without recomputing the other.
- **Strict inequality at the threshold.** `GreaterThreshold` is `u > t`, so a
  10.0% delta is healthy and 10.1% is not. The reference writes `> threshold`;
  the vectors pin both sides of the edge.
- **The absolute value is load-bearing.** The reference's `|actuator_cmd −
  actuator_pos|` covers the reverse case (feedback above command) as well as the
  forward one. `absErr` implements that literally, which means over-travel and
  reversed feedback wiring alarm on the same schedule as a jam — diagnosis 3
  depends on it.
- The reference tags this fault for AHU, RTU, VAV, and FCU. This is the
  AHU-family instance; the other families reuse the same block graph unchanged,
  since the template points carry no equipment-specific semantics.
- `delayOnInit = true` on both timers (Modelica/CDL default is `false`), the
  library's standing choice: an actuator already mistracking at load waits out
  the full 35 minutes rather than alarming on the first tick after a controller
  restart.

## Notes

The reference states the rule applies generically to any actuated device and is
instantiated per device. In the AHU chapter that usually means three instances —
outdoor air damper, heating coil valve, cooling coil valve — and the three are
worth deploying together, because the diagnosis often depends on which of them
fired. Sites without position feedback on an actuator simply do not instantiate
the rule there; there is no degraded mode, and pretending otherwise is what the
NO_EVAL precondition guards against.

Remote fixes are limited to releasing overrides and checking for demand-limiting
that clamps the command range (playbook `stuck-actuator`, step 2). Everything
else is on-site: reconnecting a linkage costs $0–$50, replacing an actuator
$200–$800, replacing a seized valve body $500–$2,000. After the repair, stroke
the device 0 → 100 → 0 from the BAS and confirm feedback tracks within 5% — half
the threshold this rule uses, so a repair that only just passes will show up here
again.
