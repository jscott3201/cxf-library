# HVAC FDD Reference v1.0 — Digest

Source: `/Users/justin/Documents/HVAC_FDD_Reference_v1.0_FINAL.pdf` (Feb 2026, 178 pp).
Status: **guidance, not final truth** — early-version research paper used to ground our
CDL-based fault detection work and future agentic fault generation.

Consolidates ASHRAE Guideline 36-2021 fault conditions with research from PNNL
(PNNL-25985, PNNL-27338, PNNL-13890), LBNL, ORNL, and NIST. Implementation-neutral:
defines *what* to detect, not *how* to build the engine.

## Catalog shape

64 fault rules, 13 equipment types, 18 remediation playbooks.

### Naming: `{EQUIP}-FC-{NNN}`

| ID range | Origin | Phase |
|---|---|---|
| 001–049 | ASHRAE G36-2021 standard faults | 1 |
| 050–099 | Research-backed (threshold / simple statistical) | 1–2 |
| 100–149 | Advanced statistical (change-point, regression) | 3 |
| 150–199 | ML / anomaly detection (future) | 4 |

### Equipment prefixes and rule counts

AHU (20, ch.9) · VAV (7, ch.10) · RTU (7, ch.11) · HP (3, ch.11) · FCU (5, ch.12) ·
CHW (4, ch.13) · HW (3, ch.14) · ERV (2, ch.15) · PMP (2, ch.15) · VFD (2, ch.15) ·
SYS (8, ch.16) · META (1, ch.16)

### Detection methods
`rule` (thresholds, phase 1–2) · `statistical` (rolling stats/regression, 2–3) ·
`ml` (4) · `meta` (monitors health of other rules, 2+)

### Severity scale
1 Critical (same-day, FP <1%) · 2 High (48h, FP <1%) · 3 Warning (1–2 wk, FP <5%) ·
4 Info (advisory, relaxed)

### Hierarchical suppression (root cause silences symptoms)
1. Sensor faults suppress all rules depending on the faulty sensor.
2. Actuator faults suppress control-performance faults on the affected loop.
3. Root-cause faults suppress symptom faults within the same cluster.
4. Meta rules can suppress statistical/ML rule groups when the model is unreliable.

## Fault specification card (ch.2) — every rule has:

Header (code+name) · Metadata (phase, method, severity, equipment, source) ·
Description · **Equation/Logic** · **Required Points** (with Haystack 4.0 markers, SI units) ·
**Tunable Parameters** (defaults) · Operating States + Preconditions ·
Possible Diagnoses (ranked) · Energy Impact Profile · Emissions Impact Profile ·
Runtime Estimation formula · **Test Vectors** (input/output validation scenarios) ·
Related Rules · Notes

## Canonical point dictionary (ch.3)

snake_case, SI units, Haystack 4.0 markers. Core points:

| Variable | Meaning | Unit |
|---|---|---|
| sat / sat_sp | Supply air temp / setpoint | °C |
| mat, oat, rat, zone_temp | Mixed / outdoor / return / zone air temp | °C |
| chwst, hwst | CHW / HW supply temp | °C |
| htg_vlv_cmd, clg_vlv_cmd, rht_vlv_cmd | Valve commands | % |
| oa_dmpr_cmd | OA damper command | % |
| sf_status, sf_speed | Supply fan status / speed | bool, % |
| comp_status | Compressor status | bool |
| zone_airflow | Zone measured airflow | L/s |
| dsp / dsp_sp | Duct static pressure / setpoint | Pa |

Suffixes: none=measured, `_sp`=setpoint, `_cmd`=command, `_status`=status, `_fbk`=feedback.

## Data quality (ch.4) — engine semantics

- **NO_EVAL over false positive**: never produce a verdict from unreliable data.
- BACnet flags: none→good; in-alarm/overridden→uncertain (reduced confidence);
  fault→skip point; out-of-service→NO_EVAL.
- Gap handling: ≤2× poll interval interpolate; 2–10× hold-last+flag; 10×–60min pause
  eval and hold active faults; >60min NO_EVAL + reset rolling state.
- Warmup delay after fan start / mode change (AlarmDelay param, typ. 5–15 min).

## Energy & cost impact framework (ch.5)

- Impact categories: CRITICAL_WASTE (10–30% subsystem) · EFFICIENCY_LOSS (5–15%) ·
  EXCESS_CONSUMPTION (2–10%) · COMFORT_ENERGY (1–5%) · PROTECTIVE (avoided repair).
- Confidence: HIGH (PNNL sim/field measured) · MEDIUM (literature) · LOW (judgment).
- Estimation methods: DIRECT_MEASUREMENT (live waste calc from points+capacities) ·
  BASELINE_COMPARISON (trained baseline, ≥14-day learning) · PROXY_ESTIMATION
  (PNNL coefficient × capacity × hours × climate factor) · QUALITATIVE_ONLY.
- Climate multipliers by ASHRAE zone (heating-dominant 0.3–2.0, cooling-dominant
  reversed, schedule faults 1.0).
- Site config for $ estimates: blended_elec_rate, gas_rate, equipment capacities,
  annual_operating_hours, climate_zone. Graceful degradation: $ → kWh → % of subsystem.
- Key study metrics: median 12% whole-building savings (151-bldg GSA study);
  "74% problem": SAT reset (EEM-05) + DSP reset (EEM-12) absent in 74% of buildings —
  desk-only fixes worth 2–7% of site energy (AHU-FC-057/058).

## Emissions framework (ch.5A)

Parallel accumulator: waste_kgco2e = waste_kwh × emission_factor(t). Scope 1 (on-site
combustion, static factors: NG 0.181 kgCO2e/kWh) vs Scope 2 (grid, time-varying MOER
preferred for impact, AOER for reporting). Mirrors energy confidence; never invents its
own severity. Fallback chain: real-time MOER → cached → eGRID annual → national avg.

## Complete fault index (§5.8)

### AHU (ch.9)
| Code | Name | Category | Method |
|---|---|---|---|
| AHU-FC-001 | DSP too low, full fan speed | PROTECTIVE | QUAL |
| AHU-FC-002 | MAT too low | COMFORT_ENERGY | QUAL |
| AHU-FC-003 | MAT too high | COMFORT_ENERGY | QUAL |
| AHU-FC-004 | Excessive OS changes | COMFORT_ENERGY | QUAL |
| AHU-FC-005 | SAT too low vs MAT (htg) | EXCESS_CONSUMP | PROXY |
| AHU-FC-006 | OA fraction deviation | EXCESS_CONSUMP | DIRECT |
| AHU-FC-007 | SAT too low, full htg | EXCESS_CONSUMP | PROXY |
| AHU-FC-008 | SAT ≠ MAT in econ | COMFORT_ENERGY | QUAL |
| AHU-FC-009 | OAT too high for free clg | COMFORT_ENERGY | QUAL |
| AHU-FC-010 | OAT ≠ MAT mech+econ | COMFORT_ENERGY | QUAL |
| AHU-FC-011 | OAT too low for mech clg | COMFORT_ENERGY | QUAL |
| AHU-FC-012 | SAT too high vs MAT (clg) | EXCESS_CONSUMP | PROXY |
| AHU-FC-013 | SAT too high, full clg | EXCESS_CONSUMP | PROXY |
| AHU-FC-014 | Inactive CC temp drop | CRITICAL_WASTE | DIRECT |
| AHU-FC-015 | Inactive HC temp rise | CRITICAL_WASTE | DIRECT |
| AHU-FC-050 | Simultaneous H&C | CRITICAL_WASTE | DIRECT |
| AHU-FC-051 | Econ not operational | CRITICAL_WASTE | DIRECT |
| AHU-FC-052 | Unoccupied override | CRITICAL_WASTE | DIRECT |
| AHU-FC-053 | SAT SP too low | EXCESS_CONSUMP | PROXY |
| AHU-FC-054 | Stuck actuator | CRITICAL_WASTE | PROXY |
| AHU-FC-055 | Excess OA occupied | EXCESS_CONSUMP | DIRECT |
| AHU-FC-056 | SAT hunting | COMFORT_ENERGY | QUAL |
| AHU-FC-057 | SAT reset missing | EXCESS_CONSUMP | PROXY |
| AHU-FC-058 | DSP reset missing | EXCESS_CONSUMP | PROXY |
| AHU-FC-059 | H/C lockout not active | CRITICAL_WASTE | DIRECT |
| AHU-FC-060 | OA dmpr not closed unocc | CRITICAL_WASTE | DIRECT |
| AHU-FC-061 | Manual override | EXCESS_CONSUMP | QUAL |
| AHU-FC-062 | Mixing box dmpr fault | COMFORT_ENERGY | QUAL |
| AHU-FC-063 | Operating mode mismatch | CRITICAL_WASTE | PROXY |
| AHU-FC-064 | Excess OA during htg | EXCESS_CONSUMP | DIRECT |
| AHU-FC-065 | Fan at excess SP | EXCESS_CONSUMP | PROXY |

(Note: index lists codes through 065; chapter header says "20 fully specified" —
G36 001–015 + research 050–065.)

### VAV (ch.10)
VAV-FC-050 min airflow SP too high · 051 rogue zone driving reset · 052 reheat vlv
open zone OK · 053 airflow tracking error · 054 damper hunting · 055 reheat waste
in cooling season

### RTU (ch.11)
RTU-FC-050 compressor short-cycling · 051 evap coil fouling · 052 SAT/MAT
inconsistency · 053 econ not modulating · 054 excess OA · 055 insufficient
ventilation · 100 condenser airflow restriction

### HP (ch.11)
HP-FC-050 COP degradation · 051 defrost cycle anomaly · 052 reversing valve fault

### FCU (ch.12)
FCU-FC-001 excessive OS changes · 002 SAT too low full htg · 003 SAT too high full
clg · 004 inactive CC temp drop · 005 inactive HC temp rise

### CHW plant (ch.13)
CHW-FC-050 chiller kW/ton degradation · 051 CHWST reset missing · 052 CHW DP reset
missing · 053 low delta-T syndrome

### HW plant (ch.14)
HW-FC-050 boiler short-cycling · 051 boiler efficiency degradation · 052 boiler/pump
OAT lockout

### ERV / PMP / VFD (ch.15)
ERV-FC-050 effectiveness degradation · 051 frost protection not engaged ·
PMP-FC-050 pump on no flow · 051 deadheading · VFD-FC-050 cmd vs feedback
deviation · 051 at min speed unsatisfied

### SYS / META (ch.16)
SYS-FC-050 CHW flow no clg demand · 051 HW flow no htg demand · 052 lighting on no
occupancy · 053 exhaust fan running unocc · 054 sensor drift cross-validation ·
055 virtual sensor drift · 056 zone summer htg lockout · 057 exhaust fan schedule
misalignment · META-FC-050 model confidence degradation

## Fault clusters (ch.7) — syndromes with a shared root cause

| ID | Cluster | Trigger rule | Prevalence |
|---|---|---|---|
| CLU-01 | Simultaneous H&C | AHU-FC-050 | Common |
| CLU-02 | Missing reset strategy | AHU-FC-057/058 | 74% of buildings |
| CLU-03 | Economizer failure | AHU-FC-051 | 54% of RTUs |
| CLU-04 | After-hours operation | AHU-FC-052 | ~15% |
| CLU-05 | Zone H/C conflict | VAV-FC-055 | Common |
| CLU-06 | CHW plant inefficiency | CHW-FC-050 | — |
| CLU-07 | Unnecessary plant operation | SYS-FC-050/051 | — |
| CLU-08 | Schedule dysfunction | AHU-FC-052 | ~15% |
| CLU-09 | Sensor integrity failure | AHU-FC-062 | ~15% |

Fix the trigger rule first; members should clear within 24–48h.

## Remediation (ch.8)

Remote-fix ($0, address first — 60–80% of retro-cx savings per PNNL-27338):
AHU-FC-052 (fix schedule/overrides), 057 (program SAT reset), 058 (program DSP reset),
059 (enable OAT lockout), 060 (close OA damper unocc), 061 (release overrides),
HW-FC-052 (boiler OAT lockout), VAV-FC-050/055 (reduce minimums, seasonal reheat lockout).

Prioritization: remote fixes → clusters (CLU-02, CLU-03 first) → rank by energy impact →
batch on-site work by location → re-evaluate after each round.

## Example fault cards (transcribed for format grounding)

### AHU-FC-001 — DSP too low at full fan speed (G36 §5.16.14 FC#1)
- Logic: `dsp < (dsp_sp − ε_dsp) AND sf_speed ≥ 99%`
- Points: dsp, dsp_sp, sf_speed · Params: ε_dsp=25 Pa, AlarmDelay=30 min
- States: OS 1–5 · Precondition: supply fan running
- Test vectors: (350,375,60%)→NO_FAULT · (370,375,100%)→NO_FAULT · (300,375,100%)→FAULT

### AHU-FC-002/003 — MAT too low/high (G36 FC#2/FC#3)
- Logic: `MAT < min(OAT, RAT) − ε_MAT` / `MAT > max(OAT, RAT) + ε_MAT`; ε_MAT=2°C.
- **Deliberate simplification** vs G36's per-sensor error bands (documented deviation;
  more conservative, less sensitive to individual sensor drift).

### AHU-FC-050 — Simultaneous heating and cooling (PNNL-27338)
- Logic: `htg_vlv_cmd > 5% AND clg_vlv_cmd > 5%`, AlarmDelay 15 min
- Waste: `htg_vlv_cmd/100 × ahu_htg_capacity_kw + clg_vlv_cmd/100 × ahu_clg_capacity_kw`
- Severity 2, CRITICAL_WASTE, HIGH conf, DIRECT.

### AHU-FC-051 — Economizer not operational when favorable
- Logic: `econ_favorable(OAT,RAT,econ_type,econ_hl_temp) AND clg_vlv_cmd > 10%
  AND oa_dmpr_cmd < 25%`; DDB: `(RAT−OAT) > 1°C`; HL_DB: `(econ_hl_temp−OAT) > 1°C`
- OS 4 only · Precondition: fan running, |OAT−RAT| ≥ TMIN.

### AHU-FC-052 — Unoccupied override
- Logic: `sf_status=ON AND NOT in_occupied_schedule(t) AND NOT override_active`;
  grace_period 30 min · Waste: `ahu_fan_design_kw × (sf_speed/100)³ + active H/C`.

### AHU-FC-053 — SAT setpoint too low (over-cooling)
- Logic: `sat_sp < 12°C AND num_zones_reheating/total_zones > 50%` — note this
  needs zone-array aggregation (rht_vlv_cmd_all), a cross-equipment input.

## Not yet read (pages 64–178)

Remaining fault cards (AHU 054–065 details, VAV/RTU/HP/FCU/CHW/HW/ERV/PMP/VFD/SYS/META
chapters), full playbooks (pp.153–175), references (pp.176–178). Read on demand when
authoring each equipment family.
