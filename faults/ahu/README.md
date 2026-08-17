# AHU Fault Rules

Air handling unit fault detection rules (`AHU-FC-*`). Source grounding: HVAC
FDD Reference v1.0 ch.9 (adapted authority — see each card's Deviations
section) and ASHRAE Guideline 36-2021 §5.16.14 for the 001-range.

Point dictionary: [`points/ahu.points.json`](../../points/ahu.points.json).

## Index

| ID | Name | Sev | Method | Status |
|---|---|---|---|---|
| AHU-FC-001 | Duct static pressure too low at full fan speed | 3 | rule | **verified** |
| AHU-FC-002 | Mixed air temperature too low | 3 | rule | **verified** |
| AHU-FC-003 | Mixed air temperature too high | 3 | rule | **verified** |
| AHU-FC-004 | Excessive operating state changes per hour | 3 | rule | **verified** |
| AHU-FC-005 | SAT too low vs MAT in heating | 3 | rule | planned |
| AHU-FC-006 | OA fraction deviation | 3 | rule | planned |
| AHU-FC-007 | SAT too low at full heating | 3 | rule | planned |
| AHU-FC-008 | SAT ≠ MAT in economizer mode | 3 | rule | planned |
| AHU-FC-009 | OAT too high for free cooling | 3 | rule | planned |
| AHU-FC-010 | OAT ≠ MAT in mech + econ cooling | 3 | rule | planned |
| AHU-FC-011 | OAT too low for mechanical cooling | 3 | rule | planned |
| AHU-FC-012 | SAT too high vs MAT in cooling | 3 | rule | planned |
| AHU-FC-013 | SAT too high at full cooling | 3 | rule | planned |
| AHU-FC-014 | Inactive cooling coil temperature drop | 2 | rule | planned |
| AHU-FC-015 | Inactive heating coil temperature rise | 2 | rule | planned |
| AHU-FC-050 | Simultaneous heating and cooling | 2 | rule | **verified** |
| AHU-FC-051 | Economizer not operational when favorable | 3 | rule | **verified** |
| AHU-FC-052 | Unoccupied override — running during off-hours | 3 | rule | **verified** |
| AHU-FC-053 | SAT setpoint too low (over-cooling) | 3 | rule | **verified** |
| AHU-FC-054 | Stuck actuator | 2 | rule | **verified** |
| AHU-FC-055 | Excess outdoor air while occupied | 3 | rule | **verified** |
| AHU-FC-056 | SAT hunting | 3 | statistical | **verified** |
| AHU-FC-057 | SAT reset missing | 3 | statistical | **verified** |
| AHU-FC-058 | DSP reset missing | 3 | statistical | **verified** |
| AHU-FC-059 | Heating/cooling lockout not active | 3 | rule | **verified** |
| AHU-FC-060 | OA damper not closed when unoccupied | 3 | rule | **verified** |
| AHU-FC-061 | Manual override active | 4 | rule | **verified** |
| AHU-FC-062 | Mixing box damper fault | 3 | rule | **verified** |
| AHU-FC-063 | Operating mode mismatch | 3 | rule | **verified** |
| AHU-FC-064 | Excess OA during heating | 3 | rule | **verified** |
| AHU-FC-065 | Fan at excess static pressure | 3 | rule | **verified** |

Reference note: the FDD Reference's index (§5.8.1) lists 31 AHU codes while its
ch.9 header claims "20 fully specified" — some 0xx cards in the reference are
abbreviated. Our library treats every code above as in scope; severities shown
are the reference's and may be adjusted per card (recorded under Deviations).

## Working order (first pass)

1. **AHU-FC-050** — highest-impact fault, simplest logic; proves the schema.
2. AHU-FC-052, 057, 058 — the remote-fix "74% problem" cluster (CLU-02/04).
3. AHU-FC-051 — economizer (CLU-03).
4. AHU-FC-001…015 — the G36 001-range.
5. Remaining 05x/06x research rules.
