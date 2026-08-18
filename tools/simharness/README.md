# simharness — EnergyPlus → vectors.json FPR harness

Replays a building's simulated week through the library's rules and counts
false positives. The building runs under its own schedule-based baseline
control (no RL, no external controller); `tools/verify` is the replay
engine, consuming generated `cxf-library/vectors/v1` scenarios whose only
expectation is `yFault == false` inside host-gated windows. Every FAIL is a
false positive to explain: a rule-robustness finding, a mapping-proxy
artifact, or a fault genuinely present in the model.

## Usage

```
export ENERGYPLUS_PATH=/path/to/EnergyPlus-25.1.0   # native install
python3 tools/simharness/harness.py run --building <dir>
```

`<dir>` holds `building.epjson` + a `*.epw` (the Building2Building dataset's
per-building layout; DOE prototype IDFs convert via `ConvertInputFormat`).
The harness patches the run period (default one July week) and
`Output:Variable` requests, runs EnergyPlus, extracts per-air-loop point
series, emits one replay dir per (rule × loop), and prints a per-rule
clean/FP table.

## Point mapping (packaged VAV)

Per air loop, derived from the epJSON topology (see `harness.py` docstring
for the exact node→point table). Two mappings are **proxies** and any
conclusion drawn from them carries that caveat: `clg_vlv_cmd` ← DX cooling
runtime fraction × 100 (packaged units have no CHW valve), and
`oa_dmpr_cmd` ← realized OA flow fraction × 100 (not the damper command
signal).

## Host gating

The graphs compute fault-given-valid-data; NO_EVAL gating is the host's
job, so the harness implements it as expect-window construction:

- **Fan gate**: windows only inside contiguous fan-on intervals
  (fan power > 50 W), with a 3600 s lead margin so delay state accumulated
  while ungated clears — a real host suspends evaluation entirely.
- **Operating-state gate**: each card's `operating_states` frontmatter is
  transcribed into an OS set (`OS_MAP`); per-tick OS is derived
  APAR-style from actuator signatures (burner heating rate, DX runtime
  fraction with 30-min any-window smoothing over compressor cycling,
  E+ economizer status), and windows intersect the rule's set with an
  1800 s lead after each state entry. Vent-only operation (no heating, no
  cooling, no economizing) maps to no OS and is never evaluated.

Ungated replay is meaningless: the first run without OS gating produced
wall-to-wall "false positives" from OS#2-scoped rules correctly detecting
mechanical cooling at night — the gating is part of the deployment
contract, not a fudge.

## Fleet results (sweep v3, 2026-08-18)

**B2B OfficeMedium × 8 ASHRAE climate zones (1–8), one July + one January
week, 3 VAV loops each — 787 host-gated scenario-replays. 17 of 20
auto-eligible AHU rules fully clean.** Recorded on each swept card as a
`validation:` frontmatter block (SCHEMA.md contract). Remaining failures
are two explained findings, not noise:

1. **AHU-FC-006/055 (31 events each, winter-dominant, all buildings)** —
   DCV-driven excess outdoor air: `Controller:MechanicalVentilation` holds
   ventilation flow while VAV turndown shrinks total flow, so OA fraction
   legitimately exceeds any fixed minimum (~86% observed at −7.8 °C OAT —
   freeze-stat territory in a real building). Conclusion: OA-fraction
   rules need a DCV-aware host precondition.
2. **AHU-FC-067 (8 events, winter only)** — the fleet publishes one
   constant cooling-oriented SAT setpoint, so heating-season tracking
   error is real per the rule's letter while the setpoint no longer means
   the active mode's target. Per-mode setpoint binding is a deployment
   requirement.

Sweep-methodology lessons baked into the harness: OS smoothing is
majority-of-window (an any-window smoother stretched compressor blips into
OS misclassification); heating takes outright precedence in OS derivation;
and an incomplete hand-maintained OS_MAP produced two spurious FP clusters
before being caught — the map should eventually be parsed from each card's
`operating_states` frontmatter (`OS#x` tokens) instead of hand-kept (TODO).

The B2B baseline also runs its fans 24/7 (no setback) — an after-hours
fault by construction; excluded from FPR claims, useful as a
known-positive. Reset-family rules are likewise excluded (constant-setpoint
baselines read "reset absent" by construction).

## TPR: sensor-bias campaigns (`--bias point=delta`, `--reuse`)

Injects a bias into the replayed inputs of an already-simulated healthy run
(the faulted-sensor-as-seen-by-FDD case; zero EnergyPlus time). FAILs are
DETECTIONS; attribution requires differencing against the healthy baseline
(rules that fail on the healthy run — the DCV pair — are confounded and
excluded). First campaign, +/-3 degC OAT bias (OfficeMedium-4004, July):
the envelope family and the direction-appropriate economizer rule catch the
bias in both directions — +3: AHU-FC-062 (3/3), 002 (3/3), 068 (3/3,
~2.3 h); -3: 051 (3/3, ~40 min), 003 (2/3), 062 (2/3) — while a dozen
non-OAT rules stay correctly silent. Empirical demonstration of the CLU-09
biased-OAT cascade; recorded as `simulation_tpr` validation blocks
(failures = missed detections).

## TPR: physics-level FaultModel campaigns (`--faultmodel kind=delta`)

Patches EnergyPlus `FaultModel:*` objects into the epJSON before
simulation, so the CONTROLLER acts on the faulted sensor while FDD replays
true node values — the complement of the `--bias` campaign (where FDD's
own input lies). First campaign, OAT sensor offset +/-4 degC on all OA
controllers (OfficeMedium-4004, July): +4 (economizer locks out early) is
caught by AHU-FC-051 (3/3 loops); -4 (economizes past true changeover) by
AHU-FC-068 (3/3, one loop in ~5 min); each direction's mirror rule and the
entire envelope family stay correctly silent, since every replayed sensor
is physically consistent. Where FDD and the controller share a sensor,
real deployments see BOTH signatures — the input-bias envelope detections
and the behavioral detections — which is what the cluster grouping is for.

The OS gating map is now parsed from each card's `operating_states`
frontmatter (`parse_operating_states`; ranges, comma lists, "all");
unparseable prose is a hard error requiring an explicit `OS_OVERRIDE`
entry — never a silent all-states default.

## Plant mode (DOE prototypes)

`--mode plant` maps CHW/HW plant loops instead of air loops: loop
supply/return node temperatures and setpoints from `PlantLoop`, chiller/
boiler part-load ratios for load and status, pump electricity for
`hw_pump_status`, and `hw_pump_vfd_speed` as a pump mass-flow fraction
(affinity-law proxy). DOE prototype IDFs enter via the E+ transition chain
(`PreProcess/IDFVersionUpdater`, e.g. 22.1 → 25.1 in six steps) +
`ConvertInputFormat`. Rules replay per family with rule-specific gates
(`PLANT_GATE`: CHW-FC-053 needs chiller load > 40%; boiler rules need the
boiler active; unnecessary-operation rules replay ungated — gating on the
equipment they accuse would mask them). `PLANT_EXCLUDE` names the
baseline-fitted, reset-class, and by-construction rules with reasons.

First plant results (OfficeLarge STD2019 Atlanta, Jul + Jan weeks):
CHW-FC-053, HW-FC-052/053/054 all clean in their gated windows (recorded
as `validation:` blocks); HW-FC-056 verified firing correctly on the
prototype's constant-HWST-at-low-load operation (excluded by-construction);
Atlanta January never crosses CHW-FC-053's 40% chiller-load floor — season
selection matters per family.

## First results (single building, superseded by the fleet sweep above) (B2B OfficeMedium-4004, Albuquerque, July week, 3 loops)

**16 of 18 auto-eligible AHU rules replayed clean across all three loops
for the full week** — the envelope pair (002/003), SAT families
(011/012/013/015/056/057/066/067), economizer directions (051/068), staging
(010), and plausibility (062) among them.

Two findings:

1. **AHU-FC-006 and AHU-FC-055 fire together during hot afternoons** (e.g.
   day 2 ~11:20, implied OA fraction (mat−rat)/(oat−rat) ≈ 66% at
   OAT 30.6 °C, economizer locked out). Root cause is real, not an
   artifact: `Controller:MechanicalVentilation` holds ventilation *flow*
   while VAV turndown shrinks total flow, so OA *fraction* balloons.
   Field-relevant conclusion: **OA-fraction rules need a DCV-aware host
   precondition** (suspend evaluation while ventilation demand overrides
   the minimum-OA state) — a documented noise source in the FDD
   literature, reproduced here with ground truth. Candidate card edit
   pending the owner's decision on recording validation results.
2. **The B2B baseline runs its fans 24/7** (no night setback): the fleet
   carries an after-hours fault by construction. Useful as a
   known-positive for schedule rules; excluded from FPR claims.

Reset-family rules (AHU-FC-057/058-style) read "reset absent" against
constant-setpoint baselines by construction and are excluded from FPR
claims, per the validation plan.
