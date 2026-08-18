# Playbook: Fan Coil Unit Faults

| | |
|---|---|
| **Applies to** | FCU-0001 (cycling), FCU-0002 (SAT low heating), FCU-0003 (SAT high cooling), FCU-0004 (cooling leak), FCU-0005 (heating leak) |
| **Fix complexity** | Remote fix (cycling/leak detection) · On-site (valve replacement) |
| **Typical time** | 15 min remote / 1–2 h on-site per unit |
| **Typical cost** | $0 remote / $150–$600 per valve replacement |
| **Energy impact** | EEM-03 (fix leaking valves): 0.5–5% site energy in cold climates. FCU faults are insidious — each unit wastes a small amount, but hotels and apartments may have hundreds of FCUs. Leaking valves (FCU-0004/FCU-0005) are classified as CRITICAL_WASTE because they represent energy being added and removed simultaneously at the zone level. |

Adapted from HVAC FDD Reference v1.0, Remediation Playbooks (pp. 171–172).

## Step 1 — Verify the fault

1. **Excessive cycling (FCU-0001):** count operating state transitions per
   hour — more than 7/hr indicates a problem. The most common cause is a
   narrow deadband between the heating and cooling setpoints.
2. **SAT deviations (FCU-0002/FCU-0003):** confirm SAT is below setpoint at full
   heating (FC-002) or above setpoint at full cooling (FC-003). Rule out
   plant-side issues first — is the HW/CHW supply temperature adequate?
3. **Leaking valves (FCU-0004/FCU-0005):** with the valve commanded to 0%,
   measure the temperature drop (cooling) or rise (heating) across the coil.
   Any measurable temperature change when the valve is commanded closed
   confirms a leak. In multi-story buildings, check gravity circulation: hot
   water can thermosiphon through vertically oriented coils even with the
   valve closed.

## Step 2 — Remote fix

1. **Cycling:** widen the deadband between the heating and cooling setpoints
   to at least 2 °F (1 °C). Check for sensor noise causing mode oscillation —
   apply a software filter or averaging if available.
2. **SAT deviations:** verify that the central plant is providing adequate
   supply temperatures. If the CHW supply is too warm or the HW supply too
   cold, the FCU coils cannot produce the expected output regardless of valve
   position.
3. **Leaking valves:** if the leak is small, a temporary workaround is a
   seasonal lockout that disables the leaking coil's valve entirely during the
   opposite season (e.g. lock out the heating valve in summer). This
   eliminates the simultaneous heating and cooling effect while the valve
   awaits replacement.

## Step 3 — On-site service

1. **SAT deviations with adequate plant supply:** inspect the coil for fouling
   or air locks. Bleed air from the coil piping. Clean the coil surface.
2. **Leaking valves:** the valve seat is worn or the valve body is corroded.
   Replace the valve ($150–$600 depending on size and type).
3. **Gravity circulation:** install a check valve on the coil piping to
   prevent thermosiphon flow, or reorient the coil piping to eliminate the
   vertical loop.
4. **Hotels and apartments with hundreds of FCUs:** prioritize by measuring
   the waste at each unit — waste_kW = |temp_change| × airflow × cp_air.
   Replace the worst offenders first.

## Step 4 — Confirm resolution

1. After repair, verify the valve closes to zero leakage: no measurable
   temperature change across the coil when the valve is at 0%.
2. For cycling: verify state transitions drop below 7/hr.
3. Monitor for 48 hours before closing the fault.
