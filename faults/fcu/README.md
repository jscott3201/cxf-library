# FCU Fault Rules

Fan coil unit fault detection rules (`FCU-*`). Source grounding: HVAC FDD
Reference v1.0 ch.12 and ASHRAE Guideline 36 §5.22.6 for the 001-range (the
FCU analog of the AHU §5.16.14 set). FCUs are two-coil air handlers in
miniature, distributed by the dozens; faults persist because nobody is
watching any single unit.

Point dictionary: [`points/fcu.points.json`](../../points/fcu.points.json).

## Index

| ID | Name | Sev | Method | Status |
|---|---|---|---|---|
| FCU-0001 | Excessive operating state changes | 3 | rule | **verified** |
| FCU-0002 | SAT too low in full heating | 3 | rule | **verified** |
| FCU-0003 | SAT too high in full cooling | 3 | rule | **verified** |
| FCU-0004 | Inactive cooling coil temperature drop (leak) | 3 | rule | **verified** |
| FCU-0005 | Inactive heating coil temperature rise (leak) | 3 | rule | **verified** |
| FCU-0006 | FCU fan proof-of-operation failure | 2 | rule | **verified** |
| FCU-0007 | Simultaneous heating and cooling commands | 2 | rule | **verified** |

Severity and method for FCU-0001..005 follow the reference's ch.12 cards (its
§5.8.5 index carries no severity column); FCU-0006 is a severity-2 library
proof-of-operation adaptation and FCU-0007 is the command-level FCU adaptation
of the simultaneous-conditioning signature. The first five rules are siblings
of verified AHU patterns:
FC-001 mirrors AHU-0004's rolling transition counter, FC-002/003 mirror the
AHU-0007/AHU-0013 saturated-coil pair, FC-004/005 mirror the AHU-0014/AHU-0015
inactive-coil signatures with rat/sat as the entering/leaving proxies.

## Relationships

- FCU-0001..007 share the fcu-faults playbook.
- FCU-0006 compares the final fan command with independent proof. Its
  fail-to-start direction contests the airflow premise of FCU-0002..005; the
  unexpected-run direction can leave those temperature signatures meaningful,
  so the relationship is informational rather than a whole-rule suppression.
- Passive/convection terminal units do not instantiate FCU-0006.
- FCU-0007 detects a control-command conflict; FCU-0004/0005 detect thermal
  evidence while the corresponding command is closed. They are related and do
  not suppress one another. Intentional cooling-plus-reheat is host-excluded.
- FCU-0007 shares the simultaneous-hc workflow but remains outside CLU-01:
  the cluster's AHU-0016 trigger cannot causally clear a local FCU conflict.
- FC-004/005 are the zone-scale members of the simultaneous-conditioning
  family (AHU-0016's world): a leaking valve conditions air nobody asked
  to condition.
