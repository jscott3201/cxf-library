# RTU Fault Rules

Packaged rooftop unit fault detection rules (`RTU-*`). Source grounding:
HVAC FDD Reference v1.0 ch.11 (adapted authority — see each card's Deviations
section). RTUs are the most common commercial HVAC system type, and the
chapter's emphasis follows the field data: economizer problems affect 54% of
units (Cowan 2004), and compressor short-cycling and coil fouling dominate the
mechanical failures.

Point dictionary: [`points/rtu.points.json`](../../points/rtu.points.json).

## Index

| ID | Name | Sev | Method | Status |
|---|---|---|---|---|
| RTU-0001 | Compressor short-cycling | 2 | rule | **verified** |
| RTU-0002 | Evaporator coil fouling | 3 | statistical | **verified** |
| RTU-0003 | SAT/MAT inconsistency (AFDD0) | 3 | rule | **verified** |
| RTU-0004 | Economizer not modulating | 3 | rule | **verified** |
| RTU-0005 | Excess outdoor air | 3 | rule | **verified** |
| RTU-0006 | Insufficient ventilation | 2 | rule | **verified** |
| RTU-0007 | Condenser airflow restriction | 3 | statistical | **verified** |
| RTU-0008 | Refrigerant undercharge — superheat/subcooling divergence | 3 | rule | **verified** |
| RTU-0009 | Refrigerant overcharge — high liquid subcooling | 3 | rule | **verified** |
| RTU-0010 | RTU supply-fan proof-of-operation failure | 2 | rule | **verified** |
| RTU-0011 | RTU supply-air temperature tracking failure | 3 | rule | **verified** |

Severity and method for RTU-0001..009 follow the reference's ch.11 cards (its
§5.8.3 index carries no severity column); RTU-0010 is a severity-2 library
proof-of-operation adaptation and RTU-0011 is a library tracking adaptation.
RTU-0007 shipped once the host-fitted-baseline
convention resolved its two-variable (stage AND outdoor temperature) curve
as the derived point `cond_split_baseline`; its remaining constraint is the
condenser leaving-air temperature sensor most packaged units lack, declared
on the card as a retrofit gate rather than a deferral.

## Relationships

- **RTU-0003 is PNNL's AFDD0** — the sensor-consistency prerequisite for the
  chapter. While active it suppresses RTU-0002 and RTU-0004 (declared in
  its frontmatter).
- **RTU-0005/RTU-0006** are the excess/deficit halves of the outdoor-air-fraction
  measurement; the reference gates both behind the AHU-0028 mixing-box
  envelope check, instantiated against the RTU's own mat/oat/rat points (the
  062 graph is equipment-agnostic).
- **RTU-0004** is a CLU-03 member (economizer failure, trigger AHU-0017's
  cluster) and shares the economizer-failure playbook.
- **RTU-0010** compares the final supply-fan command with independent proof.
  Read its direction before RTU-0001..006 and RTU-0008/0009: fail-to-start
  contests their running/airflow premise or evidence quality, while unexpected
  operation does not make their physical evidence invalid by itself.
- **RTU-0011** compares discharge temperature with the final active mode-specific
  target while fan and mechanical delivery are proven. Its warm/cold direction
  leads investigation across capacity, airflow, economizer, refrigerant, and
  control findings; proof rules remain related rather than unconditional suppressors.
