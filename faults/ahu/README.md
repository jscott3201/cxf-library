# AHU Fault Rules

Air handling unit fault detection rules (`AHU-*`). Source grounding: HVAC
FDD Reference v1.0 ch.9 (adapted authority — see each card's Deviations
section) and ASHRAE Guideline 36-2021 §5.16.14 for the 001-range.
AHU-0032–068 are **library-authored extensions** past the reference's
ch.9 range (which ends at 065), grounded in Bushby, Castro, Schein &
House (2001), NIST/CEC PIER Project 2.3 — the original APAR rule set —
with AHU-0034 additionally corroborated by PNNL-27338 §3.4 (HW-0004
extension precedent: explicit non-reference sourcing on each card).

Point dictionary: [`points/ahu.points.json`](../../points/ahu.points.json).

## Index

| ID | Name | Sev | Method | Status |
|---|---|---|---|---|
| AHU-0001 | Duct static pressure too low at full fan speed | 3 | rule | **verified** |
| AHU-0002 | Mixed air temperature too low | 3 | rule | **verified** |
| AHU-0003 | Mixed air temperature too high | 3 | rule | **verified** |
| AHU-0004 | Excessive operating state changes per hour | 3 | rule | **verified** |
| AHU-0005 | SAT too low vs MAT in heating | 3 | rule | **verified** |
| AHU-0006 | OA fraction deviation | 3 | rule | **verified** |
| AHU-0007 | SAT too low at full heating | 3 | rule | **verified** |
| AHU-0008 | SAT ≠ MAT in economizer mode | 3 | rule | **verified** |
| AHU-0009 | OAT too high for free cooling | 3 | rule | **verified** |
| AHU-0010 | OAT ≠ MAT in mech + econ cooling | 3 | rule | **verified** |
| AHU-0011 | OAT too low for mechanical cooling | 3 | rule | **verified** |
| AHU-0012 | SAT too high vs MAT in cooling | 3 | rule | **verified** |
| AHU-0013 | SAT too high at full cooling | 3 | rule | **verified** |
| AHU-0014 | Inactive cooling coil temperature drop | 2 | rule | **verified** |
| AHU-0015 | Inactive heating coil temperature rise | 2 | rule | **verified** |
| AHU-0016 | Simultaneous heating and cooling | 2 | rule | **verified** |
| AHU-0017 | Economizer not operational when favorable | 3 | rule | **verified** |
| AHU-0018 | Unoccupied override — running during off-hours | 3 | rule | **verified** |
| AHU-0019 | SAT setpoint too low (over-cooling) | 3 | rule | **verified** |
| AHU-0020 | Stuck actuator | 2 | rule | **verified** |
| AHU-0021 | Excess outdoor air while occupied | 3 | rule | **verified** |
| AHU-0022 | SAT hunting | 3 | statistical | **verified** |
| AHU-0023 | SAT reset missing | 3 | statistical | **verified** |
| AHU-0024 | DSP reset missing | 3 | statistical | **verified** |
| AHU-0025 | Heating/cooling lockout not active | 3 | rule | **verified** |
| AHU-0026 | OA damper not closed when unoccupied | 3 | rule | **verified** |
| AHU-0027 | Manual override active | 4 | rule | **verified** |
| AHU-0028 | Mixing box damper fault | 3 | rule | **verified** |
| AHU-0029 | Operating mode mismatch | 3 | rule | **verified** |
| AHU-0030 | Excess OA during heating | 3 | rule | **verified** |
| AHU-0031 | Fan at excess static pressure | 3 | rule | **verified** |
| AHU-0032 | SAT too high vs RAT in cooling | 3 | rule | **verified** |
| AHU-0033 | SAT tracking error (ungated, all occupied modes) | 3 | rule | **verified** |
| AHU-0034 | Economizing past changeover | 3 | rule | **verified** |
| AHU-0035 | Supply air temperature too high for the zone population | 3 | rule | **verified** |
| AHU-0036 | Duct static pressure too low for the zone population | 3 | rule | **verified** |
| AHU-0037 | Economizing when it should not (damper position) | 3 | rule | **verified** |
| AHU-0038 | Cooling coil valve-position creep (fouling / authority loss) | 3 | statistical | **verified** |

Reference note: the FDD Reference's index (§5.8.1) lists 31 AHU codes while its
ch.9 header claims "20 fully specified" — some 0xx cards in the reference are
abbreviated. Our library treats every code above as in scope; severities shown
are the reference's and may be adjusted per card (recorded under Deviations).

## Working order (first pass)

1. **AHU-0016** — highest-impact fault, simplest logic; proves the schema.
2. AHU-0018, 057, 058 — the remote-fix "74% problem" cluster (CLU-02/04).
3. AHU-0017 — economizer (CLU-03).
4. AHU-0001…015 — the G36 001-range.
5. Remaining 05x/06x research rules.
