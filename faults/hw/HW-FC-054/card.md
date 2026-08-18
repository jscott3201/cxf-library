---
schema: cxf-library/fault-card/v1
id: HW-FC-054
name: HW loop DP too high (pump speed vs mild OAT)
equipment: hw
status: verified
phase: 2
method: rule
severity: 3
category: EXCESS_CONSUMPTION
confidence: MEDIUM
estimation_method: PROXY_ESTIMATION
source:
  - "PNNL-27338 §4.2 (high hot-water loop differential pressure, pp. 4.7-4.8) — both thresholds: pump VFD above 45% with outdoor air above 60 °F"
  - "PNNL-27338 (Katipamula et al. 2018) — adapted via an internal paraphrased deep-read digest, not distributed (paraphrased algorithm digest; candidate 4)"
  - "Sibling precedent: HW-FC-052 (mild-OAT comparator plus TrueDelay), CHW-FC-053 (evaluability output shape), CHW-FC-052 (the DP-reset finding this rule does not duplicate)"
  - "Library extension: the HVAC FDD Reference v1.0 ch.14 specifies only HW-FC-050..052 — see faults/hw/README.md"
g36: null
clusters: []
suppresses: []
suppressed_by: []
related: [HW-FC-053, HW-FC-055, HW-FC-052, CHW-FC-052, PMP-FC-051]
playbooks: [hot-water-plant-faults]
operating_states: "Heating distribution enabled with variable-speed pumps under differential-pressure control, in weather above mild_weather_oat — the rule's own yMildWeather is that second half"
preconditions: "hw_pump_vfd_speed must be a speed feedback from the distribution pumps that serve the heating loop, and it must fall to zero when the pump stops. A drive that latches its last commanded speed while stopped, or a point bound to the speed command rather than the feedback, fabricates this fault on an idle plant; bind the feedback, or gate host-side on hw_pump_status. On a multi-pump loop bind the lead drive or a host-computed maximum across the running drives — an average across a lead/standby pair halves the reading and hides the fault. The loop must be variable-flow under DP control for the inference to hold at all: a constant-speed pump reads full speed forever and alarms every mild day, and a three-way-valve loop has no DP control to mis-set. oat must be a trustworthy outdoor reading on the same site; a sensor in afternoon sun reads high and manufactures evaluability, one shaded or over-damped reads low and hides the fault for weeks. The plant must not be circulating for a domestic hot water or process load: a DHW recirculation pump running through July is not a DP setpoint fault, and nothing in two points tells them apart — exclude the rule, bind a pump that does not serve DHW, or accept summer noise, the same decision HW-FC-052 forces. Evaluability is signalled in-rule by yMildWeather; when it is false the verdict is NO_EVAL, not a healthy loop."
points:
  - hw_pump_vfd_speed
  - oat
outputs:
  - name: yFault
    description: True while the HW distribution pumps have run above high_pump_speed with outdoor air above mild_weather_oat, continuously for at least alarm_delay
  - name: yMildWeather
    description: Evaluability signal — true when oat is above mild_weather_oat, the weather above which a hard-working distribution pump has no load to justify it. False means NO_EVAL and the host must ignore yFault
params:
  high_pump_speed:
    default: 45.0
    unit: "%"
    description: "Distribution pump speed above which the pumps are working harder than mild weather can justify. PNNL-27338 §4.2's threshold verbatim (its avg_pump_vfd > 45%)."
    cxf: pumpHigh.t
  mild_weather_oat:
    default: 15.6
    unit: "°C"
    description: "Outdoor air temperature above which the heating load is light enough that pump speed becomes evidence about the DP setpoint. PNNL-27338 §4.2's 60 °F, converted and rounded to a tenth of a kelvin. Distinct from HW-FC-052's heating_plant_lockout_temp despite the similar value — different rule, different source, retune separately (see Deviations)."
    cxf: mildOat.t
  alarm_delay:
    default: 3600.0
    unit: s
    description: "Continuous hard pumping in mild weather required before the alarm asserts (60 min). ADOPTED — PNNL-27338 specifies a 15-60 min averaging window (§1.2), not an alarm persistence; 60 min matches HW-FC-052 and HW-FC-053."
    cxf: sustained.delayTime
energy_impact:
  affected_subsystem: HW distribution pump energy
  savings_range: "0.5-2% site energy for a commissioned DP reset (PNNL-25985 EEM-10/11, carried through CHW-FC-052 and playbooks/vfd-pump-faults.md); PNNL-27338 §4.2 itself publishes no savings figure"
  climate_sensitivity: heating-dominant (the fault is only visible, and mostly costly, in the shoulder seasons)
  runtime_estimation: "pump_waste_kw ≈ hw_pump_kw × [1 − (1 − speed_reduction/100)³] — CHW-FC-052's estimator on the heating loop's pumps. The cube is the whole argument: dropping the drives from 80% to 55% is roughly two thirds of the pump power. hw_pump_kw is not one of this rule's points and is not in the HW dictionary, so the host supplies it, along with the speed reduction a commissioned reset would have achieved"
emissions:
  scope: "2"
  method: PROXY_EMISSIONS
verified:
  engine_rev: e2ff2f8
  content_id: "cxf:fnv1a128:6d35dff9c968ba4897bf8966d5555c16"
  date: 2026-08-17
---

## Description

A variable-speed heating loop tells you what its pressure setpoint costs by how
fast the pumps have to run. On a mild day the heating valves are mostly closed,
the loop wants very little water, and a pump holding a properly reset
differential pressure should be somewhere near its minimum. Find it still
turning at 80% in mild weather and the loop is being pressurised to a number
nobody chose for that day — almost always the design-day setpoint the balancer
left behind, being held all year because no reset schedule was ever written.

The evidence is the pump, not the pressure. A differential pressure of 80 kPa
means nothing on its own: one loop's correct value is another's absurdity, and
the setpoint is being *tracked* perfectly in almost every building where this
fault lives — the controller is doing its job, which is precisely why the waste
is invisible on a DP trend. What gives it away is that the work required to
hold the setpoint has not fallen with the load.

Pump power follows the cube of speed, so this is a fault with unusually good
economics for the effort: the repair is a reset schedule and a lower base
setpoint, both remote, and the savings arrive every mild hour of the heating
season without touching a valve. Its cost also compounds. Over-pressurising a
loop pushes water through control valves that are already throttling, which
takes authority away from every valve on the loop and drags the loop's delta-T
down — the finding HW-FC-053 reports independently.

This rule is a library extension. The HVAC FDD Reference's chapter 14 specifies
three hot water rules (HW-FC-050 through 052) and this is not one of them; both
of its thresholds come from PNNL-27338 §4.2, and the numbers that section does
not fix are adopted and argued below.

## Detection Logic

```
yMildWeather = oat > mild_weather_oat                    (false ⇒ host reports NO_EVAL)
yFault = hw_pump_vfd_speed > high_pump_speed AND yMildWeather,
         sustained continuously for alarm_delay
```

Block graph (`rule.cxf.jsonld`):

![HW-FC-054 block graph](diagram.svg)

Four blocks, and both comparisons are PNNL-27338 §4.2's own numbers. `pumpHigh`
is a strict `Reals.GreaterThreshold` at 45%, so a drive sitting exactly on the
threshold reads clear; `mildOat` is the same block at 15.6 °C, so outdoor air
exactly at the floor is NO_EVAL rather than a fault. Both lines are pinned on
the line and from both sides (`pump_speed_exactly_at_the_threshold` with its
0.1% neighbours, `oat_exactly_at_the_mild_weather_floor` with its 0.1 K
neighbours).

`mildOat.y` feeds the conjunction and the `yMildWeather` boundary output. That
second consumer is the rule's whole NO_EVAL story: on a cold day a pump at 80%
is doing exactly what it was bought to do, so `yFault = false` there means the
question was not asked. `cold_day_pumps_working_hard` is that case, and
`evening_cooldown_releases_evaluability` is the one where an alarm and its
evaluability drop on the same tick because the weather turned rather than
because anyone fixed anything — contrast `pumps_slow_after_alarm`, where the
alarm falls and `yMildWeather` stays true, which is what a repair looks like.

`sustained` requires 60 continuous minutes, and continuous means continuous: a
dip below the speed threshold discards the elapsed time rather than pausing it
(`pump_speed_dips_and_restarts_the_clock` lands its alarm a full hour after the
second crossing).

## Possible Diagnoses

Library-authored — PNNL-27338 §4.2 specifies a threshold test, not a list of
causes:

1. No DP reset schedule at all. The usual finding, and the reason this rule
   exists: the loop holds one setpoint from October to May. HW-FC-055 tests the
   setpoint trend directly and is the confirming rule
2. A reset schedule that exists but resets from the wrong thing, or across too
   narrow a range — outdoor-air-based reset on a loop whose load is driven by
   internal gains, or a 10 kPa span on a loop that could give up 60
3. The base setpoint itself set too high. A commissioned reset schedule whose
   *whole* range sits above what the loop needs looks healthy on a setpoint
   trend and still fails this test, which is the case HW-FC-055 cannot see
4. Balancing valves throttled hard at the far end of the loop, so the pumps
   must overcome a restriction that a rebalance would remove
5. The DP sensor in the wrong place. A sensor at the pump discharge rather than
   near the hydraulically most remote coil forces the loop to be pressurised for
   a distribution loss the coils never see
6. Manual override or hand mode on the drive — a pump left at a fixed speed
   after a service call, which reads identically to a setpoint that is too high
7. Oversized pumps against an actual load the building never reached. The case
   with no repair beyond a trim or a lower setpoint, where the speed is telling
   the truth

## Energy Impact

EXCESS_CONSUMPTION, MEDIUM confidence, PROXY_ESTIMATION. The waste is pump
electricity and the arithmetic is the affinity law:
`pump_waste_kw ≈ hw_pump_kw × [1 − (1 − speed_reduction/100)³]`, CHW-FC-052's
estimator applied to the heating loop's drives. Because power goes as the cube
of speed, the recoverable fraction is large for a modest setpoint change — a
loop that could run at 55% instead of 80% is giving away roughly two thirds of
its pump power for every hour it does not.

PNNL-27338 §4.2 publishes no savings range of its own, so `savings_range`
carries the DP-reset figure this library already uses on the chilled water side
(0.5-2% of site energy, PNNL-25985 EEM-10/11 via CHW-FC-052 and the
`vfd-pump-faults` playbook). Treat it as an order of magnitude rather than a
site estimate: the actual number depends on pump horsepower and on how many
mild hours the heating season has, and a shoulder-season-heavy climate can beat
the range comfortably.

Confidence is MEDIUM because the evidence is one step removed from the fault.
The rule observes that the pumps are working hard when the weather says they
should not be; it does not measure the setpoint, and a plant can fail this test
for the honest reasons in diagnoses 4 through 7 without the DP setpoint being
wrong at all. What makes it worth shipping at that confidence is the cost of
the check: two points already in the dictionary, and a repair that is remote and
free when the finding is right.

## Emissions Impact

Scope 2, PROXY_EMISSIONS, MEDIUM confidence. All of the direct waste is
purchased electricity for the distribution pumps, so the scope assignment does
not vary by site the way a boiler fault's does, and the marginal operating
emissions rate is the right factor. There is a second-order Scope 1 term this
card does not try to quantify: over-pressurising the loop costs valve authority
and therefore loop delta-T, and a heating plant that cannot make its delta-T
burns extra fuel through staging and lost condensing operation — that penalty
belongs to HW-FC-053, which measures it directly.

## Deviations

- **This rule is a library extension, not a transcription.** The HVAC FDD
  Reference's ch.14 specifies HW-FC-050, 051 and 052 and stops;
  `faults/hw/README.md` frames FC-053 through 057 as library-authored rules
  grounded in PNNL-27338 §4. The name, severity 3 and `method: rule` are that
  index's and are not open to argument here. Both thresholds are §4.2's, the
  graph is HW-FC-052's shape, and everything else — the diagnosis list, the
  energy claim, the evaluability output, the suppression call — is authored on
  this card.
- **`hw_dp` and `hw_dp_sp` are deliberately not bound, and the rule is better
  for it.** The obvious-looking version of this fault compares the loop's
  differential pressure against its setpoint, or against a threshold. Both were
  rejected. A DP *tracking* comparison measures whether the pressure controller
  is working, and in almost every building carrying this fault it is working
  perfectly — that is why the waste is invisible. A DP *threshold* would need a
  per-loop number with no published basis: 60 kPa is generous on one loop and
  starvation on another, and PNNL-27338 §4.2 does not test the
  pressure either. Pump speed is the quantity that already normalises for the
  loop, because it is what the plant must do to hold whatever setpoint it has.
  Binding the two pressure points as context would also make them binding
  obligations under this library's points convention, for signals the graph
  never reads. They stay in the dictionary for HW-FC-055 and for the playbook's
  verification step, and `points` stays at two.
- **`yMildWeather` is an evaluability output, and HW-FC-052's identical
  comparison deliberately is not.** Both rules compare `oat` against a mild
  threshold; the two comparisons mean different things. In HW-FC-052 the mild
  weather *is* the fault claim — the plant should be locked out and is not — so
  a cold day is a healthy verdict, not an unasked question. Here the mild
  weather is what makes a pump-speed reading interpretable at all: on a design
  day a pump at 80% proves nothing about the setpoint, so `yFault = false`
  below the floor must not be read as a clean loop. Exposing the conjunct adds
  no logic and changes no verdict, and it is a comparison against a parameter
  rather than an echo of a boundary input, which is what SCHEMA.md asks such an
  output to be. Same shape as CHW-FC-053's `yLoadOk`.
- **15.6 °C and 16.0 °C are two different parameters and must stay that way.**
  This rule's `mild_weather_oat` is PNNL-27338 §4.2's 60 °F converted and
  rounded to a tenth (15.5556 → 15.6, the same rounding convention CHW-FC-053
  used for its 10 °F); HW-FC-052's `heating_plant_lockout_temp` is 16.0 °C from
  the HVAC FDD Reference's ch.14 card. They are within half a kelvin and they
  are not the same number: one is the temperature above which a heating plant
  should be off, the other the temperature above which pump speed becomes
  evidence. A site that raises its lockout to 18 °C has said nothing about where
  this rule's inference starts being valid, and a host that consolidates them
  will silently retune two rules with one edit.
- **Strict `>` on both comparisons.** CDL `Reals` has no `GreaterEqual`, and
  §4.2's own arithmetic is strict. A drive at exactly 45.0% and outdoor air at
  exactly 15.6 °C both read clear; both disagreements are measure-zero on
  real-valued signals and both err toward silence. Six vectors pin the two
  lines: each exactly at its threshold, and each a tenth either side. Sites
  whose BAS quantises drive speed to whole percent or outdoor air to whole
  degrees will sit on a boundary often enough to notice, and should set the
  parameters between two quantisation levels.
- **Persistence stands in for PNNL's window average.** §4.2 tests
  `avg_pump_vfd` and `avg_OAT` over a 15-60 minute data window (§1.2); this rule
  consumes instantaneous points and requires the condition continuously.
  `pump_speed_dips_and_restarts_the_clock` pins the difference: a 10-minute dip
  to 40% restarts the hour here, where an average over the window would have
  carried straight through it. The trade is a rule that never alarms on a
  transient and can be talked out of a genuine finding by a loop that oscillates
  around the threshold — worth it on a fault whose whole character is that it
  sits still for months.
- **No run-status conjunct.** The rule reads speed alone and relies on a
  stopped pump reporting 0%, which `plant_off_in_mild_weather` pins. Adding
  `hw_pump_status` would guard against drives that latch their last commanded
  speed while stopped, at the cost of a third point on a two-point rule and a
  second binding obligation for a case that is a wiring question rather than a
  plant one. It is `preconditions` text instead, alongside the multi-pump
  binding rule (lead drive or host-computed maximum, never an average across a
  lead/standby pair).
- **The domestic-hot-water confound is the same one HW-FC-052 documents, and it
  is not detectable here either.** A plant circulating in July for a service
  water or process load runs its pumps in mild weather for a legitimate reason
  and produces identical values on both points. Combined heating/DHW plants are
  common in older buildings; the answer is to exclude the rule, bind a pump that
  does not serve DHW, or accept summer noise — never to raise
  `mild_weather_oat`, which converts a false positive into a silent miss across
  the whole shoulder season.
- **`suppresses` and `suppressed_by` are both empty, and the HW-FC-055 pairing
  is the reason to say so explicitly.** A flat DP setpoint is the usual root
  cause of a pump that never slows down, so the tempting edge is
  "HW-FC-055 suppresses HW-FC-054". It is wrong in both directions. The two
  rules can fire independently and each carries information the other does not:
  a plant with a commissioned reset schedule whose entire range sits too high
  fails this test and passes HW-FC-055's (diagnosis 3), while a plant with a
  flat setpoint that happens to be low enough that the drives stay under 45% in
  mild weather fails HW-FC-055's and passes this one. Where both fire they are
  cause and consequence, and suppressing the consequence would delete the energy
  claim that justifies writing the reset schedule — this rule is the one that
  says the pumps are actually paying for the missing reset, which is the number
  an operator needs to approve the work. So: `related`, not suppression. The
  edge would also have to be declared on both cards, and HW-FC-055 is not
  written yet; its author is free to disagree, and this bullet is the argument
  they would have to answer.
- **`playbooks: [hot-water-plant-faults]`, not `missing-reset`.** The hot water
  playbook's Step 3 already ends on this finding — high HW differential pressure
  setpoints, reset from the most-open valve — and its energy row names the same
  PNNL-27338 measures. `missing-reset` is the natural home for HW-FC-055, whose
  verification step is a setpoint trend; this rule's verification step is a
  pump-speed trend against outdoor air, which that playbook does not describe.
  The hot water playbook's Applies-To row names FC-050 through 052 and not this
  card, which is the index owner's edit rather than this card's.
- **`clusters: []`.** `clusters/clusters.json` has no hot water cluster, and
  CLU-02 (Missing Reset Strategy) is triggered by AHU-FC-057 with AHU and CHW
  members — this rule is a plausible future member, and adding it is the cluster
  owner's edit rather than this card's.
- **`alarm_delay = 3600 s` is adopted.** PNNL-27338 specifies a data window and
  a minimum sample count, not an alarm persistence, so there is no reference
  number to transcribe; an hour matches HW-FC-052 and HW-FC-053, and this fault
  moves on a scale of months.
- `sustained.delayOnInit = true` (the CDL default is `false`), the library's
  standing choice: a plant already pumping hard in mild weather when the
  controller restarts waits out the full hour rather than alarming on the first
  tick.
- **`TrueDelay` asserts at exactly `T + delayTime`, so the realized test is
  "above both thresholds for strictly more than `alarm_delay`" at tick
  resolution.** `pumps_slow_on_the_maturity_tick` (drives fall at exactly
  3600 s, never reported) and `pumps_slow_one_tick_later` (asserts for one tick
  and clears) pin both sides of that edge.
- **No published test vectors exist for this algorithm.** PNNL-27338 §4.2
  specifies thresholds, not cases, so all sixteen scenarios in `vectors.json`
  are authored: three ordinary cases, three sides of the speed threshold, three
  of the evaluability floor, the idle-plant case, the morning crossing into
  evaluability, the two release edges, the restart-the-clock case, and both
  sides of the delay edge.
- Operating states and preconditions are declared in frontmatter for host
  enforcement rather than encoded in the block graph, per the library's design
  stance.

## Notes

Read `yMildWeather` before reading `yFault`. Through most of a heating season
this rule is not evaluating anything, and that is the intended behaviour: it
has one useful window, the mild hours, and it is silent by construction in the
weather where a hard-working pump proves nothing.

Verify with a scatter plot before dispatching anyone, because it costs nothing.
Plot pump speed against outdoor air for a fortnight of the shoulder season. A
loop with a working reset draws a slope; a loop with this fault draws a
horizontal band, and the height of that band is roughly what the setpoint is
costing. Check the DP setpoint trend on the same axes — if it is flat, the
finding is HW-FC-055's as well and the reset schedule is the repair; if it
moves and the pumps still do not slow down, the base setpoint is too high and
the repair is a lower number, not a new schedule.

Then find the DP sensor. Diagnosis 5 is the one that survives every remote fix:
a sensor at the pump discharge instead of out at the hydraulically most remote
coil makes the loop hold a pressure that includes distribution losses no coil
ever sees, and no reset schedule written against that sensor can give the
saving back. Moving it is on-site work and usually the largest single win on
this list.

Re-check the loop's delta-T after the setpoint comes down. Excess pressure
takes authority away from every control valve on the loop, so this fault and
HW-FC-053 travel together; a plant that fixes the pressure and does not re-look
at delta-T has usually left half the finding on the table.
