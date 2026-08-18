# FCU Fault Rules

Fan coil unit fault detection rules (`FCU-FC-*`). Source grounding: HVAC FDD
Reference v1.0 ch.12 and ASHRAE Guideline 36 §5.22.6 for the 001-range (the
FCU analog of the AHU §5.16.14 set). FCUs are two-coil air handlers in
miniature, distributed by the dozens; faults persist because nobody is
watching any single unit.

Point dictionary: [`points/fcu.points.json`](../../points/fcu.points.json).

## Index

| ID | Name | Sev | Method | Status |
|---|---|---|---|---|
| FCU-FC-001 | Excessive operating state changes | 3 | rule | **verified** |
| FCU-FC-002 | SAT too low in full heating | 3 | rule | **verified** |
| FCU-FC-003 | SAT too high in full cooling | 3 | rule | **verified** |
| FCU-FC-004 | Inactive cooling coil temperature drop (leak) | 3 | rule | **verified** |
| FCU-FC-005 | Inactive heating coil temperature rise (leak) | 3 | rule | **verified** |

Severity and method per the reference's ch.12 cards (its §5.8.5 index carries
no severity column). Every rule here is a sibling of a verified AHU pattern:
FC-001 mirrors AHU-FC-004's rolling transition counter, FC-002/003 mirror the
AHU-FC-007/013 saturated-coil pair, FC-004/005 mirror the AHU-FC-014/015
inactive-coil signatures with rat/sat as the entering/leaving proxies.

## Relationships

- FCU-FC-001..005 share the fcu-faults playbook.
- FC-004/005 are the zone-scale members of the simultaneous-conditioning
  family (AHU-FC-050's world): a leaking valve conditions air nobody asked
  to condition.
