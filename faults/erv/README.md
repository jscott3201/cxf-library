# ERV Fault Rules

Energy recovery ventilator fault detection rules (`ERV-*`). Source
grounding: HVAC FDD Reference v1.0 ch.15 (Energy Recovery — adapted
authority; see each card's Deviations section) plus clearly labeled
library-authored operating, proof, and airflow-balance extensions.

Point dictionary: [`points/erv.points.json`](../../points/erv.points.json).

## Index

| ID | Name | Sev | Method | Status |
|---|---|---|---|---|
| ERV-0001 | Sensible effectiveness degradation | 3 | statistical | **verified** |
| ERV-0002 | Frost protection not engaging | 2 | rule | **verified** |
| ERV-0003 | Frost protection active above release conditions | 3 | rule | **verified** |
| ERV-0004 | Recovery device proof-of-operation failure | 2 | rule | **verified** |
| ERV-0005 | Supply/exhaust airflow imbalance | 3 | rule | **verified** |

ERV-0001/0002 adapt the reference chapter. ERV-0003..0005 are library-authored:
the cards classify every threshold and name their reusable graph precedents.

## Applicability and point availability

- **Passive plate cores:** ERV-0001, ERV-0002/0003 where a frost-state point
  exists, and ERV-0005 where both device-local flow measurements exist.
  ERV-0004 is not applicable because the core has no commanded active device.
- **Rotary wheels:** all five rules may apply. ERV-0004 needs a final wheel-run
  command and independent rotation/speed proof; command echo is not proof.
- **Runaround loops:** all five rules may apply where a frost sequence/state
  exists and temperatures/flows map to both air streams. ERV-0004 binds the
  loop pump's final command and independent pump work/rotation proof.
- **Point scarcity:** enabled/frost flags and three temperatures do not imply
  command/status proof or two comparable airflow measurements. Omit a rule
  rather than substitute a high-level enable or an unrelated AHU flow meter.

## Relationships

- All rules share the `erv-effectiveness` investigation order. ERV-0004 also
  uses `proof-of-operation` for command/status diagnosis.
- ERV-0003 relates to both existing frost/effectiveness rules but suppresses
  neither: excessive frost protection can be the real cause of lost recovery.
- ERV-0005's direction flags identify the air path to inspect; `yFlowOk=false`
  means NO_EVAL, not balanced operation.
