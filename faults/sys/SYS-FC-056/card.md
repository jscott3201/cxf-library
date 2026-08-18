---
schema: cxf-library/fault-card/v1
id: SYS-FC-056
name: Zone heating active during summer / warm weather
equipment: sys
status: verified
phase: 2
method: rule
severity: 3
category: CRITICAL_WASTE
confidence: HIGH
estimation_method: DIRECT_MEASUREMENT
source:
  - "HVAC FDD Reference v1.0 §16, SYS-FC-056 (pdf pp. 145-146) — equation, all three tunables, the four diagnoses, the whole impact profile, and the truncated notes line"
  - "The reference's own provenance line for that card: PNNL RetuningOpps Z01; ~20% prevalence (PNNL 151-building study)"
  - "Library precedent: VAV-FC-055 (the zone-level reheat rule this one overlaps and does not duplicate — see Deviations), VAV-FC-052, AHU-FC-050"
g36: null
clusters: [CLU-05]
suppresses: []
suppressed_by: []
related: [VAV-FC-055, VAV-FC-052, VAV-FC-050, AHU-FC-050, SYS-FC-051]
playbooks: [vav-min-flow-reheat]
operating_states: "all. There is no occupied gate and no mode gate, because the reference specifies none and because the fault is defined by the weather rather than by the schedule: a zone reheating at 26 degC outdoors is waste at 03:00 as surely as at 15:00, and a night-setback heating cycle at that outdoor temperature is itself the finding."
preconditions: "Instantiated PER ZONE. `rht_vlv_cmd` is one VAV box's or one FCU's reheat command, not a building aggregate, and the deployment runs one instance per zone (the reference files this rule under SYS and scopes it to VAV and FCU equipment). `rht_vlv_cmd` must be the modulating command in percent of travel; a two-position coil that reports only on/off should be bound as 0/100 and the threshold left where it is, and a coil whose command is in some other unit needs `reheat_active_threshold` retuned to it. `oat` must be a fresh, shaded site outdoor air temperature: this rule's standing false positive is a sun-baked wall sensor reading 23 degC on a 17 degC afternoon, and the sensor-health rules (SYS-FC-054/100/101) are what adjudicate that before the finding is believed. Where a zone has a legitimate reason to heat above the lockout — a freezer anteroom, a pool hall, a humidity-controlled space with reheat downstream of a dehumidification coil — the binding is wrong rather than the rule, and that zone should not be instantiated."
points:
  - rht_vlv_cmd
  - oat
outputs:
  - name: yFault
    description: True while this zone's reheat command has stayed above reheat_active_threshold with outdoor air above zone_heating_lockout_temp, continuously for alarm_delay
params:
  reheat_active_threshold:
    default: 10.0
    unit: "%"
    description: "Reheat command above which the coil counts as actively consuming energy rather than leaking through a shut valve (the reference's own 10%, and the same number VAV-FC-055 uses for the same test)"
    cxf: rhtOn.t
  zone_heating_lockout_temp:
    default: 21.0
    unit: "°C"
    description: "Outdoor air temperature above which no zone should be calling for heat — the temperature an OAT heating lockout would be programmed at (the reference's own 21 °C / 70 °F). Note this is 3 K above VAV-FC-055's cooling_season_oat and asks a different question; see Deviations"
    cxf: warmOut.t
  alarm_delay:
    default: 1800.0
    unit: s
    description: "Continuous persistence required before the alarm asserts (30 min). This is the reference's published AlarmDelay and also stands in for the `lockout_check_duration` its equation names but never publishes — one knob, see Deviations"
    cxf: persist.delayTime
energy_impact:
  affected_subsystem: Zone reheat energy during warm weather (pure waste)
  savings_range: "100% of reheat energy while active; up to 20% of zone annual energy (PNNL RetuningOpps Z01; ~20% prevalence in the PNNL 151-building study)"
  climate_sensitivity: cooling-dominant
  runtime_estimation: "waste_kw = rht_vlv_cmd/100 × vav_rht_capacity_kw, accumulated over the hours yFault holds; the cooling energy spent on the air the coil is undoing is waste on top and belongs to the air handler's own accounting"
emissions:
  scope: "1"
  method: DIRECT_EMISSIONS
verified:
  engine_rev: e2ff2f8
  content_id: "cxf:fnv1a128:81170d88e808d51ed3e4980ee1e99faa"
  date: 2026-08-17
---

## Description

A reheat coil is heating a zone while it is 26 degC outside. Nothing about the
building needs that heat, and whatever the coil delivers, the plant paid to cool
the air first — it is simultaneous heating and cooling seen from the zone end,
and PNNL found it in about a fifth of the buildings it retuned.

The usual cause is the absence of a control decision rather than the failure of
one. Most zone sequences will happily call for reheat any time the space
temperature falls under its heating setpoint, and nothing in that logic knows
what the weather is doing; a zone under an overcooled supply duct in July will
ask for heat all afternoon and get it. The fix is a line of programming — lock
the reheat valve out above an outdoor air temperature — which is why this fault
belongs to the retuning literature rather than to the hardware failure
literature, and why one instance of it usually means the whole zone family is
affected.

The rule is two comparisons and a timer. It is filed in the system chapter
because the reference files it there, and it is instantiated per zone because
that is the only thing it can mean: `rht_vlv_cmd` is one box's valve.

## Detection Logic

```
yFault = rht_vlv_cmd > reheat_active_threshold
     AND oat > zone_heating_lockout_temp
     sustained continuously for alarm_delay
```

Block graph (`rule.cxf.jsonld`):

![SYS-FC-056 block graph](diagram.svg)

Four blocks. `rhtOn` asks whether the coil is consuming, `warmOut` whether the
weather makes that indefensible, `both` requires them at the same time, and
`persist` requires them to stay that way for 30 minutes. Either conjunct blocks
the fault on its own, which the vectors pin from both sides:
`warm_weather_valve_closed` is warm weather with a shut valve and
`cold_weather_reheat_wide_open` is a zone doing its job in January.

Both comparisons are strict, which is what the reference writes (`>` in both
terms) rather than a reinterpretation of it — the library's standing
strict-comparison convention costs nothing on this card. A valve reported at
exactly 10.0% and an outdoor air temperature of exactly 21.0 degC each fail
their term, and both edges are pinned from both sides
(`reheat_exactly_at_the_threshold` / `reheat_just_above_the_threshold`,
`oat_exactly_at_the_lockout` / `oat_just_above_the_lockout`). Those exact values
matter more than usual here because 10% and 21 degC are round numbers a retuned
site will park on deliberately.

`persist` starts on the crossing, not at midnight: `morning_warmup_into_a_hot_afternoon`
holds the valve at 45% while the weather crosses the lockout at 600 s, and the
alarm lands at 2400 s. Sustained means continuous — a ten-minute dip below the
lockout discards the elapsed time rather than pausing it
(`cloud_cover_restarts_the_clock`, alarm a full 1800 s after the second
crossing) — and the fault clears on the tick the valve shuts, because
`TrueDelay` delays the rising edge only.

## Possible Diagnoses

The reference's four, in its order:

1. **Zone heating lockout not programmed by OAT.** The common case and the
   cheap fix: the sequence has no weather term at all. It is also the diagnosis
   that explains why these findings arrive in batches — nobody programs the
   lockout for one box
2. **Reheat valve stuck open.** Mechanical, and distinguishable from the trend:
   a stuck valve reads the same command all day and does not respond to a
   commanded close, while a sequence with no lockout tracks the space
   temperature
3. **Zone controller demanding heat due to sensor error.** A zone temperature
   sensor reading low makes the box genuinely believe the space is cold, and
   every part of the control chain then behaves correctly. The finding here is a
   symptom; the sensor rules are what name it
4. **Perimeter heating operating independently of BAS.** Baseboard or radiant
   perimeter on its own thermostat or its own outdoor reset curve, which the BAS
   neither commands nor sees. Where the reheat command is the only point the
   rule reads, this one shows up as a zone that reheats regardless of what the
   valve is told

## Energy Impact

CRITICAL_WASTE, HIGH confidence, DIRECT_MEASUREMENT — the reference's own
profile, transcribed. This is one of the few faults where the waste term needs
no counterfactual: `waste_kw = rht_vlv_cmd/100 × vav_rht_capacity_kw` for every
hour the condition holds, and every one of those kilowatts is pure loss because
the heat is being applied to air the plant just paid to cool. The reference puts
it at 100% of reheat energy while active and up to 20% of the zone's annual
energy, with ~20% prevalence across the PNNL 151-building study.

Cooling-dominant by climate, since the fault is defined by hours above the
lockout temperature, but the multiplier is what matters: a building runs dozens
to hundreds of these zones and the defect is nearly always systemic, so the
site-level number is the per-zone number times the count of zones sharing the
sequence.

## Emissions Impact

Scope 1, DIRECT_EMISSIONS, HIGH confidence; the reference gives 500-4,000 kg
CO₂e/yr for reheat waste during warm weather, on a static Scope 1 factor. That
assignment assumes hot-water reheat from a gas-fired boiler, which is the common
case. Electric reheat coils, or hot water from a heat pump or a district loop,
move the same kilowatts into Scope 2 — the quantity is unchanged and the
inventory line is not, so hosts should follow the actual heating source rather
than this default (the same caveat VAV-FC-055 carries).

## Deviations

- **`lockout_check_duration` and `AlarmDelay` are treated as one knob.** The
  reference's equation ends "sustained for `lockout_check_duration`" and its
  tunables table then publishes exactly three parameters, none of them named
  that: `zone_heating_lockout_temp`, `reheat_active_threshold`, and
  `AlarmDelay = 30 min`. Both names describe the same thing — how long the
  condition must hold before it is reported — and only one of them has a
  published number, so the graph carries a single `TrueDelay` at 30 minutes and
  the card calls it `alarm_delay`. This is the opposite call from VAV-FC-055 and
  SYS-FC-054, which chain two timers; there, the reference publishes two
  numbers, and inventing a second one here would put a duration in a card that
  no source supports.
- **Both comparisons are strict, matching the reference's own operators.** The
  library's standing deviation — CDL `Reals` has no `GreaterEqual`, so `>=` in a
  source becomes `>` at the boundary — does not apply, because the reference
  writes `>` in both terms. The four boundary vectors exist anyway, since the
  behaviour at exactly 10.0% and exactly 21.0 degC is what a retuning technician
  will land on.
- **Filed under SYS, instantiated per VAV or FCU zone.** The reference's own
  header reads `Equipment: VAV, FCU` while the ID is `SYS-FC-056`, which is a
  tension in the source rather than in this card: the rule is zone-scoped and
  lives in the system chapter because that is where the reference put it. The
  consequence for deployment is one instance per zone and a host-side rollup;
  the consequence for this library is that `rht_vlv_cmd` and `oat` are
  duplicated into `points/sys.points.json` with matched groundings, because lint
  resolves a card's points against its own family dictionary and the dictionary
  entry says so in its notes.
- **No cross-zone aggregation in the graph, and the count is where the real
  diagnosis lives.** One zone reheating in summer is a zone problem; half the
  zones on an air handler reheating in summer is a supply-air-temperature
  problem, and the
  [vav-min-flow-reheat](../../../playbooks/vav-min-flow-reheat.md) playbook's
  step 1.4 turns that ratio into the discriminator. The graph cannot express a
  variable-width zone vector, so the rollup is the host's — the same treatment
  SYS-FC-050 gives its served-AHU set, but without even a derived aggregate
  point, because this rule's answer is per zone and only its *interpretation*
  is per air handler.
- **Overlaps VAV-FC-055 deliberately, and the two ask different questions.**
  VAV-FC-055 is reheat *at minimum flow* during the cooling season: three terms,
  an 18 degC season threshold, and a damper term that exists precisely to
  separate waste from a zone answering a genuine load. This card has no damper
  term and a 21 degC threshold, so it fires on a zone that is genuinely cold and
  genuinely being heated — because above 21 degC outdoors the reference's claim
  is that no zone should be heating at all, whatever the space temperature says.
  A box tripping both is the ordinary case; a box tripping this one alone is
  reheating with its damper open, which points at diagnosis 3 or at an
  overcooled supply duct rather than at minimum-flow configuration. Both are
  CLU-05 members and VAV-FC-055 is its trigger, so the cluster already encodes
  the fix order.
- **No occupancy gate, no mode gate, and no supply-fan gate.** The reference
  specifies none, and adding one would change the fault: unoccupied reheat above
  21 degC outdoors is not an exception to this rule, it is a worse instance of
  it. The one gate that would be defensible — a zone whose reheat coil sits
  downstream of a dehumidification coil, where warm-weather reheat is the design
  intent — is a binding decision rather than a runtime one, and `preconditions`
  puts it there.
- **`oat` drift is the standing false positive and this card does not solve
  it.** A sun-baked or drifted outdoor sensor reading 3 K high manufactures this
  fault across every zone on the site simultaneously, which is also the tell:
  the finding arrives everywhere at once and the trend shows the outdoor sensor
  separating from the weather every afternoon. SYS-FC-054, SYS-FC-100 and
  SYS-FC-101 are the rules that adjudicate `oat` directly; where a host runs
  them, an active sensor finding on the bound `oat` makes this rule NO_EVAL
  through the `adjudicates` fan-out.
- **`persist.delayOnInit = true`** (the CDL default is `false`), the library's
  standing choice: a zone already reheating in warm weather when the controller
  restarts waits out the full 30 minutes rather than alarming on the first tick.
- **`TrueDelay` asserts at exactly `T + delayTime`,** so the realized test is
  "both conditions held for strictly more than `alarm_delay`" at tick
  resolution. `valve_closes_on_the_maturity_tick` (valve shuts at exactly
  1800 s, never reported) and `valve_closes_one_tick_later` (exactly one tick of
  alarm) pin both sides of that edge.
- **`clusters: [CLU-05]` is a declaration, not an edit.** CLU-05 (Zone Heating &
  Cooling Conflict) already lists SYS-FC-056 as a member with VAV-FC-055 as its
  trigger, so this card is claiming a membership written before it. Likewise
  `playbooks/vav-min-flow-reheat.md` already names SYS-FC-056 in its step 2.3
  text but not in its Applies-To row; adding the ID there is the playbook
  owner's edit, flagged here rather than made.
- **The reference publishes no test vectors for this card,** so all thirteen
  scenarios in `vectors.json` are authored: the seasonal pair, each conjunct
  blocking alone, both threshold edges from both sides, the mid-run crossing,
  both sides of the delay maturity tick, the restart-the-clock case, and the
  recovery edge.
- **The reference's Notes block is truncated mid-sentence in the source
  document** — "Found in ~20% of buildings. In perimeter zones this is
  especially" — and is quoted below as far as the source runs. The perimeter-zone
  claim it was introducing is not recoverable from the chapter text and has not
  been reconstructed.
- Severity 3, `method: rule`, phase 2 and the whole impact profile are the
  chapter card's, which matches the provisional row in `faults/sys/README.md`;
  the reference's §5.8.1 index carries no severity column, so the chapter card
  governs.
- Operating states and preconditions are declared in frontmatter for host
  enforcement rather than encoded in the block graph, per the library's design
  stance.

## Notes

Reference note, quoted as far as the source runs: "Found in ~20% of buildings.
In perimeter zones this is especially".

Count the zones before dispatching anyone. This fault is systemic far more often
than it is mechanical: diagnosis 1 is a missing line of sequence logic that
nobody wrote for any box, so the normal shape of the finding is dozens of zones
alarming on the same warm afternoon and clearing together when one lockout is
programmed. A single zone alarming while its neighbours stay quiet is the
unusual case and the one that points at diagnoses 2, 3 and 4 — a stuck valve,
a lying zone sensor, or perimeter heat the BAS does not control.

The remote fix is in the
[vav-min-flow-reheat](../../../playbooks/vav-min-flow-reheat.md) playbook's step
2.3: a summer reheat lockout above an outdoor air temperature, applied in batch,
at no cost. Set the lockout at the reference's 21 degC before arguing about the
number — a site that lowers it too far starts fighting genuine morning heating
loads in the shoulder seasons, and a site that raises it is paying for the
difference in reheat.

Check the outdoor air sensor first, and check it once rather than per zone. It
is the single input every instance of this rule shares, a 3 K error on it moves
every finding at the site together, and verifying it against a hand-held
reference takes ten minutes.
