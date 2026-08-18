# Building2Building as a fault-exploration and validation harness

Reviewed 2026-08-18. Source: <https://github.com/vtaboga/building2building>
(MIT license; Taboga, Veilleux, Jang, Rankawat & Bacon 2026, "Building2Building:
A Large Scale Benchmark for Generalizable Real-World Reinforcement Learning",
RLJ / arXiv:2607.16534). Local clone at `~/Development/building2building`.

## What it is

6,000 parametrically generated EnergyPlus 24.1 building models (ASHRAE
90.1-2022 prototypes + residential archetypes; 6 building types × 16 ASHRAE
climate zones; unitary and VAV air-loop systems) wrapped as Gymnasium
environments. Per-building artifacts download from HuggingFace as
`building.epjson` + metadata parquet. Observations are EnergyPlus runtime-API
variables/meters; actions are HVAC actuator setpoints with per-equipment
`ActuatorDescription`s and a `fixed_actuator_overrides` hook in the building
config.

**It has no native fault injection or FDD labels** — it is an RL benchmark.
That does not matter much, for three reasons below.

## Three exploitation routes (in order of leverage)

### 1. Healthy-fleet false-positive harness (highest value, least work)

Run the baseline (reactive) controller over N buildings × M simulated days per
climate zone, log the observation stream, map E+ variables → our canonical
point names, and replay through the library's rules. Our `vectors.json` files
prove logic correctness; they say nothing about false-positive behavior under
realistic coupled dynamics. 6,000 buildings × 16 climate zones gives the
library something no hand-authored vector can: an **empirical FPR per rule per
climate zone** (e.g., do the economizer rules chatter in humid 1A/2A zones?
does AHU-FC-067's ungated 1.7 °C / 60 min hold up during morning pulldown?).
Output format: generate `vectors.json`-shaped scenario files from E+ output so
the existing `tools/verify` replay engine IS the evaluator — no new runtime.

### 2. Behavioral fault injection via actuator overrides (ground-truth TPR)

`fixed_actuator_overrides` (and per-step action overrides in a custom
wrapper) reproduce actuator-class faults directly: stuck/leaking valve
(AHU-FC-050/053/054, FCU family), damper stuck (AHU-FC-055/064/068,
economizer family), schedule misalignment (SYS-FC-052/053/057 — run the fan
actuator against a shifted schedule), simultaneous H&C. Every run is labeled
by construction → detection-rate and time-to-detect measurements per rule,
plus alarm_delay calibration where our sources were silent.

### 3. epJSON patching with EnergyPlus `FaultModel:*` objects (sensor faults)

`building.epjson` is plain JSON. EnergyPlus ships first-class fault objects —
`FaultModel:TemperatureSensorOffset:OutdoorAir/ReturnAir/SupplyAir`,
`FaultModel:EnthalpySensorOffset:*`, `FaultModel:ThermostatOffset`,
`FaultModel:Fouling:Coil`, `FaultModel:Fouling:AirFilter` — which inject
faults *inside the physics*, so the economizer controller itself acts on the
biased sensor. That exercises exactly the sensor-bias cascade our sensor-health
family (SYS-FC-054/055/100/101, AHU-FC-002/003/062) and the reference's
CLU-09 framing claim: one biased OAT disabling an economizer. Patch → rerun →
compare rule verdicts against the injected offset. This is the same fault
taxonomy as the LBNL/ORNL validation datasets in the reference's Part III
table, but generatable in any volume and any climate.

## What it does not give us

- Controllers are reactive baselines, not G36 sequences — reset-family rules
  (AHU-FC-057/058, CHW/HW reset detectors) will read "reset absent"
  everywhere; exclude them from FPR claims or treat them as known-positive.
- The default observation set is comfort/energy-oriented; valve/damper
  command variables may need adding to the variable request list (E+ exposes
  them; the wrapper's variable list is configurable — verified in
  `simulator/observation_spaces.py`).
- No refrigerant-side detail in air-loop models — HP/RTU charge-fault rules
  stay validated by the Purdue/NIST datasets route, not B2B.

## Recon results (2026-08-18, B2B-1 executed)

- **EnergyPlus 25.1.0 arm64 runs natively** — no Docker needed for
  simulation. The repo's env.py carries the Darwin arm64 tarball URL (only
  the auto-download wiring is missing); installed to
  `~/Development/building2building/energyplus/`, B2B imports and constructs
  environments against it (`ENERGYPLUS_PATH` env var).
- **Sample epJSON verified** (OfficeMedium-4004, E+ 25.1, Albuquerque): 3 VAV
  air loops, `Controller:OutdoorAir` with **DifferentialDryBulb economizer**
  (the exact convention AHU-FC-051/068 encode), 15
  `AirTerminal:SingleDuct:VAV:Reheat`, `SetpointManager:MixedAir`, DX cooling
  + fuel/electric heating. Every node our AHU/VAV/economizer rules bind is
  requestable via `Output:Variable`.
- **Default Gym observation surface is thin** (zone temps + OAT/humidity +
  meters — no SAT/MAT/valve/damper), which flips the architecture: the FPR
  harness should run **pure EnergyPlus CLI on the epJSON** with our own
  `Output:Variable` list — the epJSON's schedules ARE the baseline
  controller, no RL env involved. The Gym env (36 actuators: per-loop SAT
  setpoint, per-zone flow fraction + dual setpoints) is only needed for
  actuated fault campaigns.
- **Bigger local asset found**: the DOE/PNNL prototype sets already on disk
  at Google Drive `Datasets/SimulationSets/` — `ASHRAE901_all` (1,387 IDFs:
  11 building types × STD2004–STD2022 vintages × ~17 cities, including
  **OfficeLarge / HotelLarge / SchoolPrimary**, which carry CHW/HW plants),
  `AppendixG_all` (2,146), `IECC_all` (1,253), TMY3 EPWs. **Plant coverage
  confirmed** (OfficeLarge STD2019 Atlanta: 2× `Boiler:HotWater`, 2×
  `CoolingTower:VariableSpeed`, 8 air loops with `Controller:OutdoorAir`,
  15 VAV reheat terminals). B2B covers only 6 plantless air-loop types; the
  prototype sets extend validation to the CHW/HW/PMP families and cooling
  towers — the equipment classes where deep-read round 2 said we lack a
  second data source, and simulated tower approach/range data is exactly the
  fault-grade grounding the BEE-manual verdict said the TOWER family is
  blocked on. IDFs convert to epJSON with E+'s bundled `ConvertInputFormat`.

## Phased plan

- **B2B-1 (recon, ~done):** clone, confirm epJSON access + actuator override
  hooks (this note). Next: pip install core, pull 2-3 OfficeMedium VAV
  buildings, dump their observation/actuator name lists, draft the E+-variable
  → canonical-point mapping table.
- **B2B-2:** healthy-fleet FPR harness — small sample first (5 buildings ×
  3 climate zones × 7 days), `vectors.json` generation adapter, replay
  through `tools/verify`, FPR report per rule.
- **B2B-3:** behavioral fault campaigns (stuck valve, stuck damper, schedule
  shift) → TPR/time-to-detect per rule; tune alarm_delay defaults where
  library-chosen.
- **B2B-4:** `FaultModel:*` sensor-offset campaigns → sensor-health family
  validation + cascade study (biased OAT → economizer misbehavior → which
  rules fire, in what order — direct evidence for cluster/adjudicates
  design).
- **B2B-5:** mine surviving false negatives / unexplained E+ behaviors for
  NEW fault-condition candidates; feed the research backlog.

Decision point for the owner: B2B-2 sample scope and whether FPR/TPR results
should land on cards (a `validation:` frontmatter block?) or stay in
`_research/`.
