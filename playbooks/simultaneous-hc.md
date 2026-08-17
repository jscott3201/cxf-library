# Playbook: Simultaneous Heating & Cooling

| | |
|---|---|
| **Applies to** | AHU-FC-050, AHU-FC-059, AHU-FC-063, CLU-01 |
| **Fix complexity** | Remote fix (70%) · On-site service (30%) |
| **Typical time** | 30 min remote / 2–4 h on-site |
| **Typical cost** | $0 remote / $200–$1,500 on-site (actuator replacement) |
| **Energy impact** | EEM-38: 10–30% of AHU thermal energy. Simultaneous heating and cooling is pure waste with no occupant benefit; common across all building types with heating and cooling coils. |

Adapted from HVAC FDD Reference v1.0, Remediation Playbooks (pp. 153–154).

## Step 1 — Verify the fault

1. Pull a 24-hour trend of the heating valve command and cooling valve command
   on the same chart.
2. Confirm both valves are open above 5% at the same time for sustained periods
   — more than 15 minutes of continuous overlap indicates a real fault, not a
   transient mode change.
3. Check data quality flags — rule out bad sensor readings before acting.
4. If position feedback sensors exist, compare command vs. actual position to
   determine whether the problem is the control sequence (software) or a
   physical issue (stuck valve).
5. Quantify the waste: overlap energy = heating kW × (clg_vlv_cmd/100) during
   overlap periods — energy simultaneously added and removed, all of it waste.

## Step 2 — Remote fix (BAS changes, no site visit)

1. Check the control sequence for a heating/cooling interlock:
   - The heating valve should close to 0% before the cooling valve may open,
     and vice versa. If no interlock exists, add one — the most common fix.
   - G36 §5.16 specifies a minimum deadband of 2.8 °C (5 °F) between heating
     and cooling loops.
2. Check for a deadband between the heating and cooling PID loops:
   - At least 1 °C (2 °F) between where heating stops and cooling starts; if
     the loops overlap, insert a deadband.
   - For single-duct VAV systems, verify the SAT setpoint is above the reheat
     lockout temperature before investigating individual zone interlocks.
3. Check for stuck manual overrides on either valve command (BACnet priority
   array). Release any override holding a valve open — among the most common
   retro-commissioning findings (PNNL-27338).
4. Check whether the heating coil has an OAT lockout; if outdoor temps are warm
   enough that heating shouldn't run, enable one (typical: disable heating when
   OAT > 16 °C with 2 °C hysteresis).
5. If the AHU serves mixed interior/perimeter zones, verify perimeter reheat is
   not fighting the central cooling coil — SAT reset (see
   [missing-reset](missing-reset.md)) often resolves this.

## Step 3 — On-site service (if remote fix doesn't resolve)

1. Inspect the heating valve actuator: command to 0% from the BAS and
   physically verify full closure; check the mechanical linkage (disconnected
   linkages are common on older systems); verify normally-open vs.
   normally-closed — an NO valve opens whenever the actuator loses its signal.
2. Inspect the cooling valve actuator with the same checks.
3. On pneumatic-to-digital conversions: normally-open pneumatic valves need
   spring-return actuators; check for air leaks in the tubing — small leaks can
   prevent full closure.
4. If a valve cannot close mechanically, replace the actuator ($200–$800) or
   valve body ($500–$1,500).
5. Check for coil bypass: on older AHUs a face-and-bypass damper can mix hot
   and cold decks — inspect the bypass damper actuator and linkage.

## Step 4 — Confirm resolution

1. Monitor both valve commands for 48 hours after the fix.
2. Verify both valves are never open above threshold at the same time.
3. The fault should clear automatically; clustered faults (mode mismatch,
   lockout issues) should resolve with it.
4. Re-calculate energy impact to quantify savings — at 10–30% of AHU thermal
   energy this is often the single highest-value fix in a building.
