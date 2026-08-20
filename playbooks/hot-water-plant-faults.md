# Playbook: Hot Water Plant Faults

| | |
|---|---|
| **Applies to** | HW-0001 through HW-0012 |
| **First objective** | Prove point identity, plant state, safety/limit state, and finding direction before changing control |
| **Typical scope** | Remote trend/sequence review, followed by qualified controls, boiler, burner, or hydronic service as evidence requires |
| **Impact posture** | Qualitative unless the site has aligned fuel, electrical, useful-load, and commissioned counterfactual data |

The first three rules originate in the HVAC FDD Reference boiler family.
HW-0004..0008 are PNNL-grounded loop-side additions, HW-0009 is a
command/proof adaptation, and HW-0010..0012 apply NIST regulation concepts,
LBNL boiler-plant data contracts, and verified library graph precedents. Do not
treat one rule's shipped threshold as a universal boiler setting.

## Step 1 — Establish a safe, coherent record

1. Identify the exact plant, header, boiler fleet, pump(s), controlled outlet,
   and final active setpoint. Distinguish the plant/header target from each
   boiler's local leaving-water target and any upstream reset request.
2. Prove modes and signals independently: final enable/command, firing proof,
   circulation/flow, stage count, firing feedback, HWS/HWR, active setpoint,
   OAT, and any load/capacity derivation used by the finding.
3. Check timestamps, units, range, sensor placement, calibration, and stale or
   held values. A common-header OR/max is not a per-boiler measurement.
4. Mark startup, setback recovery, reset ramps, load steps, lead/lag transfers,
   rotation, stage overlap, exercise, maintenance, freeze protection, emergency
   redundancy, manual tuning, and emissions/demand limits as NO_EVAL where the
   card requires it.
5. Read the boiler/burner controller and safety contacts before changing BAS
   logic. Never force or bypass flame safeguard, purge, ignition, high-limit,
   low-water, fuel-pressure, combustion-air, minimum-flow, venting, freeze, or
   emissions interlocks. Use qualified burner/boiler personnel for that work.

## Step 2 — Resolve operating and proof contradictions

### Warm-weather operation — HW-0003

1. Verify that OAT represents the plant and that DHW, freeze, process, or other
   legitimate heat modes are excluded.
2. Compare the site's lockout and hysteresis with its design criteria and active
   sequence. Do not copy a generic lockout temperature into another plant.
3. If the sequence is correct but the plant operates, trace the final enable,
   local hand mode, interposing relays, and lead pump/boiler authority.

### Command/proof mismatch — HW-0009

1. Read `yFailToStart` versus `yUnexpectedRun` first.
2. For failure to start, prove the boiler is actually called to fire rather than
   enabled-and-satisfied, then read the burner lockout and permissive chain.
3. For unexpected run, inspect Hand/Off/Auto state, local aquastat authority,
   relays/contacts, and the status source.
4. Never increase proof timers to hide an ignition or safety trip; commission
   them only against the listed burner sequence.

## Step 3 — Investigate distribution, setpoint, and tracking

### Delta-T and DP — HW-0004, HW-0005, HW-0006

1. Confirm supply/return direction and that flow, pump speed, DP, and setpoint
   belong to the same distribution loop.
2. Inspect bypasses, decouplers, three-way valves, valve authority, sensor taps,
   minimum-flow paths, and simultaneous pump operation before retuning DP.
3. Compare actual reset behavior with the final active DP target. Adjust reset
   only after proving the served valve/flow feedback is representative.

### HWS reset and high temperature — HW-0007, HW-0008

1. Confirm that distribution-side HWS—not a boiler-primary outlet—is compared
   with the intended reset sequence.
2. Review reset endpoints against emitter requirements, boiler minimum-return
   constraints, mixing/buffer topology, and current design conditions.
3. High supply temperature can be appropriate during warm-up or for legacy
   emitters; establish the operating state before lowering a target.

### HWS tracking — HW-0010

1. Read `yTooCold` versus `yTooHot`, and verify firing plus circulation were
   continuous after all excluded transitions settled.
2. Compare the final plant/header target, measured header, each active boiler's
   local target/outlet, and mixing-valve position. This separates plant control
   authority from capacity and mixing problems.
3. Investigate sensor/proof/flow issues in parallel with capacity, fouling,
   fuel, and application limits; do not assume control tuning is first.

## Step 4 — Investigate cycling, hunting, and staging

### Boiler starts — HW-0001

1. Verify the edge count is one boiler's firing proof at a legal cadence.
2. Trend demand, firing rate, stage requests, minimum on/off timers, flow, and
   HWS together. Look for oversizing, narrow differential, minimum-fire/load
   mismatch, lost flow, or a sequence that repeatedly transfers load.
3. Buffering, sequence, and plant-design changes require hydronic and
   manufacturer review; do not defeat minimum-flow or safety limits.

### Regulation hunting — HW-0011

1. If only `yFiringRateHunting` is true, inspect modulation feedback, minimum
   fire, signal quantization, and staging continuity before changing PI gains.
2. If only `yTemperatureUnstable` is true, inspect the sensor, flow, load, final
   setpoint, mixing loop, and competing controllers.
3. If both are true, first exclude a real transition. Then compare phase and
   timing to distinguish load/sensor motion from controller-driven motion.
4. Change PID or lead/lag tuning only with qualified controls/burner staff and a
   rollback plan; observe several plant response times after each change.

### Excess stages at low load — HW-0012

1. Stop if `yLoadOk` is false. Audit the useful-load numerator, commissioned
   eligible-fleet capacity, fleet membership, and timestamps.
2. Prove the count represents firing comparable units—not enabled/available
   equipment—and that rotation, overlap, redundancy, or exercise is not active.
3. Compare the finding with the commissioned staging map, boiler sizes,
   turndown, minimum flow, venting, emissions, and minimum run-time constraints.
4. Stage fewer boilers only after those obligations are satisfied. Unequal or
   modular fleets may need a capacity-weighted state model instead of a count.

These findings are related but do not form a causal cluster. Over-staging can
cause cycling or hunting, poor tuning can provoke stage changes, and a capacity
limit can cause tracking error; none reliably occurs first and their repairs
differ.

## Step 5 — Evaluate boiler efficiency — HW-0002

1. Verify the fitted baseline, fuel heating-value convention, aligned useful
   thermal output, and firing-rate range before interpreting residuals.
2. Use a qualified combustion technician and the manufacturer procedure to
   measure combustion, draft, O2/CO, flue temperature, and burner operation.
   This library does not prescribe generic combustion targets.
3. Inspect fireside/waterside heat-transfer surfaces, fuel train, burner,
   venting, condensate path where applicable, and water quality based on the
   measured evidence.
4. Refit or revalidate the model only on a disjoint known-good period after the
   physical/control condition is resolved.

## Step 6 — Confirm resolution

1. Re-establish all card preconditions and allow the stated warm-up, rolling
   window, and persistence intervals to complete.
2. Confirm directional and evaluability outputs, not only `yFault`. A cleared
   fault during NO_EVAL is not proof of repair.
3. Verify the intended sequence through representative load and stage changes
   without safety or comfort regression.
4. Quantify savings only from aligned measured fuel/power and useful load
   against a documented counterfactual; fault hours alone are not energy.
