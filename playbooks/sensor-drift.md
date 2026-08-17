# Playbook: Sensor Drift / Calibration

| | |
|---|---|
| **Applies to** | SYS-FC-054, SYS-FC-055, AHU-FC-002, AHU-FC-003, AHU-FC-008, AHU-FC-010, AHU-FC-062, RTU-FC-052, CLU-09 |
| **Fix complexity** | On-site service required |
| **Typical time** | 1–2 h per sensor |
| **Typical cost** | $50–$200 per sensor (recalibrate or replace) |
| **Energy impact** | EEM-01: 0–5% site energy from sensor recalibration; ~15% prevalence. The direct energy impact of one drifted sensor is small, but the cascade is not — a single biased OAT sensor can disable the economizer (0–7% waste), trigger false alarms across multiple rules, and mask real faults. |

Adapted from HVAC FDD Reference v1.0, Remediation Playbooks (pp. 165–166).

## Step 1 — Verify the fault

1. Compare the suspect sensor to a portable reference instrument:
   temperature → NIST-traceable digital thermometer; pressure → calibrated
   manometer; CO₂ → fresh-air baseline (outdoor CO₂ ≈ 420 ppm); humidity →
   sling psychrometer or calibrated RH probe (humidity sensors are the most
   drift-prone, typical lifespan 1–2 years between recalibrations).
2. If the FDD system's virtual sensor model (SYS-FC-055) shows bias greater
   than 1.5 °C, drift is confirmed (virtual sensors demonstrate RMSE ≈
   0.30 °C — Koo & Yoon 2022 — so 1.5 °C is well outside normal error).
3. A drifted sensor may be triggering false alarms on other rules: if
   multiple faults fire on the same equipment, this sensor may be the root
   cause (the CLU-09 suppression rationale).

## Step 2 — Remote fix (temporary)

1. Apply a sensor offset / calibration correction in the BAS to compensate;
   document the offset value and date. This is a stopgap — the physical
   sensor still needs service.
2. If the drifted sensor is an OAT sensor disabling the economizer, the
   offset provides immediate energy savings while waiting for on-site work.

## Step 3 — On-site service

1. Recalibrate per the manufacturer's procedure.
2. If the sensor cannot hold calibration, replace it: temperature $30–$80;
   pressure transducers $80–$200; humidity $50–$150 (most frequent);
   CO₂ $100–$300 (calibrate with a known gas standard or fresh outdoor air).
3. Verify the reading against the reference instrument before leaving.
4. For paired installations (SYS-FC-054 cross-validation), recalibrate both
   sensors in the pair.

## Step 4 — Confirm resolution

1. The sensor drift fault should clear within 1–2 evaluation windows.
2. Downstream false alarms caused by the drifted sensor should also clear.
3. If the Sensor Integrity cluster (CLU-09) was active, the entire cluster
   should resolve.
