# Playbook: Cooling Tower Performance Degradation

| | |
|---|---|
| **Applies to** | TOWER-0001 (approach high at capacity), TOWER-0002 (range collapse), TOWER-0003 (fan short-cycling), CHW-0005 (condenser approach high) |
| **Fix complexity** | On-site (70%) · Remote fix (30%) |
| **Typical time** | 1–4 h on-site; 15–30 min remote |
| **Typical cost** | $0 remote / $300–$3,000 on-site (cleaning, water treatment, fan drive service) |
| **Energy impact** | Condenser-side degradation raises chiller lift; chiller power rises ~2–4% per °C of added lift (BEE 2006 §3; PNNL O&M guides give 1.2–1.7%/°F split by compressor type). Condenser fouling of ~0.6 mm is associated with ~20% chiller power increase (HVAC HESS factsheet). |

**Library-authored playbook** (no reference playbook exists for cooling
towers): grounded in the DOE FEMP/PNNL O&M guides (PNNL-13890; O&M Best
Practices 3.0 ch. 9) and BEE Best Practice Manual: HVAC Chillers (2006),
paraphrased; plus this library's 4-climate simulation envelope study
(tools/simharness README, tower groundwork).

## Step 1 — Verify the fault

1. For approach-high (TOWER-0001): confirm the tower fan is at or near
   full speed — approach is only diagnostic at capacity; VFD modulation
   legitimately lets approach ride high at part load (healthy un-gated
   spread observed 1.6–13.3 °C across climates).
2. Trend approach (leaving water − outdoor wet-bulb) against the
   commissioned full-load baseline; compare same-season history.
3. For range-collapse (TOWER-0002): check condenser water flow first — a
   flow increase mimics range collapse without any tower degradation.
4. For fan short-cycling (TOWER-0003): confirm ≥ 4–5 starts/hour
   sustained (PNNL O&M guides' motor-protection trigger) and rule out an
   aggressive basin/leaving-temperature deadband before blaming the drive.
5. For condenser approach (CHW-0005): confirm at the chiller —
   saturated condensing temperature minus leaving condenser water
   temperature against the commissioned band.

## Step 2 — Remote fix

1. Widen the leaving-temperature deadband or stage fan cells to stop
   short-cycling; verify minimum on/off timers are configured.
2. Check condenser water setpoint and tower staging sequence — a setpoint
   below what the wet-bulb allows drives fans to capacity chasing an
   unreachable target.
3. Release manual overrides on fans, bypass valves, and pumps.

## Step 3 — On-site service

1. Approach high at capacity: inspect fill for scale/fouling, nozzles for
   clogging, drift eliminators and air inlets for blockage; verify water
   distribution across cells.
2. Verify water treatment: cycles of concentration against the treatment
   spec, blowdown operation, makeup metering.
3. Condenser approach high with tower approach normal: clean condenser
   tubes (brush/chemical), verify condenser water flow, check for air or
   non-condensables in the refrigerant side.
4. Fan short-cycling that survives control fixes: inspect the VFD/starter,
   belt/gearbox, and vibration switches.

## Step 4 — Confirm resolution

1. At the next sustained full-fan period, approach should return to the
   commissioned band; trend for 7 days.
2. Chiller kW/ton at matched load and lift should recover with the
   condenser-side fix (see the Chiller Efficiency Degradation playbook).
3. Fan starts per hour should fall below the trigger with normal
   deadbands; the faults should clear within 24–48 h.
