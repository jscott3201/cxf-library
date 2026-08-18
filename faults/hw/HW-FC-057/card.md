---
schema: cxf-library/fault-card/v1
id: HW-FC-057
name: HWS temperature reset not functioning
equipment: hw
status: verified
phase: 2
method: statistical
severity: 3
category: EXCESS_CONSUMPTION
confidence: HIGH
estimation_method: PROXY_ESTIMATION
source:
  - "PNNL-27338 §4.5.2 (no HW supply-temperature reset; daily MAX−MIN of the HWS setpoint against a 10 °F range), pp. 4.16-4.17"
  - "PNNL-27338 §4.4.2 (high HW supply temperature), pp. 4.12-4.13 — the fault this reset exists to prevent"
  - "PNNL-27338 (Katipamula et al. 2018) — adapted via an internal paraphrased deep-read digest, not distributed (rule candidate 7)"
  - "Sibling-rule precedent: AHU-FC-057 (window, OAT-range evaluability, half-range tolerance), CHW-FC-051 (plant-side binding of the same detector)"
  - "Library extension: HVAC FDD Reference v1.0 ch.14 specifies HW-FC-050..052 only — index framing in faults/hw/README.md"
g36: null
clusters: []
suppresses: []
suppressed_by: []
related: [HW-FC-055, CHW-FC-051, AHU-FC-057]
playbooks: [missing-reset, hot-water-plant-faults]
operating_states: "Heating season — boiler plant enabled and serving the loop for the bulk of the evaluation window"
preconditions: "hws_temp_sp must be the active setpoint the boilers track — the plant controller's live value, not a design figure in a schedule table or a boiler's local panel setting that the BAS overrides. On a multi-boiler plant bind the plant-level setpoint; an individual boiler's leaving-water setpoint is set by staging logic and reads flat while the plant resets. oat must be a trustworthy outdoor reading: the whole evaluability test rests on it, and the same sensor that HW-FC-052's diagnosis 5 warns about (in the sun, above a warm roof, or dead at its last value) feeds this rule too. A plant that must hold a fixed supply temperature for a domestic hot water load has a legitimate reason to keep the setpoint flat — Legionella control sets a floor no reset may cross — and combined heating/DHW plants must either be excluded, be bound to a heating-only boiler where the plant has one, or be gated host-side on the DHW load. The plant must be running for most of the window; a boiler off for the season holds the setpoint still for reasons this rule cannot see. Evaluability is signalled in-rule by yOatVaried: when it is false the verdict is NO_EVAL, not healthy."
points:
  - hws_temp_sp
  - oat
outputs:
  - name: yFault
    description: True while the hot water supply temperature setpoint has stayed flat over the evaluation window despite sufficient outdoor-air variation, for at least alarm_delay
  - name: yOatVaried
    description: Evaluability signal — true when OAT has varied enough within the evaluation window for a flat setpoint to mean anything; false means NO_EVAL and the host must ignore yFault
params:
  evaluation_window:
    default: 604800.0
    unit: s
    description: Window over which setpoint flatness and OAT variation are assessed (7 days); drives both baseline sample periods and both dwell timers
    cxf: [spRef.samplePeriod, oatRef.samplePeriod, spFlatHeld.delayTime, oatFlatHeld.delayTime]
  sp_flat_tolerance:
    default: 2.75
    unit: "°C"
    description: Max deviation of hws_temp_sp from its sampled baseline to count as flat — half of PNNL-27338 §4.5.2's 10 °F (5.6 °C) minimum expected setpoint range
    cxf: spFlat.t
  oat_variation_tolerance:
    default: 4.0
    unit: "°C"
    description: "Max deviation of oat from its sampled baseline to still count as flat (half AHU-FC-057's 8 °C minimum OAT range; PNNL-27338 states no weather gate for this check — see Deviations)"
    cxf: oatFlat.t
  alarm_delay:
    default: 86400.0
    unit: s
    description: Fault persistence before alarm (24 h)
    cxf: persist.delayTime
energy_impact:
  affected_subsystem: Boiler plant efficiency and distribution standby loss
  savings_range: "1-3% site energy for HW supply-temperature reset and DP reset together (playbooks/hot-water-plant-faults.md, per PNNL-27338); no split between the two measures is published"
  climate_sensitivity: heating-dominant
  runtime_estimation: "annual_waste = boiler_annual_fuel × reset_savings_fraction, where reset_savings_fraction is the host's estimate of what an OAT-scheduled reset would recover on this plant. Two mechanisms feed it and the host must decide which apply: distribution and standby losses fall with the water-to-space temperature difference, and a condensing boiler gains a step change once its return water drops below roughly 55 °C. Neither the fuel figure nor the fraction is in this rule's point set"
emissions:
  scope: "1"
  method: PROXY_EMISSIONS
verified:
  engine_rev: e2ff2f8
  content_id: "cxf:fnv1a128:d14378530edda50c195f5757ef979370"
  date: 2026-08-17
---

## Description

The hot water supply setpoint sits at its design value from October to April
while the weather moves through thirty degrees underneath it. A working reset
schedules the supply temperature against outdoor air — hot water when it is
cold out, cooler water when it is mild — and the savings arrive by two routes:
every metre of distribution pipe sheds less heat, and a condensing boiler that
sees return water below roughly 55 °C picks up something like ten points of
combustion efficiency it cannot reach at design temperature. A plant pinned at
its design setpoint spends the whole heating season outside that regime.

This rule is a **library extension**. The HVAC FDD Reference's chapter 14
specifies three hot water rules — short-cycling, efficiency degradation and the
OAT lockout — and no reset checks. The detection here is grounded in
PNNL-27338 §4.5.2, whose hot-water measure-identification algorithm flags a
plant whose supply setpoint moves less than 10 °F across a day. That threshold
and the shape of the test are the reference material; the window, the weather
gate, and every block in the graph are this library's, argued in Deviations.

The weather gate is what makes a flat setpoint evidence. Hot water reset is
driven by outdoor air in nearly every sequence that implements it, so a week
where the weather did not move is a week where a correctly programmed reset had
nothing to do — and a frozen OAT sensor, which is one of the things that
*causes* a flat setpoint, also flattens the driver and takes the rule out of
service instead of letting it report a fault it cannot substantiate. That is
what `yOatVaried` is for, and why the host must read it first.

## Detection Logic

```
baseline(x)  = x sampled and held every evaluation_window (7 days)
sp_flat      = |hws_temp_sp − baseline(hws_temp_sp)| < sp_flat_tolerance,
               continuously for evaluation_window
oat_flat     = |oat − baseline(oat)| < oat_variation_tolerance,
               continuously for evaluation_window

yOatVaried   = NOT oat_flat        (false ⇒ host reports NO_EVAL)
yFault       = sp_flat AND yOatVaried, sustained for alarm_delay
```

Block graph (`rule.cxf.jsonld`):

![HW-FC-057 block graph](diagram.svg)

This is AHU-FC-057's detector with the boiler plant's points bound to it, and
the mechanism is unchanged. Two symmetric chains compare each signal against a
weekly sample-and-hold baseline (`Discrete.Sampler`, which emits the live input
on its first tick, so there is no startup artifact). `spFlatHeld` asserts only
after the setpoint has stayed within tolerance of that baseline continuously
for a full window; any reset activity of 2.75 °C or more restarts it.
`oatFlatHeld` does the same for outdoor air, and its negation is `yOatVaried`:
"not varied" means a full window of continuous flatness, so the signal is
optimistically true during the first window after startup — harmless, because
`yFault` needs the same full window before it can fire at all.

Both dwell timers fire on the same tick when plant and weather are flat
together, so the fault conjunction is false by construction on that tick and
there is no boundary race; `oat_within_variation_tolerance` pins it. `persist`
(24 h) filters the remainder. Worst-case time to alarm from cold start:
`evaluation_window + alarm_delay` — 8 days. A plant whose reset stops mid-run
alarms 8 days after the setpoint settles, which `sp_goes_flat_mid_run` pins at
exactly 734,400 s for a 12 h startup transient.

## Possible Diagnoses

The reference algorithm publishes a detection test and no diagnosis list; these
are this library's, in the order a technician should work them.

1. HWS reset never programmed. The common case, and a desk fix
2. Reset programmed but disabled, or the setpoint overridden to a fixed value
   after a cold-weather complaint and never released
3. Reset schedule configured with endpoints so close together that the plant
   never leaves its design temperature — programmed, reviewed, and useless
4. Boilers running to their own local panel setpoints and ignoring the BAS
   value entirely, in which case the trended setpoint may even be resetting
   while the water does not
5. Domestic hot water load holding the plant at a fixed temperature. Not a
   fault; a precondition this rule cannot check (see Deviations)

## Energy Impact

EXCESS_CONSUMPTION, HIGH confidence, PROXY_ESTIMATION. The savings figure is
the hot water playbook's: HW supply-temperature reset and DP reset together are
worth 1–3% of site energy, with no published split between the two. The share
that belongs to this rule depends almost entirely on the boiler: on a
non-condensing plant the recovery is distribution and standby loss, worth a
few percent of plant fuel, while on a condensing plant a reset that drops
return water under about 55 °C for the mild half of the season is worth
several times that.

Climate sensitivity is heating-dominant for the obvious reason, but the
strongest case for the fix is in mild climates and shoulder seasons, where a
plant pinned at design temperature spends most of its running hours making
water far hotter than any zone is asking for.

## Emissions Impact

Scope 1, PROXY_EMISSIONS, HIGH confidence; typical 500–5,000 kg CO₂e/yr for a
plant carrying an uncommissioned setpoint through a heating season. The scope
is what separates this rule from its DP twin: this is combustion at the site,
on a static fuel emissions factor, so a site that has decarbonised its
electricity still owns every kilogram of it. Plants heated electrically or by
heat pump move the accounting to Scope 2 and the marginal operating emissions
rate; the fault is the same and the host owns the classification.

## Deviations

- **This rule extends the reference rather than transcribing it.** The HVAC FDD
  Reference's ch.14 covers HW-FC-050, 051 and 052 only, so there is no
  reference card behind this one: no published Description, Operating States,
  diagnosis list, tunable-parameter line or test vectors. The detection is
  paraphrased from PNNL-27338 §4.5.2 via the deep-read memo; `name`, `severity`
  and `method` come from `faults/hw/README.md`, which owns the index. Everything
  else is authored, and the bullets below mark which choices had no published
  spec behind them.
- **Daily MAX−MIN → rolling sampled baseline plus dwell.** PNNL's reset checks
  run once a day at midnight over the prior day's setpoint array; this engine
  has no windowed min/max block and no batch clock, and the library settled the
  question at AHU-FC-057 and has reused the answer since. Each chain compares
  its signal against a `Discrete.Sampler` hold refreshed once per window, with
  the tolerance set to half the reference range — the half-range convention,
  because a signal swinging ±t about a baseline spans 2t. Detection is
  equivalent for a setpoint that moves and returns, and slightly conservative
  for monotonic drift inside one window: a setpoint sliding steadily by 5 °C
  across the week crosses the tolerance and clears the dwell, where a range test
  would still call it flat.
- **10 °F becomes a 2.75 °C half-range.** PNNL states the threshold in °F and
  the point dictionary carries `hws_temp_sp` in °C, so the conversion happens
  here, once. A 10 °F *interval* is 5.56 °C, half-range 2.78 °C, shipped as
  **2.75 °C** (a 5.5 °C range, 9.9 °F). The rounding is 1% tight — a hair less
  willing to call the setpoint flat, so it errs toward silence — and 2.75 is
  exactly representable in binary floating point, which is what lets
  `sp_at_flat_tolerance` pin the boundary to the bit rather than to within a
  rounding error.
- **The 7-day window is adopted from AHU-FC-057, not from PNNL.** PNNL's window
  is one calendar day, which works there because the daily batch discards its
  evidence at every midnight; a rolling dwell does not, and a one-day dwell
  would alarm on the first stable weekend of the season. Seven days is the
  window the reference specifies for the air-side reset checks this rule copies
  its mechanism from, and it is also what makes the weather gate meaningful: a
  front takes days to move through, so a window shorter than that would report
  NO_EVAL constantly. `evaluation_window` drives all four timing parameters
  together and hosts must set them as a group.
- **The OAT gate is a library addition; §4.5.2 has none.** PNNL's test is a bare
  range test on the setpoint trend with no driver condition at all, so a plant
  holding its setpoint through a genuinely stable week is a fault by that
  algorithm and NO_EVAL by this one. The conjunct can only make the rule
  quieter — it never creates a finding — and it is the same trade AHU-FC-057
  made against the same reference for the same reason. It also buys the
  degradation property described above: a dead OAT sensor flattens the driver
  and suppresses the rule, rather than letting a flat setpoint the dead sensor
  caused be reported as a controls fault.
- **`min_oat_range_for_eval` = 8 °C is adopted from AHU-FC-057.** PNNL supplies
  no figure because it has no gate. The air-side card's 8 °C (shipped here as
  `oat_variation_tolerance = 4 °C`, half-range) is a low bar that any heating
  season clears easily — 8 °C of movement across a week is unremarkable weather
  anywhere a boiler runs — and it is the value a host tuning both rules would
  expect to find the same on each. Sites in
  genuinely stable climates should lower it; the direction matters, since
  lowering it makes the rule evaluable more often and therefore noisier.
- **The DHW case is a precondition, not a detection.** A plant that must hold
  60 °C for domestic hot water has a legitimate flat setpoint, and nothing in
  these two points distinguishes it from a plant nobody programmed. This is the
  same limitation HW-FC-052 records for the OAT lockout, and it has the same
  answer: exclude the rule, bind a heating-only boiler where the plant has one,
  or gate host-side on the DHW load. Widening `sp_flat_tolerance` to silence
  the alarm would convert a false positive into a blind spot.
- **NO_EVAL surfaced as `yOatVaried`.** Boolean block logic has no tri-state, so
  evaluability is a second boundary output the host consults before
  interpreting `yFault` — false means NO_EVAL, never healthy. Same name and
  same inverted-flat semantics as AHU-FC-057, deliberately, so a host binding
  both rules reads one convention. It also earns its place as an output rather
  than an echo of a boundary input, being a stateful window test over the
  signal's own sampled baseline rather than a comparison a host could recompute
  from the input alone.
- **`Reals.MovingAverage` rejected, and the tick band that follows.** The engine
  implements it with a fixed 64-checkpoint ring, so a window needs
  `dt ≥ evaluation_window/63` — 9,600 s (2 h 40 min) at seven days — before the
  window stops silently dropping its oldest samples. No BAS ticks that slowly,
  so the block is unusable here; AHU-FC-057 found this and every reset rule
  since has inherited the finding. The sampler-and-dwell chain has no lower
  bound on tick period at all. Its upper bound is what you want to see: a reset
  excursion shorter than one tick is invisible to the flatness test, so trend at
  5–15 min. These vectors run at 5 min.
- **Strict comparisons, and both measure-zero boundaries pinned.**
  `Reals.LessThreshold` is `u < t`, so a signal sitting exactly on a tolerance
  falls on the *not-flat* side: a setpoint deviating exactly 2.75 °C from its
  baseline clears the flatness dwell, and an outdoor temperature deviating
  exactly 4 °C counts as varied. Equality is measure-zero in continuous data and
  perfectly reachable in a BAS that quantises setpoints to whole degrees, so
  both boundaries are pinned from both sides in the vectors —
  `sp_at_flat_tolerance` / `sp_within_flat_tolerance` and
  `oat_at_variation_tolerance` / `oat_within_variation_tolerance`. The delay
  edges are pinned the same way, to the tick: the alarm asserts at exactly
  691,200 s from a cold start and at exactly 734,400 s when the setpoint goes
  flat 12 h into the run, and `yOatVaried` drops at exactly 604,800 s.
- **`alarm_delay` = 24 h implemented as `TrueDelay` on the fault conjunction**;
  the evaluation window itself is enforced by the two flatness dwells.
  `delayOnInit = true` on every `TrueDelay` (startup conservatism per
  AHU-FC-050), so a rule loaded onto a plant that is already faulted still waits
  the full window plus delay before it says so. PNNL has no analog to the delay,
  since its whole evaluation is one shot per midnight.
- **Two playbooks, matching HW-FC-055.** `missing-reset` owns the reset family's
  verification step — plot the setpoint against its driver over the window — and
  `hot-water-plant-faults` already carries this fault's remedy in its step 1
  (program an OAT-based reset schedule). Neither covers the fault alone and both
  index owners are other writers, so this card lists both rather than stretching
  one.
- **Blind spots.** The rule reads the setpoint, never the water: a plant whose
  setpoint schedules beautifully while the boilers make design-temperature water
  anyway is diagnosis 4 and invisible here — pair with HW-FC-051 and the planned
  HW-FC-056 to see it. Diagnoses 1–3 are one signature. A reset driven by
  something other than weather (a valve-request trim-and-respond sequence, which
  some hot water plants do run) is legitimately flat in stable weather and
  legitimately active when the weather is still, so on those plants the gate is
  loosely coupled to the thing it is gating: the rule stays correct but reports
  NO_EVAL more often than it needs to. And a plant that is simply off for the
  window holds both signals flat; `yOatVaried` will usually catch it, but the
  host's operating-state gate is what should.

## Notes

Fix path is the [missing-reset](../../../playbooks/missing-reset.md) playbook
for the verification step and
[hot-water-plant-faults](../../../playbooks/hot-water-plant-faults.md) for the
remedy, whose step 1 already gives the schedule shape — hotter water at design
outdoor temperature, resetting down toward the mild end — with a worked example
range. Plot `hws_temp_sp` against `oat` over the window first: a flat line
against moving weather is this fault, and a line that moves but never leaves a
2 °C band is diagnosis 3, which looks programmed in a screenshot and behaves
almost as badly.

`clusters` is deliberately empty. CLU-02 ("Missing Reset Strategy") is an
AHU-scoped cluster triggered by AHU-FC-057, and membership is
`clusters/clusters.json`'s to declare, not this card's — the same call the CHW
pair made. A plant that fails both HW-FC-055 and HW-FC-057 has one root cause,
which is that nobody commissioned the hot water resets, and it should be
dispatched as one visit.
