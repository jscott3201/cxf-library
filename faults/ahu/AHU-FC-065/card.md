---
schema: cxf-library/fault-card/v1
id: AHU-FC-065
name: Supply fan operating at excessive static pressure
equipment: ahu
status: verified
phase: 2
method: rule
severity: 3
category: EXCESS_CONSUMPTION
confidence: HIGH
estimation_method: PROXY_ESTIMATION
source:
  - "HVAC FDD Reference v1.0 §9, AHU-FC-065"
  - "PNNL-25985 EEM-12/EEM-15"
  - "NIST TN 2024"
  - "PNNL-27338"
g36: null
clusters: [CLU-02]
suppresses: []
suppressed_by: []
related: [AHU-FC-058, AHU-FC-001]
playbooks: [missing-reset]
operating_states: "Occupied, fan running"
preconditions: "AHU serves multiple zones; zone damper feedback available and aggregated by the host into zone_dmpr_pos_max, as AHU-FC-058. When zone damper data is missing or stale, the verdict is NO_EVAL, not healthy."
points:
  - dsp
  - dsp_sp
  - zone_dmpr_pos_max
  - sf_status
outputs:
  - name: yFault
    description: True while duct static pressure has held above high_sp_fraction of its setpoint with every zone damper below low_demand_damper_threshold and the fan running, for at least alarm_delay
params:
  high_sp_fraction:
    default: 0.95
    unit: "1"
    description: Fraction of the DSP setpoint above which the fan counts as running at the top of its pressure band
    cxf: scaled.k
  low_demand_damper_threshold:
    default: 50.0
    unit: "%"
    description: Highest zone damper position below which no zone is asking for the pressure being delivered
    cxf: dmprLow.t
  alarm_delay:
    default: 1800.0
    unit: s
    description: Continuous fault persistence required before the alarm asserts (30 min)
    cxf: persist.delayTime
energy_impact:
  affected_subsystem: AHU fan energy
  savings_range: 5-30% of fan energy (fan power scales with the cube of pressure; PNNL-25985 EEM-12)
  climate_sensitivity: neutral
  runtime_estimation: "excess_fan_kw = ahu_fan_design_kw × [1 − (needed_dsp/actual_dsp)³]"
emissions:
  scope: "2"
  method: PROXY_EMISSIONS
verified:
  engine_rev: e2ff2f8
  content_id: "cxf:fnv1a128:7137eb21f1dba596056b75ab058fd631"
  date: 2026-08-17
---

## Description

The fan holds duct static pressure at the top of its band while every zone
damper sits well below fully open. Those two facts together say the setpoint is
higher than the system needs: the dampers are throttling away pressure the fan
spent energy producing, and the excess leaves as noise, leakage, and heat. Fan
power scales with the cube of pressure, so the arithmetic is brutal in both
directions — a setpoint 20% above what the worst zone needs costs roughly half
again the fan energy, and trimming it back returns that energy immediately, at
no capital cost. DSP reset is absent in 74% of buildings (PNNL 151-building
study); this rule is the CLU-02 member that catches the resulting operating
symptom.

## Detection Logic

```
yFault = dsp > dsp_sp × high_sp_fraction
     AND zone_dmpr_pos_max < low_demand_damper_threshold
     AND sf_status
     sustained continuously for alarm_delay
```

Block graph (`rule.cxf.jsonld`):

![AHU-FC-065 block graph](diagram.svg)

`scaled` turns the live setpoint into the top-of-band pressure — a ratio rather
than a fixed offset, so the test travels with a setpoint the reset is allowed
to move. `spHigh` compares the measurement against that band and `dmprLow`
against the host-aggregated damper maximum; `demand` requires both, which is
the whole diagnostic content of the rule. Note what the pair excludes: high
pressure with an open damper is a system doing its job, and low dampers at low
pressure are a reset already working. `gated` adds the fan-running condition —
`dsp` and `dsp_sp` mean nothing with the fan off, and a stale reading held over
from the last occupied period would otherwise alarm overnight. `persist`
requires 30 minutes of continuous violation, which rides out morning start-up,
the pressure spike after a damper slams, and the settling period after any
setpoint change.

## Possible Diagnoses

1. DSP setpoint configured too high — a design-static value entered once and
   never revisited
2. Trim-and-respond active but not aggressive enough (trim magnitude too small,
   trim interval too long, or a minimum setpoint floor set at the old fixed
   value)
3. DSP reset responding to one rogue zone — a single box with a stuck damper or
   a failed flow sensor requests pressure continuously and holds the whole
   system up
4. Zone damper feedback not wired back to the AHU controller, so the reset has
   nothing to respond to and parks at maximum

## Energy Impact

EXCESS_CONSUMPTION, HIGH confidence, PROXY_ESTIMATION (EEM-12). Excess fan
power follows the cube law: `excess_fan_kw = ahu_fan_design_kw × [1 −
(needed_dsp/actual_dsp)³]`, where `needed_dsp` is the pressure at which the
most-open zone reaches its damper target. Savings run 5–30% of fan energy
depending on how far above the true requirement the setpoint sits — the wide
range is the cube law, not uncertainty in the measurement. Climate-neutral:
fan energy tracks operating hours and pressure, not weather. Prevalence: 74% of
buildings lack DSP reset.

## Emissions Impact

Scope 2, PROXY_EMISSIONS, HIGH confidence; typical 300–2,000 kg CO₂e/yr (excess
fan energy). Fan waste runs through the whole occupied period, so it lands
across the daytime grid mix rather than concentrating in any one hour.
Avoided-emissions basis: marginal operating emissions rate (MOER).

## Deviations

- **`dsp >= dsp_sp × high_sp_fraction` → strict `>`.** CDL has no
  `Reals.GreaterEqual`, so the band test is `Reals.Greater`. On a measured
  pressure signal the exact-equality case has measure zero, and the strict form
  errs toward silence; the vectors pin `dsp` exactly at the scaled setpoint as
  NO_FAULT. (At the bit level the distinction is moot for the default
  parameters: `400 × 0.95` rounds to 380.000000000000057 in IEEE-754, so a
  reading of exactly 380 Pa sits below the band either way.)
- **`zone_dmpr_pos_all` (zone array) → host-derived `zone_dmpr_pos_max`
  (scalar).** The reference takes `max()` over every zone damper position;
  library v1 avoids array boundary points, so the host aggregates and feeds one
  scalar — the same point AHU-FC-058 consumes, flagged `derived` in the point
  dictionary. The zone-side semantic tags land with the VAV dictionary.
- **The fan-running condition is in the block graph, not the preconditions.**
  The library's stance puts operating-state gating on the host, but the
  reference states `sf_status = ON` as part of the detection logic and
  `sf_status` is a canonical point, so it is wired as a boundary input (as in
  AHU-FC-052). The multi-zone and damper-data preconditions stay in frontmatter
  where the host can enforce them.
- `high_sp_fraction` is dimensionless (0–1), consistent with the reference's
  0.95; `low_demand_damper_threshold` stays in percent because
  `zone_dmpr_pos_max` is a percent point.
- `persist.delayOnInit = true` (Modelica/CDL default is `false`), the library's
  standing choice: a violation already present at load waits out the full
  30 minutes instead of alarming on the first tick after a controller restart.

## Notes

This rule and AHU-FC-058 are the DSP half of CLU-02, approached from opposite
sides. FC-058 is statistical and patient: it watches the setpoint sit flat for
three days and concludes the reset is absent. This rule is instantaneous and
symptomatic: it does not care whether a reset exists, only that right now the
fan is pushing pressure nobody is asking for. A misconfigured but active reset
— trim too small, floor too high — leaves FC-058 quiet and fires this rule,
which is exactly the case diagnosis 2 covers. Both point at the same
`missing-reset` playbook and the same $0 remote fix, programmed per G36
§5.16.1 (step 2.3).

Before touching the setpoint, check for a rogue zone: the playbook's step 1.2
plot of DSP setpoint against the highest zone damper position separates "the
setpoint is too high" from "one box is holding it there." Healthy operation
puts most zone dampers in the 50–75% band; all of them near 0% with pressure at
maximum is the signature this rule detects, and all of them near 100% is the
opposite fault (AHU-FC-001, insufficient static pressure).
