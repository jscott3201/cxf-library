# RTU Fault Rules

Packaged rooftop unit fault detection rules (`RTU-FC-*`). Source grounding:
HVAC FDD Reference v1.0 ch.11 (adapted authority — see each card's Deviations
section). RTUs are the most common commercial HVAC system type, and the
chapter's emphasis follows the field data: economizer problems affect 54% of
units (Cowan 2004), and compressor short-cycling and coil fouling dominate the
mechanical failures.

Point dictionary: [`points/rtu.points.json`](../../points/rtu.points.json).

## Index

| ID | Name | Sev | Method | Status |
|---|---|---|---|---|
| RTU-FC-050 | Compressor short-cycling | 2 | rule | **verified** |
| RTU-FC-051 | Evaporator coil fouling | 3 | statistical | **verified** |
| RTU-FC-052 | SAT/MAT inconsistency (AFDD0) | 3 | rule | **verified** |
| RTU-FC-053 | Economizer not modulating | 3 | rule | **verified** |
| RTU-FC-054 | Excess outdoor air | 3 | rule | **verified** |
| RTU-FC-055 | Insufficient ventilation | 2 | rule | **verified** |
| RTU-FC-100 | Condenser airflow restriction | 3 | statistical | deferred |

Severity and method per the reference's ch.11 cards (its §5.8.3 index carries
no severity column). RTU-FC-100 is deferred: its baseline is a function of two
variables (compressor stage AND outdoor temperature), which needs baseline-
curve infrastructure the block set does not yet express; it also requires a
condenser leaving-air temperature sensor most RTUs lack.

## Relationships

- **RTU-FC-052 is PNNL's AFDD0** — the sensor-consistency prerequisite for the
  chapter. While active it suppresses RTU-FC-051 and RTU-FC-053 (declared in
  its frontmatter).
- **RTU-FC-054/055** are the excess/deficit halves of the outdoor-air-fraction
  measurement; the reference gates both behind the AHU-FC-062 mixing-box
  envelope check, instantiated against the RTU's own mat/oat/rat points (the
  062 graph is equipment-agnostic).
- **RTU-FC-053** is a CLU-03 member (economizer failure, trigger AHU-FC-051's
  cluster) and shares the economizer-failure playbook.
