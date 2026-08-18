# Playbook: Unnecessary Plant Operation

| | |
|---|---|
| **Applies to** | SYS-0001 (CHW flow, no cooling demand), SYS-0002 (HW flow, no heating demand), CLU-07 |
| **Fix complexity** | Remote fix (80%) · On-site (20%) |
| **Typical time** | 15–30 min remote |
| **Typical cost** | $0 remote / $200–$800 on-site (valve repair) |
| **Energy impact** | PNNL EEM-09 (plant shutdown when no load): < 1% site energy directly, but this is 100% waste — every kWh consumed by the pump and chiller/boiler standby during zero-demand periods provides zero useful conditioning. The waste is pure pump energy plus chiller/boiler parasitic loads (oil heaters, controls, heat loss). For a 100-hp pump system, unnecessary operation costs $5–$10/hr. |

Adapted from HVAC FDD Reference v1.0, Remediation Playbooks (pp. 171–172).

## Step 1 — Verify the fault

1. Confirm CHW or HW flow is present: flow sensor reads above the no-demand
   threshold (typically 10% of design flow).
2. Confirm that all served AHU valves are closed: every cooling (SYS-0001)
   or heating (SYS-0002) valve command is below 2%.
3. Check whether the flow is from a leaking bypass valve, a leaking coil
   valve, or simply the pump running when it shouldn't be.
4. Verify the condition persists for at least 15 minutes — brief transients
   during mode changes are normal.

## Step 2 — Remote fix

1. Check the pump enable logic in the BAS:
   - The pump should shut down when no AHUs are calling for heating or
     cooling.
   - If the pump runs on a fixed schedule, convert to demand-based enable:
     pump runs only when at least one served AHU valve opens above a
     threshold (typically 5%).
2. Check for manual overrides on the pump command — release them.
3. For CHW plants: verify the chiller staging sequence includes a no-load
   shutdown. Some plants keep the lead chiller running 24/7 as a default.
4. For HW plants: verify the boiler OAT lockout is active (see the Hot Water
   Plant Faults playbook). If the boiler is locked out but the pump still
   runs, the pump enable logic needs correction.
5. Check for minimum flow bypass valves stuck open — these allow flow to
   circulate without any end-use demand.

## Step 3 — On-site service (if flow persists after control fix)

1. If the bypass valve is stuck open: inspect and repair or replace the valve
   actuator.
2. If one or more AHU coil valves are leaking through: see the Stuck Actuator
   or Fan Coil Unit playbooks for valve repair procedures.
3. Check for check valve failures that allow reverse flow through idle
   equipment.

## Step 4 — Confirm resolution

1. Monitor CHW/HW flow during periods of confirmed zero demand (overnight,
   weekends).
2. Flow should drop to zero within minutes of the last AHU valve closing.
3. The fault should clear within 24 hours.
