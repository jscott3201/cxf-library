---
schema: cxf-library/fault-card/v1
id: PMP-FC-051
name: Pump deadheading (high DP, low/no flow)
equipment: pmp
status: verified
phase: 2
method: rule
severity: 2
category: PROTECTIVE
confidence: HIGH
estimation_method: DIRECT_MEASUREMENT
source:
  - "HVAC FDD Reference v1.0 §15 (ch. 'Pumps', pdf pp. 134-135), PMP-FC-051"
  - "Engineering best practice"
g36: null
clusters: []
suppresses: [PMP-FC-050]
suppressed_by: []
related: [PMP-FC-050, VFD-FC-051]
playbooks: [vfd-pump-faults]
operating_states: "pump proven running"
preconditions: "pump_dp must be the differential pressure ACROSS THIS PUMP — discharge minus suction — and the point dictionary marks it provisional for exactly this reason. A loop or decoupler DP bound here breaks the rule rather than degrading it: depending on where the taps sit, a deadhead can read high, unchanged, or low, and in the last case the rule is silent forever on the fault it exists to find. Confirm the tap location at binding review. deadhead_dp_threshold must then be set from this pump's curve and deadhead_flow_threshold from this loop's design flow; both shipped values are placeholders (see Deviations), and the DP one is the more dangerous of the two because the reference's 150%-of-design multiplier is above the shutoff head of many pumps. All three points must belong to the same pump; on a headered set a common loop flow meter or a header DP tap bound to each pump makes the rule read one machine's hydraulics onto another. The pump must be proven running by rotation — a current switch or drive feedback — and when pump_status is false this rule has no verdict at all: the host reports NO_EVAL, not healthy. There is no in-rule evaluability output (see Deviations), so that gate is the host's to enforce."
points:
  - pump_status
  - pump_dp
  - pump_flow
outputs:
  - name: yFault
    description: True while the pump has been proven running with its differential pressure above deadhead_dp_threshold and its flow below deadhead_flow_threshold, continuously for at least alarm_delay
params:
  deadhead_dp_threshold:
    default: 300.0
    unit: kPa
    description: "Differential pressure across the pump above which it is working against a closed system. PER-PUMP SITE CONFIGURATION — the reference states 150% of design head and the rule carries absolute units, so the shipped 300.0 kPa is 150% of a 200 kPa (≈20 m) design head and means nothing on any other pump. Set it from the pump curve, not from the multiplier (see Deviations)"
    cxf: dpHigh.t
  deadhead_flow_threshold:
    default: 2.0
    unit: L/s
    description: "Flow below which the pump is delivering nothing useful. PER-LOOP SITE CONFIGURATION — the reference states 10% of design flow; the shipped 2.0 L/s is 10% of the same 20 L/s design flow PMP-FC-050's placeholder assumes, which keeps the pair's 5%/10% relationship intact at the defaults"
    cxf: lowFlow.t
  alarm_delay:
    default: 300.0
    unit: s
    description: "Continuous violation required before the alarm asserts (5 min). ADOPTED — the reference's tunables line for this card truncates mid-sentence and its equation states no persistence at all; 300 s is the sibling PMP-FC-050's published AlarmDelay (see Deviations)"
    cxf: persist.delayTime
energy_impact:
  affected_subsystem: Pump energy plus equipment damage risk
  savings_range: "100% of pump energy while active, plus avoided seal and bearing damage ($5K-$20K) (HVAC FDD Reference §15)"
  climate_sensitivity: neutral
  runtime_estimation: "waste_kw = pump_rated_kw × (pump_speed/100)³ — the reference's formula verbatim, and the same one PMP-FC-050 carries. Neither term is an input to this rule: pump_rated_kw is nameplate data and pump_speed is the drive feedback the VFD family binds as vfd_speed, so the host supplies both. A deadheaded pump on DP control usually sits at or near its minimum speed, which is where the cube law makes the standing waste smaller than the mechanical risk"
emissions:
  scope: "2"
  method: DIRECT_EMISSIONS
verified:
  engine_rev: e2ff2f8
  content_id: "cxf:fnv1a128:cdf8042c408d62c7d323457a8f2103ac"
  date: 2026-08-17
---

## Description

A deadheaded pump is running against a closed system. The discharge valve, or
every terminal valve on the loop, or a check valve someone installed backwards,
leaves the water nowhere to go, so the pump rides up its curve to shutoff head
and recirculates the same volute of water until that water boils. This is the
fault on the pump family's list that damages hardware fastest: the mechanical
seal loses the flow that cools it, the bearings take the radial thrust that a
pump running far off its best efficiency point produces, and the reference
prices the outcome at $5,000 to $20,000.

The signature is the pair of readings, not either one alone. High differential
pressure by itself is a loop running at high head, which is a reset opportunity
and not a fault. Low flow by itself is PMP-FC-050's condition and has four
mechanical explanations before it has this one. Together — the pump making more
head than it should while moving less water than it should — they mean the
resistance downstream went up, which is the definition of deadheading, and that
is why this card carries HIGH confidence where its sibling carries MEDIUM.

The DP term is also what makes this rule diagnostic rather than merely
detective. A pump with a failed impeller or a sheared coupling makes *no* head
while making no flow; a deadheaded pump makes its maximum. Same flow reading,
opposite pressure reading, completely different work order.
`impeller_failure_signature` is the vector that pins the distinction.

## Detection Logic

```
dp_high  = pump_dp   > deadhead_dp_threshold
low_flow = pump_flow < deadhead_flow_threshold

yFault = (pump_status AND dp_high AND low_flow)
         sustained continuously for alarm_delay
```

Block graph (`rule.cxf.jsonld`):

![PMP-FC-051 block graph](diagram.svg)

`dpHigh` and `lowFlow` are the two comparisons and `hydraulic` conjoins them
into the deadhead signature; `gate` adds the reference's `pump_status` conjunct,
and `persist` measures the duration. The nesting is only structural — CDL's
`Logical.And` takes two inputs, so a three-way conjunction is two blocks — but
it does group the graph the way the physics does, with the hydraulic evidence on
one side and the run proof on the other.

Both comparisons are strict, so a DP sitting exactly on the threshold is not
high and a flow sitting exactly on its threshold is not low. Each boundary is
pinned from three sides.

`persist` requires five continuous minutes, which is what separates a
deadheading pump from the ordinary event that produces the identical trace for
half that: every zone valve on a loop closing together at the end of a setback,
or a two-way control valve stroking shut while its neighbour has not yet opened.
`valve_closure_transient` is that case. Any moment where the flow returns or the
DP falls back drops the timer and discards the accumulated time, so the alarm
always describes one continuous episode; the alarm from a mid-run onset lands at
exactly 300 s after the event (`deadhead_starts_mid_run`).

There is no evaluability output. Both hydraulic terms are direct comparisons on
bound inputs and the run term *is* a bound input — exposing `pump_status` as
`yStatusOk` would echo a point the host already has, which SCHEMA.md's
boundary-output convention exists to prevent. The exclusions that matter here
are operating-state gating and live in `preconditions`: a stopped pump is
NO_EVAL, and `stopped_pump_reading_header_dp` pins that the graph reports false
in a geometry where it would otherwise alarm forever.

## Possible Diagnoses

Transcribed from the reference's PMP-FC-051 card:

1. Downstream isolation valve closed — the single valve case, usually left shut
   after service on a branch, and the cheapest of the four to fix
2. Severe system blockage — a plugged strainer basket after a piping repair, or
   debris carried into a reducer. The playbook's step 2.4 checks the strainer
   before anything is disassembled
3. Check valve installed backwards — a commissioning error rather than a
   failure, and one that will not resolve itself. Worth suspecting on a pump
   that has never made flow since it was installed or since a repair
4. All terminal unit valves closed — nothing is broken at all. The loop is at
   no load and the pump has no minimum-flow path, which is a control or design
   finding: a differential pressure reset that never trims, a missing bypass, or
   a lead pump that should have staged off. On a variable-primary chilled water
   plant this is the common one

The first three are field failures on one pump and the fourth is a
plant-sequencing problem that will recur on every pump in the building. The
distinction is available before anyone goes to site: check whether the loop was
at genuine no load when the alarm started.

## Energy Impact

PROTECTIVE, HIGH confidence, DIRECT_MEASUREMENT. The energy line is the same as
the sibling's — 100% of the pump's draw while the condition lasts, since none of
it is moving water anywhere — but the number that matters to an owner is the
$5K–$20K of seal and bearing damage the reference attaches to this card and not
to PMP-FC-050. A pump can deadhead for an afternoon and cost a few dollars of
electricity and a mechanical seal.

HIGH confidence is the reference's rating and it is earned by the second term:
two independent measurements agreeing on one hydraulic story is a much stronger
claim than either alone. It survives a single failed sensor in one direction —
a flow meter stuck at zero on a normally operating loop leaves DP at its
ordinary value and this rule stays silent — and not in the other, since a DP
transmitter reading high and a flow meter reading low together are
indistinguishable from the real thing.

Climate sensitivity is neutral. A deadheaded chilled water pump and a
deadheaded heating pump cost the same and break the same way.

## Emissions Impact

Scope 2, DIRECT_EMISSIONS, HIGH confidence; the reference's typical range is
100–500 kg CO₂e/yr for pump energy plus the equipment damage risk, on a marginal
operating emissions rate (MOER) basis. Pump motors are electric, so the scope
assignment does not vary with the plant the way a heating fault's does. The
embodied emissions of a replaced pump end are outside the range and outside this
rule's reach, and they are plausibly the larger number over a decade of a
recurring deadhead nobody diagnosed.

## Deviations

- **`alarm_delay` has no published value, and no published existence.** Two
  transcription gaps compound here. The reference's equation for this card is
  the bare three-term conjunction with no "sustained for" clause at all, unlike
  PMP-FC-050's, and its tunables line ends mid-sentence — "deadhead_dp_threshold
  = 150% of design, deadhead_flow_threshold = 10% of design," — the same
  truncation artifact VFD-FC-051's line carries. Whatever followed that comma
  did not survive, and a fault-persistence parameter is the obvious candidate
  since the sibling's tunables table publishes exactly one ("AlarmDelay — fault
  persistence — 5 min"). So both the persistence and its value are ADOPTED. The
  300 s comes from PMP-FC-050: same chapter, same equipment family, same
  physical event seen from a second angle, and the reference's own number for
  the quantity. VFD-FC-051's adopted 900 s was the other candidate and is
  rejected here — fifteen minutes is a control-loop response window, and a pump
  running its seal dry does not have fifteen minutes to spare. Hosts should
  shorten rather than lengthen it.
- **`deadhead_dp_threshold` ships an absolute placeholder, and the reference's
  multiplier is physically suspect.** Two separate problems. First the units:
  the reference says 150% of design head, the rule carries kPa, and the point
  dictionary is canonical — "deadhead_dp_threshold (150% of design head) ships
  as an absolute kPa placeholder." The shipped 300.0 kPa is 150% of a 200 kPa
  (≈20 m, ≈67 ft) design head and is arbitrary on any other pump. **Hosts MUST
  set it per pump.** Second, and more seriously: a centrifugal pump's shutoff
  head is typically only 110–130% of its head at the design point, so a
  threshold set literally at 150% of design head is *above the highest pressure
  the pump can produce* and the rule will never fire. A site that adopts the
  multiplier without checking the curve gets a rule that is silent by
  construction, which is worse than one that is noisy. The retune target is the
  pump curve's shutoff head less a margin — commonly 105–120% of design head —
  or, where the bound point is a loop DP held by a reset sequence, a value above
  the sequence's maximum setpoint. The reference's number is transcribed because
  it is the reference's number; this paragraph is why it should not be used
  unexamined.
- **`deadhead_flow_threshold` ships an absolute placeholder too, at twice
  PMP-FC-050's.** 2.0 L/s is 10% of the same notional 20 L/s design flow that
  card's 1.0 L/s assumes, so the pair's published 5%/10% relationship survives
  at the defaults and there is a band — 5% to 10% of design — where a
  high-DP pump trips this rule and not that one (`flow_in_the_deadhead_band` is
  the sibling's vector for it). Hosts retuning one threshold should retune both
  from the same design flow; retuning them independently is how the pair stops
  making sense.
- **The DP tap location is an assumption, and binding the wrong point inverts
  the rule.** The point dictionary marks `pump_dp` provisional and states the
  reason: sites trend differential pressure across the pump (deadhead reads
  high) or across the loop or decoupler (deadhead may read high or low depending
  on where the taps sit). This card assumes the across-the-pump reading, as the
  dictionary says it must. On a loop-DP binding the failure is silent in the bad
  direction — the rule simply never fires — and on a header-DP binding it can be
  loud in the wrong one, which `stopped_pump_reading_header_dp` illustrates: a
  stopped standby pump whose tap sees the running pump's header pressure has
  high DP and no flow, and only the `pump_status` conjunct keeps it quiet.
  Binding review owns this; no logic can detect it.
- **No evaluability output, deliberately.** `pump_status` is a boundary input,
  so exposing it as an output would echo a point the host already reads and add
  nothing — the case SCHEMA.md's convention rules out. Neither hydraulic term is
  a derived quantity that a host could not compute for itself either. Contrast
  PMP-FC-050's `yRunOk`, which is a conjunction held for a delay, and
  VFD-FC-050's `yCmdOk`. The consequence is that this card's NO_EVAL cases live
  entirely in `preconditions`: a stopped pump, a pump in hand, and any binding
  where `pump_dp` is not measured across the pump.
- **`suppresses: [PMP-FC-050]` is an authored relationship, not the
  reference's.** Neither card declares suppression. Both fire on one physical
  event — a loop closed against a running pump satisfies both rules' flow
  conjunct — and this one is the specific diagnosis while PMP-FC-050 is the
  general condition. The direction matters more than usual because the general
  card's diagnosis list is wrong for this fault: impeller failure, air lock, and
  a broken coupling all produce *low* DP, so leaving both alarms up sends a
  technician to open a volute on a pump whose isolation valve is shut.
  PMP-FC-050 carries the matching `suppressed_by`. Precedent for authoring the
  relationship at all: the VFD-FC-050/051 pair.
- **Strict comparisons at both thresholds.** The reference writes `>` and `<`
  too, so nothing is lost, but CDL `Reals` has no `GreaterEqual` or `LessEqual`
  and could not have expressed the inclusive forms in any case. A DP of exactly
  300.0 kPa is not high and a flow of exactly 2.0 L/s is not low. Both
  disagreements have measure zero on real-valued signals and both err toward
  silence; each boundary is pinned from three sides
  (`dp_just_below_threshold` / `dp_exactly_at_threshold` /
  `dp_just_above_threshold`, and the same three for flow).
- **A DP transmitter reading high and a flow meter reading zero produce this
  fault exactly.** Two failed sensors are less likely than one, which is the
  whole reason this card outranks its sibling on confidence, but the rule has no
  third measurement to cross-check with and the failure is not exotic: a
  plugged DP tap reads whatever pressure it last saw, and several flow meter
  types read zero when they lose signal. Motor current is the field check that
  settles it in a minute — a deadheaded centrifugal pump draws noticeably *less*
  than at design, not more.
- **A constant-speed pump deadheads differently from a variable-speed one.** On
  DP control, closing valves drives the measured pressure up and the drive
  responds by slowing to its minimum, so the DP that this rule finally sees is
  the pump's shutoff head *at minimum speed*, which can be well below the
  threshold a site derived from a full-speed curve. That is a second, quieter
  reason the shipped multiplier can leave the rule silent, and it argues for
  deriving the threshold from the DP setpoint's maximum rather than from the
  curve on any drive-controlled loop. VFD-FC-051 is the rule that reports the
  pump parked at minimum, and it is `related` for this reason.
- **The energy formula's inputs are not this rule's inputs.** `waste_kw =
  pump_rated_kw × (pump_speed/100)³` needs nameplate power and drive speed and
  the pump point dictionary carries neither; the host supplies both. Transcribed
  unchanged otherwise, including its identity with PMP-FC-050's, which the
  reference states for both cards.
- **The chapter number is uncertain.** The reference's page headers label Energy
  Recovery, Pumps, and Variable Frequency Drives all as "Ch. 15", which cannot
  be right for all three. `source` follows the VFD cards' precedent of §15 and
  names the chapter title and page range so the citation resolves regardless.
- **`g36` is null and no G36 provenance is claimed.** The reference sources this
  card to engineering best practice alone — unlike PMP-FC-050, which cites G36
  alarm patterns — so the field is null and `source` says only what the
  reference says.
- `persist.delayOnInit = true` (the CDL default is `false`), the library's
  standing choice: a pump already deadheading when the controller restarts waits
  out the full five minutes rather than alarming on the first tick.
- **No published test vectors.** The reference publishes a vector table for
  PMP-FC-050 and none for this card, so every scenario in `vectors.json` is
  library-authored: the healthy case, three sides of each threshold, the
  stopped-pump geometry, the impeller-failure signature this rule must *not*
  claim, high DP at normal flow, a transient valve closure, a mid-run onset, and
  the two ways the alarm releases.
- **Persistence stands in for averaging.** The rule consumes instantaneous
  points; the reference specifies no averaging. A loop that cycles in and out of
  a deadhead faster than `alarm_delay` — a hunting control valve, a pump
  staging against a badly tuned bypass — is a real finding this rule cannot
  make, the same blind spot PMP-FC-050 documents and pins.
- **`clusters` is empty.** `clusters/clusters.json` defines no cluster
  containing a pump rule, and this card does not edit the cluster set.

## Notes

Treat this card as the pair's head. When both pump rules are firing, this is the
finding and PMP-FC-050 is its shadow — that is what the `suppresses` line
encodes, and the reason is that the two cards' diagnosis lists point in opposite
physical directions and only one of them fits a pump making full head.

Before deploying it on a fleet, do two things that cost one trend each. Confirm
where the DP transmitter is tapped, because the rule is meaningless if it is not
across the pump. Then compare `deadhead_dp_threshold` against the pump curve's
shutoff head: if the threshold is higher, the rule cannot fire, and the
reference's 150%-of-design multiplier puts it higher on a good many pumps.

The [vfd-pump-faults](../../../playbooks/vfd-pump-faults.md) playbook's step 2
is the service order, and its first two entries are remote: the differential
pressure setpoint may simply be too high, and a loop with no DP reset sequence
is a loop that pumps against closed valves by design (EEM-10, 0.5–2% of site
energy). Step 2.6 names the variable-primary chilled water case, which is the
fourth diagnosis in a sentence: without a working minimum-flow bypass, the lead
pump deadheads every time the last AHU valve closes. That playbook's header
still describes the pump family as future work, and the chapter README still
lists this rule as `planned`; both lines are out of date as of this card and
both files belong to other owners to correct.

VFD-FC-051 asks the drive-side version of the fourth diagnosis — a pump parked
on its minimum speed with the loop still unsatisfied — and a deadheaded
variable-speed pump usually satisfies it too. Neither rule suppresses the other
across families; they are `related` because seeing both is a strong hint that
the finding is the sequence rather than the pump.
