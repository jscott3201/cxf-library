---
schema: cxf-library/fault-card/v1
id: SYS-FC-050
name: CHW flow with no cooling demand
equipment: sys
status: verified
phase: 2
method: rule
severity: 3
category: CRITICAL_WASTE
confidence: HIGH
estimation_method: DIRECT_MEASUREMENT
source:
  - "HVAC FDD Reference v1.0 §16, SYS-FC-050 (pdf pp. 139-140) — equation, required points, all three tunables, the four diagnoses, and both impact profiles"
  - "The reference's own provenance line for that card: PNNL AIRCx"
  - "Library precedent: CHW-FC-052 (chw_valve_max, the served-set valve aggregate this card mirrors), VAV-FC-050 and HP-FC-050 (parameters shipped as documented placeholders because the reference publishes a fitting rule rather than a number)"
g36: null
clusters: [CLU-07]
suppresses: []
suppressed_by: []
related: [SYS-FC-051, CHW-FC-053, AHU-FC-014, AHU-FC-054, PMP-FC-051]
playbooks: [unnecessary-plant-operation, stuck-actuator]
operating_states: all
preconditions: "ahu_clg_vlv_max must span every cooling load the loop serves, not the AHUs someone remembered. A maximum taken over a subset reads 0% while an unmonitored coil is wide open, which is exactly the case the fault claims to have excluded — and on a CHW loop the unmonitored load is rarely another AHU. Computer-room units, lab equipment, chilled beams, process heat exchangers and fan coils all hold legitimate demand that an AHU-only aggregate cannot see, and a plant serving them alarms here every hour it works correctly. Either extend the aggregate to those valves or do not bind the rule. no_demand_flow_threshold ships as a placeholder in L/s and MUST be fitted to roughly 10% of the loop's design flow before any verdict means anything (see Deviations); the reference publishes the fitting rule, not the number. chw_flow must be in L/s — the rule converts nothing — and must read a true zero on a dead loop: a magnetic meter with a standing zero offset, or an ultrasonic meter reporting noise on an empty pipe, holds the flow conjunct true forever and turns this into a permanent alarm on a plant that is off. The loop must be variable-flow on modulating two-way valves. A three-way-valve loop circulates near design flow with every coil diverted to its bypass, so the rule fires continuously and means nothing; a loop whose valves are two-position has no meaningful maximum either. Windows where flow with no demand is the sequence working — a chiller pump-down, a scheduled proof-of-operation run, freeze or condensation protection — are the host's to exclude, because the graph has no way to tell them from waste. When the aggregate is stale, partial, or missing the verdict is NO_EVAL, not healthy: there is no in-rule evaluability output, since a stale feed and a genuinely shut valve are the same number at the boundary."
points:
  - chw_flow
  - ahu_clg_vlv_max
outputs:
  - name: yFault
    description: True while the CHW distribution loop has carried more than no_demand_flow_threshold with every served cooling valve commanded below valve_closed_threshold, continuously for at least alarm_delay
params:
  no_demand_flow_threshold:
    default: 5.0
    unit: L/s
    description: "Distribution flow above which the loop counts as circulating rather than resting. PER-LOOP SITE CONFIGURATION — the reference's default is `10% of design`, a commissioning-fitted quantity rather than a constant, and a CXF literal has to be one number in one unit. The shipped 5.0 L/s is 10% of a 50 L/s design loop (about 800 gpm, a mid-size plant at 2.4 gpm/ton); it is not a site value. Fit it from the loop's design flow, and check it against what the meter actually reports with the pumps off."
    cxf: flowHigh.t
  valve_closed_threshold:
    default: 2.0
    unit: "%"
    description: "Cooling valve command at or below which a coil counts as closed (the reference's own 2%). Applied to the served-set maximum, so it is the whole demand test. Sites whose valve commands park at a nonzero rest position must retune it above that position or accept a standing alarm."
    cxf: valvesShut.t
  alarm_delay:
    default: 900.0
    unit: s
    description: "Continuous flow-without-demand required before the alarm asserts (the reference's AlarmDelay, 15 min). It is what separates the fault from the minutes after the last valve shuts, while the loop coasts down and the plant sequence runs."
    cxf: persist.delayTime
energy_impact:
  affected_subsystem: CHW pump + chiller standby energy
  savings_range: "100% of the distribution pump energy and the chiller standby energy drawn while no cooling demand exists"
  climate_sensitivity: both
  runtime_estimation: "waste_kw = chw_pump_kw + chiller_standby_kw — the reference's own term. Both are host-supplied: the rule reads a flow meter and a valve aggregate and sees neither kW"
emissions:
  scope: "2"
  method: DIRECT_EMISSIONS
verified:
  engine_rev: e2ff2f8
  content_id: "cxf:fnv1a128:bce909255e3c56c02e9e03c9ecd80247"
  date: 2026-08-17
---

## Description

Water is moving and nothing is asking for it. Every cooling coil on the loop is
commanded shut, so the chilled water leaves the plant and comes back at the
temperature it left, and the pump energy that pushed it around the building
turns into heat in the water it was supposed to cool. The chiller, if it is
still enabled, holds its evaporator and its controls alive for a load that is
not there.

What makes this a system rule rather than a plant rule is that neither side can
see it alone. The plant knows its flow and knows nothing about demand: a pump
running at 40% against a closed system looks like a pump running. The air
handlers know their valves are shut and know nothing about the loop: a shut
valve is the normal state of a coil that is satisfied. The fault only exists in
the pair, which is why the reference files it under cross-equipment rules and
why the two points come from opposite ends of the building.

It also tends to be invisible in the utility bill. There is no comfort
complaint, no alarm from the chiller, and no obvious signature in monthly
consumption, because the waste is a base load rather than a peak — a 15 kW
distribution pump running 24/7 through a shoulder season is around 65 MWh
nobody notices. The reference puts the fault's category at CRITICAL_WASTE for
that reason: the energy is not merely being spent inefficiently, it is buying
nothing at all.

## Detection Logic

```
flow_high   = chw_flow > no_demand_flow_threshold
valves_shut = ahu_clg_vlv_max < valve_closed_threshold

yFault = (flow_high AND valves_shut) sustained continuously for alarm_delay
```

Block graph (`rule.cxf.jsonld`):

![SYS-FC-050 block graph](diagram.svg)

Four blocks. `flowHigh` decodes the meter, `valvesShut` decodes demand, `both`
requires them at once, and `persist` holds the pair for the reference's
15-minute `AlarmDelay`.

The second conjunct is where the reference's equation and a block graph have to
be reconciled. The reference writes `all(ahu.clg_vlv_cmd <=
valve_closed_threshold for ahu in served_ahus)`, a quantifier over a set whose
width is a property of the site, and CXF has no variable-width input. The host
computes `ahu_clg_vlv_max` instead — the maximum cooling valve command across
the served AHUs — and a maximum below the closed threshold is exactly every
member below it. Nothing is approximated in that step; what moves is the
obligation, from the rule to the host's aggregate, which is why the
preconditions spend their length on which valves belong in it.
`one_open_valve_holds_the_aggregate_up` is the vector that states the
consequence: one coil trimming at 8% with every other valve shut is a plant
serving a load, and an aggregate that missed that coil would report a fault.

Both comparisons are single-sided and strict. `flow_high` is strict in the
reference too. `valves_shut` is not — the reference writes `<=` and CDL `Reals`
has no `LessEqual` — so the shipped test is `LessThreshold` pinned at 2.0 and a
served set whose maximum sits at exactly 2.0% reads as demand rather than as
closed. The error is one part in fifty of a valve command, in the direction of
silence, and
`valve_max_exactly_at_the_closed_threshold` / `valve_max_just_below_the_closed_threshold`
pin both sides of it.

`persist` is a `TrueDelay` that asserts at exactly `T + delayTime`, so the
realized test is "flow with no demand for strictly more than `alarm_delay`" at
tick resolution. `demand_returns_on_the_maturity_tick` (a valve reopens at
exactly 900 s, never reported) and `demand_returns_one_tick_after_maturity`
(one tick of alarm, then clear) pin that edge from both sides. Continuous means
continuous: `demand_returns_before_the_delay_matures` reopens a valve one tick
short of maturity and shuts it again, and the alarm lands a full 900 s after
the *second* shut rather than resuming where it stopped.

## Possible Diagnoses

The reference's four, in its order:

1. CHW pump running unnecessarily — the common case and the cheapest fix. The
   pump is enabled by a schedule, a hand switch, or a start command nobody
   revoked, and the loop circulates because something told it to
2. Leaking cooling coil valve(s): a valve commanded shut that does not seat
   passes water continuously, and on a variable-flow loop that leakage is what
   the pump is chasing. AHU-FC-014 sees the same defect from the air side, as a
   temperature drop across a coil that is supposed to be inactive
3. Bypass valve stuck open — a minimum-flow or pressure-bypass valve that
   never closed, which keeps the loop circulating no matter what the coils do
4. Control sequence not shutting down the CHW loop: the plant has no logic that
   stops the pumps when demand goes away, so it runs whenever it is enabled.
   This is the diagnosis that turns into a sequence change rather than a work
   order, and the one most likely to be shared with SYS-FC-051 on the same site

Diagnoses 1 and 4 are remote fixes; 2 and 3 send someone to a valve. The first
question to settle is which of the two groups you are in, and the pump status
answers it: a pump that is off while the meter reads flow is a valve problem by
elimination.

## Energy Impact

CRITICAL_WASTE, HIGH confidence, DIRECT_MEASUREMENT — the reference's own
profile, transcribed. The affected subsystem is the distribution pump plus
chiller standby, and the savings figure is 100% of both while the condition
holds, because the load being served is zero by construction: that is what the
second conjunct establishes.

`waste_kw = chw_pump_kw + chiller_standby_kw` is the reference's runtime term,
and both quantities are the host's. This rule reads a flow meter and a valve
aggregate; it never sees a kW. DIRECT_MEASUREMENT is honest where the pump has
a power meter or a drive that reports kW, and becomes an estimate the moment
the host substitutes nameplate power for a measurement. Climate sensitivity is
Both, per the reference — a CHW loop left circulating in winter wastes exactly
as much as one left circulating in summer, and arguably more, because there is
less chance anyone is looking at the plant.

## Emissions Impact

Scope 2, DIRECT_EMISSIONS, HIGH confidence; the reference's typical range is
1,500-10,000 kg CO₂e/yr for the pump plus chiller standby, on a marginal
operating emissions rate (MOER) basis. All of it is electricity, and the
marginal basis is the right one because the waste is dispatchable — it stops
the moment someone stops the pump, so the emissions avoided are those of
whatever generator was on the margin at that hour rather than an annual
average.

## Deviations

- **The reference's `all(...)` quantifier becomes one host-derived aggregate.**
  `ahu_clg_vlv_max` is the maximum cooling valve command across the served
  AHUs, and `max < t` is exactly `all < t`, so the substitution is an identity
  rather than an approximation. The reason it is needed is structural: the
  reference's required-points table lists a per-AHU `clg_vlv_cmd`, the served
  set is a site property, and a CXF block has a fixed number of inputs.
  Precedent is CHW-FC-052's `chw_valve_max`, and the point dictionary carries
  the same warning both cards do — the aggregate must span every coil on the
  loop, and a maximum over a subset is worse than no rule.
- **`<=` becomes a strict `<`.** CDL `Reals` has no `LessEqual`, so
  `valve_closed_threshold` is applied as `LessThreshold` with `t = 2.0`: a
  served-set maximum of exactly 2.0% reads as demand and blocks the fault,
  where the reference would call it closed. The library's standing convention
  is to pin the threshold at the boundary and take the strict form. The
  direction is the conservative one for a waste rule.
- **`no_demand_flow_threshold` ships as a placeholder, not a default.** The
  reference gives `10% of design`, which is a fitting rule and not a number:
  design flow is a per-loop quantity, and a CXF `S231:value` is one double in
  one unit. The card publishes the parameter in absolute L/s and ships 5.0,
  which is 10% of a 50 L/s design loop. **It is not a site value**, and a host
  that leaves it unset is comparing a flow meter against an arbitrary number:
  too low and the rule alarms on the leakage every real loop has, too high and
  a pump running at minimum speed never trips it. Same precedent and same
  words as VAV-FC-050's `ventilation_requirement` and HP-FC-050's fitted
  baseline coefficients.
- **The valve aggregate is built from commands, deliberately, and not from
  feedback.** CHW-FC-052 prefers position feedback for its own aggregate,
  because it is asking how open the loop's valves really are. This rule asks a
  different question — what is the control system requesting — and the command
  is the direct answer to it. The choice is also what keeps diagnoses 2 and 3
  visible: a leaking or stuck-open valve reads 0% on the command while it
  passes water, which is the fault; bind feedback instead and the same valve
  reads 20%, the demand conjunct blocks, and the rule goes quiet on the case it
  was written to catch.
- **No schedule or occupancy gate.** The reference does not put one in this
  fault's equation, and the omission is right: flow with no demand costs the
  same at 2 pm as at 2 am. SYS-FC-052 and SYS-FC-053 are the chapter's
  schedule-gated rules and this is not one of them, so nothing in the graph
  consumes `occ_scheduled`.
- **`AlarmDelay = 15 min` becomes `persist.delayTime = 900 s` with
  `delayOnInit = true`** (the CDL default is `false`), the library's standing
  choice: a loop already circulating with no demand when the controller
  restarts waits out the full 15 minutes rather than alarming on the first
  tick.
- **`TrueDelay` asserts at exactly `T + delayTime`,** verified against the
  engine at the pin rather than assumed, so the realized test is "strictly more
  than `alarm_delay`" at tick resolution. Two vectors pin that edge and a third
  pins that a dip discards the elapsed time rather than pausing it.
- **Playbook binding.** The primary playbook is
  `unnecessary-plant-operation` (CLU-07's declared slug; transcribed from the
  reference's remediation playbooks, pp. 171–172, in the same batch as this
  card). `stuck-actuator` stays bound as the secondary procedure for
  diagnoses 2 and 3 (leaking coil valve, stuck bypass).
- **The reference publishes no test vectors for this card,** so all thirteen
  scenarios in `vectors.json` are authored: the two healthy cases that isolate
  each conjunct, the plain fault, both sides of the flow threshold, both sides
  of the valve threshold, the partial aggregate, the demand-stops transition,
  the restart-the-clock case, both sides of the maturity edge, and the
  recovery.
- Operating states and preconditions are declared in frontmatter for host
  enforcement rather than encoded in the block graph, per the library's design
  stance.

## Notes

Read the finding as a question about the pump before it is a question about a
valve. Pull the CHW pump status and the chiller status alongside the trend: if
the pump is commanded on, the fault is diagnosis 1 or 4 and the work is in the
BAS; if the pump is off and the meter still reads flow, something is open that
should not be, and diagnoses 2 and 3 are what remain. PMP-FC-051 is worth
checking at the same time, because a pump running against a closed system is
the definition of deadheading and the two rules will often fire together on the
same hour.

The mirror is SYS-FC-051, and a site that has one usually has both — the
sequence gap in diagnosis 4 tends to be written once and copied to the other
plant. CLU-07 exists for exactly that pairing: this rule is the cluster's
trigger, SYS-FC-051 is its member, and clearing the CHW sequence should clear
the HW one within a day or two.

A finding here is also a standing warning about CHW-FC-053. Flow with no load
is the low delta-T syndrome's cleanest possible case — the return water comes
back at supply temperature — so a plant that trips both is not showing two
independent problems.
