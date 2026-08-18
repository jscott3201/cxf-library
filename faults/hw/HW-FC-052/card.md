---
schema: cxf-library/fault-card/v1
id: HW-FC-052
name: Boiler or HW pump operating above OAT lockout temperature
equipment: hw
status: verified
phase: 2
method: rule
severity: 3
category: CRITICAL_WASTE
confidence: HIGH
estimation_method: DIRECT_MEASUREMENT
source:
  - "HVAC FDD Reference v1.0 §14 (ch. 'Hot Water Plants', pdf pp. 126-127), HW-FC-052"
  - "PNNL RetuningOpps H01; >25% prevalence (PNNL 151-building study)"
g36: null
clusters: []
suppresses: []
suppressed_by: []
related: [HW-FC-050, HW-FC-051, AHU-FC-052]
playbooks: [hot-water-plant-faults]
operating_states: all
preconditions: "oat must be a trustworthy outdoor reading. The reference's own diagnosis 5 is an OAT sensor reading low, and this rule cannot tell that from a correctly-programmed lockout — a sensor in afternoon sun or above a warm roof fails the other way and hides the fault instead. Cross-check against a nearby weather station or a second outdoor sensor before dispatching on a fleet of these. The plant must not be serving a domestic hot water load: diagnosis 4 is DHW demand legitimately keeping a boiler firing in July, and nothing in three points distinguishes a boiler making 60 °C service water from a boiler heating an empty building. Sites with combined heating/DHW plants must exclude this rule, gate it on the DHW valve position host-side, or accept that the summer months are noise. boiler_status and hw_pump_status must belong to the same plant as oat; on a multi-boiler plant either may legitimately be bound to the OR across boilers, which is the one place in this library where that aggregation is correct (contrast HW-FC-050, where it destroys the measurement). Both status points should be proof of operation — a current switch or a flow proof — rather than the command echoed back from a relay."
points:
  - boiler_status
  - hw_pump_status
  - oat
outputs:
  - name: yFault
    description: True while the boiler or the HW pump has been running with the outdoor air temperature above heating_plant_lockout_temp, continuously for lockout_check_duration
params:
  heating_plant_lockout_temp:
    default: 16.0
    unit: "°C"
    description: Outdoor air temperature above which the heating plant should be locked out. 16 °C (61 °F) is the reference's default and a common code and retro-commissioning value; sites with high-mass buildings or 24-hour perimeter loads sometimes set it higher, and that is a finding rather than a reason to retune
    cxf: mildOat.t
  lockout_check_duration:
    default: 3600.0
    unit: s
    description: How long the plant must run above the lockout temperature before the alarm asserts (60 min). This is the rule's only timer — the reference states no separate AlarmDelay for this card, so the duration is the persistence (see Deviations)
    cxf: sustained.delayTime
energy_impact:
  affected_subsystem: Entire HW plant above lockout temp
  savings_range: 100% of plant energy while active — boiler fuel and pump power both buy nothing
  climate_sensitivity: both (worst in the swing seasons)
  runtime_estimation: "waste_kw = boiler_current_kw + hw_pump_kw — the reference's formula verbatim. Neither term is in this rule's point set: the host supplies the boiler's current fuel input (HW-FC-051's fuel_power where it is metered) and the pump's electrical draw"
emissions:
  scope: "1+2"
  method: DIRECT_EMISSIONS
verified:
  engine_rev: e2ff2f8
  content_id: "cxf:fnv1a128:d6dd066552fff48e4a1b0ebab1cff9e6"
  date: 2026-08-17
---

## Description

The reference calls the outdoor air lockout one of the simplest and
highest-return fixes in its whole catalogue, and the arithmetic is why: above
about 16 °C a commercial building does not need its heating plant, and every
therm the boiler burns and every kilowatt the pump draws while the plant runs
anyway is waste in full. Not a percentage of waste — the whole thing. There is
no efficiency to recover and no setpoint to optimise, because the correct amount
of plant energy at 20 °C outdoors is zero.

It is also, by the PNNL 151-building study, present in more than a quarter of
buildings. Lockouts get left out of a sequence, set to a temperature nobody
revisited, overridden one cold morning in April and never released, or defeated
by a domestic hot water load that keeps the boiler alive all summer. The plant
runs, the building is warm enough that nobody complains, and the finding sits
there through every swing season until somebody trends the boiler against the
weather.

The pump half matters as much as the boiler half and is easier to miss. A
circulator running through a summer against no heating load costs its full draw
in electricity, keeps the distribution piping warm, and pushes heat into
ceilings that the cooling plant then has to remove — which is why the disjunction
in the equation is a disjunction and not a boiler test with a pump footnote.

## Detection Logic

```
yFault = (boiler_status OR hw_pump_status)
     AND oat > heating_plant_lockout_temp
     sustained continuously for lockout_check_duration
```

Block graph (`rule.cxf.jsonld`):

![HW-FC-052 block graph](diagram.svg)

Four blocks, and the shape is the reference's sentence in order. `plantOn` is
the disjunction: either machine running counts as the plant running, and because
it is evaluated tick by tick rather than per point, a lead pump handing over to
a boiler keeps the condition continuously true across the handover. The
`lead_pump_hands_over_to_the_boiler` vector is that case — neither point is true
for a full hour, the plant is, and the alarm still lands at 3600 s. A rule
written as two per-point tests would miss it.

`mildOat` is a strict `Reals.GreaterThreshold`, so exactly 16.0 °C is not above
16.0 °C, and `aboveLockout` conjoins the two. `sustained` is the whole timing
story: one `Logical.TrueDelay` at 60 minutes, which is simultaneously the
reference's `lockout_check_duration` and the only persistence this card has. An
hour is long enough to ride out a morning warm-up finishing as the sun comes up,
a boiler completing the cycle it was in when the outdoor temperature crossed, and
the flow proof chattering on a pump changeover.

Persistence is continuous, not accumulated: a dip back under the lockout
discards the elapsed time rather than pausing it
(`oat_dips_below_lockout_and_restarts_the_clock`), and the alarm falls the
instant the plant stops, with no release delay
(`alarm_clears_when_the_plant_shuts_down`).

## Possible Diagnoses

Transcribed from the reference's HW-FC-052 card:

1. Boiler lockout sequence never programmed. The most common cause and a $0
   remote fix — the sequence exists in every controls vendor's library and
   somebody skipped it at commissioning
2. Lockout setpoint set too high. A plant locked out at 21 °C instead of 16 °C
   looks programmed and behaves almost as badly; this is the one that survives a
   casual review of the sequence
3. Lockout overridden by an operator. Usually a cold snap in the shoulder season
   and an override with no expiry, which is the same failure the after-hours
   family sees on fans
4. Domestic hot water demand keeping the boiler on. Not a fault at all, and this
   rule cannot see the difference — a host precondition rather than a diagnosis
   (see Deviations)
5. OAT sensor reading incorrectly low. Also not a plant fault, also invisible
   here, and worth ruling out first because it is free: compare the reading
   against a weather station before anyone opens a controls panel

## Energy Impact

CRITICAL_WASTE, HIGH confidence, DIRECT_MEASUREMENT. While the fault is active
the entire plant draw is waste — `waste_kw = boiler_current_kw + hw_pump_kw`,
the reference's formula — because there is no heating load for any of it to
serve. That is the strongest energy claim in the hot water chapter, and it is
also the simplest: no baseline, no efficiency, no proxy, just a plant that
should be off and is not.

Climate sensitivity is "both", which reads oddly for a heating fault until the
mechanism is clear. The cost peaks in the swing seasons, when outdoor
temperatures spend weeks above the lockout and a plant left enabled runs
through all of them. In a cooling-dominant climate the same fault also loads the
chillers with the heat the distribution piping sheds. Confidence is HIGH because
both halves of the finding are directly measured: the plant is running or it is
not, and the outdoor temperature is what it is — subject to the sensor caveat
that is diagnosis 5.

## Emissions Impact

Scope 1 + 2, DIRECT_EMISSIONS, HIGH confidence; the reference's typical range is
2,000–15,000 kg CO₂e/yr for an entire hot water plant running above its lockout.
The split across scopes is unusual and worth keeping: the boiler's fuel is Scope
1 on a static combustion factor, the pump's electricity is Scope 2 on the
marginal operating emissions rate, and the two respond to different levers. A
site that has decarbonised its electricity still owns the whole Scope 1 half of
this fault, which makes it one of the better arguments for a lockout sequence in
a building that thinks it has already dealt with its emissions.

## Deviations

- **There is one timer, and it is the reference's `lockout_check_duration`.**
  The reference's tunables line for this card reads "heating_plant_lockout_temp
  = 16°C, lockout_check_duration = 60 min," — a trailing comma and then the
  section ends, exactly as HW-FC-051's does. No `AlarmDelay` appears for this
  card anywhere in the chapter. Rather than adopt one and stack two hours of
  delay on a fault whose whole appeal is that it is unambiguous, this rule reads
  the duration as the persistence, which is what "sustained for
  lockout_check_duration" says in the equation. The consequence is that a host
  wanting a separate alarm persistence must add it downstream; the consequence
  of the other choice would have been an alarm arriving two hours after a
  condition that is fully decided in one.
- **Diagnoses 4 and 5 are host preconditions, not detections.** A boiler firing
  in July for a domestic hot water load and a boiler firing in July because the
  lockout was never programmed produce identical values on all three points, and
  so do a correctly locked-out plant and one whose OAT sensor reads 8 °C low.
  Both are in the reference's diagnosis list, neither is separable inside the
  rule, and both are recorded in `preconditions` so a host can gate or
  cross-check before trusting the verdict. The DHW case is the one that will
  generate false positives at scale — combined heating/DHW plants are common in
  older buildings — and the OAT case is the one that generates silent misses,
  which is worse and has no in-rule remedy at all.
- **Strict `>` at the lockout temperature.** The reference writes
  `OAT > heating_plant_lockout_temp` and `Reals.GreaterThreshold` reads it
  literally; CDL `Reals` has no `GreaterEqual` in any case. A plant running at
  exactly 16.0 °C reads clear. The disagreement is measure-zero on a real-valued
  signal and errs toward silence, and both sides are pinned
  (`oat_exactly_at_the_lockout_temperature`,
  `oat_one_tenth_above_the_lockout_temperature`). A site whose BAS quantises
  outdoor temperature to whole degrees will sit on the boundary often enough to
  notice, and should set the parameter between two of its quantisation levels.
- **The disjunction is plant-level, and the OR across boilers is correct here.**
  The point dictionary notes that a multi-boiler plant may bind `boiler_status`
  to the OR of the individual boiler statuses for this rule. That is the
  opposite of what HW-FC-050 requires, and the reason is that this rule asks
  whether *anything* is running while HW-FC-050 counts transitions of a specific
  burner: an OR preserves the first question exactly and destroys the second.
  Both cards state the constraint so a binding engineer meets it in whichever
  one they read first.
- **`TrueDelay` asserts at exactly `T + delayTime`, so the realized test is
  "above the lockout for strictly more than `lockout_check_duration`" at tick
  resolution.** A plant that stops on the maturity tick is never reported
  (`plant_stops_on_the_maturity_tick`); one that runs a single tick longer
  asserts for that tick and clears (`plant_stops_one_tick_later`). Both sides of
  the delay edge are pinned, and the pair is what makes the boundary observable
  rather than assumed.
- `sustained.delayOnInit = true` (the CDL default is `false`), the library's
  standing choice: a plant already running above its lockout when the controller
  restarts waits out the full hour rather than alarming on the first tick. On a
  fault this slow-moving the difference is cosmetic, but the convention is
  worth more than the exception.
- **`operating_states: all`, and this is deliberate.** Every other rule in the
  hot water chapter is gated to the heating season; this one is the rule that
  detects a plant behaving as though it were the heating season when it is not,
  so gating it on the heating season would delete it. Nothing about the graph
  needs an operating state: it reads two proofs of operation and a temperature.
- **`playbooks: []`.** The nearest playbook is `after-hours-operation`, which
  shares this fault's shape — equipment running when the conditions say it
  cannot be useful — and its remedies are recognisably the same three (find the
  sequence, fix the setpoint, release the override). But it is written around
  occupancy schedules and time-of-day trends throughout, its verification step
  is a schedule overlay this fault has no use for, and its Applies-To list is
  owned by another writer. The schema tolerates an empty list, so this card
  ships one and points at its `source` and diagnosis list instead. VAV-FC-054
  set the precedent for declining rather than stretching.
- **`clusters: []`.** `clusters/clusters.json` defines no cluster containing a
  hot water plant rule. CLU-07 (Unnecessary Plant Operation, triggered by
  SYS-FC-050) is the syndrome this fault belongs to on the heating side, and
  when the `sys` family lands this card is a candidate member; adding it is the
  cluster owner's edit, not this card's.
- **The energy formula's inputs are not this rule's inputs.**
  `waste_kw = boiler_current_kw + hw_pump_kw` needs a fuel or firing measurement
  and a pump power measurement, and the hot water point dictionary carries
  neither as a plant-power point. The host supplies them — `fuel_power` from
  HW-FC-051's point set where it is metered, pump draw from the pump or drive
  family — and the formula is transcribed unchanged otherwise.
- **No test vectors are transcribed, because the reference publishes none for
  this card.** All twelve scenarios in `vectors.json` are authored from the
  equation and replayed against the pinned engine rev.
- Severity 3, phase 2, `method: rule`, `category: CRITICAL_WASTE`, and both
  tunable defaults are the reference's chapter 14 card. `g36: null` — this is a
  PNNL retro-commissioning finding (RetuningOpps H01), not a G36 clause.

## Notes

Check the outdoor air sensor before dispatching anyone. It is diagnosis 5, it is
free, and it is the only diagnosis on the list where the correct action is to
fix the measurement rather than the plant. A sensor reading low turns a
correctly-programmed lockout into a plant that runs all summer, and the same
sensor is feeding whatever reset schedules the building has, so finding it
resolves more than this fault. The economizer playbook makes the same argument
about the same sensor from the air side.

This rule and AHU-FC-052 are the same finding at different scales, and on a site
where both fire the plant is the one to fix first: an air handler running
after-hours wastes its own fan and coil energy, while a heating plant running
above its lockout wastes fuel for every zone it serves. They do not suppress
each other — different equipment, different sequences, different owners — but a
building with both usually has one cause, which is a controls contractor who
left the schedules and lockouts for a commissioning phase that got cut.

The DHW caveat deserves a decision before deployment rather than after. On a
combined heating/DHW plant this rule will alarm every summer day and the right
response is not to widen the parameter — 16 °C is correct — but either to
exclude the rule, to gate it host-side on the heating loop's isolation valve or
the DHW valve position, or to bind `boiler_status` to a boiler that does not
serve DHW where the plant has a dedicated one. Widening the lockout to silence
the alarm converts a false positive into a real fault.
