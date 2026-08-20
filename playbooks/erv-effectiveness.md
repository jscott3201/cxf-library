# Playbook: ERV Delivery and Effectiveness

| | |
|---|---|
| **Applies to** | ERV-0001, ERV-0002, ERV-0003, ERV-0004, ERV-0005 |
| **Fix complexity** | On-site service required |
| **Typical time** | 2–4 h |
| **Typical cost** | $200–$1,000 (cleaning) / $2,000–$5,000 (wheel or core replacement) |
| **Energy impact** | PNNL EEM-37 (optimized heat recovery wheel): significant heating and cooling energy savings in cold and hot climates. A wheel operating at 50% of rated effectiveness is recovering only half the available energy — the other half is wasted conditioning that outdoor air brings in. |

Adapted from HVAC FDD Reference v1.0, Remediation Playbooks (pp. 166–167).

## Step 1 — Confirm mode and frost state

1. Confirm the ERV is scheduled to run and both air streams should be moving.
   Exclude smoke, purge, commissioning, manual test, and maintenance modes.
2. Read the actual frost-sequence state and compare its configured engagement
   and release settings with OAT. Verify OAT against a second local sensor.
3. For ERV-0002/0003, command the frost sequence through one safe transition
   and confirm the flag means **active**, not enabled or available.
4. Suspend ERV-0005 during frost strategies that intentionally unbalance the
   core paths; otherwise verify its measurements are at a whole-unit boundary
   where the intentional core-path offset is not being diagnosed.

## Step 2 — Prove the active recovery device

1. On wheels and runaround loops, compare the final recovery command with an
   independent rotation, speed, current, flow, or work proof.
2. A wheel motor current switch proves the motor, not the belt or wheel; inspect
   the belt/coupling whenever ERV-0001 is active with motor proof present.
3. Release HOA/local and software overrides. Record drive or pump fault history
   before resetting it. Passive plate cores skip this step.
4. Confirm any automatic wheel-jog/exercise command is included in the final
   command binding or excluded from evaluation.

## Step 3 — Compare the two air streams

1. Confirm supply and exhaust flow sensors belong to the same ERV, use L/s,
   have nonnegative polarity, and share an averaging interval.
2. Compare the measured offset with the design pressure strategy. Normalize an
   intentional offset before treating the residual as imbalance.
3. Inspect filters, outdoor/exhaust openings, dampers, fan belts/speeds, and the
   recovery core on both streams. Use ERV-0005's direction only as evidence of
   which measured flow is higher; it does not isolate restriction or sensor cause.

## Step 4 — Verify temperature effectiveness

1. Calculate the sensible effectiveness during conditions with adequate
   temperature difference between outdoor and indoor air — minimum
   |OAT − RAT| > 10 °F for a reliable measurement.
2. Compare it to the commissioning baseline or the manufacturer's rated
   effectiveness.
3. If effectiveness has dropped below 50% of the rated value, degradation is
   confirmed.
4. Check whether the effectiveness drop is seasonal — some units perform
   differently in heating vs. cooling mode.

## Step 5 — On-site service

1. Inspect and clean the enthalpy wheel or plate core: accumulated dust and
   particulate reduces heat transfer surface area. Use low-pressure compressed
   air or a vacuum on plate cores; for enthalpy wheels, follow the
   manufacturer's cleaning procedure.
2. For enthalpy wheel units, verify the wheel itself spins — a failed drive
   motor, belt, or coupling leaves it stationary. Check belt tension, alignment,
   rotation proof, speed, and motor amperage.
3. Check the seal and purge section for cross-contamination between the
   airstreams.
4. If the core is permanently fouled or physically damaged, replace it
   ($2,000–$5,000).
5. Verify that the bypass damper (if equipped) is not stuck in the bypass
   position, which would route air around the recovery core entirely.

## Step 6 — Confirm resolution

1. Command active equipment through stop→start→stop and confirm both proof
   directions clear inside their configured windows.
2. Confirm frost mode engages and releases at the commissioned boundaries.
3. Rebalance/normalize both streams and verify ERV-0005 stays clear through a
   full operating transition.
4. Recalculate effectiveness. Target: return to within 15 percentage points of
   the commissioning or rated value.
